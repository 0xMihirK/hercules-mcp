"""
Nmap scanning tools for Hercules MCP server.
"""

from __future__ import annotations

import logging
import re
import shlex
from typing import TYPE_CHECKING, Any, Literal

from defusedxml.ElementTree import fromstring as safe_xml_fromstring
from fastmcp import Context

from hercules.core.guidance import (
    TOOL_DESCRIPTIONS,
    missing_param_error,
    selector_error,
    target_error,
)
from hercules.core.security import safe_filename, validate_target_async
from hercules.output.truncator import truncate_output

if TYPE_CHECKING:
    from fastmcp import FastMCP

logger = logging.getLogger("hercules.tools.nmap")


def register_nmap_tools(mcp: FastMCP) -> None:

    @mcp.tool(description=TOOL_DESCRIPTIONS["nmap_scan"])
    async def nmap_scan(
        mode: Literal["quick", "aggressive", "port", "script", "custom"],
        target: str = "",
        ports: str = "",
        scripts: str = "",
        raw_args: str = "",
        extra_args: str = "",
        ctx: Context = None,
    ) -> dict:
        """Run nmap in quick, aggressive, port, script, or custom mode."""
        docker = ctx.lifespan_context["docker"]
        config = ctx.lifespan_context["config"]
        concurrency = ctx.lifespan_context["concurrency"]

        mode = (mode or "").lower()

        if mode == "quick":
            if not target:
                return missing_param_error(
                    "nmap_scan",
                    "target",
                    when="mode='quick'",
                    examples="nmap_scan(mode='quick', target='scanme.nmap.org')",
                )
            try:
                await validate_target_async(config, target)
            except ValueError as exc:
                return target_error("nmap_scan", target, exc, config)
            async with concurrency.acquire_light("nmap_quick_scan"):
                cmd = f"nmap -T4 -F {extra_args} -oX - {shlex.quote(target)}"
                result = await docker.exec_command(
                    cmd.strip(),
                    timeout=120,
                    max_output_chars=2_000_000,
                    preserve_raw=True,
                )
            return {"tool": "nmap_scan", "mode": mode, "target": target, **_format_result(result)}

        if mode == "aggressive":
            if not target:
                return missing_param_error(
                    "nmap_scan",
                    "target",
                    when="mode='aggressive'",
                    examples="nmap_scan(mode='aggressive', target='scanme.nmap.org')",
                )
            try:
                await validate_target_async(config, target)
            except ValueError as exc:
                return target_error("nmap_scan", target, exc, config)
            async with concurrency.acquire_heavy("nmap_aggressive_scan"):
                cmd = f"nmap -T4 -A -v {extra_args} -oX - {shlex.quote(target)}"
                result = await docker.exec_command(
                    cmd.strip(),
                    timeout=600,
                    max_output_chars=2_000_000,
                    preserve_raw=True,
                )
            return {"tool": "nmap_scan", "mode": mode, "target": target, **_format_result(result)}

        if mode == "port":
            if not target:
                return missing_param_error(
                    "nmap_scan",
                    "target",
                    when="mode='port'",
                    examples="nmap_scan(mode='port', target='host', ports='22,80')",
                )
            if not ports:
                return missing_param_error(
                    "nmap_scan",
                    "ports",
                    when="mode='port'",
                    examples="nmap_scan(mode='port', target='host', ports='22,80')",
                )
            try:
                await validate_target_async(config, target)
            except ValueError as exc:
                return target_error("nmap_scan", target, exc, config)
            if not re.fullmatch(r"[0-9,\-:TUtu]+", ports):
                return {
                    "tool": "nmap_scan",
                    "status": "invalid_parameter",
                    "parameter": "ports",
                    "error": "ports contains unsupported characters",
                }
            async with concurrency.acquire_light("nmap_port_scan"):
                cmd = f"nmap -p {shlex.quote(ports)} {extra_args} -oX - {shlex.quote(target)}"
                result = await docker.exec_command(
                    cmd.strip(),
                    timeout=300,
                    max_output_chars=2_000_000,
                    preserve_raw=True,
                )
            return {"tool": "nmap_scan", "mode": mode, "target": target, "ports": ports, **_format_result(result)}

        if mode == "script":
            if not target:
                return missing_param_error(
                    "nmap_scan",
                    "target",
                    when="mode='script'",
                    examples="nmap_scan(mode='script', target='host', scripts='vuln')",
                )
            if not scripts:
                return missing_param_error(
                    "nmap_scan",
                    "scripts",
                    when="mode='script'",
                    examples="nmap_scan(mode='script', target='host', scripts='vuln')",
                )
            try:
                await validate_target_async(config, target)
            except ValueError as exc:
                return target_error("nmap_scan", target, exc, config)
            if not re.fullmatch(r"[A-Za-z0-9_.,*+\-]+", scripts):
                return {
                    "tool": "nmap_scan",
                    "status": "invalid_parameter",
                    "parameter": "scripts",
                    "error": "scripts contains unsupported characters",
                }
            timeout_arg = "" if "--script-timeout" in extra_args else "--script-timeout 60s"
            cmd = (
                f"nmap --script {shlex.quote(scripts)} {timeout_arg} {extra_args} "
                f"-oX - {shlex.quote(target)}"
            )
            async with concurrency.acquire_light("nmap_script_scan"):
                result = await docker.exec_command(
                    cmd.strip(),
                    timeout=300,
                    max_output_chars=2_000_000,
                    preserve_raw=True,
                )
            return {"tool": "nmap_scan", "mode": mode, "target": target, "scripts": scripts, **_format_result(result)}

        if mode == "custom":
            if not raw_args:
                return missing_param_error(
                    "nmap_scan",
                    "raw_args",
                    when="mode='custom'",
                    examples="nmap_scan(mode='custom', raw_args='-sS -p80 scanme.nmap.org')",
                )
            wants_xml = "-oX -" in raw_args
            async with concurrency.acquire_light("nmap_custom_scan"):
                kwargs = {"max_output_chars": 2_000_000, "preserve_raw": True} if wants_xml else {}
                result = await docker.exec_command(f"nmap {raw_args}", timeout=600, **kwargs)
            return {"tool": "nmap_scan", "mode": mode, "raw_args": raw_args, **_format_result(result)}

        return selector_error(
            "nmap_scan",
            "mode",
            mode,
            ["quick", "aggressive", "port", "script", "custom"],
            examples=[
                "nmap_scan(mode='quick', target='scanme.nmap.org')",
                "nmap_scan(mode='custom', raw_args='-sS -p80 scanme.nmap.org')",
            ],
        )

    @mcp.tool(description=TOOL_DESCRIPTIONS["nmap_write_nse_script"])
    async def nmap_write_nse_script(name: str, content: str, ctx: Context) -> dict:
        """Write custom NSE script and update DB."""
        docker = ctx.lifespan_context["docker"]
        try:
            safe_name = safe_filename(name, label="NSE script name", maximum=80)
        except ValueError as exc:
            return {
                "tool": "nmap_write_nse_script",
                "status": "invalid_parameter",
                "parameter": "name",
                "error": str(exc),
            }
        container_path = f"/opt/workspace/nmap-scripts/{safe_name}.nse"
        await docker.write_file(container_path, content)

        return {
            "tool": "nmap_write_nse_script",
            "script_path": container_path,
            "script_db_updated": False,
            "script_db_update_required": False,
            "script_ready": True,
            "storage": "managed_workspace",
        }

    @mcp.tool(description=TOOL_DESCRIPTIONS["nmap_run_nse_script"])
    async def nmap_run_nse_script(target: str, script_name: str, extra_args: str = "", ctx: Context = None) -> dict:
        """Run a custom NSE script against a target."""
        docker = ctx.lifespan_context["docker"]
        config = ctx.lifespan_context["config"]
        concurrency = ctx.lifespan_context["concurrency"]

        try:
            await validate_target_async(config, target)
        except ValueError as exc:
            return target_error("nmap_run_nse_script", target, exc, config)

        try:
            safe_name = safe_filename(
                script_name, label="NSE script name", maximum=80
            )
        except ValueError as exc:
            return {
                "tool": "nmap_run_nse_script",
                "status": "invalid_parameter",
                "parameter": "script_name",
                "error": str(exc),
            }
        script_path = f"/opt/workspace/nmap-scripts/{safe_name}.nse"
        try:
            await docker.validate_workspace_file(script_path)
        except (FileNotFoundError, ValueError) as exc:
            return {
                "tool": "nmap_run_nse_script",
                "status": "invalid_parameter",
                "parameter": "script_name",
                "error": f"custom NSE script is unavailable: {exc}",
                "script_path": script_path,
            }
        cmd = (
            f"nmap --script {shlex.quote(script_path)} {extra_args} "
            f"-oX - {shlex.quote(target)}"
        )

        async with concurrency.acquire_light("nmap_run_nse_script"):
            result = await docker.exec_command(
                cmd.strip(),
                timeout=300,
                max_output_chars=2_000_000,
                preserve_raw=True,
            )

        return {
            "tool": "nmap_run_nse_script",
            "target": target,
            "script": safe_name,
            "script_path": script_path,
            **_format_result(result),
        }

