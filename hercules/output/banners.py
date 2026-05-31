"""
Known-pattern banner blocklist for tool output cleaning.

Only explicit banner lines are stripped. The patterns are intentionally narrow
to avoid false positives on exploit code, certificates, hexdumps, and payloads.
"""

from __future__ import annotations

import re
from typing import Dict, List

# Each entry maps a tool name to regexes matched against individual lines.
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
        r"^\s*__\s*$",
        r"^\s*___\s+___.*v\d+.*$",
        r"^.*commixproject\.com.*$",
        r"^Automated All-in-One OS Command Injection Exploitation Tool.*$",
        r"^Copyright .*Anastasios Stasinopoulos.*$",
        r"^\(!\) Legal disclaimer:.*$",
        r"^\s*commix.*v\d+.*$",
        r"^\(\+\) .*commix.*$",
    ],
    "wafw00f": [
        r"^\s*______\s*$",
        r"^\s*/\s*\\\s*$",
        r"^\s*\(\s*Woof!\s*\)\s*$",
        r"^\s*\(\s*W00f!\s*\)\s*$",
        r"^.*404 Hack Not Found.*$",
        r"^.*405 Not Allowed.*$",
        r"^.*403 Forbidden.*$",
        r"^.*502 Bad Gateway.*$",
        r"^.*500 Internal Error.*$",
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
    "nuclei": [
        r"^\s*__\s+_\s*$",
        r"^\s*____\s+__\s+_______.*$",
        r"^\s*/ __ \\/ / / / ___/.*$",
        r"^\s*/ / / / /_/ / /__/.*$",
        r"^\s*/_/ /_/\\__,_/\\___/.*v\d+.*$",
        r"^\s*projectdiscovery\.io\s*$",
    ],
    "arjun": [
        r"^\s*_\s*$",
        r"^\s*/_\|.*v\d+.*$",
        r"^\s*\(\s*\|/ /\(//\).*$",
        r"^\s*_/.*$",
    ],
}

_COMPILED_BANNERS: Dict[str, List[re.Pattern]] = {
    tool: [re.compile(pattern) for pattern in patterns]
    for tool, patterns in KNOWN_BANNERS.items()
}


def strip_known_banners(text: str, tool_name: str) -> str:
    """Remove known ASCII-art/banner lines for a specific tool."""
    patterns = _COMPILED_BANNERS.get(tool_name)
    if not patterns:
        return text

    lines = text.splitlines()
    cleaned = [line for line in lines if not any(pattern.match(line) for pattern in patterns)]
    return "\n".join(cleaned)
