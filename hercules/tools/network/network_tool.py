"""
Networking and packet crafting tools for Hercules MCP server.

Includes curl, consolidated ncat actions, and hping3.
"""

from __future__ import annotations

import asyncio
import base64
import logging
import re
import shlex
import uuid
from typing import TYPE_CHECKING, Literal

from fastmcp import Context

from hercules.core.guidance import (
    TOOL_DESCRIPTIONS,
    missing_param_error,
    selector_error,
    target_error,
)
from hercules.core.security import (
    redact_url,
    safe_filename,
    shell_quote,
    validate_target_async,
)

if TYPE_CHECKING:
    from fastmcp import FastMCP

logger = logging.getLogger("hercules.tools.network")


def register_network_tools(mcp: FastMCP) -> None:

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
            await validate_target_async(config, url)
        except ValueError as exc:
            return target_error("network_curl", url, exc, config)

        method = (method or "GET").upper()
        if not re.fullmatch(r"[A-Z]{1,16}", method):
            return {
                "tool": "network_curl",
                "status": "invalid_parameter",
                "parameter": "method",
                "error": "HTTP method must contain 1-16 ASCII letters.",
            }
        parts = ["curl", "-s", "-X", method, "--proto", "=http,https"]
        if include_headers:
            parts.append("-i")
        scoped = bool(config.allowed_targets or config.blocked_targets)
        if follow_redirects and not scoped:
            parts.append("-L")

        if headers:
            for h in headers.split(","):
                if h.strip():
                    parts.extend(["-H", shell_quote(h.strip(), label="HTTP header")])

        if data:
            parts.extend(["-d", shell_quote(data, label="request data")])

        if cookie:
            parts.extend(["-b", shell_quote(cookie, label="cookie")])

        if extra_args:
            parts.append(extra_args)

        parts.append(shell_quote(url, label="URL"))

        cmd = " ".join(parts)

        async with concurrency.acquire_light("network_curl"):
            result = await docker.exec_command(
                cmd,
                timeout=60,
                sensitive_values=[headers, data, cookie],
            )

        return {
            "tool": "network_curl",
            "url": redact_url(url),
            "redirects_followed": bool(follow_redirects and not scoped),
            "redirect_note": (
                "Redirect following is disabled while target scopes are configured."
                if follow_redirects and scoped
                else ""
            ),
            **result.to_dict(),
        }

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
        if not 0 <= int(port or 0) <= 65_535 or not 1 <= int(listen_port or 0) <= 65_535:
            return {
                "tool": "ncat",
                "status": "invalid_parameter",
                "parameter": "port",
                "error": "Ports must be between 1 and 65535.",
            }

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
                await validate_target_async(config, target)
            except ValueError as exc:
                return target_error("ncat", target, exc, config)

            parts = ["ncat"]
            if udp:
                parts.append("-u")
            parts.extend([shell_quote(target, label="target"), str(port)])
            if execute:
                parts.extend(["-e", shell_quote(execute, label="execute path")])
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
                try:
                    job_id = safe_filename(job_id, label="job_id", maximum=64)
                except ValueError as exc:
                    return {
                        "tool": "ncat",
                        "status": "invalid_parameter",
                        "parameter": "job_id",
                        "error": str(exc),
                    }

                await docker.exec_command("mkdir -p /opt/workspace/jobs")

                pipe_in = f"/opt/workspace/jobs/{job_id}.in"
                parts = ["ncat"]
                if udp:
                    parts.append("-u")
                parts.extend(["-lvnp", str(effective_port)])
                if extra_args:
                    parts.append(extra_args)
                quoted_pipe = shlex.quote(pipe_in)
                cmd = f"touch {quoted_pipe} && tail -f {quoted_pipe} | " + " ".join(parts)

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
                parts.extend(["-e", shell_quote(execute, label="execute path")])
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
            try:
                job_id = safe_filename(job_id, label="job_id", maximum=64)
            except ValueError as exc:
                return {
                    "tool": "ncat",
                    "status": "invalid_parameter",
                    "parameter": "job_id",
                    "error": str(exc),
                }

            pipe_in = f"/opt/workspace/jobs/{job_id}.in"

            if command:
                encoded = base64.b64encode(command.encode("utf-8") + b"\n").decode("utf-8")
                await docker.exec_command(
                    f"printf %s {shlex.quote(encoded)} | base64 -d >> {shlex.quote(pipe_in)}",
                    clean_output=False,
                )
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
            await validate_target_async(config, target)
        except ValueError as exc:
            return target_error("network_hping3", target, exc, config)
        if not 1 <= int(count) <= 100_000 or not 0 <= int(port or 0) <= 65_535:
            return {
                "tool": "network_hping3",
                "status": "invalid_parameter",
                "error": "count must be 1-100000 and port must be 0-65535.",
            }

        parts = ["hping3", "-c", str(count)]
        if syn:
            parts.append("-S")
        if port:
            parts.extend(["-p", str(port)])
        if extra_args:
            parts.append(extra_args)

        parts.append(shell_quote(target, label="target"))

        cmd = " ".join(parts)

        async with concurrency.acquire_light("network_hping3"):
            result = await docker.exec_command(cmd, timeout=120)

        return {"tool": "network_hping3", "target": target, **result.to_dict()}