def _format_result(result) -> dict:
    base = result.to_dict()
    if result.exit_code == 0 and result.stdout.strip().startswith("<?xml"):
        try:
            base["parsed"] = _parse_nmap_xml(result.stdout)
            # Remove raw XML output to save tokens when parsed successfully
            base.pop("stdout", None)
            base["inline_stdout_chars"] = 0
            base["structured_output"] = True
            base["stdout_replaced_by"] = "parsed"
        except Exception as exc:
            base["xml_parse_error"] = str(exc)
    elif result.exit_code == 0 and len(base.get("stdout", "")) > 8000:
        stdout, truncated = truncate_output(
            base["stdout"],
            max_chars=8000,
            artifact_path=base.get("stdout_artifact") or base.get("raw_artifact", ""),
        )
        base["stdout"] = stdout
        if truncated:
            base["truncated"] = True
    return base


def _parse_nmap_xml(xml_str: str) -> dict:
    root = safe_xml_fromstring(xml_str)
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
                if state_el is not None:
                    port_info["state"] = state_el.get("state")
                service_el = port_el.find("service")
                if service_el is not None:
                    port_info["service"] = {
                        "name": service_el.get("name"),
                        "product": service_el.get("product"),
                        "version": service_el.get("version"),
                    }
                scripts = []
                for script_el in port_el.findall("script"):
                    scripts.append(_parse_script_el(script_el))
                if scripts:
                    port_info["scripts"] = scripts
                ports.append(port_info)
        host_info["ports"] = ports
        host_scripts_el = host_el.find("hostscript")
        if host_scripts_el is not None:
            host_info["scripts"] = [
                _parse_script_el(script_el)
                for script_el in host_scripts_el.findall("script")
            ]
        hosts.append(host_info)

    return {
        "scanner": root.get("scanner"),
        "start_time": root.get("start"),
        "host_count": len(hosts),
        "hosts": hosts,
    }


def _parse_script_el(script_el: Any) -> dict:
    script: dict = {
        "id": script_el.get("id"),
        "output": script_el.get("output", ""),
    }
    tables = [_parse_table_el(table_el) for table_el in script_el.findall("table")]
    elems = [_parse_elem_el(elem_el) for elem_el in script_el.findall("elem")]
    if tables:
        script["tables"] = tables
    if elems:
        script["elements"] = elems
    return script


def _parse_table_el(table_el: Any) -> dict:
    table: dict = {}
    key = table_el.get("key")
    if key:
        table["key"] = key
    elems = [_parse_elem_el(elem_el) for elem_el in table_el.findall("elem")]
    tables = [_parse_table_el(child) for child in table_el.findall("table")]
    if elems:
        table["elements"] = elems
    if tables:
        table["tables"] = tables
    return table


def _parse_elem_el(elem_el: Any) -> dict:
    elem = {"value": elem_el.text or ""}
    key = elem_el.get("key")
    if key:
        elem["key"] = key
    return elem
