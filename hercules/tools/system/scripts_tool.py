"""
Custom script execution tools for Hercules MCP server.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

from fastmcp import Context

if TYPE_CHECKING:
    from fastmcp import FastMCP

logger = logging.getLogger("hercules.tools.scripts")


def register_scripts_tools(mcp: "FastMCP") -> None:

    @mcp.tool()
    async def workspace_scripts(
        language: Literal["python", "shell"],
        action: Literal["write", "run", "run_background"],
        name: str,
        payload_or_args: str = "",
        job_id: str = "",
        venv: bool = False,
        ctx: Context = None
    ) -> dict:
        """Write, run, or background-run Python/Shell scripts. 'write' validates Python syntax."""
        docker = ctx.lifespan_context["docker"]
        concurrency = ctx.lifespan_context["concurrency"]

        safe_name = name.replace("/", "").replace("..", "").replace("\\", "")
        ext = "py" if language == "python" else "sh"
        script_path = f"/opt/workspace/{ext}/{safe_name}.{ext}"

        if action == "write":
            mode = 0o755 if language == "shell" else 0o644
            await docker.write_file(script_path, payload_or_args, mode=mode)
            
            # Syntax validation for Python
            if language == "python":
                syntax_check = await docker.exec_command(f"python3 -m py_compile {script_path}")
                if syntax_check.exit_code != 0:
                    return {
                        "tool": "workspace_scripts",
                        "action": action,
                        "path": script_path,
                        "status": "error",
                        "message": "Script written but contains syntax errors.",
                        "error": syntax_check.stderr
                    }
                    
            return {"tool": "workspace_scripts", "action": action, "path": script_path, "status": "success", "message": "Written successfully."}
            
        else: # run or run_background
            if language == "python":
                if venv:
                    cmd = (
                        f"cd /opt/workspace/py && "
                        f"python3 -m venv .venv 2>/dev/null; "
                        f"source .venv/bin/activate && "
                        f"python3 {script_path} {payload_or_args}"
                    )
                else:
                    cmd = f"python3 {script_path} {payload_or_args}"
            else:
                cmd = f"bash {script_path} {payload_or_args}"

            if action == "run_background":
                if not job_id:
                    import uuid
                    job_id = f"job_{uuid.uuid4().hex[:6]}"
                assigned_id = await docker.exec_background(cmd, job_id)
                return {
                    "tool": "workspace_scripts",
                    "action": action,
                    "job_id": assigned_id,
                    "message": "Script started in background. Use shell_check_job to read output or shell_kill_job to stop it."
                }
            else:
                async with concurrency.acquire_light("workspace_scripts_run"):
                    result = await docker.exec_command(cmd, timeout=300)

                return {"tool": "workspace_scripts", "action": action, "script": script_path, **result.to_dict()}
