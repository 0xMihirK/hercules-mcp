"""
Information gathering, DNS, and OSINT tools for Hercules MCP server.

Includes whois, dig, amass, and dnsx.
"""

from __future__ import annotations

import logging
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

logger = logging.getLogger("hercules.tools.recon")


def register_recon_tools(mcp: "FastMCP") -> None:

    @mcp.tool(description=TOOL_DESCRIPTIONS["recon_whois"])
    async def recon_whois(
        domain: str,
        extra_args: str = "",
        include_raw: bool = False,
        ctx: Context = None,
    ) -> dict:
        """Domain OSINT via whois."""
        docker = ctx.lifespan_context["docker"]
        concurrency = ctx.lifespan_context["concurrency"]

        cmd = f"whois {extra_args} {domain}"

        async with concurrency.acquire_light("recon_whois"):
            result = await docker.exec_command(
                cmd,
                timeout=60,
                tool_name="whois",
                compact_output=not include_raw,
                preserve_raw=not include_raw,
            )

        return {"tool": "recon_whois", "domain": domain, **result.to_dict()}

    @mcp.tool(description=TOOL_DESCRIPTIONS["recon_amass"])
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

        try:
            config.validate_target(domain)
        except ValueError as exc:
            return target_error("recon_amass", domain, exc, config)

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

    @mcp.tool(description=TOOL_DESCRIPTIONS["recon_dns"])
    async def recon_dns(
        tool: Literal["dig", "dnsx"],
        target: str = "",
        domains: str = "",
        record_type: str = "A",
        server: str = "",
        short: bool = False,
        axfr: bool = False,
        silent: bool = True,
        extra_args: str = "",
        ctx: Context = None,
    ) -> dict:
        """Run DNS lookups with dig or bulk DNS resolution with dnsx."""
        docker = ctx.lifespan_context["docker"]
        concurrency = ctx.lifespan_context["concurrency"]

        tool = (tool or "").lower()

        if tool == "dig":
            if not target:
                return missing_param_error(
                    "recon_dns",
                    "target",
                    when="tool='dig'",
                    examples="recon_dns(tool='dig', target='example.com', record_type='MX')",
                )
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

            return {"tool": "recon_dns", "selected_tool": "dig", "target": target, "command": cmd, **result.to_dict()}

        if tool == "dnsx":
            source_domains = domains or target
            if not source_domains:
                return missing_param_error(
                    "recon_dns",
                    "domains",
                    when="tool='dnsx' and target is not provided",
                    examples="recon_dns(tool='dnsx', domains='a.example.com,b.example.com')",
                )
            domain_str = "\\n".join([d.strip() for d in source_domains.split(",") if d.strip()])

            parts = ["dnsx"]
            if silent:
                parts.append("-silent")
            if extra_args:
                parts.append(extra_args)

            cmd = f"echo -e '{domain_str}' | " + " ".join(parts)

            async with concurrency.acquire_light("recon_dnsx"):
                result = await docker.exec_command(cmd, timeout=300)

            return {"tool": "recon_dns", "selected_tool": "dnsx", "domains": source_domains, **result.to_dict()}

        return selector_error(
            "recon_dns",
            "tool",
            tool,
            ["dig", "dnsx"],
            examples=[
                "recon_dns(tool='dig', target='example.com', record_type='A')",
                "recon_dns(tool='dnsx', domains='a.example.com,b.example.com')",
            ],
        )
