"""
Universal tool exception firewall for Hercules MCP.

Every Hercules tool returns a structured dict on success and on *handled*
errors (see hercules.core.guidance). But several tools call
``docker.exec_command`` directly and let unexpected exceptions propagate
(``ContainerUnavailable``, the concurrency ``RuntimeError``, parser bugs, …).
When a tool *raises*, FastMCP turns it into an opaque ``ToolError`` that the
agent cannot repair from — which feels like the session breaking.

This middleware sits in FastMCP's ``on_call_tool`` hook and converts ANY
uncaught exception into a normal, structured ``ToolResult`` — identical on the
wire to the structured errors tools already return — so a single tool failure
can never crash or wedge the session. The full traceback is always logged
(``logger.exception``) so the firewall never hides a real bug from operators.
"""

from __future__ import annotations

import asyncio
import logging

from fastmcp.server.middleware.middleware import CallNext, Middleware, MiddlewareContext
from fastmcp.tools.base import ToolResult

from hercules.core.guidance import backend_unavailable, usage_error
from hercules.core.tool_catalog import all_tool_names

logger = logging.getLogger("hercules.firewall")

_HOST_ONLY_TOOLS = frozenset(
    {
        "system_list_sessions",
        "system_start_container",
        "system_start_new_session",
        "system_stop_container",
    }
)
_DOCKER_BACKED_TOOLS = frozenset(all_tool_names()) - _HOST_ONLY_TOOLS


# Import the domain exception types defensively so the firewall stays importable
# even if a module is refactored. Fall back to name-based matching when absent.
try:  # pragma: no cover - trivial import guard
    from hercules.core.docker_manager import (
        ContainerUnavailable,
        RuntimeNotStarted,
    )
except Exception:  # pragma: no cover
    ContainerUnavailable = None  # type: ignore[assignment]
    RuntimeNotStarted = None  # type: ignore[assignment]

try:  # pragma: no cover - trivial import guard
    from hercules.tools.exploitation.metasploit_tool import (
        MetasploitUnavailable,
    )
except Exception:  # pragma: no cover
    MetasploitUnavailable = None  # type: ignore[assignment]


def _is(exc: BaseException, cls) -> bool:
    return cls is not None and isinstance(exc, cls)


def classify_exception(exc: BaseException, tool: str) -> dict:
    """
    Map an uncaught exception to a consistent, agent-repairable error dict:
    ``{tool, status:"error", error_type, recoverable, message, next_steps}``.

    Never includes a traceback in the payload (that goes to the logs).
    """
    name = type(exc).__name__
    msg = str(exc)

    runtime_not_started = (
        _is(exc, RuntimeNotStarted)
        or name == "RuntimeNotStarted"
        or "call system_start_container before using docker-backed tools"
        in msg.lower()
    )
    if runtime_not_started:
        return usage_error(
            tool,
            "runtime_not_started",
            "The Kali container has not been started for this MCP session.",
            recoverable=True,
            next_steps=[
                "Call system_start_container.",
                "Retry the Docker-backed tool after startup succeeds.",
            ],
        )

    if _is(exc, ContainerUnavailable) or name == "ContainerUnavailable":
        return usage_error(
            tool,
            "container_unavailable",
            "The Kali container is being recovered. Your workspace is preserved.",
            recoverable=True,
            next_steps=[
                "Retry the same tool call in a few seconds.",
                "If it persists, call system_list_sessions to check session state.",
            ],
        )

    if _is(exc, MetasploitUnavailable) or name == "MetasploitUnavailable":
        result = backend_unavailable(tool, msg or "Metasploit RPC is unavailable.")
        result["recoverable"] = False
        return result

    # Only the concurrency message maps to "busy" — never mask arbitrary
    # RuntimeErrors (real bugs) as a transient capacity issue.
    if isinstance(exc, RuntimeError) and "concurrency limit reached" in msg.lower():
        return usage_error(
            tool,
            "server_busy",
            "The server is at capacity for this job type.",
            recoverable=True,
            next_steps=[
                "Retry shortly.",
                "Reduce the number of parallel tool calls in flight.",
            ],
        )

    if isinstance(exc, (asyncio.TimeoutError, TimeoutError)):
        return usage_error(
            tool,
            "timeout",
            "The operation exceeded its time budget.",
            recoverable=True,
            next_steps=[
                "For long-running work use shell_exec_background and poll with shell_check_job.",
                "Retry with a narrower scope, or raise the tool's timeout if it accepts one.",
            ],
        )

    if name == "NotFoundError" and "unknown tool" in msg.lower():
        return usage_error(
            tool,
            "tool_not_found",
            f"Unknown MCP tool: {tool}",
            recoverable=False,
            next_steps=[
                "List the server's current tools and use an exact registered name.",
                "Check whether the capability was disabled by configuration.",
            ],
        )

    # Unknown / internal error — visibly "server bug, not your fault".
    return usage_error(
        tool,
        "internal_error",
        f"Internal server error ({name}): {msg[:300]}",
        recoverable=False,
        next_steps=[
            "This is an internal server error, not a usage error.",
            "Retry once; if it recurs, adjust parameters or use a different tool.",
        ],
    )


