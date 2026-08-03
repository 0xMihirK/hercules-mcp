"""
System management tools for Hercules MCP server.

Provides container lifecycle controls: start new sessions, list sessions,
and stop the environment. All tools carry explicit agent-facing instructions
in their docstrings explaining WHEN and WHY to use them.
"""

from __future__ import annotations

import asyncio
import logging
import platform
import socket
import subprocess
from typing import TYPE_CHECKING

from fastmcp import Context

from hercules.core.guidance import TOOL_DESCRIPTIONS
from hercules.core.runtime import services_from_context

if TYPE_CHECKING:
    from fastmcp import FastMCP

logger = logging.getLogger("hercules.tools.system")


def _is_vpn_ip(ip_value: str) -> bool:
    parts = ip_value.split(".")
    if len(parts) != 4 or ip_value == "127.0.0.1":
        return False
    return parts[0] == "10"


def _is_useless_ip(ip_value: str) -> bool:
    return (
        not ip_value
        or ip_value.startswith(("127.", "169.254.", "172.17.", "172.18."))
    )


def _host_network_snapshot() -> dict:
    """Collect host network details without blocking the MCP event loop."""
    host_os = platform.system()
    host_interfaces: list[dict] = []
    recommended_lhost = None
    default_ip = None
    vpn_keywords = (
        "tun",
        "tap",
        "wg",
        "wireguard",
        "vpn",
        "openvpn",
        "nordlynx",
        "zerotier",
        "utun",
        "ppp",
    )

    try:
        # A UDP connect selects a route locally without sending application data.
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as route_socket:
            route_socket.settimeout(2)
            route_socket.connect(("192.0.2.1", 9))
            default_ip = route_socket.getsockname()[0]
        host_interfaces.append({"name": "default_route", "ip": default_ip})
    except OSError:
        pass

    try:
        if host_os == "Windows":
            raw = subprocess.check_output(
                ["ipconfig"],
                text=True,
                timeout=5,
            )
            current_adapter = ""
            for line in raw.splitlines():
                if line and not line.startswith(" "):
                    current_adapter = line.strip().rstrip(":")
                elif "IPv4" in line and ":" in line:
                    ip_value = line.split(":")[-1].strip()
                    if _is_useless_ip(ip_value):
                        continue
                    is_vpn = (
                        any(key in current_adapter.lower() for key in vpn_keywords)
                        or _is_vpn_ip(ip_value)
                    )
                    host_interfaces.append(
                        {"name": current_adapter, "ip": ip_value, "vpn": is_vpn}
                    )
                    if is_vpn and recommended_lhost is None:
                        recommended_lhost = ip_value
        elif host_os == "Darwin":
            raw = subprocess.check_output(
                ["ifconfig"],
                text=True,
                timeout=5,
            )
            current_adapter = ""
            for line in raw.splitlines():
                if line and not line.startswith(("\t", " ")):
                    current_adapter = line.split(":", 1)[0]
                elif "inet " in line:
                    ip_value = line.split("inet ", 1)[1].split(" ", 1)[0]
                    if _is_useless_ip(ip_value):
                        continue
                    is_vpn = (
                        any(current_adapter.lower().startswith(key) for key in vpn_keywords)
                        or _is_vpn_ip(ip_value)
                    )
                    host_interfaces.append(
                        {"name": current_adapter, "ip": ip_value, "vpn": is_vpn}
                    )
                    if is_vpn and recommended_lhost is None:
                        recommended_lhost = ip_value
        else:
            raw = subprocess.check_output(
                ["ip", "-4", "-o", "addr", "show"],
                text=True,
                timeout=5,
            )
            for line in raw.splitlines():
                parts = line.split()
                if len(parts) < 4:
                    continue
                interface = parts[1]
                ip_value = parts[3].split("/", 1)[0]
                if _is_useless_ip(ip_value):
                    continue
                is_vpn = (
                    any(interface.startswith(key) for key in vpn_keywords)
                    or _is_vpn_ip(ip_value)
                )
                host_interfaces.append(
                    {"name": interface, "ip": ip_value, "vpn": is_vpn}
                )
                if is_vpn and recommended_lhost is None:
                    recommended_lhost = ip_value
    except (OSError, subprocess.SubprocessError) as exc:
        logger.debug("Failed to enumerate host interfaces: %s", exc)

    return {
        "host_os": host_os,
        "host_interfaces": host_interfaces,
        "recommended_lhost": recommended_lhost or default_ip,
    }


