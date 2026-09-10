"""
Hercules — AI-Orchestrated Kali MCP Server for Offensive Security.

Entry point. Uses composable FastMCP lifespans to separate Docker
container management from concurrency control. Registers all tool
modules and post-exploitation resources.
"""

from __future__ import annotations

import argparse
import asyncio
import importlib
import json
import logging
import logging.handlers
import sys
import uuid
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.server.lifespan import lifespan

from hercules.core.concurrency import ConcurrencyManager
from hercules.core.config import HerculesConfig
from hercules.core.docker_manager import DockerManager
from hercules.core.firewall import ParameterFilterMiddleware, ToolExceptionFirewall
from hercules.core.guidance import SERVER_INSTRUCTIONS
from hercules.core.tool_catalog import (
    CORE_TOOLS,
    METASPLOIT_TOOLS,
    TOOL_REGISTRARS,
    all_tool_names,
)

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


# ---------------------------------------------------------------------------
# Composable lifespans
# ---------------------------------------------------------------------------

@lifespan
async def docker_lifespan(server):
    """Manage the Kali Docker container lifecycle."""
    config = HerculesConfig.from_env()
    docker_mgr = DockerManager(
        config,
        instance_id=uuid.uuid4().hex,
    )

    # Durable, host-side, session-tagged log for post-mortem of mid-session crashes.
    _add_file_logging(config.resolved_workspace_root, docker_mgr.session_id)

    logger.info("=== Hercules starting ===")
    logger.info("Session ID: %s", docker_mgr.session_id)
    logger.info("Skip Metasploit: %s", config.skip_metasploit)
    logger.info("Preserve container: %s", config.preserve_container)

    msf_state = {"client": None}
    lifespan_context = {
        "docker": docker_mgr,
        "config": config,
        "msf_state": msf_state,
    }
    from hercules.tools.browser.browser_tool import reset_browser_runtime_state
    from hercules.tools.exploitation.metasploit_tool import (
        reset_metasploit_runtime_state,
    )

    def reset_generation_state(_generation: int) -> None:
        reset_browser_runtime_state()
        reset_metasploit_runtime_state()
        msf_state["client"] = None
        set_log_session_id(docker_mgr.session_id)

    docker_mgr.register_generation_callback(reset_generation_state)

    watchdog_task = None
    if getattr(config, "watchdog_interval", 0) and config.watchdog_interval > 0:
        watchdog_task = asyncio.create_task(
            _watchdog(docker_mgr, config.watchdog_interval)
        )
        logger.info(
            "Watchdog enabled: health check every %ds after explicit startup.",
            config.watchdog_interval,
        )

    try:
        yield lifespan_context
    finally:
        # Signal teardown so the watchdog/recovery never resurrects a
        # container we are deliberately removing.
        docker_mgr.begin_shutdown()
        if watchdog_task is not None and not watchdog_task.done():
            watchdog_task.cancel()
            try:
                await watchdog_task
            except asyncio.CancelledError:
                pass
        logger.info("=== Hercules shutting down ===")
        try:
            await docker_mgr.stop_container(release_workspace=True)
        finally:
            docker_mgr.cleanup_unused_workspace()


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

# Expose the confirmed capability profile minus independently hidden tools.
# FastMCP visibility hides both schemas and calls; core tools remain fixed.
config = HerculesConfig.from_env()
_hidden_tools = (set(config.disabled_tools) & set(all_tool_names())) - CORE_TOOLS
if config.skip_metasploit:
    _hidden_tools -= METASPLOIT_TOOLS

for registrar in TOOL_REGISTRARS:
    if registrar.metasploit and config.skip_metasploit:
        logger.info(
            "SKIP_METASPLOIT=true: Metasploit tools will not be registered."
        )
        continue
    module_name, function_name = registrar.path.split(":", 1)
    module = importlib.import_module(module_name)
    register = getattr(module, function_name)
    register(mcp)

if _hidden_tools:
    mcp.disable(names=_hidden_tools, components={"tool"})
    logger.info(
        "Uninstalled or operator-hidden tools (not exposed): %s",
        ", ".join(sorted(_hidden_tools)),
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
        "unavailable_or_hidden_tools": sorted(_hidden_tools),
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
    mcp.run(show_banner=False)


if __name__ == "__main__":
    main()
