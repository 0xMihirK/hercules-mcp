"""
Password and hash cracking tools for Hercules MCP server.

Includes hydra (online brute-force) and john the ripper (offline cracking).
"""

from __future__ import annotations

import logging
import shlex
import uuid
from typing import TYPE_CHECKING

from fastmcp import Context

from hercules.core.guidance import TOOL_DESCRIPTIONS, target_error
from hercules.core.security import safe_identifier, shell_quote, validate_target_async
from hercules.output.filters import TOOL_FILTERS

if TYPE_CHECKING:
    from fastmcp import FastMCP

logger = logging.getLogger("hercules.tools.cracking")

_DEFAULT_WORDLIST = "/usr/share/wordlists/rockyou.txt"


def register_cracking_tools(mcp: FastMCP) -> None:

    @mcp.tool(description=TOOL_DESCRIPTIONS["bruteforce_hydra"])
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

        try:
            await validate_target_async(config, target)
        except ValueError as exc:
            return target_error("bruteforce_hydra", target, exc, config)

        try:
            service = safe_identifier(service, label="service", maximum=32)
        except ValueError as exc:
            return {
                "tool": "bruteforce_hydra",
                "status": "invalid_parameter",
                "parameter": "service",
                "error": str(exc),
            }
        if not 0 <= int(port or 0) <= 65_535:
            return {
                "tool": "bruteforce_hydra",
                "status": "invalid_parameter",
                "parameter": "port",
                "error": "port must be between 0 and 65535",
            }

        parts = ["hydra"]

        if usernames.startswith("file:"):
            parts.extend(["-L", shell_quote(usernames[5:], label="username file")])
        else:
            parts.extend(["-l", shell_quote(usernames, label="username")])

        if passwords.startswith("file:"):
            parts.extend(["-P", shell_quote(passwords[5:], label="password file")])
        else:
            parts.extend(["-p", shell_quote(passwords, label="password")])

        if port > 0:
            parts.append(f"-s {port}")

        if options:
            parts.append(options)

        parts.append(shell_quote(f"{service}://{target}", label="service target"))

        cmd = " ".join(parts)

        async with concurrency.acquire_heavy("bruteforce_hydra"):
            result = await docker.exec_command(
                cmd,
                timeout=600,
                tool_name="hydra",
                sensitive_values=[usernames, passwords],
            )

        # Apply per-tool filter: keep only credential lines
        hydra_filter = TOOL_FILTERS.get("bruteforce_hydra")
        if hydra_filter:
            result.summary = hydra_filter(result.stdout)

        return {"tool": "bruteforce_hydra", "target": target, "service": service, **result.to_dict()}

    @mcp.tool(description=TOOL_DESCRIPTIONS["crack_john"])
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

        if format:
            try:
                format = safe_identifier(format, label="hash format", maximum=64)
            except ValueError as exc:
                return {
                    "tool": "crack_john",
                    "status": "invalid_parameter",
                    "parameter": "format",
                    "error": str(exc),
                }

        # Write the hashes to a temporary file in the workspace
        run_id = uuid.uuid4().hex[:8]
        hash_file = f"/opt/workspace/hashes_{run_id}.txt"
        await docker.write_file(hash_file, hashes)

        wl = wordlist or _DEFAULT_WORDLIST

        parts = ["john", shlex.quote(hash_file), f"--wordlist={shell_quote(wl, label='wordlist')}"]
        if format:
            parts.append(f"--format={format}")
        if extra_args:
            parts.append(extra_args)

        cmd = " ".join(parts)

        async with concurrency.acquire_heavy("crack_john"):
            # John can run a long time, give it 15 minutes max
            result = await docker.exec_command(cmd, timeout=900, tool_name="john")
            
            # Extract cracked passwords
            show_result = await docker.exec_command(
                f"john --show {shlex.quote(hash_file)}", timeout=30, clean_output=False
            )

        # Cleanup
        await docker.exec_command(
            f"rm -f {shlex.quote(hash_file)}", timeout=10, clean_output=False
        )

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
