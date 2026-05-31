"""
Networking and packet crafting tools for Hercules MCP server.

Includes curl, consolidated ncat actions, and hping3.
"""

from __future__ import annotations

import asyncio
import base64
import logging
import uuid
from typing import TYPE_CHECKING, Literal

from fastmcp import Context
from hercules.core.guidance import (
    TOOL_DESCRIPTIONS,
    missing_param_error,
    selector_error,
    target_error,
)

if TYPE_CHECKING:
    from fastmcp import FastMCP

logger = logging.getLogger("hercules.tools.network")


def register_network_tools(mcp: "FastMCP") -> None:

    @mcp.tool(description=TOOL_DESCRIPTIONS["network_curl"])
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

        try:
            config.validate_target(url)
        except ValueError as exc:
            return target_error("network_curl", url, exc, config)

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

    @mcp.tool(description=TOOL_DESCRIPTIONS["ncat"])
    async def ncat(
        action: Literal["connect", "listen", "interact"],
        target: str = "",
        port: int = 0,
        listen_port: int = 4444,
        job_id: str = "",
        command: str = "",
        tail_lines: int = 50,
        execute: str = "",
        udp: bool = False,
        extra_args: str = "",
        background: bool = True,
        ctx: Context = None,
    ) -> dict:
        """Use ncat to connect, listen, or interact with a background listener."""
        docker = ctx.lifespan_context["docker"]
        config = ctx.lifespan_context["config"]
        concurrency = ctx.lifespan_context["concurrency"]

        action = (action or "").lower()

        if action == "connect":
            if not target:
                return missing_param_error(
                    "ncat",
                    "target",
                    when="action='connect'",
                    examples="ncat(action='connect', target='10.0.0.1', port=4444)",
                )
            if not port:
                return missing_param_error(
                    "ncat",
                    "port",
                    when="action='connect'",
                    examples="ncat(action='connect', target='10.0.0.1', port=4444)",
                )
            try:
                config.validate_target(target)
            except ValueError as exc:
                return target_error("ncat", target, exc, config)

            parts = ["ncat"]
            if udp:
                parts.append("-u")
            parts.extend([target, str(port)])
            if execute:
                parts.extend(["-e", execute])
            if extra_args:
                parts.append(extra_args)

            cmd = " ".join(parts)

            async with concurrency.acquire_heavy("network_ncat"):
                result = await docker.exec_command(cmd, timeout=300)

            return {"tool": "ncat", "action": action, "command": cmd, **result.to_dict()}

        if action == "listen":
            effective_port = port or listen_port

            if background:
                if not job_id:
                    job_id = f"ncat_{uuid.uuid4().hex[:6]}"

                await docker.exec_command("mkdir -p /opt/workspace/jobs")

                pipe_in = f"/opt/workspace/jobs/{job_id}.in"
                parts = ["ncat"]
                if udp:
                    parts.append("-u")
                parts.extend(["-lvnp", str(effective_port)])
                if extra_args:
                    parts.append(extra_args)
                cmd = f"touch {pipe_in} && tail -f {pipe_in} | " + " ".join(parts)

                assigned_id = await docker.exec_background(cmd, job_id)

                return {
                    "tool": "ncat",
                    "action": action,
                    "job_id": assigned_id,
                    "port": effective_port,
                    "background": True,
                    "message": f"Listener started on port {effective_port} in background. Use ncat(action='interact') to send commands and read output.",
                }

            parts = ["ncat"]
            if udp:
                parts.append("-u")
            parts.extend(["-l", "-p", str(effective_port)])
            if execute:
                parts.extend(["-e", execute])
            if extra_args:
                parts.append(extra_args)

            cmd = " ".join(parts)

            async with concurrency.acquire_heavy("network_ncat"):
                result = await docker.exec_command(cmd, timeout=300)

            return {"tool": "ncat", "action": action, "command": cmd, "background": False, **result.to_dict()}

        if action == "interact":
            if not job_id:
                return missing_param_error(
                    "ncat",
                    "job_id",
                    when="action='interact'",
                    examples="ncat(action='interact', job_id='listener1', command='id')",
                )

            pipe_in = f"/opt/workspace/jobs/{job_id}.in"

            if command:
                encoded = base64.b64encode(command.encode("utf-8") + b"\n").decode("utf-8")
                await docker.exec_command(f"echo '{encoded}' | base64 -d >> {pipe_in}", clean_output=False)
                await asyncio.sleep(1.5)

            result = await docker.check_job(job_id, tail_lines=tail_lines)
            return {"tool": "ncat", "action": action, "command_sent": bool(command), **result}

        return selector_error(
            "ncat",
            "action",
            action,
            ["connect", "listen", "interact"],
            examples=[
                "ncat(action='connect', target='10.0.0.1', port=4444)",
                "ncat(action='listen', port=4444, job_id='listener1')",
            ],
        )

    @mcp.tool(description=TOOL_DESCRIPTIONS["network_hping3"])
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

        try:
            config.validate_target(target)
        except ValueError as exc:
            return target_error("network_hping3", target, exc, config)

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
