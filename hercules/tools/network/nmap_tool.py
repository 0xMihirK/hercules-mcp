"""
Nmap scanning tools for Hercules MCP server.
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING

from fastmcp import Context

if TYPE_CHECKING:
    from fastmcp import FastMCP

logger = logging.getLogger("hercules.tools.nmap")


def register_nmap_tools(mcp: "FastMCP") -> None:

    @mcp.tool()
    async def nmap_quick_scan(target: str, ctx: Context) -> dict:
        """Fast nmap scan (-T4 -F)."""
        docker = ctx.lifespan_context["docker"]
        config = ctx.lifespan_context["config"]
        concurrency = ctx.lifespan_context["concurrency"]

        config.validate_target(target)

        async with concurrency.acquire_light("nmap_quick_scan"):
            result = await docker.exec_command(f"nmap -T4 -F -oX - {_sanitize(target)}", timeout=120)

        return {"tool": "nmap_quick_scan", "target": target, **_format_result(result)}

    @mcp.tool()
    async def nmap_aggressive_scan(target: str, ctx: Context) -> dict:
        """Aggressive nmap scan (-T4 -A -v)."""
        docker = ctx.lifespan_context["docker"]
        config = ctx.lifespan_context["config"]
        concurrency = ctx.lifespan_context["concurrency"]

        config.validate_target(target)

        async with concurrency.acquire_heavy("nmap_aggressive_scan"):
            result = await docker.exec_command(f"nmap -T4 -A -v -oX - {_sanitize(target)}", timeout=600)

        return {"tool": "nmap_aggressive_scan", "target": target, **_format_result(result)}

    @mcp.tool()
    async def nmap_port_scan(target: str, ports: str, ctx: Context) -> dict:
        """Scan specific ports (e.g. '22,80' or '1-1000')."""
        docker = ctx.lifespan_context["docker"]
        config = ctx.lifespan_context["config"]
        concurrency = ctx.lifespan_context["concurrency"]

        config.validate_target(target)

        async with concurrency.acquire_light("nmap_port_scan"):
            result = await docker.exec_command(f"nmap -p {_sanitize(ports)} -oX - {_sanitize(target)}", timeout=300)

        return {"tool": "nmap_port_scan", "target": target, "ports": ports, **_format_result(result)}

    @mcp.tool()
    async def nmap_script_scan(target: str, scripts: str, extra_args: str = "", ctx: Context = None) -> dict:
        """Run specific NSE scripts."""
        docker = ctx.lifespan_context["docker"]
        config = ctx.lifespan_context["config"]
        concurrency = ctx.lifespan_context["concurrency"]

        config.validate_target(target)

        cmd = f"nmap --script {_sanitize(scripts)} {extra_args} -oX - {_sanitize(target)}"

        async with concurrency.acquire_light("nmap_script_scan"):
            result = await docker.exec_command(cmd.strip(), timeout=300)

        return {"tool": "nmap_script_scan", "target": target, "scripts": scripts, **_format_result(result)}

    @mcp.tool()
    async def nmap_custom_scan(raw_args: str, ctx: Context) -> dict:
        """Run nmap with fully custom args (speed -T, type -sS, etc)."""
        docker = ctx.lifespan_context["docker"]
        concurrency = ctx.lifespan_context["concurrency"]

        async with concurrency.acquire_light("nmap_custom_scan"):
            result = await docker.exec_command(f"nmap {raw_args}", timeout=600)

        return {"tool": "nmap_custom_scan", "raw_args": raw_args, **result.to_dict()}

    @mcp.tool()
    async def nmap_write_nse_script(name: str, content: str, ctx: Context) -> dict:
        """Write custom NSE script and update DB."""
        docker = ctx.lifespan_context["docker"]
        safe_name = name.replace("/", "").replace("..", "").replace("\\", "")
        container_path = f"/usr/share/nmap/scripts/custom/{safe_name}.nse"

        await docker.write_file(container_path, content)
        update_result = await docker.exec_command("nmap --script-updatedb", timeout=60)

        return {
            "tool": "nmap_write_nse_script",
            "script_path": container_path,
            "script_db_updated": update_result.exit_code == 0,
        }

    @mcp.tool()
    async def nmap_run_nse_script(target: str, script_name: str, extra_args: str = "", ctx: Context = None) -> dict:
        """Run a custom NSE script against a target."""
        docker = ctx.lifespan_context["docker"]
        config = ctx.lifespan_context["config"]
        concurrency = ctx.lifespan_context["concurrency"]

        config.validate_target(target)

        safe_name = script_name.replace("/", "").replace("..", "").replace("\\", "")
        cmd = f"nmap --script custom/{safe_name}.nse {extra_args} -oX - {_sanitize(target)}"

        async with concurrency.acquire_light("nmap_run_nse_script"):
            result = await docker.exec_command(cmd.strip(), timeout=300)

        return {"tool": "nmap_run_nse_script", "target": target, "script": safe_name, **_format_result(result)}


def _sanitize(value: str) -> str:
    forbidden = set(";|&$`(){}[]!><\n\r")
    return "".join(c for c in value if c not in forbidden)


def _format_result(result) -> dict:
    base = result.to_dict()
    if result.exit_code == 0 and result.stdout.strip().startswith("<?xml"):
        try:
            base["parsed"] = _parse_nmap_xml(result.stdout)
            # Remove raw XML output to save tokens when parsed successfully
            base.pop("stdout", None)
            base.pop("stderr", None)
        except Exception as exc:
            pass
    return base


def _parse_nmap_xml(xml_str: str) -> dict:
    root = ET.fromstring(xml_str)
    hosts = []
    for host_el in root.findall("host"):
        host_info: dict = {}
        status_el = host_el.find("status")
        if status_el is not None:
            host_info["status"] = status_el.get("state", "unknown")
        
        addresses = []
        for addr_el in host_el.findall("address"):
            addresses.append({"addr": addr_el.get("addr"), "addrtype": addr_el.get("addrtype")})
        host_info["addresses"] = addresses
        
        ports = []
        ports_el = host_el.find("ports")
        if ports_el is not None:
            for port_el in ports_el.findall("port"):
                port_info = {"portid": port_el.get("portid"), "protocol": port_el.get("protocol")}
                state_el = port_el.find("state")
                if state_el is not None: port_info["state"] = state_el.get("state")
                service_el = port_el.find("service")
                if service_el is not None:
                    port_info["service"] = {
                        "name": service_el.get("name"),
                        "product": service_el.get("product"),
                        "version": service_el.get("version"),
                    }
                ports.append(port_info)
        host_info["ports"] = ports
        hosts.append(host_info)

    return {
        "scanner": root.get("scanner"),
        "start_time": root.get("start"),
        "host_count": len(hosts),
        "hosts": hosts,
    }
