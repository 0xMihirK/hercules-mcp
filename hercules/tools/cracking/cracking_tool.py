"""
Password and hash cracking tools for Hercules MCP server.

Includes hydra (online brute-force) and john the ripper (offline cracking).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
import uuid

from fastmcp import Context

from hercules.output.filters import TOOL_FILTERS

if TYPE_CHECKING:
    from fastmcp import FastMCP

logger = logging.getLogger("hercules.tools.cracking")

_DEFAULT_WORDLIST = "/usr/share/wordlists/rockyou.txt"


def register_cracking_tools(mcp: "FastMCP") -> None:

    @mcp.tool()
    async def bruteforce_hydra(
        target: str,
        service: str,
        usernames: str,
        passwords: str,
        port: int = 0,
        options: str = "",
        ctx: Context = None,
    ) -> dict:
        """Run hydra brute-force attack against a service.

        Wordlists available at:
        - /usr/share/wordlists/rockyou.txt (14M passwords)
        - /usr/share/wordlists/metasploit/ (service-specific lists)
        - /usr/share/wordlists/seclists/ (if SecLists mounted)
        - /usr/share/wordlists/john.lst (John default list)

        Use file: prefix for wordlist files, e.g. passwords='file:/usr/share/wordlists/rockyou.txt'
        """
        docker = ctx.lifespan_context["docker"]
        config = ctx.lifespan_context["config"]
        concurrency = ctx.lifespan_context["concurrency"]

        config.validate_target(target)

        parts = ["hydra"]

        if usernames.startswith("file:"):
            parts.append(f"-L {usernames[5:]}")
        else:
            parts.append(f"-l {usernames}")

        if passwords.startswith("file:"):
            parts.append(f"-P {passwords[5:]}")
        else:
            parts.append(f"-p {passwords}")

        if port > 0:
            parts.append(f"-s {port}")

        if options:
            parts.append(options)

        parts.append(f"{service}://{target}")

        cmd = " ".join(parts)

        async with concurrency.acquire_heavy("bruteforce_hydra"):
            result = await docker.exec_command(cmd, timeout=600, tool_name="hydra")

        # Apply per-tool filter: keep only credential lines
        hydra_filter = TOOL_FILTERS.get("bruteforce_hydra")
        if hydra_filter:
            result.summary = hydra_filter(result.stdout)

        return {"tool": "bruteforce_hydra", "target": target, "service": service, **result.to_dict()}

    @mcp.tool()
    async def crack_john(
        hashes: str,
        format: str = "",
        wordlist: str = "",
        extra_args: str = "",
        ctx: Context = None,
    ) -> dict:
        """Offline password cracking using John the Ripper. Hashes written to temp file."""
        docker = ctx.lifespan_context["docker"]
        concurrency = ctx.lifespan_context["concurrency"]

        # Write the hashes to a temporary file in the workspace
        run_id = uuid.uuid4().hex[:8]
        hash_file = f"/opt/workspace/hashes_{run_id}.txt"
        await docker.write_file(hash_file, hashes)

        wl = wordlist or _DEFAULT_WORDLIST

        parts = ["john", hash_file, f"--wordlist={wl}"]
        if format:
            parts.append(f"--format={format}")
        if extra_args:
            parts.append(extra_args)

        cmd = " ".join(parts)

        async with concurrency.acquire_heavy("crack_john"):
            # John can run a long time, give it 15 minutes max
            result = await docker.exec_command(cmd, timeout=900, tool_name="john")
            
            # Extract cracked passwords
            show_result = await docker.exec_command(f"john --show {hash_file}", timeout=30, clean_output=False)

        # Cleanup
        await docker.exec_command(f"rm -f {hash_file}", timeout=10, clean_output=False)

        # Apply per-tool filter to main output
        john_filter = TOOL_FILTERS.get("crack_john")
        if john_filter:
            result.summary = john_filter(result.stdout)

        return {
            "tool": "crack_john",
            "format": format,
            "cracked_passwords": show_result.stdout,
            **result.to_dict()
        }
