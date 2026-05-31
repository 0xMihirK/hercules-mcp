"""
Deprecated script helpers for Hercules MCP server.

Script write/run helpers were removed from the registered MCP surface because
the same workflows are covered by shell_exec, shell_exec_background, and
workspace_write_file.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import FastMCP

logger = logging.getLogger("hercules.tools.scripts")


def register_scripts_tools(mcp: "FastMCP") -> None:
    """No-op registrar kept for import compatibility."""
    logger.debug("workspace_scripts is deprecated and no longer registered.")
