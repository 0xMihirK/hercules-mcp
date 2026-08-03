"""
Hercules — AI-Orchestrated Kali MCP Server for Offensive Security.

Entry point. Uses composable FastMCP lifespans to separate Docker
container management from concurrency control. Registers all tool
modules and post-exploitation resources.
"""

from __future__ import annotations

import asyncio
import importlib
import argparse
import json
import logging
import logging.handlers
import sys
from datetime import UTC, datetime
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.server.lifespan import lifespan

from hercules.core.concurrency import ConcurrencyManager
from hercules.core.config import HerculesConfig
from hercules.core.docker_manager import DockerManager
from hercules.core.firewall import ParameterFilterMiddleware, ToolExceptionFirewall
from hercules.core.guidance import SERVER_INSTRUCTIONS
from hercules.core.instance_lock import HerculesInstanceLock, InstanceLockError
from hercules.core.runtime import RuntimeServices
from hercules.core.security import redact_secrets
from hercules.core.tool_catalog import CORE_TOOLS, TOOL_REGISTRARS

# Resource registrations
from hercules.resources.agent_skills import register_agent_skill_resources
from hercules.resources.post_exploitation import register_post_exploitation_resources

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

# Mutable holder so the session_id in log lines tracks the active session. It
# changes only on a deliberate rotation (system_start_new_session), not on
# recovery (recovery preserves the session id).
_LOG_SESSION = {"id": "-"}


def set_log_session_id(session_id: str) -> None:
    """Update the session tag injected into subsequent log records."""
    _LOG_SESSION["id"] = session_id

_LOG_FORMAT = "%(asctime)s [%(session_id)s] [%(name)s] %(levelname)s: %(message)s"
_LOG_DATEFMT = "%Y-%m-%d %H:%M:%S"


