"""
Networking and packet crafting tools for Hercules MCP server.

Includes curl, ncat, and hping3.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fastmcp import Context

if TYPE_CHECKING:
    from fastmcp import FastMCP

logger = logging.getLogger("hercules.tools.network")


def register_network_tools(mcp: "FastMCP") -> None:

    @mcp.tool()
    async def network_curl(
        url: str,
        method: str = "GET",
        headers: str = "",
        data: str = "",
        cookie: str = "",
        include_headers: bool = True,
        follow_redirects: bool = True,
        extra_args: str = "",
        ctx: Context = None,
    ) -> dict:
        """HTTP client (curl) for arbitrary web requests."""
        docker = ctx.lifespan_context["docker"]
        config = ctx.lifespan_context["config"]
        concurrency = ctx.lifespan_context["concurrency"]

        config.validate_target(url)

        parts = ["curl", "-s", "-X", method]
        if include_headers:
            parts.append("-i")
        if follow_redirects:
            parts.append("-L")
        
        if headers:
            for h in headers.split(","):
                if h.strip():
                    parts.extend(["-H", f"'{h.strip()}'"])
        
        if data:
            parts.extend(["-d", f"'{data}'"])
            
        if cookie:
            parts.extend(["-b", f"'{cookie}'"])

        if extra_args:
            parts.append(extra_args)
            
        parts.append(f"'{url}'")

        cmd = " ".join(parts)

        async with concurrency.acquire_light("network_curl"):
            result = await docker.exec_command(cmd, timeout=60)

        return {"tool": "network_curl", "url": url, **result.to_dict()}

    @mcp.tool()
    async def network_ncat(
        target: str = "",
        port: int = 0,
        listen: bool = False,
        listen_port: int = 4444,
        execute: str = "",
        udp: bool = False,
        extra_args: str = "",
        ctx: Context = None,
    ) -> dict:
        """Reverse shell standard, listener, and networking tool (ncat)."""
        docker = ctx.lifespan_context["docker"]
        config = ctx.lifespan_context["config"]
        concurrency = ctx.lifespan_context["concurrency"]

        parts = ["ncat"]
        if udp:
            parts.append("-u")
        
        if listen:
            parts.extend(["-l", "-p", str(listen_port)])
        else:
            config.validate_target(target)
            parts.extend([target, str(port)])
            
        if execute:
            parts.extend(["-e", execute])
            
        if extra_args:
            parts.append(extra_args)

        cmd = " ".join(parts)

        async with concurrency.acquire_heavy("network_ncat"):
            # Listening or reverse shells can hang indefinitely.
            # The MCP timeout will eventually kill it.
            result = await docker.exec_command(cmd, timeout=300)

        return {"tool": "network_ncat", "command": cmd, **result.to_dict()}

    @mcp.tool()
    async def network_ncat_listen(port: int, job_id: str, ctx: Context = None) -> dict:
        """Start a Netcat (ncat) listener in the background for catching reverse shells."""
        docker = ctx.lifespan_context["docker"]
        
        await docker.exec_command("mkdir -p /opt/workspace/jobs")
        
        pipe_in = f"/opt/workspace/jobs/{job_id}.in"
        
        # We use a regular file with tail -f to pipe input into ncat. 
        # This keeps the stdin stream open permanently, allowing us to append commands to the file.
        cmd = f"touch {pipe_in} && tail -f {pipe_in} | ncat -lvnp {port}"
        
        assigned_id = await docker.exec_background(cmd, job_id)
        
        return {
            "tool": "network_ncat_listen",
            "job_id": assigned_id,
            "port": port,
            "message": f"Listener started on port {port} in background. Use network_ncat_interact to send commands and read output."
        }

    @mcp.tool()
    async def network_ncat_interact(job_id: str, command: str = "", tail_lines: int = 50, ctx: Context = None) -> dict:
        """Send a command to a background ncat listener and read the latest output buffer."""
        docker = ctx.lifespan_context["docker"]
        
        pipe_in = f"/opt/workspace/jobs/{job_id}.in"
        
        if command:
            import base64
            import asyncio
            
            # Base64 encode the command to avoid all quoting/escaping hell
            encoded = base64.b64encode(command.encode("utf-8") + b"\n").decode("utf-8")
            
            await docker.exec_command(f"echo '{encoded}' | base64 -d >> {pipe_in}", clean_output=False)
            
            # Wait a moment for the reverse shell to process the command and output to be logged
            await asyncio.sleep(1.5)
            
        result = await docker.check_job(job_id, tail_lines=tail_lines)
        return {"tool": "network_ncat_interact", "command_sent": bool(command), **result}

    @mcp.tool()
    async def network_hping3(
        target: str,
        count: int = 4,
        syn: bool = True,
        port: int = 80,
        extra_args: str = "",
        ctx: Context = None,
    ) -> dict:
        """Packet crafting and firewall testing (hping3)."""
        docker = ctx.lifespan_context["docker"]
        config = ctx.lifespan_context["config"]
        concurrency = ctx.lifespan_context["concurrency"]

        config.validate_target(target)

        parts = ["hping3", "-c", str(count)]
        if syn:
            parts.append("-S")
        if port:
            parts.extend(["-p", str(port)])
        if extra_args:
            parts.append(extra_args)
            
        parts.append(target)

        cmd = " ".join(parts)

        async with concurrency.acquire_light("network_hping3"):
            result = await docker.exec_command(cmd, timeout=120)

        return {"tool": "network_hping3", "target": target, **result.to_dict()}
