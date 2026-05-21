"""
Per-tool output filters for high-noise tools.

Generic sanitization does almost nothing for brute-force tools that print
a status line for every password tried. These filters extract only the
actionable output (found credentials, cracked hashes, discovered domains).
"""

from __future__ import annotations

import re
from typing import Callable, Dict


def filter_hydra(output: str) -> str:
    """Keep only lines showing successful credentials and the summary."""
    lines = output.splitlines()
    kept = []
    for line in lines:
        # Credential lines: [22][ssh] host: 10.0.0.1   login: admin   password: pass123
        if re.search(r"\[\d+\]\[", line) and ("login:" in line or "host:" in line):
            kept.append(line)
        # Summary line
        elif "successfully completed" in line.lower():
            kept.append(line)
        elif "valid password" in line.lower():
            kept.append(line)
    return "\n".join(kept)


def filter_john(output: str) -> str:
    """Keep only cracked hash lines and the summary."""
    lines = output.splitlines()
    kept = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Skip John metadata lines
        if stripped.startswith("Using ") or stripped.startswith("Loaded "):
            continue
        if stripped.startswith("Press ") or stripped.startswith("Warning:"):
            continue
        if stripped.startswith("Proceeding ") or stripped.startswith("Cost "):
            continue
        # Keep cracked results and summary
        if "cracked" in stripped.lower() or "guesses" in stripped.lower():
            kept.append(line)
        elif ":" in stripped and not stripped.startswith("Note:"):
            # Cracked passwords appear as hash:password
            kept.append(line)
    return "\n".join(kept)


def filter_amass(output: str) -> str:
    """Keep only discovered domain/IP lines, drop status messages."""
    lines = output.splitlines()
    kept = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Skip Amass status/progress lines
        if stripped.startswith("[") or stripped.startswith("Querying"):
            continue
        if "OWASP" in stripped or "Copyright" in stripped:
            continue
        if stripped.startswith("Discoveries are being"):
            continue
        kept.append(line)
    return "\n".join(kept)


# Registry mapping tool names to their filter functions.
# Used by the pipeline to automatically apply the correct filter.
TOOL_FILTERS: Dict[str, Callable[[str], str]] = {
    "bruteforce_hydra": filter_hydra,
    "crack_john": filter_john,
    "recon_amass": filter_amass,
}