class _SessionFilter(logging.Filter):
    """Inject the active session id into every record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.session_id = _LOG_SESSION["id"]
        return True


def _configure_stderr_logging() -> None:
    """Attach the stderr handler (idempotent). Logs always go to stderr so they
    never corrupt the stdio MCP transport on stdout."""
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    for h in root.handlers:
        if getattr(h, "_hercules_stderr", False):
            return
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT, _LOG_DATEFMT))
    handler.addFilter(_SessionFilter())
    handler._hercules_stderr = True  # type: ignore[attr-defined]
    root.addHandler(handler)


def _add_file_logging(workspace_root: Path, session_id: str) -> None:
    """Attach a rotating file handler on the HOST workspace (survives container
    kills) so a mid-session crash leaves a durable post-mortem log. Idempotent."""
    set_log_session_id(session_id)
    log_path = workspace_root / "hercules.log"
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        return
    root = logging.getLogger()
    target = str(log_path)
    for h in root.handlers:
        if getattr(h, "_hercules_file_path", "") == target:
            return  # already attached
    try:
        fh = logging.handlers.RotatingFileHandler(
            target, maxBytes=5_000_000, backupCount=3, encoding="utf-8"
        )
    except Exception:
        return
    fh.setFormatter(logging.Formatter(_LOG_FORMAT, _LOG_DATEFMT))
    fh.addFilter(_SessionFilter())
    fh._hercules_file_path = target  # type: ignore[attr-defined]
    root.addHandler(fh)


_configure_stderr_logging()
logger = logging.getLogger("hercules")


class _RegistrationFilter:
    """Thin proxy around the FastMCP server that lets the operator opt out of
    individual installed MCP tools (set via ``HERCULES_DISABLED_TOOLS``).

    A disabled tool simply isn't registered, so its name/description/schema never
    enters the model's context — that is the token saving. The binary is still in
    the image, so the agent can fall back to ``shell_exec``. Core tools are never
    skippable (``shell_exec`` itself is the fallback path). Every non-``tool``
    attribute access is forwarded to the real server unchanged, so middleware,
    resources, and the request-handler patch below all see the genuine FastMCP.
    """

    def __init__(self, mcp, disabled: frozenset[str] | set[str]):
        self._mcp = mcp
        self._disabled = {d for d in disabled if d not in CORE_TOOLS}
        self.skipped: list[str] = []

    def tool(self, *args, **kwargs):
        real_decorator = self._mcp.tool(*args, **kwargs)

        def decorator(fn):
            if getattr(fn, "__name__", "") in self._disabled:
                self.skipped.append(fn.__name__)
                return fn  # not registered → dropped from the tool surface
            return real_decorator(fn)

        return decorator

    def __getattr__(self, name):
        return getattr(self._mcp, name)


async def _watchdog(docker_mgr, interval: int) -> None:
    """
    Proactively detect a dead container and recover it BEFORE the next tool
    call, so recovery is transparent rather than lazy. Shares the recovery lock
    (via _recover_container) so it can never collide with a tool-triggered
    recovery — it just no-ops if the container is already healthy.
    """
    while True:
        try:
            await asyncio.sleep(interval)
            if await docker_mgr.health_ok():
                continue
            logger.warning("Watchdog: container unhealthy, proactively recovering.")
            await docker_mgr._recover_container("watchdog proactive recovery")
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("Watchdog recovery attempt failed: %s", exc)


async def _connect_metasploit_background(context: dict) -> None:
    """Connect to msfrpcd without blocking MCP initialization."""
    docker_mgr = context["docker"]
    state = context["msf_state"]
    state["status"] = "initializing"
    context["msf_status"] = "initializing"
    try:
        client = await docker_mgr.wait_for_msfrpcd()
        state["client"] = client
        context["msf_client"] = client
        state["status"] = "ready"
        context["msf_status"] = "ready"
        state["error"] = ""
        context["msf_error"] = ""
    except asyncio.CancelledError:
        state["status"] = "cancelled"
        context["msf_status"] = "cancelled"
        raise
    except Exception as exc:
        state["status"] = "unavailable"
        state["error"] = str(exc)
        context["msf_status"] = "unavailable"
        context["msf_error"] = str(exc)
        logger.warning("msfrpcd did not become ready: %s", exc)


def _runtime_timestamp() -> str:
    return datetime.now(UTC).isoformat()


async def _bootstrap_runtime(context: dict, services: RuntimeServices) -> None:
    """Initialize Docker after MCP schemas are available to the client."""
    docker_mgr = context["docker"]
    config = context["config"]
    runtime_state = services.runtime_state
    runtime_state.update(
        {
            "status": "starting",
            "started_at": _runtime_timestamp(),
            "completed_at": "",
            "error": "",
            "diagnostic": "",
        }
    )
    services.publish_runtime_state()
    try:
        await docker_mgr.start_container()
        await docker_mgr.ensure_ready()
    except asyncio.CancelledError:
        runtime_state.update(
            {
                "status": "cancelled",
                "completed_at": _runtime_timestamp(),
                "error": "Runtime initialization was cancelled during shutdown.",
                "diagnostic": "Runtime initialization was cancelled during shutdown.",
            }
        )
        services.publish_runtime_state()
        try:
            await docker_mgr.stop_container()
        except Exception as exc:
            logger.warning("Runtime cancellation cleanup failed: %s", exc)
        raise
    except BaseException as exc:
        safe_error = redact_secrets(
            str(exc),
            [
                getattr(config, "msf_password", ""),
                getattr(config, "browser_proxy_url", ""),
            ],
        )[:2000]
        docker_mgr.mark_startup_unavailable(safe_error)
        runtime_state.update(
            {
                "status": "unavailable",
                "completed_at": _runtime_timestamp(),
                "error": safe_error,
                "diagnostic": safe_error,
            }
        )
        services.publish_runtime_state()
        logger.error("Hercules runtime initialization failed: %s", safe_error)
        try:
            await docker_mgr.stop_container()
        except Exception as cleanup_error:
            logger.warning("Incomplete runtime cleanup failed: %s", cleanup_error)
        return

    runtime_state.update(
        {
            "status": "ready",
            "completed_at": _runtime_timestamp(),
            "error": "",
            "diagnostic": "",
            "reclaimed_containers": list(
                getattr(docker_mgr, "_reclaimed_containers", [])
            ),
        }
    )
    services.publish_runtime_state()
    logger.info("Workspace: %s", docker_mgr.workspace_path)

    if not config.skip_metasploit:
        task = asyncio.create_task(_connect_metasploit_background(context))
        context["msf_state"]["connect_task"] = task
        context["msf_connect_task"] = task

    if getattr(config, "watchdog_interval", 0) and config.watchdog_interval > 0:
        watchdog_task = asyncio.create_task(
            _watchdog(docker_mgr, config.watchdog_interval)
        )
        context["watchdog_task"] = watchdog_task
        logger.info(
            "Watchdog enabled: health check every %ds.",
            config.watchdog_interval,
        )


# ---------------------------------------------------------------------------
# Composable lifespans
# ---------------------------------------------------------------------------

@lifespan
async def docker_lifespan(server):
    """Manage the Kali Docker container lifecycle."""
    config = HerculesConfig.from_env()
    instance_lock = HerculesInstanceLock(config.project_root)
    try:
        instance_lock.acquire()
    except InstanceLockError as exc:
        logger.critical("%s", exc)
        raise SystemExit(str(exc)) from exc

    docker_mgr = DockerManager(
        config,
        instance_id=instance_lock.instance_id,
        owns_instance_lock=True,
    )

    # Durable, host-side, session-tagged log for post-mortem of mid-session crashes.
    _add_file_logging(config.resolved_workspace_root, docker_mgr.session_id)

    logger.info("=== Hercules starting ===")
    logger.info("Session ID: %s", docker_mgr.session_id)
    logger.info("Skip Metasploit: %s", config.skip_metasploit)
    logger.info("Preserve container: %s", config.preserve_container)

    msf_state = {
        "client": None,
        "connect_task": None,
        "status": "disabled" if config.skip_metasploit else "initializing",
        "error": "",
    }
    lifespan_context = {
        "docker": docker_mgr,
        "config": config,
        "msf_state": msf_state,
        "msf_client": None,
        "msf_connect_task": None,
        "msf_status": msf_state["status"],
        "msf_error": "",
        "runtime_state": {
            "status": "starting",
            "started_at": "",
            "completed_at": "",
            "error": "",
            "diagnostic": "",
        },
        "runtime_status": "starting",
        "runtime_error": "",
        "runtime_diagnostic": "",
    }
    services = RuntimeServices(
        config=config,
        docker=docker_mgr,
        workspace=docker_mgr.workspace_manager,
        msf_state=msf_state,
        runtime_state=lifespan_context["runtime_state"],
        legacy_context=lifespan_context,
    )
    from hercules.tools.browser.browser_tool import reset_browser_runtime_state
    from hercules.tools.exploitation.metasploit_tool import (
        reset_metasploit_runtime_state,
    )

    services.register_generation_resetter(reset_browser_runtime_state)
    services.register_generation_resetter(reset_metasploit_runtime_state)
    services.register_session_callback(set_log_session_id)
    docker_mgr.register_generation_callback(services.on_generation_change)
    lifespan_context["services"] = services
    startup_task = asyncio.create_task(
        _bootstrap_runtime(lifespan_context, services)
    )
    docker_mgr.attach_startup_task(startup_task)
    lifespan_context["runtime_startup_task"] = startup_task

    try:
        yield lifespan_context
    finally:
        try:
            # Signal teardown so the watchdog/recovery never resurrect a
            # container we are deliberately removing. Settle bootstrap first
            # so it cannot publish new watchdog/RPC tasks after we inspect them.
            docker_mgr.begin_shutdown()
            startup_task = lifespan_context.get("runtime_startup_task")
            if startup_task is not None and not startup_task.done():
                startup_task.cancel()
                try:
                    await startup_task
                except asyncio.CancelledError:
                    pass
            wtask = lifespan_context.get("watchdog_task")
            if wtask is not None and not wtask.done():
                wtask.cancel()
                try:
                    await wtask
                except asyncio.CancelledError:
                    pass
            task = lifespan_context.get("msf_connect_task")
            if task is not None and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            logger.info("=== Hercules shutting down ===")
            await docker_mgr.stop_container()
        finally:
            instance_lock.release()


@lifespan
async def concurrency_lifespan(server):
    """Initialize concurrency controls."""
    config = HerculesConfig.from_env()
    concurrency_mgr = ConcurrencyManager(
        max_heavy=config.max_concurrent_heavy,
        max_light=config.max_concurrent_light,
    )
    logger.info(
        "Concurrency limits: heavy=%d, light=%d",
        config.max_concurrent_heavy,
        config.max_concurrent_light,
    )
    yield {"concurrency": concurrency_mgr}


# ---------------------------------------------------------------------------
# FastMCP server — compose lifespans with | operator
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "Hercules MCP – Kali MCP Server",
    instructions=SERVER_INSTRUCTIONS,
    lifespan=docker_lifespan | concurrency_lifespan,
)

# Register tools installed in the confirmed capability profile, minus any
# independently hidden HERCULES_DISABLED_TOOLS entries. Core tools are fixed.
config = HerculesConfig.from_env()
_reg = _RegistrationFilter(mcp, config.disabled_tools)

for registrar in TOOL_REGISTRARS:
    if registrar.metasploit and config.skip_metasploit:
        logger.info(
            "SKIP_METASPLOIT=true: Metasploit tools will not be registered."
        )
        continue
    module_name, function_name = registrar.path.split(":", 1)
    module = importlib.import_module(module_name)
    register = getattr(module, function_name)
    register(_reg)

if _reg.skipped:
    logger.info(
        "Uninstalled or operator-hidden tools (not registered): %s",
        ", ".join(sorted(set(_reg.skipped))),
    )

# Register post-exploitation resources (resources are never opt-out-able).
register_agent_skill_resources(mcp)
register_post_exploitation_resources(mcp)

# ---------------------------------------------------------------------------
# Universal Tool Exception Firewall
# Converts any uncaught tool exception into a structured, agent-repairable
# ToolResult so a single tool failure can never crash or wedge the session.
# Complements the parameter interceptor above (different layer).
# ---------------------------------------------------------------------------
mcp.add_middleware(ParameterFilterMiddleware())
mcp.add_middleware(ToolExceptionFirewall())

logger.info("Hercules MCP server configured with the selected tools and resources.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def _mcp_surface_probe() -> dict[str, object]:
    """Inspect the installed FastMCP surface without entering its Docker lifespan."""
    tools = await mcp.list_tools(run_middleware=False)
    resources = await mcp.list_resources(run_middleware=False)
    return {
        "tools": len(tools),
        "resources": len(resources),
        "metasploit_enabled": not config.skip_metasploit,
        "installed_capabilities": sorted(config.installed_capabilities),
        "operator_disabled_tools": sorted(config.operator_disabled_tools),
        "unavailable_or_hidden_tools": sorted(set(_reg.skipped)),
    }


def main():
    """Run the MCP server or one explicitly selected read-only command."""
    arguments = sys.argv[1:]
    if arguments in (["-h"], ["--help"]):
        parser = argparse.ArgumentParser(
            prog="hercules",
            description=(
                "Hercules MCP server. With no arguments, starts the STDIO MCP "
                "transport; all argument modes are read-only."
            ),
        )
        parser.add_argument(
            "--setup-info-json",
            action="store_true",
            help="print deterministic setup facts as JSON",
        )
        parser.add_argument(
            "--validate-mcp-json",
            action="store_true",
            help="print the registered MCP surface as JSON",
        )
        parser.print_help()
        return
    if arguments and arguments[0] == "--setup-info-json":
        from hercules.core.setup_info import (
            SourceAssociationError,
            setup_information_from_argv,
        )

        remaining = arguments[1:]
        try:
            payload = setup_information_from_argv(config.project_root, remaining)
        except SourceAssociationError as exc:
            print(
                json.dumps(
                    {
                        "status": "error",
                        "code": "source_association_invalid",
                        "error": str(exc),
                    },
                    sort_keys=True,
                )
            )
            raise SystemExit(2) from exc
        except OSError as exc:
            print(
                json.dumps(
                    {
                        "status": "error",
                        "code": "setup_input_unavailable",
                        "error": f"A requested local setup input could not be read safely ({exc.__class__.__name__}).",
                    },
                    sort_keys=True,
                )
            )
            raise SystemExit(2) from exc
        except ValueError as exc:
            print(
                json.dumps(
                    {
                        "status": "error",
                        "code": "setup_input_invalid",
                        "error": str(exc),
                    },
                    sort_keys=True,
                )
            )
            raise SystemExit(2) from exc
        print(json.dumps(payload, indent=2, sort_keys=True))
        return
    if arguments == ["--validate-mcp-json"]:
        print(json.dumps(asyncio.run(_mcp_surface_probe()), sort_keys=True))
        return
    if arguments:
        print(
            f"hercules: unrecognized arguments: {' '.join(arguments)}\n"
            "Use 'hercules --help' for supported modes.",
            file=sys.stderr,
        )
        raise SystemExit(2)
    mcp.run()


if __name__ == "__main__":
    main()
