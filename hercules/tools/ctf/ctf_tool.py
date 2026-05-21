"""
CTF and forensics tools for Hercules MCP server.

Includes binwalk, strings, steghide, base64, and xxd.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

from fastmcp import Context

if TYPE_CHECKING:
    from fastmcp import FastMCP

logger = logging.getLogger("hercules.tools.ctf")


def register_ctf_tools(mcp: "FastMCP") -> None:

    @mcp.tool()
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
        if extra_args:
            parts.append(extra_args)
        
        parts.append(f"'{filepath}'")

        cmd = " ".join(parts)

        async with concurrency.acquire_heavy("ctf_binwalk"):
            result = await docker.exec_command(cmd, timeout=300)

        return {"tool": "ctf_binwalk", "filepath": filepath, **result.to_dict()}

    @mcp.tool()
    async def ctf_strings(
        filepath: str,
        min_length: int = 4,
        grep_pattern: str = "",
        extra_args: str = "",
        ctx: Context = None,
    ) -> dict:
        """Extract printable strings from a binary file."""
        docker = ctx.lifespan_context["docker"]
        concurrency = ctx.lifespan_context["concurrency"]

        parts = ["strings", f"-n {min_length}"]
        if extra_args:
            parts.append(extra_args)
            
        parts.append(f"'{filepath}'")

        cmd = " ".join(parts)
        if grep_pattern:
            cmd += f" | grep -i '{grep_pattern}'"

        async with concurrency.acquire_light("ctf_strings"):
            result = await docker.exec_command(cmd, timeout=60)

        return {"tool": "ctf_strings", "filepath": filepath, **result.to_dict()}

    @mcp.tool()
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

        parts = ["steghide", action, "-sf", f"'{filepath}'"]
        
        if passphrase:
            parts.extend(["-p", f"'{passphrase}'"])
        else:
            # Without a passphrase, steghide will prompt unless we pass empty
            parts.extend(["-p", "''"])
            
        if extra_args:
            parts.append(extra_args)

        cmd = " ".join(parts)

        async with concurrency.acquire_light("ctf_steghide"):
            result = await docker.exec_command(cmd, timeout=60)

        return {"tool": "ctf_steghide", "action": action, "filepath": filepath, **result.to_dict()}

    @mcp.tool()
    async def ctf_base64(
        text: str = "",
        filepath: str = "",
        decode: bool = True,
        ctx: Context = None,
    ) -> dict:
        """Encode or decode base64 strings/files."""
        docker = ctx.lifespan_context["docker"]
        concurrency = ctx.lifespan_context["concurrency"]

        parts = ["base64"]
        if decode:
            parts.append("-d")
            
        if filepath:
            parts.append(f"'{filepath}'")
            cmd = " ".join(parts)
        else:
            cmd = f"echo -n '{text}' | " + " ".join(parts)

        async with concurrency.acquire_light("ctf_base64"):
            result = await docker.exec_command(cmd, timeout=30)

        return {"tool": "ctf_base64", **result.to_dict()}

    @mcp.tool()
    async def ctf_xxd(
        filepath: str,
        reverse: bool = False,
        extra_args: str = "",
        ctx: Context = None,
    ) -> dict:
        """Create a hex dump or reverse it using xxd."""
        docker = ctx.lifespan_context["docker"]
        concurrency = ctx.lifespan_context["concurrency"]

        parts = ["xxd"]
        if reverse:
            parts.append("-r")
        if extra_args:
            parts.append(extra_args)
            
        parts.append(f"'{filepath}'")

        cmd = " ".join(parts)

        async with concurrency.acquire_light("ctf_xxd"):
            result = await docker.exec_command(cmd, timeout=60)

        return {"tool": "ctf_xxd", "filepath": filepath, **result.to_dict()}
