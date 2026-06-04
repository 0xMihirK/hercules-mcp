"""
Stealth browser automation tools for Hercules MCP.

Combines two tools so the agent can drive a real, bot-evading browser:

  * cloakbrowser  — a fingerprint-patched stealth Chromium (compile-time C++
    patches: navigator.webdriver=false, canvas/WebGL/audio/font spoofing, ...).
    The pip package bakes the patched Chromium binary; its path is reported by
    `python3 -m cloakbrowser info`.
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
import logging
import shlex
import uuid
from typing import TYPE_CHECKING, Literal

from fastmcp import Context
from hercules.core.guidance import (
    TOOL_DESCRIPTIONS,
    backend_unavailable,
    missing_param_error,
    path_error,
    selector_error,
    target_error,
)

if TYPE_CHECKING:
    from fastmcp import FastMCP

logger = logging.getLogger("hercules.tools.browser")

_BROWSER_DIR = "/opt/workspace/browser"
_LOG_DIR = "/opt/workspace/logs"
_DISPLAY = ":99"

# Resolve the cloak stealth-Chromium binary once per process and cache it.
_cloak_lock = asyncio.Lock()
_cloak_cache: dict = {"resolved": False, "path": ""}
# Xvfb for headed mode.
_xvfb_lock = asyncio.Lock()
_xvfb_state: dict = {"ok": False}

_ACT_ACTIONS = ("click", "fill", "type", "press", "hover", "select", "check", "uncheck")
_READ_FIELDS = ("text", "html", "value", "url", "title")
_TARGET_TYPES = ("ref", "css", "role", "text", "label")
_WAIT_CONDITIONS = ("selector", "ms", "text", "url", "load")
_SESSION_ACTIONS = ("current", "list", "close", "close_all", "stream")


class BrowserBackendError(RuntimeError):
    """The stealth browser backend could not be prepared."""


async def _resolve_cloak(docker) -> str:
    """
    Resolve and cache the path to the cloak stealth-Chromium binary (via
    `python3 -m cloakbrowser info`) and ensure the workspace dirs exist.
    Returns the path, or "" if the stealth binary is unavailable (agent-browser
    would then fall back to its own browser, if installed).
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
        path = ""
        for line in (res.stdout or "").splitlines():
            stripped = line.strip()
            if stripped.lower().startswith("binary:"):
                path = stripped.split(":", 1)[1].strip()
                break
        _cloak_cache["path"] = path
        _cloak_cache["resolved"] = True
        if path:
            logger.info("Stealth browser binary resolved: %s", path)
        else:
            logger.warning("cloakbrowser stealth binary not found via 'cloakbrowser info'.")
        return path


async def _ensure_xvfb(docker) -> str:
    """Start a persistent Xvfb for headed mode and return the DISPLAY value."""
    if _xvfb_state["ok"]:
        return _DISPLAY
    async with _xvfb_lock:
        if _xvfb_state["ok"]:
            return _DISPLAY
        await docker.exec_command(
            f"pgrep -x Xvfb >/dev/null 2>&1 || "
            f"(nohup Xvfb {_DISPLAY} -screen 0 1920x1080x24 -nolisten tcp "
            f">{_LOG_DIR}/xvfb.log 2>&1 & sleep 1)",
            timeout=20, clean_output=False, tool_name="xvfb",
        )
        _xvfb_state["ok"] = True
        return _DISPLAY


async def _backend(ctx: Context, tool: str, *, launch_env: dict | None = None):
    """
    Prepare the stealth browser backend for a tool call.

    Returns (docker, concurrency, headed, env) or a structured error dict.
    `env` carries AGENT_BROWSER_EXECUTABLE_PATH (the cloak binary) plus any
    launch_env (TZ/LANG/proxy/DISPLAY) — these only take effect when a session's
    browser is first launched.
    """
    docker = ctx.lifespan_context["docker"]
    concurrency = ctx.lifespan_context["concurrency"]
    config = ctx.lifespan_context["config"]
    headed = not getattr(config, "browser_headless", True)
    try:
        cloak = await _resolve_cloak(docker)
    except Exception as exc:
        return backend_unavailable(
            tool, f"Failed to resolve the stealth browser binary: {exc}",
            next_steps=[
                "Rebuild the image so cloakbrowser + agent-browser are installed (python hercules_setup.py --rebuild).",
                "Check workspace/logs via workspace_read_file.",
            ],
        )
    env: dict = {}
    if cloak:
        env["AGENT_BROWSER_EXECUTABLE_PATH"] = cloak
    if headed:
        try:
            display = await _ensure_xvfb(docker)
            env["DISPLAY"] = display
        except Exception as exc:
            logger.warning("Xvfb start failed, headed mode may not work: %s", exc)
    if launch_env:
        env.update(launch_env)
    return docker, concurrency, headed, env


