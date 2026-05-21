"""
Interactive shell tool for Hercules MCP server.

High-privilege escape hatch — every invocation is logged at WARN level.
Allows unrestricted command execution inside the Kali container, including
installing additional tools via apt, downloading scripts, etc.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fastmcp import Context

if TYPE_CHECKING:
    from fastmcp import FastMCP

logger = logging.getLogger("hercules.tools.shell")

def register_shell_tools(mcp: "FastMCP") -> None:

    @mcp.tool()
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

        # WARN-level audit log for every shell command
        logger.warning("shell_exec invoked: %s", command)

        # Write to a temp script to safely handle complex quotes/newlines
        script_path = "/opt/workspace/tmp_shell.sh"
        await docker.write_file(script_path, command, mode=0o755)

        async with concurrency.acquire_light("shell_exec"):
            result = await docker.exec_command(
                f"bash {script_path}",
                timeout=timeout,
                clean_output=not raw,
            )

        return {"tool": "shell_exec", **result.to_dict()}

    @mcp.tool()
    async def shell_exec_background(command: str, job_id: str, ctx: Context = None) -> dict:
        """Run a long shell command in the background, returning a job_id."""
        docker = ctx.lifespan_context["docker"]
        logger.warning("shell_exec_background invoked: %s (job_id: %s)", command, job_id)
        
        assigned_id = await docker.exec_background(command, job_id)
        return {
            "tool": "shell_exec_background",
            "job_id": assigned_id,
            "message": "Process started in background. Use shell_check_job to see live output."
        }
        
    @mcp.tool()
    async def shell_check_job(job_id: str, tail_lines: int = 50, ctx: Context = None) -> dict:
        """Check the status and read live output of a background shell job. Use tail_lines to control how many lines to retrieve."""
        docker = ctx.lifespan_context["docker"]
        result = await docker.check_job(job_id, tail_lines=tail_lines)
        return {"tool": "shell_check_job", **result}
        
    @mcp.tool()
    async def shell_kill_job(job_id: str, ctx: Context = None) -> dict:
        """Kill a running background shell job (useful for stuck commands)."""
        docker = ctx.lifespan_context["docker"]
        killed = await docker.kill_job(job_id)
        return {
            "tool": "shell_kill_job",
            "job_id": job_id,
            "killed": killed
        }
