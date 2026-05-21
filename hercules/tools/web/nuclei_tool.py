"""
Nuclei template-based vulnerability scanning tools for Hercules MCP server.

Supports running built-in and custom templates with JSON output,
and authoring custom YAML templates with path traversal protection.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from fastmcp import Context

if TYPE_CHECKING:
    from fastmcp import FastMCP

logger = logging.getLogger("hercules.tools.nuclei")


def register_nuclei_tools(mcp: "FastMCP") -> None:

    @mcp.tool()
    async def nuclei_run(
        targets: str,
        templates: str = "",
        severity: str = "",
        tags: str = "",
        rate_limit: int = 150,
        extra_args: str = "",
        ctx: Context = None,
    ) -> dict:
        """Run nuclei vulnerability scanner against targets."""
        docker = ctx.lifespan_context["docker"]
        config = ctx.lifespan_context["config"]
        concurrency = ctx.lifespan_context["concurrency"]

        # Validate each target
        for t in targets.split(","):
            t = t.strip()
            if t:
                config.validate_target(t)

        parts = ["nuclei", "-jsonl"]
        parts.append(f"-target {targets}")
        parts.append(f"-rate-limit {rate_limit}")
        if templates:
            parts.append(f"-t {templates}")
        if severity:
            parts.append(f"-severity {severity}")
        if tags:
            parts.append(f"-tags {tags}")
        if extra_args:
            parts.append(extra_args)

        cmd = " ".join(parts)

        async with concurrency.acquire_heavy("nuclei_run"):
            result = await docker.exec_command(cmd, timeout=600)

        return {"tool": "nuclei_run", "targets": targets, **result.to_dict()}

    @mcp.tool()
    async def nuclei_write_template(path: str, content: str, ctx: Context) -> dict:
        """Write custom nuclei YAML template to workspace."""
        docker = ctx.lifespan_context["docker"]

        # Path traversal sanitization
        safe_path = os.path.normpath(path).replace("\\", "/")
        # Remove leading slashes
        safe_path = safe_path.lstrip("/")
        if ".." in safe_path:
            raise ValueError(f"Path traversal detected in template path: {path}")

        container_path = f"/opt/workspace/nuclei-templates/{safe_path}"
        await docker.write_file(container_path, content)

        return {
            "tool": "nuclei_write_template",
            "path": container_path,
            "message": f"Template written to {container_path}",
        }
