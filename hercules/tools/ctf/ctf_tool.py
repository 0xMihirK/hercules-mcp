"""
CTF and forensics tools for Hercules MCP server.

Includes binwalk and steghide. Thin shell-equivalent wrappers were removed
from the MCP surface in favor of shell_exec.
"""

from __future__ import annotations

import logging
import posixpath
import shlex
from typing import TYPE_CHECKING, Literal

from fastmcp import Context
from hercules.core.guidance import TOOL_DESCRIPTIONS, selector_error

if TYPE_CHECKING:
    from fastmcp import FastMCP

logger = logging.getLogger("hercules.tools.ctf")


def register_ctf_tools(mcp: "FastMCP") -> None:

    @mcp.tool(description=TOOL_DESCRIPTIONS["ctf_binwalk"])
    async def ctf_binwalk(
        filepath: str,
        extract: bool = True,
        extra_args: str = "",
        ctx: Context = None,
    ) -> dict:
        """Firmware/archive analysis and extraction using binwalk."""
        docker = ctx.lifespan_context["docker"]
        concurrency = ctx.lifespan_context["concurrency"]

        parts = ["binwalk"]
        if extract:
            parts.append("-e")
            if "--run-as" not in extra_args:
                parts.append("--run-as=root")
        if extra_args:
            parts.append(extra_args)

        if extract and filepath.startswith("/"):
            directory = posixpath.dirname(filepath) or "/"
            filename = posixpath.basename(filepath)
            parts.append(shlex.quote(filename))
            cmd = f"cd {shlex.quote(directory)} && {' '.join(parts)}"
        else:
            parts.append(shlex.quote(filepath))
            cmd = " ".join(parts)

        async with concurrency.acquire_heavy("ctf_binwalk"):
            result = await docker.exec_command(cmd, timeout=300)

        return {"tool": "ctf_binwalk", "filepath": filepath, **result.to_dict()}

    @mcp.tool(description=TOOL_DESCRIPTIONS["ctf_steghide"])
    async def ctf_steghide(
        action: Literal["info", "extract"],
        filepath: str,
        passphrase: str = "",
        extra_args: str = "",
        ctx: Context = None,
    ) -> dict:
        """Steganography analysis and extraction via steghide."""
        docker = ctx.lifespan_context["docker"]
        concurrency = ctx.lifespan_context["concurrency"]

        action = (action or "").lower()

        if action == "info":
            parts = ["steghide", action, shlex.quote(filepath)]
        elif action == "extract":
            parts = ["steghide", action, "-sf", shlex.quote(filepath)]
        else:
            return selector_error(
                "ctf_steghide",
                "action",
                action,
                ["info", "extract"],
                examples=[
                    "ctf_steghide(action='info', filepath='/opt/workspace/image.jpg')",
                    "ctf_steghide(action='extract', filepath='/opt/workspace/image.jpg', passphrase='secret')",
                ],
            )
        
        if passphrase:
            parts.extend(["-p", shlex.quote(passphrase)])
        else:
            # Without a passphrase, steghide will prompt unless we pass empty
            parts.extend(["-p", "''"])
            
        if extra_args:
            parts.append(extra_args)

        cmd = " ".join(parts)

        async with concurrency.acquire_light("ctf_steghide"):
            result = await docker.exec_command(cmd, timeout=60)

        return {"tool": "ctf_steghide", "action": action, "filepath": filepath, **result.to_dict()}