class ToolExceptionFirewall(Middleware):
    """Convert any uncaught tool exception into a structured ToolResult."""

    async def on_call_tool(
        self,
        context: MiddlewareContext,
        call_next: CallNext,
    ) -> ToolResult:
        tool_name = getattr(getattr(context, "message", None), "name", "<unknown>")
        try:
            if tool_name in _DOCKER_BACKED_TOOLS:
                fastmcp_context = getattr(context, "fastmcp_context", None)
                server = getattr(fastmcp_context, "fastmcp", None)
                try:
                    registered = (
                        await server.get_tool(tool_name)
                        if server is not None
                        else None
                    )
                except Exception:
                    registered = None
                if registered is not None:
                    fastmcp_context.lifespan_context["docker"].require_runtime_started()
            return await call_next(context)
        except Exception as exc:  # NOT BaseException: let CancelledError/SystemExit propagate
            try:
                payload = classify_exception(exc, tool_name)
                if payload.get("error_type") == "runtime_not_started":
                    logger.info("Docker-backed tool '%s' called while stopped.", tool_name)
                else:
                    logger.exception("Firewall caught exception in tool '%s'", tool_name)
                return ToolResult(structured_content=payload)
            except Exception:
                # Last resort — the firewall must NEVER raise.
                return ToolResult(
                    structured_content={
                        "tool": tool_name,
                        "status": "error",
                        "error_type": "internal_error",
                        "recoverable": False,
                        "message": "Internal server error.",
                    }
                )


class ParameterFilterMiddleware(Middleware):
    """Drop unknown tool arguments through FastMCP's supported middleware API."""

    async def on_call_tool(
        self,
        context: MiddlewareContext,
        call_next: CallNext,
    ) -> ToolResult:
        message = getattr(context, "message", None)
        tool_name = getattr(message, "name", "")
        arguments = getattr(message, "arguments", None) or {}
        fastmcp_context = getattr(context, "fastmcp_context", None)
        server = getattr(fastmcp_context, "fastmcp", None)
        if server is not None and tool_name:
            try:
                tool = await server.get_tool(tool_name)
                expected = set((tool.parameters or {}).get("properties", {}))
                filtered = {key: value for key, value in arguments.items() if key in expected}
                dropped = set(arguments) - set(filtered)
                if dropped:
                    logger.debug(
                        "Stripped unknown injected parameters from '%s': %s",
                        tool_name,
                        sorted(dropped),
                    )
                    message.arguments = filtered
            except Exception as exc:
                logger.debug("Parameter filter failed for '%s': %s", tool_name, exc)
        return await call_next(context)
