"""
Per-tool output filters for high-noise tools.

The filters in this module are intentionally explicit. They remove known
banner, progress, and legal boilerplate while keeping findings, payloads,
credentials, target metadata, and no-finding messages.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Dict


@dataclass(frozen=True)
class FilteredOutput:
    text: str
    changed: bool
    note: str = ""


def _lines(text: str) -> list[str]:
    return text.splitlines()


def _join_kept(original: str, kept: list[str]) -> str:
    if not kept and original.strip():
        return original
    return "\n".join(kept).strip()


def _filter_by_line(text: str, predicate: Callable[[str], bool]) -> str:
    return _join_kept(text, [line for line in _lines(text) if predicate(line)])


def filter_hydra(output: str) -> str:
    """Keep successful credentials and the summary."""
    kept = []
    for line in _lines(output):
        if re.search(r"\[\d+\]\[", line) and ("login:" in line or "host:" in line):
            kept.append(line)
        elif "successfully completed" in line.lower():
            kept.append(line)
        elif "valid password" in line.lower():
            kept.append(line)
    return _join_kept(output, kept)


def filter_john(output: str) -> str:
    """Keep cracked hash lines and the summary."""
    kept = []
    for line in _lines(output):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(("Using ", "Loaded ", "Press ", "Warning:")):
            continue
        if stripped.startswith(("Proceeding ", "Cost ", "Will run ", "Created directory:")):
            continue
        if "cracked" in stripped.lower() or "guesses" in stripped.lower():
            kept.append(line)
        elif ":" in stripped and not stripped.startswith("Note:"):
            kept.append(line)
        elif stripped.startswith("Session completed"):
            kept.append(line)
    return _join_kept(output, kept)


def filter_amass(output: str) -> str:
    """Keep discovered domain/IP lines, drop status messages."""
    def keep(line: str) -> bool:
        stripped = line.strip()
        if not stripped:
            return False
        if stripped.startswith("[") or stripped.startswith("Querying"):
            return False
        if "OWASP" in stripped or "Copyright" in stripped:
            return False
        if stripped.startswith("Discoveries are being"):
            return False
        return True

    return _filter_by_line(output, keep)


def filter_wafw00f(output: str) -> str:
    """Remove WAFW00F art while keeping detection results."""
    art_words = (
        "W00f!", "Hack Not Found", "Not Allowed", "Forbidden",
        "Bad Gateway", "Internal Error", "WAFW00F", "Web Application Firewall",
    )

    def keep(line: str) -> bool:
        stripped = line.strip()
        if not stripped:
            return False
        if any(word in stripped for word in art_words):
            return False
        if re.fullmatch(r"[\\/\-|_`'\".,()*=~\s]+", stripped):
            return False
        return True

    return _filter_by_line(output, keep)


def filter_nikto(output: str) -> str:
    """Drop separators/update noise while keeping Nikto target data and findings."""
    def keep(line: str) -> bool:
        stripped = line.strip()
        if not stripped:
            return False
        if re.fullmatch(r"-{20,}", stripped):
            return False
        if "Failed to check for updates" in stripped:
            return False
        if stripped.startswith("+ Start Time:") or stripped.startswith("+ End Time:"):
            return False
        return True

    return _filter_by_line(output, keep)


def filter_wpscan(output: str) -> str:
    """Remove WPScan update chatter while preserving scan results."""
    skip_prefixes = (
        "[i] Updating the Database",
        "[i] Update completed",
        "[i] No WPScan API Token",
    )

    def keep(line: str) -> bool:
        stripped = line.strip()
        return bool(stripped) and not stripped.startswith(skip_prefixes)

    return _filter_by_line(output, keep)


def filter_nuclei(output: str) -> str:
    """Remove Nuclei banner/version chatter while preserving warnings/errors/results."""
    banner_fragments = (
        "projectdiscovery.io",
        "____  __  _______",
        "/_/ /_/",
        "Current nuclei version",
        "Current nuclei-templates version",
        "New templates added",
        "Templates loaded for current scan",
        "Targets loaded for current scan",
        "Scan completed in",
        "Started metrics server",
    )

    def keep(line: str) -> bool:
        stripped = line.strip()
        if not stripped:
            return False
        if any(fragment in stripped for fragment in banner_fragments):
            return False
        if re.fullmatch(r"[_/\\() ,.-]+v?\d*(?:\.\d+)?", stripped):
            return False
        return True

    return _filter_by_line(output, keep)


def filter_arjun(output: str) -> str:
    """Remove Arjun banner and progress, keep discovered/no-parameter results."""
    progress = (
        "[*] Scanning ",
        "[*] Probing the target",
        "[*] Analysing HTTP response",
        "[*] Logicforcing the URL endpoint",
        "[!] Processing chunks:",
    )

    def keep(line: str) -> bool:
        stripped = line.strip()
        if not stripped:
            return False
        if "v2." in stripped and "/" in stripped:
            return False
        if re.fullmatch(r"[_/()|\\' ]+", stripped):
            return False
        if stripped.startswith(progress):
            return False
        return True

    return _filter_by_line(output, keep)


def filter_dalfox(output: str) -> str:
    """Keep Dalfox PoCs/findings and concise no-finding status."""
    def keep(line: str) -> bool:
        stripped = line.strip()
        if not stripped:
            return False
        if stripped.startswith(("[POC]", "[V]", "[R]", "[G]", "[INFO]", "[WARN]", "[ERROR]")):
            return True
        if any(token in stripped.lower() for token in ("xss", "poc", "vulnerab", "no ")):
            return True
        return not stripped.startswith(("[*]", "[I]", "[W]"))

    return _filter_by_line(output, keep)


def filter_commix(output: str) -> str:
    """Strip Commix banner/legal blocks while keeping findings and command output."""
    skip_phrases = (
        "Automated All-in-One OS Command Injection Exploitation Tool",
        "Legal disclaimer:",
        "Developers assume no liability",
        "Copyright",
        "commixproject.com",
        "(@commixproject)",
    )
    art_chars = set("_/\\`' .+-|()<>")

    def keep(line: str) -> bool:
        stripped = line.strip()
        if not stripped:
            return False
        if any(phrase in stripped for phrase in skip_phrases):
            return False
        if set(stripped) <= art_chars:
            return False
        if re.search(r"\bv\d+\.\d+\b", stripped) and "___" in stripped:
            return False
        return True

    return _filter_by_line(output, keep)


def filter_sqlmap(output: str) -> str:
    """Keep sqlmap findings, payloads, DB data, warnings, and final paths."""
    keep_keywords = (
        "parameter:",
        "type:",
        "title:",
        "payload:",
        "back-end dbms",
        "web server operating system",
        "web application technology",
        "current database",
        "available databases",
        "database:",
        "table:",
        "columns for table",
        "entries",
        "dumped to csv file",
        "fetched data logged",
        "command standard output",
        "os shell",
        "is vulnerable",
        "appears to be",
        "identified the following injection",
        "sqlmap resumed",
    )
    noisy_keywords = (
        "testing connection",
        "checking if the target",
        "do you want to",
        "using '/opt/workspace/sqlmap-results",
        "testing url",
        "heuristic",
        "reflective value",
    )
    kept: list[str] = []
    post_context = 0
    for line in _lines(output):
        stripped = line.strip()
        lower = stripped.lower()
        if not stripped:
            continue
        if lower.startswith(("[warning]", "[error]", "[critical]")) or re.match(r"^\[\d\d:\d\d:\d\d\] \[(warning|error|critical)\]", lower):
            kept.append(line)
            continue
        if any(noise in lower for noise in noisy_keywords):
            continue
        if stripped.startswith(("+", "|")) or stripped.startswith("[*] "):
            kept.append(line)
            continue
        if any(keyword in lower for keyword in keep_keywords):
            kept.append(line)
            post_context = 4 if "command standard output" in lower else 2
            continue
        if post_context > 0:
            kept.append(line)
            post_context -= 1
    return _join_kept(output, kept)


def filter_whois(output: str) -> str:
    """Remove registry terms-of-use boilerplate after preserving WHOIS fields."""
    boilerplate = (
        "For more information on Whois status codes",
        "Terms of Use:",
        "NOTICE:",
        "TERMS OF USE:",
        "The data in",
        "By submitting a query",
        ">>> Last update of WHOIS database",
    )
    kept = []
    for line in _lines(output):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(boilerplate):
            if stripped.startswith(">>> Last update"):
                kept.append(line)
            break
        kept.append(line)
    return _join_kept(output, kept)


def apply_tool_filter(text: str, tool_name: str) -> FilteredOutput:
    """Apply a registered high-noise filter and report whether it changed text."""
    filter_fn = TOOL_FILTERS.get(tool_name)
    if not filter_fn:
        return FilteredOutput(text=text, changed=False)
    filtered = filter_fn(text)
    return FilteredOutput(
        text=filtered,
        changed=filtered != text,
        note=f"{tool_name} output compacted",
    )


TOOL_FILTERS: Dict[str, Callable[[str], str]] = {
    "arjun": filter_arjun,
    "bruteforce_hydra": filter_hydra,
    "commix": filter_commix,
    "crack_john": filter_john,
    "dalfox": filter_dalfox,
    "hydra": filter_hydra,
    "john": filter_john,
    "nikto": filter_nikto,
    "nuclei": filter_nuclei,
    "recon_amass": filter_amass,
    "sqlmap": filter_sqlmap,
    "wafw00f": filter_wafw00f,
    "whois": filter_whois,
    "wpscan": filter_wpscan,
}
