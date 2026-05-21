"""
Information gathering, DNS, and OSINT tools for Hercules MCP server.

Includes whois, dig, amass, and dnsx.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fastmcp import Context

if TYPE_CHECKING:
    from fastmcp import FastMCP

logger = logging.getLogger("hercules.tools.recon")


def register_recon_tools(mcp: "FastMCP") -> None:

    @mcp.tool()
    async def recon_whois(domain: str, extra_args: str = "", ctx: Context = None) -> dict:
        """Domain OSINT via whois."""
        docker = ctx.lifespan_context["docker"]
        concurrency = ctx.lifespan_context["concurrency"]

        cmd = f"whois {extra_args} {domain}"

        async with concurrency.acquire_light("recon_whois"):
            result = await docker.exec_command(cmd, timeout=60)

        return {"tool": "recon_whois", "domain": domain, **result.to_dict()}

    @mcp.tool()
    async def recon_dig(
        target: str,
        record_type: str = "A",
        server: str = "",
        short: bool = False,
        axfr: bool = False,
        extra_args: str = "",
        ctx: Context = None,
    ) -> dict:
        """DNS queries/zone transfers via dig."""
        docker = ctx.lifespan_context["docker"]
        concurrency = ctx.lifespan_context["concurrency"]

        parts = ["dig"]
        if server:
            parts.append(server if server.startswith("@") else f"@{server}")
        parts.append(target)
        if axfr:
            parts.append("AXFR")
        else:
            parts.append(record_type)
        if short:
            parts.append("+short")
        if extra_args:
            parts.append(extra_args)

        cmd = " ".join(parts)

        async with concurrency.acquire_light("recon_dig"):
            result = await docker.exec_command(cmd, timeout=60)

        return {"tool": "recon_dig", "target": target, "command": cmd, **result.to_dict()}

    @mcp.tool()
    async def recon_amass(
        domain: str,
        active: bool = False,
        brute: bool = False,
        extra_args: str = "",
        ctx: Context = None,
    ) -> dict:
        """Subdomain enumeration via amass."""
        docker = ctx.lifespan_context["docker"]
        config = ctx.lifespan_context["config"]
        concurrency = ctx.lifespan_context["concurrency"]

        config.validate_target(domain)

        parts = ["amass enum -d", domain]
        if active:
            parts.append("-active")
        else:
            parts.append("-passive")
        
        if brute:
            parts.append("-brute")
            
        if extra_args:
            parts.append(extra_args)

        cmd = " ".join(parts)

        async with concurrency.acquire_heavy("recon_amass"):
            # Amass can take a very long time
            result = await docker.exec_command(cmd, timeout=1200)

        return {"tool": "recon_amass", "domain": domain, **result.to_dict()}

    @mcp.tool()
    async def recon_dnsx(
        domains: str,
        silent: bool = True,
        extra_args: str = "",
        ctx: Context = None,
    ) -> dict:
        """Bulk DNS resolution via dnsx."""
        docker = ctx.lifespan_context["docker"]
        concurrency = ctx.lifespan_context["concurrency"]

        # Pipe domains to dnsx
        domain_str = "\\n".join([d.strip() for d in domains.split(",") if d.strip()])
        
        parts = ["dnsx"]
        if silent:
            parts.append("-silent")
        if extra_args:
            parts.append(extra_args)

        cmd = f"echo -e '{domain_str}' | " + " ".join(parts)

        async with concurrency.acquire_light("recon_dnsx"):
            result = await docker.exec_command(cmd, timeout=300)

        return {"tool": "recon_dnsx", "domains": domains, **result.to_dict()}
