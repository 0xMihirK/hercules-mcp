"""
Known-pattern banner blocklist for tool output cleaning.

Uses explicit string/regex matching against known ASCII art banners.
NO heuristic density detection — only strips what is positively identified.
This prevents false positives on hex dumps, base64 certs, and exploit payloads.
"""

from __future__ import annotations

import re
from typing import Dict, List

# Each entry: tool_name -> list of regex patterns that match banner lines.
# Patterns are matched against individual lines (re.match, not re.search).
KNOWN_BANNERS: Dict[str, List[str]] = {
    "sqlmap": [
        r"^\s*___\s*$",
        r"^\s*__H__\s*$",
        r"^\s*\|_\|\s*$",
        r"^\[!\] legal disclaimer.*",
        r"^\[!\] Usage of sqlmap for attacking.*",
        r"^\s*___\s*___\s*\[.?\]_+\s*___\s*___\s*\{.*$",
        r"^\s*\|_\s*-\|\s*\.\s*\[.?\]\s*\|\s*\.\'\|\s*\.\s*\|\s*$",
        r"^\s*\|___\|_\s*\[.?\]_\|_\|_\|__\,\|\s*\_\|\s*$",
        r"^\s*\|_\|V\.\.\.\s*\|_\|\s*https?://sqlmap\.org.*$",
    ],
    "commix": [
        r"^\s*[░▓▀█▄▌▐]+\s*$",          # ASCII art blocks
        r"^\s*commix.*v\d+.*$",
        r"^\(\+\) .*commix.*$",
    ],
    "wafw00f": [
        r"^\s*______\s*$",
        r"^\s*/\s*\\\s*$",
        r"^\s*\(\s*Woof!\s*\)\s*$",
        r"^\s*\\\s*____/.*\)$",
        r"^\s*,,.*\)\s*\(_\s*$",
        r"^\s*\.-\.\s*-\s*_______\s*\(.*$",
        r"^\s*\(\)``;\s*\|==\|_______\)\s*\.\)\|__\|\s*$",
        r"^\s*/\s*\('\s*/\|\\\s*\(.*$",
        r"^\s*\(\s*/\s*\)\s*/\s*\|\s*\\\s*\..*$",
        r"^\s*\\\(_\)_\)\)\s*/\s*\|\s*\\\s*\|__\|\s*$",
        r"^\s*~\s*WAFW00F\s*:\s*v.*$",
        r"^\s*The Web Application Firewall.*$",
    ],
    "hydra": [
        r"^Hydra v\d+\.\d+.*$",
        r"^\(c\) \d{4}.*van Hauser.*$",
        r"^Hydra \(https?://.*\).*$",
    ],
    "metasploit": [
        r"^=\[\s*metasploit\s*v\d+.*\]\s*$",
        r"^\+\s*--\s*=\[.*$",
        r"^\s*=\[.*\d+\s+exploits.*$",
        r"^\s*=\[.*\d+\s+payloads.*$",
    ],
    "nikto": [
        r"^-\s*Nikto\s*v\d+.*$",
        r"^\+\s*-{20,}.*$",
    ],
    "wpscan": [
        r"^\s*_+\s*$",
        r"^\s*/\s*\\.*WPScan.*$",
        r"^\s*WordPress Security Scanner.*$",
    ],
}

# Pre-compile all patterns at import time for performance
_COMPILED_BANNERS: Dict[str, List[re.Pattern]] = {
    tool: [re.compile(p) for p in patterns]
    for tool, patterns in KNOWN_BANNERS.items()
}


def strip_known_banners(text: str, tool_name: str) -> str:
    """
    Remove known ASCII art banner lines for a specific tool.

    If the tool_name has no registered patterns, text is returned unmodified.
    """
    patterns = _COMPILED_BANNERS.get(tool_name)
    if not patterns:
        return text

    lines = text.splitlines()
    cleaned = [line for line in lines if not any(p.match(line) for p in patterns)]
    return "\n".join(cleaned)
