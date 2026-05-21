"""
System management tools for Hercules MCP server.

Provides container lifecycle controls: start new sessions, list sessions,
and stop the environment. All tools carry explicit agent-facing instructions
in their docstrings explaining WHEN and WHY to use them.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fastmcp import Context

if TYPE_CHECKING:
    from fastmcp import FastMCP

logger = logging.getLogger("hercules.tools.system")


def register_system_tools(mcp: "FastMCP") -> None:

    @mcp.tool()
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
        docker = ctx.lifespan_context["docker"]

        logger.info("Agent requested new session (current: %s)", docker.session_id)

        old_session = docker.session_id
        try:
            new_session = await docker.restart_container()
        except Exception as exc:
            logger.error("Failed to start new session: %s", exc)
            return {
                "tool": "system_start_new_session",
                "status": "error",
                "error": str(exc),
                "old_session_id": old_session,
                "message": "Failed to start new session. The previous session may have been stopped.",
            }

        # Re-init MSF client if Metasploit is enabled
        config = ctx.lifespan_context["config"]
        msf_client = None
        if not config.skip_metasploit:
            try:
                msf_client = await docker.wait_for_msfrpcd()
            except TimeoutError:
                logger.warning("msfrpcd did not become ready in new session.")
        ctx.lifespan_context["msf_client"] = msf_client

        return {
            "tool": "system_start_new_session",
            "status": "success",
            "old_session_id": old_session,
            "new_session_id": new_session,
            "workspace": f"/opt/workspace (host: workspace/{new_session}/)",
            "message": f"New session '{new_session}' started. Previous session '{old_session}' data preserved on host.",
        }

    @mcp.tool()
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
        sessions = docker.list_sessions()

        return {
            "tool": "system_list_sessions",
            "active_session": docker.session_id,
            "total_sessions": len(sessions),
            "sessions": sessions,
        }

    @mcp.tool()
    async def system_stop_container(ctx: Context = None) -> dict:
        """
        DANGER: Permanently shuts down the Hercules environment. DESTRUCTIVE.

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
        - You will NOT be able to run any more tools after this.
        """
        docker = ctx.lifespan_context["docker"]

        logger.warning("Agent requested container shutdown! (session: %s)", docker.session_id)

        try:
            session_id = docker.session_id
            await docker.stop_container()
            return {
                "tool": "system_stop_container",
                "status": "success",
                "session_id": session_id,
                "message": f"Session '{session_id}' container stopped and removed. Workspace files preserved on host.",
            }
        except Exception as exc:
            return {"tool": "system_stop_container", "status": "error", "error": str(exc)}

    @mcp.tool()
    async def system_network_info(ctx: Context = None) -> dict:
        """
        Get network configuration for the Hercules environment.

        CRITICAL: Call this BEFORE setting LHOST on any exploit or listener.

        Returns the recommended LHOST for reverse shells by detecting:
        - The host OS networking mode (host vs bridge)
        - Host VPN/tunnel interfaces (tun0, tap0, wg0)
        - Container interfaces
        - Which ports are forwarded for reverse shell callbacks (4444-4464)

        On Linux (host networking): container shares host network, use tun/VPN IP directly.
        On Windows/Mac (bridge networking): ports 4444-4464 are forwarded from host to container.
          Use the host's VPN/tunnel IP as LHOST — the target sends the reverse shell to
          HOST_IP:PORT, Docker forwards it to the container where your listener runs.
        """
        import platform as plat
        import socket
        import subprocess

        docker = ctx.lifespan_context["docker"]
        host_os = plat.system()
        is_host_network = (host_os == "Linux")

        result = {
            "tool": "system_network_info",
            "host_os": host_os,
            "network_mode": "host" if is_host_network else "bridge",
            "forwarded_ports": "4444-4464" if not is_host_network else "all (host networking)",
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

        # --- Host interfaces ---
        host_interfaces = []
        recommended_lhost = None

        try:
            # Get default route IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(2)
            s.connect(("8.8.8.8", 80))
            default_ip = s.getsockname()[0]
            s.close()
            host_interfaces.append({"name": "default_route", "ip": default_ip})
        except Exception:
            default_ip = None

        # Helper to determine if an IP is likely a VPN IP based on subnet
        def is_vpn_ip(ip_str: str) -> bool:
            if not ip_str or ip_str == "127.0.0.1": return False
            parts = ip_str.split('.')
            if len(parts) != 4: return False
            try:
                # 10.x.x.x (Very common for VPNs like HTB, THM)
                if parts[0] == '10': return True
                # 172.16.x.x - 172.31.x.x
                if parts[0] == '172' and 16 <= int(parts[1]) <= 31:
                    # Docker uses 172.17+, so be careful, but VPNs sometimes use this too.
                    pass
                # 192.168.x.x is usually local LAN, but some VPNs use it.
            except ValueError:
                pass
            return False

        def is_useless_ip(ip_str: str) -> bool:
            if not ip_str: return True
            # Ignore loopback, APIPA, and common Docker bridge default subnets
            return ip_str.startswith("127.") or ip_str.startswith("169.254.") or ip_str.startswith("172.17.") or ip_str.startswith("172.18.")

        # Detect VPN/tunnel interfaces
        vpn_keywords = ("tun", "tap", "wg", "wireguard", "vpn", "openvpn", "nordlynx", "zerotier", "utun", "ppp")
        try:
            if host_os == "Windows":
                raw = subprocess.check_output("ipconfig", text=True, timeout=5)
                lines = raw.splitlines()
                current_adapter = ""
                for line in lines:
                    if line and not line.startswith(" "):
                        current_adapter = line.strip().rstrip(":")
                    elif "IPv4" in line and ":" in line:
                        ip = line.split(":")[-1].strip()
                        if is_useless_ip(ip): continue
                        is_vpn = any(k in current_adapter.lower() for k in vpn_keywords) or is_vpn_ip(ip)
                        entry = {"name": current_adapter, "ip": ip, "vpn": is_vpn}
                        host_interfaces.append(entry)
                        if is_vpn and recommended_lhost is None:
                            recommended_lhost = ip
            elif host_os == "Darwin": # Mac
                raw = subprocess.check_output(["ifconfig"], text=True, timeout=5)
                lines = raw.splitlines()
                current_adapter = ""
                for line in lines:
                    if line and not line.startswith("\t") and not line.startswith(" "):
                        current_adapter = line.split(":")[0]
                    elif "inet " in line:
                        ip = line.split("inet ")[1].split(" ")[0]
                        if not is_useless_ip(ip):
                            is_vpn = any(current_adapter.lower().startswith(k) for k in vpn_keywords) or is_vpn_ip(ip)
                            entry = {"name": current_adapter, "ip": ip, "vpn": is_vpn}
                            host_interfaces.append(entry)
                            if is_vpn and recommended_lhost is None:
                                recommended_lhost = ip
            else: # Linux
                raw = subprocess.check_output(["ip", "-4", "-o", "addr", "show"], text=True, timeout=5)
                for line in raw.splitlines():
                    parts = line.split()
                    if len(parts) >= 4:
                        iface = parts[1]
                        ip = parts[3].split("/")[0]
                        if not is_useless_ip(ip):
                            is_vpn = any(iface.startswith(k) for k in vpn_keywords) or is_vpn_ip(ip)
                            entry = {"name": iface, "ip": ip, "vpn": is_vpn}
                            host_interfaces.append(entry)
                            if is_vpn and recommended_lhost is None:
                                recommended_lhost = ip
        except Exception as exc:
            logger.debug("Failed to enumerate host interfaces: %s", exc)

        result["host_interfaces"] = host_interfaces

        # --- Recommend LHOST ---
        if is_host_network:
            # On Linux host networking, prefer VPN interface, fallback to default
            if recommended_lhost is None:
                recommended_lhost = default_ip
            result["recommended_lhost"] = recommended_lhost
            result["lhost_note"] = "Host networking — use this IP directly as LHOST."
        else:
            # On bridge networking, must use HOST's IP (target sends to host, Docker forwards)
            if recommended_lhost is None:
                recommended_lhost = default_ip
            result["recommended_lhost"] = recommended_lhost
            result["lhost_note"] = (
                "Bridge networking — use this HOST IP as LHOST. "
                "Ports 4444-4464 are forwarded from host to container. "
                "Set LPORT to a value in that range."
            )

        return result