async def _run_agent_browser(
    docker,
    concurrency,
    *,
    session: str,
    argv: list[str] | None = None,
    raw_suffix: str = "",
    json_out: bool = True,
    headed: bool = False,
    env: dict | None = None,
    bucket: str = "browser",
    timeout: int = 60,
):
    """Run `agent-browser [--json] [--headed] [--session S] <argv|raw>` in the container."""
    parts = ["agent-browser"]
    if json_out:
        parts.append("--json")
    if headed:
        parts.append("--headed")
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
        )


def _selector_token(target: str, target_type: str) -> str:
    """Build the agent-browser selector token from a ref/css target."""
    t = (target or "").lstrip("@")
    if target_type == "ref":
        return "@" + t
    return shlex.quote(target)


def _safe_session(session: str) -> str:
    """Sanitize a session name for use as a directory (no traversal)."""
    s = (session or "default").strip() or "default"
    return "".join(c if (c.isalnum() or c in "-_") else "_" for c in s)[:64] or "default"


def _session_dir(session: str) -> str:
    """Per-session artifact directory under the workspace (screenshots, eval temp, ...)."""
    return f"{_BROWSER_DIR}/{_safe_session(session)}"


async def _call(ctx, tool, argv, *, session, timeout=60, json_out=True, bucket="browser"):
    """Prepare the backend and run an agent-browser command; return a structured dict."""
    prepared = await _backend(ctx, tool)
    if isinstance(prepared, dict):
        return prepared  # structured error
    docker, concurrency, headed, env = prepared
    result = await _run_agent_browser(
        docker, concurrency, session=session, argv=argv,
        json_out=json_out, headed=headed, env=env, bucket=bucket, timeout=timeout,
    )
    return {"tool": tool, "session": session, **result.to_dict()}


