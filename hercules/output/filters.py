"""Conservative, evidence-first compaction for characterized scanner noise."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass

FILTER_VERSION = 2
_DIAGNOSTIC_RE = re.compile(
    r"(?i)(?:^|\W)(?:warn(?:ing)?|err(?:or)?|critical|fatal|failed|failure|"
    r"timeout|incomplete|denied|locked|rate.?limit|traceback|exception)(?:\W|$)"
)


@dataclass(frozen=True)
class FilteredOutput:
    text: str
    changed: bool
    note: str = ""
    removed_lines: int = 0
    removed_chars: int = 0
    version: int = FILTER_VERSION
    semantic: bool = True


def _lines(text: str) -> list[str]:
    return text.splitlines()


def _join_kept(original: str, kept: list[str]) -> str:
    if kept == original.splitlines():
        return original
    if not kept and original.strip():
        return original
    joined = "\n".join(kept)
    if original.endswith(("\n", "\r")) and joined:
        joined += "\n"
    return joined


def _filter_by_line(text: str, predicate: Callable[[str], bool]) -> str:
    kept = [line for line in _lines(text) if predicate(line)]
    return _join_kept(text, kept)


def _diagnostic(line: str) -> bool:
    return bool(_DIAGNOSTIC_RE.search(line))


def filter_hydra(output: str) -> str:
    """Remove only Hydra banner/attempt progress; keep all result semantics."""
    noisy = (
        re.compile(r"^Hydra v[\d.]+\s+starting\b", re.IGNORECASE),
        re.compile(r"^Hydra \(.+thc\.org", re.IGNORECASE),
        re.compile(r"^\[DATA\]\s+(?:max \d+ tasks|attacking )", re.IGNORECASE),
        re.compile(r"^\[ATTEMPT\]\s+target ", re.IGNORECASE),
    )
    return _filter_by_line(
        output,
        lambda line: bool(line.strip())
        and (_diagnostic(line) or not any(pattern.search(line.strip()) for pattern in noisy)),
    )


def filter_john(output: str) -> str:
    """Drop only characterized startup/progress chatter."""
    noisy_prefixes = (
        "Using default input encoding:",
        "Press 'q' or Ctrl-C",
        "Proceeding with ",
        "Will run ",
        "Created directory:",
    )
    return _filter_by_line(
        output,
        lambda line: bool(line.strip())
        and (_diagnostic(line) or not line.strip().startswith(noisy_prefixes)),
    )


def filter_amass(output: str) -> str:
    """Drop informational progress while preserving discoveries and diagnostics."""
    def keep(line: str) -> bool:
        stripped = line.strip()
        if not stripped:
            return False
        if _diagnostic(stripped):
            return True
        if stripped.startswith(("[INF]", "[DBG]", "Querying")):
            return False
        if "OWASP Amass" in stripped or stripped.startswith("Copyright "):
            return False
        return not stripped.startswith("Discoveries are being")

    return _filter_by_line(output, keep)


def filter_wafw00f(output: str) -> str:
    """Remove only WAFW00F art; HTTP status and detection evidence stay."""
    banner_words = ("W00f!", "WAFW00F :", "The Web Application Firewall")

    def keep(line: str) -> bool:
        stripped = line.strip()
        if not stripped:
            return False
        if any(word in stripped for word in banner_words):
            return False
        return not bool(re.fullmatch(r"[\\/\-|_`'\".,()*=~\s]+", stripped))

    return _filter_by_line(output, keep)


def filter_nikto(output: str) -> str:
    """Drop separators/update timestamps while keeping target data and findings."""
    def keep(line: str) -> bool:
        stripped = line.strip()
        if not stripped:
            return False
        if _diagnostic(stripped):
            return True
        if re.fullmatch(r"-{20,}", stripped):
            return False
        return not stripped.startswith(("+ Start Time:", "+ End Time:"))

    return _filter_by_line(output, keep)


def filter_wpscan(output: str) -> str:
    """Remove update chatter while retaining capability/completeness warnings."""
    skip_prefixes = ("[i] Updating the Database", "[i] Update completed")
    return _filter_by_line(
        output,
        lambda line: bool(line.strip()) and not line.strip().startswith(skip_prefixes),
    )


def filter_nuclei(output: str) -> str:
    """Remove artwork/version ads; keep counts, duration, warnings, and results."""
    banner_fragments = (
        "projectdiscovery.io",
        "____  __  _______",
        "/_/ /_/",
        "Current nuclei version",
        "Current nuclei-templates version",
        "New templates added",
        "Started metrics server",
    )

    def keep(line: str) -> bool:
        stripped = line.strip()
        if not stripped:
            return False
        if _diagnostic(stripped):
            return True
        if any(fragment in stripped for fragment in banner_fragments):
            return False
        return not bool(re.fullmatch(r"[_/\\() ,.-]+v?\d*(?:\.\d+)?", stripped))

    return _filter_by_line(output, keep)


def filter_arjun(output: str) -> str:
    """Remove exact progress phrases; keep findings, no-result text, and errors."""
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
        if _diagnostic(stripped):
            return True
        if stripped.startswith(progress):
            return False
        if re.fullmatch(r"/_\|\s+_\s+'\s+v\d+(?:\.\d+)+", stripped):
            return False
        return not bool(re.fullmatch(r"[_/()|\\' ]+", stripped))

    return _filter_by_line(output, keep)


def filter_dalfox(output: str) -> str:
    """Remove only characterized progress meters; retain all semantic lines."""
    def keep(line: str) -> bool:
        stripped = line.strip()
        if not stripped:
            return False
        if _diagnostic(stripped):
            return True
        if re.fullmatch(r"(?:\[[*I]\]\s*)?\d+%.*", stripped):
            return False
        return not stripped.startswith("Scanning [")

    return _filter_by_line(output, keep)


def filter_commix(output: str) -> str:
    """Strip explicit banner/legal lines while keeping command output."""
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
        if _diagnostic(stripped):
            return True
        if any(phrase in stripped for phrase in skip_phrases):
            return False
        if set(stripped) <= art_chars:
            return False
        return not (re.search(r"\bv\d+\.\d+\b", stripped) and "___" in stripped)

    return _filter_by_line(output, keep)


def filter_sqlmap(output: str) -> str:
    """Compact repetitive probe progress without allowlisting result formats."""
    noisy_patterns = (
        re.compile(r"(?i)\]\s+\[info\]\s+testing\s+'"),
        re.compile(r"(?i)\]\s+\[info\]\s+testing connection\b"),
        re.compile(r"(?i)\]\s+\[info\]\s+checking if the target\b"),
        re.compile(r"(?i)\]\s+\[info\]\s+checking if .+ is dynamic\b"),
        re.compile(r"(?i)\]\s+\[info\]\s+heuristic\b"),
        re.compile(r"(?i)\]\s+\[info\]\s+testing url\b"),
    )
    kept: list[str] = []
    removed = 0
    for line in _lines(output):
        if not line.strip():
            continue
        if not _diagnostic(line) and any(pattern.search(line) for pattern in noisy_patterns):
            removed += 1
            continue
        kept.append(line)
    if removed:
        kept.append(f"[Hercules compacted {removed} repetitive SQLMap probe lines]")
    return _join_kept(output, kept)


def filter_whois(output: str) -> str:
    """Remove explicit terms-of-use prose without terminating field parsing."""
    boilerplate = (
        "For more information on Whois status codes",
        "Terms of Use:",
        "NOTICE:",
        "TERMS OF USE:",
        "The data in",
        "By submitting a query",
    )
    kept: list[str] = []
    for line in _lines(output):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(">>> Last update of WHOIS database"):
            kept.append(line)
            continue
        if stripped.startswith(boilerplate):
            continue
        kept.append(line)
    return _join_kept(output, kept)


def apply_tool_filter(text: str, tool_name: str) -> FilteredOutput:
    """Apply a registered high-noise filter and report exact transform stats."""
    filter_fn = TOOL_FILTERS.get(tool_name)
    if not filter_fn:
        return FilteredOutput(text=text, changed=False, semantic=False)
    filtered = filter_fn(text)
    changed = filtered != text
    original_lines = text.splitlines()
    filtered_counts = Counter(filtered.splitlines())
    removed: list[str] = []
    for line in original_lines:
        if filtered_counts[line]:
            filtered_counts[line] -= 1
        else:
            removed.append(line)
    return FilteredOutput(
        text=filtered,
        changed=changed,
        note=f"{tool_name} output compacted" if changed else "",
        removed_lines=len(removed),
        removed_chars=sum(len(line) + 1 for line in removed),
    )


TOOL_FILTERS: dict[str, Callable[[str], str]] = {
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
