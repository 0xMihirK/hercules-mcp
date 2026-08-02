"""
Interactive shell tool for Hercules MCP server.

High-privilege escape hatch — every invocation is logged at WARN level.
Allows unrestricted command execution inside the Kali container, including
installing additional tools via apt, downloading scripts, etc.
"""

from __future__ import annotations

import logging
import re
import uuid
from typing import TYPE_CHECKING

from fastmcp import Context

from hercules.core.guidance import TOOL_DESCRIPTIONS
from hercules.core.security import redact_secrets, safe_filename

if TYPE_CHECKING:
    from fastmcp import FastMCP

logger = logging.getLogger("hercules.tools.shell")


def _usage_warnings(command: str) -> list[str]:
    warnings: list[str] = []
    if re.search(r"\bpython3?\s+-c\b", command) and re.search(r"[A-Za-z]:\\", command):
        warnings.append(
            "python -c with Windows-style paths can trigger Python unicodeescape errors "
            "for sequences such as \\U. Prefer workspace_write_file for a script file, "
            "or use raw string literals inside the Python snippet."
        )
    return warnings


def register_shell_tools(mcp: FastMCP) -> None:

    @mcp.tool(description=TOOL_DESCRIPTIONS["shell_exec"])
    async def shell_exec(command: str, timeout: int = 60, raw: bool = False, ctx: Context = None) -> dict:
        """
        Arbitrary shell command execution (escape hatch, WARN-logged). 
        
        WARNING: THIS SHELL IS NOT INTERACTIVE!
        Do NOT attempt to run interactive commands (like a reverse shell listener, SSH prompt, or text editor) 
        using this tool, as it will hang indefinitely and block the agent. Use background jobs or specific 
        tools for interactive tasks.
        
        MISSING TOOLS: If you try to run a command and get 'command not found', you have root access! 
        You can simply run `apt-get update && apt-get install -y <package_name>` to install it.
        
        Set raw=True to disable all output cleaning.
        """
        docker = ctx.lifespan_context["docker"]
        concurrency = ctx.lifespan_context["concurrency"]

        if not 1 <= int(timeout) <= 3600:
            return {
                "tool": "shell_exec",
                "status": "invalid_parameter",
                "error": "timeout must be between 1 and 3600 seconds",
            }

        # WARN-level audit log for every shell command, with common secrets hidden.
        logger.warning("shell_exec invoked: %s", redact_secrets(command))

        async with concurrency.acquire_light("shell_exec"):
            # Write to a per-call temp script to safely handle complex quotes/newlines.
            script_path = f"/opt/workspace/tmp/shell_{uuid.uuid4().hex}.sh"
            await docker.write_file(script_path, command, mode=0o755)
            try:
                result = await docker.exec_command(
                    f"bash {script_path}",
                    timeout=timeout,
                    clean_output=not raw,
                )
            finally:
                try:
                    await docker.exec_command(
                        f"rm -f -- {script_path}",
                        timeout=15,
                        clean_output=False,
                        require_ready=False,
                    )
                except Exception:
                    logger.warning("Failed to remove shell temp script: %s", script_path)

        response = {"tool": "shell_exec", **result.to_dict()}
        warnings = _usage_warnings(command)
        if warnings:
            response["usage_warnings"] = warnings
        return response

    @mcp.tool(description=TOOL_DESCRIPTIONS["shell_exec_background"])
    async def shell_exec_background(command: str, job_id: str, ctx: Context = None) -> dict:
        """Run a long shell command in the background, returning a job_id."""
        docker = ctx.lifespan_context["docker"]
        try:
            job_id = safe_filename(job_id, label="job_id", maximum=64)
        except ValueError as exc:
            return {
                "tool": "shell_exec_background",
                "status": "invalid_parameter",
                "error": str(exc),
            }
        logger.warning(
            "shell_exec_background invoked: %s (job_id: %s)",
            redact_secrets(command),
            job_id,
        )
        
        try:
            assigned_id = await docker.exec_background(command, job_id)
        except (RuntimeError, ValueError) as exc:
            return {
                "tool": "shell_exec_background",
                "job_id": job_id,
                "status": "conflict" if "active" in str(exc).lower() else "error",
                "error": str(exc),
            }
        return {
            "tool": "shell_exec_background",
            "job_id": assigned_id,
            "message": "Process started in background. Use shell_check_job to see live output."
        }
        
    @mcp.tool(description=TOOL_DESCRIPTIONS["shell_check_job"])
    async def shell_check_job(job_id: str, tail_lines: int = 50, ctx: Context = None) -> dict:
        """Check the status and read live output of a background shell job. Use tail_lines to control how many lines to retrieve."""
        docker = ctx.lifespan_context["docker"]
        try:
            job_id = safe_filename(job_id, label="job_id", maximum=64)
        except ValueError as exc:
            return {
                "tool": "shell_check_job",
                "status": "invalid_parameter",
                "error": str(exc),
            }
        result = await docker.check_job(job_id, tail_lines=tail_lines)
        return {"tool": "shell_check_job", **result}
        
    @mcp.tool(description=TOOL_DESCRIPTIONS["shell_kill_job"])
    async def shell_kill_job(job_id: str, ctx: Context = None) -> dict:
        """Kill a running background shell job (useful for stuck commands)."""
        docker = ctx.lifespan_context["docker"]
        try:
            job_id = safe_filename(job_id, label="job_id", maximum=64)
        except ValueError as exc:
            return {
                "tool": "shell_kill_job",
                "status": "invalid_parameter",
                "error": str(exc),
            }
        termination = (
            await docker.terminate_job(job_id)
            if hasattr(docker, "terminate_job")
            else {"killed": await docker.kill_job(job_id)}
        )
        return {
            "tool": "shell_kill_job",
            "job_id": job_id,
            **termination,
        }
