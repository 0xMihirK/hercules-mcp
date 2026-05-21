"""
Wordlist management tools for Hercules MCP server.

Helps the agent inspect and verify wordlists in /usr/share/wordlists.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

from fastmcp import Context

if TYPE_CHECKING:
    from fastmcp import FastMCP

logger = logging.getLogger("hercules.tools.wordlist")


def register_wordlist_tools(mcp: "FastMCP") -> None:

    @mcp.tool()
    async def creds_wordlists_manage(
        action: Literal["list", "search", "head", "count"],
        path: str = "/usr/share/wordlists",
        query: str = "",
        lines: int = 10,
        ctx: Context = None,
    ) -> dict:
        """
        Inspect and manage wordlists (SecLists, RockYou, etc.).
        - list: list files in a directory (default /usr/share/wordlists).
        - search: find a specific wordlist by name (e.g., query='rockyou').
        - head: read the first N lines of a wordlist to verify its content.
        - count: count the total number of lines in a wordlist.
        """
        docker = ctx.lifespan_context["docker"]
        concurrency = ctx.lifespan_context["concurrency"]

        cmd = ""
        if action == "list":
            cmd = f"ls -lh {path}"
        elif action == "search":
            cmd = f"find /usr/share/wordlists -iname '*{query}*' -type f"
        elif action == "head":
            cmd = f"head -n {lines} {path}"
        elif action == "count":
            cmd = f"wc -l {path}"

        async with concurrency.acquire_light("creds_wordlists_manage"):
            result = await docker.exec_command(cmd, timeout=30)

        return {"tool": "creds_wordlists_manage", "action": action, **result.to_dict()}
