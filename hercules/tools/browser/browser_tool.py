"""
Stealth browser automation tools for Hercules MCP.

Combines two tools so the agent can drive a fingerprint-reduced Chromium:

  * cloakbrowser  — a fingerprint-patched stealth Chromium (compile-time C++
    patches: navigator.webdriver=false, canvas/WebGL/audio/font spoofing, ...).
    The verified package manages a patched Chromium build; its installed path
    is reported by `python3 -m cloakbrowser info`.
  * agent-browser — a Rust CLI/daemon that launches and drives a browser,
    exposing an agent-friendly accessibility `snapshot` (@e refs) plus the full
    interaction/inspection command surface.

Bridge: agent-browser launches the cloak stealth Chromium directly via
`AGENT_BROWSER_EXECUTABLE_PATH` and manages its lifecycle. agent-browser's
daemon persists the browser/page/session across separate CLI invocations, so
state survives across MCP tool calls (the Kali container PID1 is `sleep
infinity`). Each tool here is a thin wrapper around
`docker.exec_command("agent-browser ...")`.

The convenience tools cover the common loop (open -> snapshot -> act/read ->
screenshot). `browser_cmd` is the escape hatch to EVERY other agent-browser
feature, and `browser_skill` lets the agent self-load agent-browser's own,
version-matched command reference.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import posixpath
import re
import shlex
import struct
import uuid
from typing import TYPE_CHECKING, Any, Literal

from fastmcp import Context

from hercules.core.guidance import (
    TOOL_DESCRIPTIONS,
    backend_unavailable,
    missing_param_error,
    path_error,
    selector_error,
    target_error,
)
from hercules.core.security import (
    redact_secrets,
    redact_url,
    reject_control_chars,
    safe_filename,
    safe_identifier,
    validate_proxy_url,
    validate_target_async,
)
from hercules.output.sanitizer import escape_display_controls

if TYPE_CHECKING:
    from fastmcp import FastMCP

logger = logging.getLogger("hercules.tools.browser")

_BROWSER_DIR = "/opt/workspace/browser"
_LOG_DIR = "/opt/workspace/logs"

# Resolve the cloak stealth-Chromium binary once per process and cache it.
_cloak_lock = asyncio.Lock()
_cloak_cache: dict = {"resolved": False, "path": ""}
_runtime_generation: dict = {"value": None}
_session_profiles: dict[str, dict] = {}

_ACT_ACTIONS = ("click", "fill", "type", "press", "hover", "select", "check", "uncheck")
_READ_FIELDS = ("text", "html", "value", "url", "title")
_TARGET_TYPES = ("ref", "css", "role", "text", "label")
_WAIT_CONDITIONS = ("selector", "ms", "text", "url", "load")
_SESSION_ACTIONS = ("current", "list", "close", "close_all", "stream")
_LOOPBACK_STREAM_RE = re.compile(
    r"(?:wss?|https?)://(?:127\.0\.0\.1|localhost|\[::1\]):(?P<port>\d{1,5})",
    re.IGNORECASE,
)


class BrowserBackendError(RuntimeError):
    """The stealth browser backend could not be prepared."""


def reset_browser_runtime_state() -> None:
    """Forget process-local state tied to a previous container generation."""
    _cloak_cache.update({"resolved": False, "path": ""})
    _session_profiles.clear()


def _sync_container_generation(docker) -> None:
    generation = getattr(docker, "generation", None)
    if _runtime_generation["value"] != generation:
        reset_browser_runtime_state()
        _runtime_generation["value"] = generation


async def _resolve_cloak(docker) -> str:
    """
    Resolve and cache the path to the cloak stealth-Chromium binary (via
    `python3 -m cloakbrowser info`) and ensure the workspace dirs exist.
    Returns the verified executable path, or "" if the stealth binary is
    unavailable. Hercules does not silently use agent-browser's fallback.
    """
    if _cloak_cache["resolved"]:
        return _cloak_cache["path"]
    async with _cloak_lock:
        if _cloak_cache["resolved"]:
            return _cloak_cache["path"]
        await docker.exec_command(
            f"mkdir -p {_BROWSER_DIR} {_LOG_DIR}", timeout=15, clean_output=False,
        )
        res = await docker.exec_command(
            "python3 -m cloakbrowser info", timeout=40, clean_output=False,
        )
        if res.exit_code != 0:
            raise BrowserBackendError("cloakbrowser readiness information failed")
        path = ""
        for line in (res.stdout or "").splitlines():
            stripped = line.strip()
            if stripped.lower().startswith("binary:"):
                path = stripped.split(":", 1)[1].strip()
                break
        if path:
            executable = await docker.exec_command(
                f"test -x {shlex.quote(path)}", timeout=15, clean_output=False,
            )
            if executable.exit_code != 0:
                path = ""
        _cloak_cache["path"] = path
        _cloak_cache["resolved"] = True
        if path:
            logger.info("Stealth browser binary resolved: %s", path)
        else:
            logger.warning("cloakbrowser stealth binary not found via 'cloakbrowser info'.")
        return path


async def _backend(ctx: Context | None, tool: str, *, launch_env: dict | None = None):
    """
    Prepare the stealth browser backend for a tool call.

    Returns (docker, concurrency, env) or a structured error dict.
    `env` carries AGENT_BROWSER_EXECUTABLE_PATH (the cloak binary) plus any
    launch_env (TZ/LANG/proxy) — these only take effect when a session's
    browser is first launched.
    """
    if ctx is None:
        return backend_unavailable(tool, "MCP lifespan context is unavailable.")
    docker = ctx.lifespan_context["docker"]
    _sync_container_generation(docker)
    concurrency = ctx.lifespan_context["concurrency"]
    try:
        cloak = await _resolve_cloak(docker)
    except Exception as exc:
        return backend_unavailable(
            tool, f"Failed to resolve the stealth browser binary: {exc}",
            next_steps=[
                "Rebuild the browser capability using the outcomes in install.md.",
                "Check workspace/logs via workspace_read_file.",
            ],
        )
    if not cloak:
        return backend_unavailable(
            tool,
            "The cloakbrowser Chromium binary is unavailable; Hercules will not "
            "silently fall back while reporting a stealth browser.",
            next_steps=[
                "Inspect the local browser readiness outcomes described in install.md.",
                "Rebuild the image if cloakbrowser is missing.",
            ],
        )
    env: dict = {}
    env["AGENT_BROWSER_EXECUTABLE_PATH"] = cloak
    if launch_env:
        env.update(launch_env)
    return docker, concurrency, env


async def _run_agent_browser(
    docker,
    concurrency,
    *,
    session: str,
    argv: list[str] | None = None,
    raw_suffix: str = "",
    json_out: bool = True,
    env: dict | None = None,
    bucket: str = "browser",
    timeout: int = 60,
    sensitive_values: tuple[str, ...] | list[str] = (),
):
    """Run `agent-browser [--json] [--session S] <argv|raw>` headlessly."""
    parts = ["agent-browser"]
    if json_out:
        parts.append("--json")
    if session:
        parts += ["--session", shlex.quote(session)]
    if raw_suffix:
        cmd = " ".join(parts) + " " + raw_suffix
    else:
        cmd = " ".join(parts + (argv or []))
    async with concurrency.acquire_light(bucket):
        return await docker.exec_command(
            cmd, timeout=timeout, env=(env or None), tool_name="agent-browser",
            clean_output=True, compact_output=False,
            sensitive_values=sensitive_values,
        )


def _selector_token(target: str, target_type: str) -> str:
    """Build the agent-browser selector token from a ref/css target."""
    t = (target or "").lstrip("@")
    if target_type == "ref":
        return "@" + t
    return shlex.quote(target)


def _safe_session(session: str) -> str:
    """Sanitize a session name for use as a directory (no traversal)."""
    return safe_filename(
        (session or "default").strip() or "default",
        label="browser session",
        maximum=64,
    )


def _session_dir(session: str) -> str:
    """Per-session artifact directory under the workspace (screenshots, eval temp, ...)."""
    return f"{_BROWSER_DIR}/{_safe_session(session)}"


def _browser_result(tool: str, session: str, result, *, json_out: bool) -> dict:
    """Normalize agent-browser JSON without returning the same payload twice."""
    response = {"tool": tool, "session": session, **result.to_dict()}
    if not json_out or result.exit_code != 0 or not result.stdout.strip():
        return response
    try:
        parsed = json.loads(result.stdout)
    except (TypeError, json.JSONDecodeError):
        return response
    response["browser_result"] = parsed
    response.pop("stdout", None)
    response["inline_stdout_chars"] = 0
    response["structured_output"] = True
    response["stdout_replaced_by"] = "browser_result"
    return response


async def _call(
    ctx,
    tool,
    argv,
    *,
    session,
    timeout=60,
    json_out=True,
    bucket="browser",
    sensitive_values: tuple[str, ...] | list[str] = (),
):
    """Prepare the backend and run an agent-browser command; return a structured dict."""
    try:
        session_key = "" if session == "" else _safe_session(session)
    except ValueError as exc:
        return path_error(tool, session, str(exc))
    prepared = await _backend(ctx, tool)
    if isinstance(prepared, dict):
        return prepared  # structured error
    docker, concurrency, env = prepared
    result = await _run_agent_browser(
        docker, concurrency, session=session_key, argv=argv,
        json_out=json_out, env=env, bucket=bucket, timeout=timeout,
        sensitive_values=sensitive_values,
    )
    return _browser_result(tool, session_key, result, json_out=json_out)


def register_browser_tools(mcp: FastMCP) -> None:

    @mcp.tool(description=TOOL_DESCRIPTIONS["browser_open"])
    async def browser_open(
        url: str,
        session: str = "default",
        fingerprint: str = "",
        timezone: str = "",
        locale: str = "",
        proxy: str = "",
        ctx: Context | None = None,
    ) -> dict:
        """Open a URL in a stealth Chromium session."""
        if not url:
            return missing_param_error("browser_open", "url")
        if fingerprint:
            return {
                "tool": "browser_open",
                "status": "unsupported_parameter",
                "parameter": "fingerprint",
                "error": (
                    "The pinned agent-browser controller does not expose deterministic "
                    "fingerprint selection. Cloakbrowser fingerprint reduction remains active."
                ),
            }
        if ctx is None:
            return backend_unavailable("browser_open", "MCP lifespan context is unavailable.")
        config = ctx.lifespan_context["config"]
        try:
            await validate_target_async(config, url)
        except ValueError as exc:
            return target_error("browser_open", url, exc, config)

        try:
            session_key = _safe_session(session)
        except ValueError as exc:
            return path_error("browser_open", session, str(exc))

        # Launch-affecting profile values are applied only when agent-browser
        # starts the session daemon, so a changed profile requires a relaunch.
        launch_env: dict = {}
        tz = timezone or getattr(config, "browser_timezone", "") or ""
        if tz:
            launch_env["TZ"] = tz
        loc = locale or getattr(config, "browser_locale", "") or ""
        if loc:
            launch_env["LANG"] = loc
            launch_env["LANGUAGE"] = loc
        px = proxy or getattr(config, "browser_proxy", "") or ""
        try:
            px, proxy_host = validate_proxy_url(px)
        except ValueError as exc:
            return {
                "tool": "browser_open",
                "status": "invalid_parameter",
                "parameter": "proxy",
                "error": str(exc),
            }
        if px:
            launch_env["AGENT_BROWSER_PROXY"] = px
            if getattr(config, "browser_disable_non_proxied_udp", True):
                launch_env["AGENT_BROWSER_ARGS"] = (
                    "--force-webrtc-ip-handling-policy=disable_non_proxied_udp"
                )
        allowed_domain_fn = getattr(config, "browser_allowed_domains", None)
        raw_allowed_domains = allowed_domain_fn(url) if callable(allowed_domain_fn) else []
        allowed_domains = (
            [str(item) for item in raw_allowed_domains]
            if isinstance(raw_allowed_domains, (list, tuple, set))
            else []
        )
        if allowed_domains:
            launch_env["AGENT_BROWSER_ALLOWED_DOMAINS"] = ",".join(allowed_domains)

        prepared = await _backend(ctx, "browser_open", launch_env=launch_env)
        if isinstance(prepared, dict):
            return prepared
        docker, concurrency, env = prepared
        generation = getattr(docker, "generation", None)
        effective_profile = {
            "proxy": px,
            "proxy_host": proxy_host,
            "timezone": tz,
            "locale": loc,
            "allowed_domains": tuple(allowed_domains),
            "generation": generation,
        }
        previous_profile = _session_profiles.get(session_key)
        session_relaunched = bool(previous_profile and previous_profile != effective_profile)
        if session_relaunched:
            close_result = await _run_agent_browser(
                docker,
                concurrency,
                session=session_key,
                argv=["close"],
                json_out=True,
                env=env,
                bucket="browser_session",
                timeout=30,
            )
            if close_result.exit_code != 0:
                return {
                    "tool": "browser_open",
                    "status": "session_relaunch_failed",
                    "session": session_key,
                    "proxy_enabled": bool(px),
                    "proxy_host": proxy_host,
                    "timezone": tz,
                    "locale": loc,
                    "session_relaunched": False,
                    "error": "The previous browser session could not be closed safely.",
                    **close_result.to_dict(),
                }
            _session_profiles.pop(session_key, None)

        result = await _run_agent_browser(
            docker, concurrency, session=session_key, argv=["open", shlex.quote(url)],
            json_out=True, env=env, bucket="browser_nav", timeout=120,
            sensitive_values=[px],
        )
        if result.exit_code == 0 and (
            getattr(config, "allowed_targets", None)
            or getattr(config, "blocked_targets", None)
        ):
            final_url_result = await _run_agent_browser(
                docker,
                concurrency,
                session=session_key,
                argv=["get", "url"],
                json_out=False,
                env=env,
                bucket="browser_nav",
                timeout=30,
            )
            final_url = final_url_result.stdout.strip()
            if final_url_result.exit_code != 0 or not final_url:
                close_result = await _run_agent_browser(
                    docker,
                    concurrency,
                    session=session_key,
                    argv=["close"],
                    json_out=True,
                    env=env,
                    bucket="browser_session",
                    timeout=30,
                )
                return {
                    "tool": "browser_open",
                    "status": "redirect_validation_failed",
                    "requested_url": redact_url(url),
                    "session": session_key,
                    "session_closed": close_result.exit_code == 0,
                    "error": "The final browser URL could not be read for scope validation.",
                    "validation_command": final_url_result.to_dict(),
                }
            try:
                await validate_target_async(config, final_url)
            except ValueError as exc:
                close_result = await _run_agent_browser(
                    docker,
                    concurrency,
                    session=session_key,
                    argv=["close"],
                    json_out=True,
                    env=env,
                    bucket="browser_session",
                    timeout=30,
                )
                denied = target_error("browser_open", final_url, exc, config)
                denied.update(
                    {
                        "requested_url": redact_url(url),
                        "redirect_url": redact_url(final_url),
                        "session": session_key,
                        "session_closed": close_result.exit_code == 0,
                    }
                )
                return denied
        if result.exit_code == 0:
            _session_profiles[session_key] = effective_profile
        response = {
            "tool": "browser_open", "url": redact_url(url), "session": session_key,
            "stealth": "cloak stealth Chromium",
            "proxy_enabled": bool(px),
            "proxy_host": proxy_host,
            "timezone": tz,
            "locale": loc,
            "session_relaunched": session_relaunched,
            "next_step": "Call browser_snapshot to see the page and obtain @refs.",
            **_browser_result("browser_open", session_key, result, json_out=True),
        }
        if session_relaunched and result.exit_code != 0:
            response["status"] = "session_relaunch_failed"
            response["error"] = "The previous session closed, but the replacement failed to open."
        return response

    @mcp.tool(description=TOOL_DESCRIPTIONS["browser_snapshot"])
    async def browser_snapshot(
        session: str = "default",
        inline_iframes: bool = False,
        compact: bool = True,
        detailed: bool = False,
        interactive: bool = False,
        include_urls: bool = False,
        depth: int = 0,
        selector: str = "",
        ctx: Context | None = None,
    ) -> dict:
        """Accessibility-tree snapshot with @e refs."""
        try:
            depth = int(depth)
        except (TypeError, ValueError):
            depth = -1
        if not 0 <= depth <= 100:
            return {
                "tool": "browser_snapshot",
                "status": "invalid_parameter",
                "parameter": "depth",
                "error": "depth must be between 0 and 100; 0 means unlimited",
            }
        argv = ["snapshot"]
        if interactive:
            argv.append("-i")
        if include_urls:
            argv.append("-u")
        if compact and not detailed:
            argv.append("-c")
        if depth:
            argv += ["-d", str(depth)]
        if selector:
            argv += ["-s", shlex.quote(selector)]
        # Text tree (not --json) so the agent sees [ref=e1] markers.
        response = await _call(
            ctx, "browser_snapshot", argv, session=session,
            json_out=False, bucket="browser_snapshot", timeout=60,
        )
        if isinstance(response, dict):
            response["iframes_auto_inlined"] = True
            if inline_iframes:
                response["inline_iframes_compatibility"] = "automatic"
        return response

    @mcp.tool(description=TOOL_DESCRIPTIONS["browser_act"])
    async def browser_act(
        action: Literal["click", "fill", "type", "press", "hover", "select", "check", "uncheck"],
        target: str = "",
        value: str = "",
        target_type: Literal["ref", "css", "role", "text", "label"] = "ref",
        name: str = "",
        exact: bool = False,
        session: str = "default",
        ctx: Context | None = None,
    ) -> dict:
        """Interact with an element (click/fill/type/press/hover/select/check)."""
        action_value = (action or "").lower()
        if action_value not in _ACT_ACTIONS:
            return selector_error("browser_act", "action", action_value, list(_ACT_ACTIONS))
        if target_type not in _TARGET_TYPES:
            return selector_error("browser_act", "target_type", target_type, list(_TARGET_TYPES))

        needs_value = action_value in ("fill", "type", "select", "press")
        if needs_value and not value:
            return missing_param_error("browser_act", "value", when=f"action={action_value}")

        if action_value == "press":
            argv = ["press", shlex.quote(value)]
        elif target_type in ("role", "text", "label"):
            if not target:
                return missing_param_error("browser_act", "target", when=f"target_type={target_type}")
            if action_value not in {"click", "fill", "check", "hover"}:
                return {
                    "tool": "browser_act",
                    "status": "unsupported_combination",
                    "parameter": "action",
                    "error": (
                        f"Semantic targeting does not support action={action_value!r}; "
                        "obtain a snapshot ref or use target_type='css'."
                    ),
                }
            # agent-browser parses the token immediately after the locator
            # value as the action. Locator options belong after the action
            # (and after fill text), as shown by its pinned `find --help`.
            argv = ["find", target_type, shlex.quote(target), action_value]
            if value and action_value == "fill":
                argv.append(shlex.quote(value))
            if target_type == "role" and name:
                argv += ["--name", shlex.quote(name)]
            if exact:
                argv.append("--exact")
        else:
            if not target:
                return missing_param_error("browser_act", "target", when=f"action={action}")
            argv = [action_value, _selector_token(target, target_type)]
            if value and action_value in ("fill", "type", "select"):
                argv.append(shlex.quote(value))

        return await _call(
            ctx, "browser_act", argv, session=session,
            json_out=True, bucket="browser_act", timeout=60,
            sensitive_values=[value] if action_value in {"fill", "type", "select"} else (),
        )

    @mcp.tool(description=TOOL_DESCRIPTIONS["browser_read"])
    async def browser_read(
        what: Literal["text", "html", "value", "url", "title"],
        target: str = "",
        target_type: Literal["ref", "css", "role", "text", "label"] = "ref",
        name: str = "",
        exact: bool = False,
        session: str = "default",
        ctx: Context | None = None,
    ) -> dict:
        """Read text/html/value/url/title from the page."""
        what_value = (what or "").lower()
        if what_value not in _READ_FIELDS:
            return selector_error("browser_read", "what", what_value, list(_READ_FIELDS))

        if target_type not in _TARGET_TYPES:
            return selector_error("browser_read", "target_type", target_type, list(_TARGET_TYPES))
        if what_value in ("url", "title"):
            argv = ["get", what_value]
        else:
            if not target:
                return missing_param_error("browser_read", "target", when=f"what={what_value}")
            if target_type in {"role", "text", "label"}:
                if what_value != "text":
                    return {
                        "tool": "browser_read",
                        "status": "unsupported_combination",
                        "parameter": "target_type",
                        "error": (
                            f"Semantic targeting supports only what='text', not {what_value!r}; "
                            "obtain a snapshot ref or use target_type='css'."
                        ),
                    }
                argv = ["find", target_type, shlex.quote(target), "text"]
                if target_type == "role" and name:
                    argv += ["--name", shlex.quote(name)]
                if exact:
                    argv.append("--exact")
            else:
                argv = ["get", what_value, _selector_token(target, target_type)]

        return await _call(
            ctx, "browser_read", argv, session=session,
            json_out=True, bucket="browser_read", timeout=30,
        )

    @mcp.tool(description=TOOL_DESCRIPTIONS["browser_screenshot"])
    async def browser_screenshot(
        path: str = "",
        session: str = "default",
        full: bool = False,
        return_base64: bool = False,
        annotate: bool = False,
        ctx: Context | None = None,
    ) -> Any:
        """Capture a PNG and return it as native MCP image content."""
        try:
            session_key = _safe_session(session)
            requested_path = reject_control_chars(path, label="screenshot path")
        except ValueError as exc:
            return path_error("browser_screenshot", path or session, str(exc))
        if ctx is None:
            return backend_unavailable("browser_screenshot", "MCP lifespan context is unavailable.")

        # Screenshots are saved per-session under /opt/workspace/browser/<session>/.
        if not path:
            out_path = f"{_session_dir(session_key)}/shot_{uuid.uuid4().hex[:10]}.png"
        elif path.startswith("/"):
            out_path = posixpath.normpath(requested_path)
            if not out_path.startswith("/opt/workspace/"):
                return path_error(
                    "browser_screenshot",
                    path,
                    "Absolute screenshot paths must stay under /opt/workspace.",
                )
        else:
            relative_path = posixpath.normpath(requested_path.replace("\\", "/"))
            if (
                relative_path == ".."
                or relative_path.startswith(("../", "/"))
            ):
                return path_error("browser_screenshot", path, "Relative paths must not contain '..'.")
            out_path = f"{_session_dir(session_key)}/{relative_path}"

        docker = ctx.lifespan_context["docker"]
        try:
            out_path = docker.normalize_workspace_path(out_path)
        except (OSError, ValueError) as exc:
            return path_error("browser_screenshot", path or out_path, str(exc))

        prepared = await _backend(ctx, "browser_screenshot")
        if isinstance(prepared, dict):
            return prepared
        docker, concurrency, env = prepared
        # Resolve first above, then create only the owned parent.
        try:
            await docker.ensure_workspace_directory(out_path.rsplit("/", 1)[0])
        except (OSError, ValueError) as exc:
            return path_error("browser_screenshot", path or out_path, str(exc))
        argv = ["screenshot"]
        if full:
            argv.append("--full")
        if annotate:
            argv.append("--annotate")
        argv.append(shlex.quote(out_path))
        result = await _run_agent_browser(
            docker, concurrency, session=session_key, argv=argv,
            json_out=False, env=env, bucket="browser_screenshot", timeout=90,
        )
        response = {
            "tool": "browser_screenshot", "session": session_key, "path": out_path,
            "mime_type": "image/png", "annotated": annotate,
            **result.to_dict(),
        }
        if result.exit_code != 0:
            return response
        try:
            data = await docker.read_file_bytes(out_path)
            if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
                raise ValueError("captured file is not a valid PNG")
            width, height = struct.unpack(">II", data[16:24])
            if width <= 0 or height <= 0:
                raise ValueError("captured PNG has invalid dimensions")
            response["bytes"] = len(data)
            response["width"] = width
            response["height"] = height
            if return_base64:
                response["screenshot_base64"] = base64.b64encode(data).decode("ascii")
        except Exception as exc:
            response["status"] = "image_read_error"
            response["error"] = f"Screenshot command completed but the PNG could not be read: {exc}"
            response["output_complete"] = False
            return response

        # Import concrete content types lazily so lightweight MCP registration
        # tests can provide a minimal fake ``fastmcp`` module.
        from fastmcp.tools.base import ToolResult
        from fastmcp.utilities.types import Image
        from mcp.types import TextContent

        return ToolResult(
            content=[
                TextContent(type="text", text=json.dumps(response, ensure_ascii=False)),
                Image(data=data, format="png").to_image_content(),
            ],
            structured_content=response,
        )

    @mcp.tool(description=TOOL_DESCRIPTIONS["browser_eval"])
    async def browser_eval(
        js: str,
        session: str = "default",
        ctx: Context | None = None,
    ) -> dict:
        """Run JavaScript in the page and return the result."""
        if not js:
            return missing_param_error("browser_eval", "js")
        prepared = await _backend(ctx, "browser_eval")
        if isinstance(prepared, dict):
            return prepared
        docker, concurrency, env = prepared

        script_path = f"{_session_dir(session)}/eval_{uuid.uuid4().hex}.js"
        await docker.write_file(script_path, js, mode=0o644)
        try:
            # Pass the file content as one argument so quoting/newlines survive.
            result = await _run_agent_browser(
                docker, concurrency, session=session,
                raw_suffix=f'eval "$(cat {shlex.quote(script_path)})"',
                json_out=False, env=env, bucket="browser_eval", timeout=60,
            )
        finally:
            try:
                await docker.exec_command(
                    f"rm -f -- {shlex.quote(script_path)}",
                    timeout=10,
                    clean_output=False,
                    require_ready=False,
                )
            except Exception:
                logger.warning("Failed to remove browser eval script: %s", script_path)
        return {"tool": "browser_eval", "session": session, **result.to_dict()}

    @mcp.tool(description=TOOL_DESCRIPTIONS["browser_wait"])
    async def browser_wait(
        condition: Literal["selector", "ms", "text", "url", "load"],
        value: str = "",
        session: str = "default",
        ctx: Context | None = None,
    ) -> dict:
        """Wait for a selector / ms / text / url / load state."""
        condition_value = (condition or "").lower()
        if condition_value not in _WAIT_CONDITIONS:
            return selector_error("browser_wait", "condition", condition_value, list(_WAIT_CONDITIONS))
        if not value:
            return missing_param_error("browser_wait", "value", when=f"condition={condition_value}")

        if condition_value == "ms":
            try:
                milliseconds = int(value)
            except (TypeError, ValueError):
                milliseconds = -1
            if not 0 <= milliseconds <= 60_000:
                return {
                    "tool": "browser_wait",
                    "status": "invalid_parameter",
                    "parameter": "value",
                    "error": "millisecond waits must be between 0 and 60000",
                }
            argv = ["wait", str(milliseconds)]
        elif condition_value == "selector":
            argv = ["wait", shlex.quote(value)]
        else:
            argv = ["wait", f"--{condition_value}", shlex.quote(value)]

        return await _call(
            ctx, "browser_wait", argv, session=session,
            json_out=True, bucket="browser_wait", timeout=60,
        )

    @mcp.tool(description=TOOL_DESCRIPTIONS["browser_session"])
    async def browser_session(
        action: Literal["current", "list", "close", "close_all", "stream"],
        session: str = "",
        stream_port: int = 0,
        ctx: Context | None = None,
    ) -> dict:
        """Manage browser sessions / live-view stream."""
        action_value = (action or "").lower()
        if action_value not in _SESSION_ACTIONS:
            return selector_error("browser_session", "action", action_value, list(_SESSION_ACTIONS))
        if ctx is None:
            return backend_unavailable("browser_session", "MCP lifespan context is unavailable.")

        configured_port = 0
        if action_value == "current":
            argv, sess, json_out = ["session"], session, True
        elif action_value == "list":
            argv, sess, json_out = ["session", "list"], "", True
        elif action_value == "close":
            argv, sess, json_out = ["close"], session or "default", True
        elif action_value == "close_all":
            argv, sess, json_out = ["close", "--all"], "", True
        else:  # stream
            docker = ctx.lifespan_context["docker"]
            configured_port = int(
                getattr(
                    docker,
                    "browser_stream_port",
                    getattr(ctx.lifespan_context.get("config"), "browser_stream_port", 0),
                )
                or 0
            )
            requested_port = int(stream_port or configured_port)
            if configured_port <= 0:
                return missing_param_error(
                    "browser_session",
                    "stream_port",
                    when="action=stream; configure BROWSER_STREAM_PORT before container startup",
                )
            if requested_port != configured_port:
                return {
                    "tool": "browser_session",
                    "status": "invalid_parameter",
                    "parameter": "stream_port",
                    "error": (
                        f"stream_port must match the loopback-mapped "
                        f"effective browser stream port ({configured_port})"
                    ),
                }
            sess = session or "default"
            docker = ctx.lifespan_context["docker"]
            status_response = await _call(
                ctx,
                "browser_session",
                ["stream", "status"],
                session=sess,
                json_out=False,
                bucket="browser_session",
                timeout=30,
            )
            if not isinstance(status_response, dict):
                return status_response
            combined = (
                f"{status_response.get('stdout', '')}\n"
                f"{status_response.get('stderr', '')}"
            )
            match = _LOOPBACK_STREAM_RE.search(combined)
            enabled_now = False
            if match is None:
                enable_response = await _call(
                    ctx,
                    "browser_session",
                    ["stream", "enable"],
                    session=sess,
                    json_out=False,
                    bucket="browser_session",
                    timeout=30,
                )
                if not isinstance(enable_response, dict):
                    return enable_response
                if enable_response.get("exit_code") != 0:
                    enable_response.update(
                        {
                            "stream_port": configured_port,
                            "stream_host": "127.0.0.1",
                            "stream_active": False,
                        }
                    )
                    return enable_response
                enabled_now = True
                status_response = await _call(
                    ctx,
                    "browser_session",
                    ["stream", "status"],
                    session=sess,
                    json_out=False,
                    bucket="browser_session",
                    timeout=30,
                )
                combined = (
                    f"{status_response.get('stdout', '')}\n"
                    f"{status_response.get('stderr', '')}"
                )
                match = _LOOPBACK_STREAM_RE.search(combined)
            if match is None:
                status_response.update(
                    {
                        "status": "stream_backend_unavailable",
                        "stream_port": configured_port,
                        "stream_host": "127.0.0.1",
                        "stream_active": False,
                        "error": (
                            "agent-browser did not report a loopback WebSocket "
                            "endpoint for the selected session"
                        ),
                    }
                )
                return status_response
            backend_port = int(match.group("port"))
            try:
                relay = await docker.ensure_browser_stream_relay(
                    session=_safe_session(sess),
                    backend_port=backend_port,
                )
            except (OSError, RuntimeError, ValueError) as exc:
                status_response.update(
                    {
                        "status": "stream_relay_failed",
                        "stream_port": configured_port,
                        "stream_host": "127.0.0.1",
                        "stream_active": False,
                        "error": str(exc),
                    }
                )
                return status_response
            status_response.update(relay)
            status_response["stream_port"] = configured_port
            status_response["stream_host"] = "127.0.0.1"
            status_response["session"] = _safe_session(sess)
            status_response["backend_enabled_now"] = enabled_now
            if relay.get("stream_active"):
                status_response["status"] = str(relay.get("relay_status", "active"))
                status_response["exit_code"] = 0
            return status_response

        response = await _call(
            ctx, "browser_session", argv, session=sess,
            json_out=json_out, bucket="browser_session", timeout=30,
        )
        if isinstance(response, dict) and response.get("exit_code") == 0:
            if action_value == "close":
                try:
                    _session_profiles.pop(_safe_session(sess), None)
                except ValueError:
                    pass
            elif action_value == "close_all":
                _session_profiles.clear()
        return response

    @mcp.tool(description=TOOL_DESCRIPTIONS["browser_skill"])
    async def browser_skill(
        name: str = "core",
        full: bool = True,
        ctx: Context | None = None,
    ) -> dict:
        """Load agent-browser's own skill/command documentation."""
        if ctx is None:
            return backend_unavailable("browser_skill", "MCP lifespan context is unavailable.")
        docker = ctx.lifespan_context["docker"]
        concurrency = ctx.lifespan_context["concurrency"]
        if name:
            try:
                name = safe_identifier(name, label="browser skill", maximum=64)
            except ValueError as exc:
                return path_error("browser_skill", name, str(exc))
            argv = ["skills", "get", shlex.quote(name)]
            if full:
                argv.append("--full")
        else:
            argv = ["skills"]
        # `skills` is a static CLI command — no browser/backend needed.
        cmd = "agent-browser " + " ".join(argv)
        async with concurrency.acquire_light("browser_skill"):
            result = await docker.exec_command(
                cmd, timeout=30, tool_name="agent-browser",
                clean_output=True, compact_output=False,
            )
        return {"tool": "browser_skill", "skill": name or "list", **result.to_dict()}

    @mcp.tool(description=TOOL_DESCRIPTIONS["browser_cmd"])
    async def browser_cmd(
        args: str,
        session: str = "default",
        timeout: int = 60,
        json: bool = True,
        ctx: Context | None = None,
    ) -> dict:
        """Escape hatch: run any agent-browser subcommand against the stealth session."""
        if not args or not args.strip():
            return missing_param_error("browser_cmd", "args")
        if re.search(r"(?:^|\s)--headed(?:=\S*)?(?=\s|$)", args):
            return {
                "tool": "browser_cmd",
                "status": "unsupported_option",
                "parameter": "args",
                "option": "--headed",
                "error": (
                    "Hercules browser sessions are headless-only. Remove --headed; "
                    "screenshots and loopback streaming remain available."
                ),
            }
        try:
            session_key = _safe_session(session)
            timeout = int(timeout)
            if not 5 <= timeout <= 1_200:
                raise ValueError("timeout must be between 5 and 1200 seconds")
        except (TypeError, ValueError) as exc:
            return {
                "tool": "browser_cmd",
                "status": "invalid_parameter",
                "parameter": "session_or_timeout",
                "error": str(exc),
            }
        logger.warning(
            "browser_cmd invoked (session=%s): %s",
            session_key,
            escape_display_controls(redact_secrets(args)),
        )
        prepared = await _backend(ctx, "browser_cmd")
        if isinstance(prepared, dict):
            return prepared
        docker, concurrency, env = prepared

        prefix = "agent-browser"
        if json:
            prefix += " --json"
        if session_key:
            prefix += f" --session {shlex.quote(session_key)}"
        # args is operator-trusted (like shell_exec) — pass through verbatim so the
        # caller's own quoting works.
        cmd = f"{prefix} {args}"
        async with concurrency.acquire_light("browser_cmd"):
            result = await docker.exec_command(
                cmd, timeout=timeout, env=(env or None),
                tool_name="agent-browser", clean_output=True, compact_output=False,
            )
        return {
            "tool": "browser_cmd",
            "session": session_key,
            "args": escape_display_controls(redact_secrets(args)),
            **result.to_dict(),
        }