def register_system_tools(mcp: FastMCP) -> None:

    @mcp.tool(description=TOOL_DESCRIPTIONS["system_start_new_session"])
    async def system_start_new_session(ctx: Context = None) -> dict:
        """
        Start a fresh Hercules session with a clean, isolated workspace.

        WHEN TO USE:
        - You are switching to a DIFFERENT target or engagement.
        - The current workspace is cluttered with artifacts from a previous task.
        - You need a clean environment without leftover scripts, logs, or jobs.

        WHEN NOT TO USE:
        - You are continuing work on the SAME target — just keep using the current session.
        - You only need to run a different tool — all tools share the same session.
        - You only want to clean up a few files — use shell_exec with rm instead of nuking the whole session.

        WHAT THIS DOES:
        1. Creates a NEW workspace subfolder on the host (workspace/{session_id}/).
        2. Stops the current Docker container (if running).
        3. Starts a new container with the clean workspace mounted.
        4. Previous session data is preserved on disk but no longer accessible from the container.

        Returns the new session_id and workspace path.
        """
        context = ctx.lifespan_context
        services = services_from_context(context)
        docker = services.docker

        logger.info("Agent requested new session (current: %s)", docker.session_id)

        old_session = docker.session_id
        try:
            new_session = await services.start_new_session()
        except Exception as exc:
            logger.error("Failed to start new session: %s", exc)
            return {
                "tool": "system_start_new_session",
                "status": "error",
                "error": str(exc),
                "old_session_id": old_session,
                "active_session_id": docker.session_id,
                "container_running": docker.container_running,
                "message": (
                    "Failed to start a new session. See active_session_id and "
                    "container_running for the exact recovery state."
                ),
            }

        return {
            "tool": "system_start_new_session",
            "status": "success",
            "old_session_id": old_session,
            "new_session_id": new_session,
            "workspace": f"/opt/workspace (host: {docker.workspace_path})",
            "message": f"New session '{new_session}' started. Previous session '{old_session}' data preserved on host.",
        }

    @mcp.tool(description=TOOL_DESCRIPTIONS["system_list_sessions"])
    async def system_list_sessions(ctx: Context = None) -> dict:
        """
        List all Hercules session workspaces on the host.

        WHEN TO USE:
        - You want to see what sessions exist, which is active, and how much disk they use.
        - You need to audit whether previous sessions left behind large artifacts.
        - You want to confirm that a new session was created after calling system_start_new_session.

        Returns a list of sessions with: session_id, is_active, file_count, total_size_mb, path.
        """
        docker = ctx.lifespan_context["docker"]
        sessions = await asyncio.to_thread(docker.list_sessions)

        return {
            "tool": "system_list_sessions",
            "active_session": docker.session_id,
            "total_sessions": len(sessions),
            "sessions": sessions,
        }

    @mcp.tool(description=TOOL_DESCRIPTIONS["system_stop_container"])
    async def system_stop_container(ctx: Context = None) -> dict:
        """
        DANGER: Shuts down the Hercules environment for this server lifespan.

        WHEN TO USE:
        - ALL your work is completely finished and you have delivered results to the user.
        - The user explicitly asks you to shut down or clean up.

        WHEN NOT TO USE:
        - You still have tools to run or results to analyze — keep the session alive.
        - You want a fresh workspace for a new target — use system_start_new_session instead.
        - You just want to tidy up files — use shell_exec with rm instead.

        WHAT THIS DOES:
        - Stops and REMOVES the Docker container (not just stop — full removal).
        - Kills all background jobs, Metasploit sessions, and listeners.
        - The workspace files on the host are preserved, but the container is gone.
        - Other tools remain unavailable until system_start_new_session is called.
        """
        docker = ctx.lifespan_context["docker"]

        logger.warning("Agent requested container shutdown! (session: %s)", docker.session_id)

        try:
            session_id = docker.session_id
            services = services_from_context(ctx.lifespan_context)
            await services.stop_for_operator()
            return {
                "tool": "system_stop_container",
                "status": "success",
                "session_id": session_id,
                "message": (
                    f"Session '{session_id}' container stopped and removed. Workspace files "
                    "are preserved; call system_start_new_session to resume."
                ),
            }
        except Exception as exc:
            return {
                "tool": "system_stop_container",
                "status": "error",
                "error": str(exc),
                "container_running": docker.container_running,
                "operator_stopped": bool(
                    getattr(docker, "_operator_stopped", False)
                ),
            }

    @mcp.tool(description=TOOL_DESCRIPTIONS["system_network_info"])
    async def system_network_info(ctx: Context = None) -> dict:
        """
        Get network configuration for the Hercules environment.

        CRITICAL: Call this BEFORE setting LHOST on any exploit or listener.

        Returns the recommended LHOST for reverse shells by detecting:
        - The host OS networking mode (host vs bridge)
        - Host VPN/tunnel interfaces (tun0, tap0, wg0)
        - Container interfaces
        - Which effective ports are forwarded for reverse shell callbacks

        On Linux (host networking): container shares host network, use tun/VPN IP directly.
        On Windows/Mac (bridge networking): the effective listener range is forwarded.
          Use the host's VPN/tunnel IP as LHOST — the target sends the reverse shell to
          HOST_IP:PORT, Docker forwards it to the container where your listener runs.
        Concurrent MCP clients may receive different collision-free effective ports.
        """
        docker = ctx.lifespan_context["docker"]
        host = await asyncio.to_thread(_host_network_snapshot)
        host_os = host["host_os"]
        network_mode = getattr(
            docker,
            "network_mode",
            "host" if host_os == "Linux" else "bridge",
        )
        is_host_network = network_mode == "host"
        listener_description = ",".join(str(port) for port in docker.listener_ports)

        result = {
            "tool": "system_network_info",
            "host_os": host_os,
            "network_mode": network_mode,
            "forwarded_ports": (
                listener_description
                if not is_host_network
                else "all (host networking)"
            ),
            "metasploit_rpc_exposure": (
                f"host loopback only (127.0.0.1:{docker.msf_rpc_port})"
            ),
            "port_allocation": docker.port_allocation,
        }

        # --- Container interfaces ---
        try:
            container_result = await docker.exec_command(
                "hostname -I 2>/dev/null || echo 'unknown'",
                timeout=5, clean_output=False,
            )
            result["container_ips"] = container_result.stdout.strip().split()
        except Exception:
            result["container_ips"] = []

        result["host_interfaces"] = host["host_interfaces"]

        # --- Recommend LHOST ---
        if is_host_network:
            # On Linux host networking, prefer VPN interface, fallback to default
            result["recommended_lhost"] = host["recommended_lhost"]
            result["lhost_note"] = "Host networking — use this IP directly as LHOST."
        else:
            # On bridge networking, must use HOST's IP (target sends to host, Docker forwards)
            result["recommended_lhost"] = host["recommended_lhost"]
            result["lhost_note"] = (
                "Bridge networking — use this HOST IP as LHOST. "
                f"Configured ports ({listener_description}) are forwarded from "
                "host to container. Set LPORT to one of those ports."
            )

        return result

