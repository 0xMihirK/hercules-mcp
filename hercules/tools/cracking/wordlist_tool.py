"""
Deprecated wordlist helpers for Hercules MCP server.

Wordlist inspection was removed from the registered MCP surface because the
same operations are covered by shell_exec.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import FastMCP

logger = logging.getLogger("hercules.tools.wordlist")


def register_wordlist_tools(mcp: "FastMCP") -> None:
    """No-op registrar kept for import compatibility."""
    logger.debug("creds_wordlists_manage is deprecated and no longer registered.")
