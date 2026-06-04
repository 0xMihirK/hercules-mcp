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

logger = logging.getLogger("hercules.firewall")


# Import the domain exception types defensively so the firewall stays importable
# even if a module is refactored. Fall back to name-based matching when absent.
try:  # pragma: no cover - trivial import guard
    from hercules.core.docker_manager import ContainerUnavailable
except Exception:  # pragma: no cover
    ContainerUnavailable = None  # type: ignore[assignment]

try:  # pragma: no cover - trivial import guard
    from hercules.tools.exploitation.metasploit_tool import (
        MetasploitInitializing,
        MetasploitUnavailable,
    )
except Exception:  # pragma: no cover
    MetasploitInitializing = None  # type: ignore[assignment]
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

    if _is(exc, MetasploitInitializing) or name == "MetasploitInitializing":
        result = backend_unavailable(
            tool,
            "Metasploit RPC is still initializing. Retry the same tool call shortly.",
            next_steps="Wait a few seconds, then retry the same tool call.",
        )
        result["error_type"] = "backend_initializing"
        result["recoverable"] = True
        return result

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
        try:
            return await call_next(context)
        except Exception as exc:  # NOT BaseException: let CancelledError/SystemExit propagate
            tool_name = getattr(getattr(context, "message", None), "name", "<unknown>")
            try:
                logger.exception("Firewall caught exception in tool '%s'", tool_name)
            except Exception:
                pass
            try:
                payload = classify_exception(exc, tool_name)
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
