"""
Agent skill resources for Hercules.

These resources give MCP clients compact but deep authoring guides for custom
Nmap NSE scripts and Nuclei templates.
"""

from __future__ import annotations

from importlib import resources
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import FastMCP


def _read_resource_text(filename: str) -> str:
    return resources.files("hercules.resources").joinpath(filename).read_text(encoding="utf-8")


def register_agent_skill_resources(mcp: "FastMCP") -> None:
    """Register AI-agent authoring guides as MCP resources."""

    @mcp.resource(
        "resource://agent_skills/nse",
        description="Detailed AI-agent handbook for authoring complex Nmap NSE scripts "
                    "and running them with Hercules nmap_write_nse_script/nmap_run_nse_script.",
        mime_type="text/markdown",
    )
    def get_nse_skills() -> str:
        return _read_resource_text("nse_skills.md")

    @mcp.resource(
        "resource://agent_skills/nuclei",
        description="Detailed AI-agent handbook for authoring complex Nuclei templates "
                    "and running them with Hercules nuclei_write_template/nuclei_run.",
        mime_type="text/markdown",
    )
    def get_nuclei_skills() -> str:
        return _read_resource_text("nuclei_skills.md")
