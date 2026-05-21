"""
File management tools for Hercules MCP server.

Provides granular control over files inside the container workspace.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fastmcp import Context

if TYPE_CHECKING:
    from fastmcp import FastMCP

logger = logging.getLogger("hercules.tools.file")


def _resolve_path(path: str) -> str:
    """Resolve relative paths to the container's workspace directory."""
    if not path.startswith("/"):
        return f"/opt/workspace/{path}"
    return path


def register_file_tools(mcp: "FastMCP") -> None:

    @mcp.tool()
    async def workspace_read_file(path: str, ctx: Context = None) -> dict:
        """Read the contents of a file inside the container workspace."""
        docker = ctx.lifespan_context["docker"]
        path = _resolve_path(path)
        
        try:
            content = await docker.read_file(path)
            return {"tool": "workspace_read_file", "path": path, "content": content}
        except Exception as exc:
            return {"tool": "workspace_read_file", "path": path, "error": str(exc)}

    @mcp.tool()
    async def workspace_write_file(path: str, content: str, mode: int = 0o644, ctx: Context = None) -> dict:
        """Write content to a file inside the container workspace (overwrites if exists)."""
        docker = ctx.lifespan_context["docker"]
        path = _resolve_path(path)
        
        try:
            await docker.write_file(path, content, mode=mode)
            return {"tool": "workspace_write_file", "path": path, "status": "success"}
        except Exception as exc:
            return {"tool": "workspace_write_file", "path": path, "error": str(exc)}

    @mcp.tool()
    async def workspace_edit_file(
        path: str, 
        target_content: str, 
        replacement_content: str, 
        ctx: Context = None
    ) -> dict:
        """Edit a file by replacing target_content with replacement_content."""
        docker = ctx.lifespan_context["docker"]
        path = _resolve_path(path)
        
        try:
            current = await docker.read_file(path)
            if target_content not in current:
                return {"tool": "workspace_edit_file", "path": path, "error": "target_content not found in file."}
                
            new_content = current.replace(target_content, replacement_content, 1)
            await docker.write_file(path, new_content)
            
            return {"tool": "workspace_edit_file", "path": path, "status": "success"}
        except Exception as exc:
            return {"tool": "workspace_edit_file", "path": path, "error": str(exc)}
