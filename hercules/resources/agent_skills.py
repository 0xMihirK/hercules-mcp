"""
Agent skill resources for Hercules.

These resources give MCP clients compact but deep authoring guides for custom
Nmap NSE scripts and Nuclei templates.
"""

from __future__ import annotations

from importlib import resources
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import FastMCP


_REFERENCE_NAMES = {
    "nse": "nmap-nse.md",
    "nuclei": "nuclei.md",
}


def _read_skill_reference(name: str) -> str:
    """Read the canonical installable-skill reference in source or wheel form."""
    filename = _REFERENCE_NAMES[name]
    bundled = (
        resources.files("hercules")
        .joinpath("_bundled_skill")
        .joinpath("hercules-mcp")
        .joinpath("references")
        .joinpath(filename)
    )
    try:
        if bundled.is_file():
            return bundled.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        pass

    source_path = (
        Path(__file__).resolve().parents[2]
        / "skills"
        / "hercules-mcp"
        / "references"
        / filename
    )
    return source_path.read_text(encoding="utf-8")


def register_agent_skill_resources(mcp: FastMCP) -> None:
    """Register AI-agent authoring guides as MCP resources."""

    @mcp.resource(
        "resource://agent_skills/nse",
        description="Detailed AI-agent handbook for authoring complex Nmap NSE scripts "
        "and running them with Hercules nmap_write_nse_script/nmap_run_nse_script.",
        mime_type="text/markdown",
    )
    def get_nse_skills() -> str:
        return _read_skill_reference("nse")

    @mcp.resource(
        "resource://agent_skills/nuclei",
        description="Detailed AI-agent handbook for authoring complex Nuclei templates "
        "and running them with Hercules nuclei_write_template/nuclei_run.",
        mime_type="text/markdown",
    )
    def get_nuclei_skills() -> str:
        return _read_skill_reference("nuclei")