def register_browser_tools(mcp: "FastMCP") -> None:

    @mcp.tool(description=TOOL_DESCRIPTIONS["browser_open"])
    async def browser_open(
        url: str,
        session: str = "default",
        fingerprint: str = "",
        timezone: str = "",
        locale: str = "",
        proxy: str = "",
        ctx: Context = None,
    ) -> dict:
        """Open a URL in a stealth Chromium session."""
        if not url:
            return missing_param_error("browser_open", "url")
        config = ctx.lifespan_context["config"]
        try:
            config.validate_target(url)
        except ValueError as exc:
            return target_error("browser_open", url, exc, config)

        # Stealth profile applied at first launch of this session (cloak binary
        # already provides realistic fingerprinting; these refine timezone/locale).
        launch_env: dict = {}
        tz = timezone or getattr(config, "browser_timezone", "") or ""
        if tz:
            launch_env["TZ"] = tz
        loc = locale or getattr(config, "browser_locale", "") or ""
        if loc:
            launch_env["LANG"] = loc
            launch_env["LANGUAGE"] = loc
        px = proxy or getattr(config, "browser_proxy", "") or ""
        if px:
            launch_env["HTTPS_PROXY"] = px
            launch_env["HTTP_PROXY"] = px

        prepared = await _backend(ctx, "browser_open", launch_env=launch_env)
        if isinstance(prepared, dict):
            return prepared
        docker, concurrency, headed, env = prepared
        result = await _run_agent_browser(
            docker, concurrency, session=session, argv=["open", shlex.quote(url)],
            json_out=True, headed=headed, env=env, bucket="browser_nav", timeout=120,
        )
        applied = {k: v for k, v in launch_env.items() if k in ("TZ", "LANG", "HTTPS_PROXY")}
        return {
            "tool": "browser_open", "url": url, "session": session,
            "stealth": "cloak stealth Chromium" + (f"; profile={applied}" if applied else ""),
            "next_step": "Call browser_snapshot to see the page and obtain @refs.",
            **result.to_dict(),
        }

    @mcp.tool(description=TOOL_DESCRIPTIONS["browser_snapshot"])
    async def browser_snapshot(
        session: str = "default",
        inline_iframes: bool = False,
        compact: bool = True,
        detailed: bool = False,
        ctx: Context = None,
    ) -> dict:
        """Accessibility-tree snapshot with @e refs."""
        argv = ["snapshot"]
        if inline_iframes:
            argv.append("-i")
        if compact:
            argv.append("-c")
        if detailed:
            argv.append("-d")
        # Text tree (not --json) so the agent sees [ref=e1] markers.
        return await _call(
            ctx, "browser_snapshot", argv, session=session,
            json_out=False, bucket="browser_snapshot", timeout=60,
        )

    @mcp.tool(description=TOOL_DESCRIPTIONS["browser_act"])
    async def browser_act(
        action: Literal["click", "fill", "type", "press", "hover", "select", "check", "uncheck"],
        target: str = "",
        value: str = "",
        target_type: Literal["ref", "css", "role", "text", "label"] = "ref",
        session: str = "default",
        ctx: Context = None,
    ) -> dict:
        """Interact with an element (click/fill/type/press/hover/select/check)."""
        action = (action or "").lower()
        if action not in _ACT_ACTIONS:
            return selector_error("browser_act", "action", action, list(_ACT_ACTIONS))
        if target_type not in _TARGET_TYPES:
            return selector_error("browser_act", "target_type", target_type, list(_TARGET_TYPES))

        needs_value = action in ("fill", "type", "select", "press")
        if needs_value and not value:
            return missing_param_error("browser_act", "value", when=f"action={action}")

        if action == "press":
            argv = ["press", shlex.quote(value)]
        elif target_type in ("role", "text", "label"):
            if not target:
                return missing_param_error("browser_act", "target", when=f"target_type={target_type}")
            argv = ["find", target_type, shlex.quote(target), action]
            if value and action in ("fill", "type", "select"):
                argv.append(shlex.quote(value))
        else:
            if not target:
                return missing_param_error("browser_act", "target", when=f"action={action}")
            argv = [action, _selector_token(target, target_type)]
            if value and action in ("fill", "type", "select"):
                argv.append(shlex.quote(value))

        return await _call(
            ctx, "browser_act", argv, session=session,
            json_out=True, bucket="browser_act", timeout=60,
        )

    @mcp.tool(description=TOOL_DESCRIPTIONS["browser_read"])
    async def browser_read(
        what: Literal["text", "html", "value", "url", "title"],
        target: str = "",
        target_type: Literal["ref", "css", "role", "text", "label"] = "ref",
        session: str = "default",
        ctx: Context = None,
    ) -> dict:
        """Read text/html/value/url/title from the page."""
        what = (what or "").lower()
        if what not in _READ_FIELDS:
            return selector_error("browser_read", "what", what, list(_READ_FIELDS))

        if what in ("url", "title"):
            argv = ["get", what]
        else:
            if not target:
                return missing_param_error("browser_read", "target", when=f"what={what}")
            argv = ["get", what, _selector_token(target, target_type)]

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
        ctx: Context = None,
    ) -> dict:
        """Capture a PNG screenshot into the session's workspace directory."""
        # Screenshots are saved per-session under /opt/workspace/browser/<session>/.
        if not path:
            out_path = f"{_session_dir(session)}/shot_{uuid.uuid4().hex[:10]}.png"
        elif path.startswith("/"):
            out_path = path
        else:
            if ".." in path:
                return path_error("browser_screenshot", path, "Relative paths must not contain '..'.")
            out_path = f"{_session_dir(session)}/{path}"

        prepared = await _backend(ctx, "browser_screenshot")
        if isinstance(prepared, dict):
            return prepared
        docker, concurrency, headed, env = prepared
        # Ensure the destination directory exists inside the container.
        await docker.exec_command(
            f"mkdir -p {shlex.quote(out_path.rsplit('/', 1)[0] or '/')}",
            timeout=15, clean_output=False,
        )
        argv = ["screenshot", shlex.quote(out_path)]
        if full:
            argv.append("--full")
        result = await _run_agent_browser(
            docker, concurrency, session=session, argv=argv,
            json_out=False, headed=headed, env=env, bucket="browser_screenshot", timeout=90,
        )
        response = {
            "tool": "browser_screenshot", "session": session, "path": out_path,
            **result.to_dict(),
        }
        if return_base64:
            try:
                data = await docker.read_file_bytes(out_path)
                response["bytes"] = len(data)
                response["screenshot_base64"] = base64.b64encode(data).decode("ascii")
            except Exception as exc:
                response["base64_error"] = str(exc)
        return response

    @mcp.tool(description=TOOL_DESCRIPTIONS["browser_eval"])
    async def browser_eval(
        js: str,
        session: str = "default",
        ctx: Context = None,
    ) -> dict:
        """Run JavaScript in the page and return the result."""
        if not js:
            return missing_param_error("browser_eval", "js")
        prepared = await _backend(ctx, "browser_eval")
        if isinstance(prepared, dict):
            return prepared
        docker, concurrency, headed, env = prepared

        script_path = f"{_session_dir(session)}/eval_{uuid.uuid4().hex}.js"
        await docker.write_file(script_path, js, mode=0o644)
        # Pass the file content as one argument so quoting/newlines survive.
        result = await _run_agent_browser(
            docker, concurrency, session=session,
            raw_suffix=f'eval "$(cat {script_path})"',
            json_out=False, headed=headed, env=env, bucket="browser_eval", timeout=60,
        )
        await docker.exec_command(f"rm -f {script_path}", timeout=10, clean_output=False)
        return {"tool": "browser_eval", "session": session, **result.to_dict()}

    @mcp.tool(description=TOOL_DESCRIPTIONS["browser_wait"])
    async def browser_wait(
        condition: Literal["selector", "ms", "text", "url", "load"],
        value: str = "",
        session: str = "default",
        ctx: Context = None,
    ) -> dict:
        """Wait for a selector / ms / text / url / load state."""
        condition = (condition or "").lower()
        if condition not in _WAIT_CONDITIONS:
            return selector_error("browser_wait", "condition", condition, list(_WAIT_CONDITIONS))
        if not value:
            return missing_param_error("browser_wait", "value", when=f"condition={condition}")

        if condition in ("selector", "ms"):
            argv = ["wait", shlex.quote(value)]
        else:
            argv = ["wait", f"--{condition}", shlex.quote(value)]

        return await _call(
            ctx, "browser_wait", argv, session=session,
            json_out=True, bucket="browser_wait", timeout=60,
        )

    @mcp.tool(description=TOOL_DESCRIPTIONS["browser_session"])
    async def browser_session(
        action: Literal["current", "list", "close", "close_all", "stream"],
        session: str = "",
        stream_port: int = 0,
        ctx: Context = None,
    ) -> dict:
        """Manage browser sessions / live-view stream."""
        action = (action or "").lower()
        if action not in _SESSION_ACTIONS:
            return selector_error("browser_session", "action", action, list(_SESSION_ACTIONS))

        if action == "current":
            argv, sess, json_out = ["session"], session, True
        elif action == "list":
            argv, sess, json_out = ["session", "list"], "", True
        elif action == "close":
            argv, sess, json_out = ["close"], session or "default", True
        elif action == "close_all":
            argv, sess, json_out = ["close", "--all"], "", True
        else:  # stream
            if stream_port <= 0:
                return missing_param_error("browser_session", "stream_port", when="action=stream")
            argv, sess, json_out = ["stream", "enable", "--port", str(int(stream_port))], session or "default", False

        return await _call(
            ctx, "browser_session", argv, session=sess,
            json_out=json_out, bucket="browser_session", timeout=30,
        )

    @mcp.tool(description=TOOL_DESCRIPTIONS["browser_skill"])
    async def browser_skill(
        name: str = "core",
        full: bool = True,
        ctx: Context = None,
    ) -> dict:
        """Load agent-browser's own skill/command documentation."""
        docker = ctx.lifespan_context["docker"]
        concurrency = ctx.lifespan_context["concurrency"]
        if name:
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
        ctx: Context = None,
    ) -> dict:
        """Escape hatch: run any agent-browser subcommand against the stealth session."""
        if not args or not args.strip():
            return missing_param_error("browser_cmd", "args")
        logger.warning("browser_cmd invoked (session=%s): %s", session, args)
        prepared = await _backend(ctx, "browser_cmd")
        if isinstance(prepared, dict):
            return prepared
        docker, concurrency, headed, env = prepared

        prefix = "agent-browser"
        if json:
            prefix += " --json"
        if headed:
            prefix += " --headed"
        if session:
            prefix += f" --session {shlex.quote(session)}"
        # args is operator-trusted (like shell_exec) — pass through verbatim so the
        # caller's own quoting works.
        cmd = f"{prefix} {args}"
        async with concurrency.acquire_light("browser_cmd"):
            result = await docker.exec_command(
                cmd, timeout=max(5, int(timeout)), env=(env or None),
                tool_name="agent-browser", clean_output=True, compact_output=False,
            )
        return {"tool": "browser_cmd", "session": session, "args": args, **result.to_dict()}
