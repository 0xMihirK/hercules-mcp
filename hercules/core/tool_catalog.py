"""
Canonical catalog of Hercules MCP tools, grouped by the underlying *capability*
(the binary/tool you actually opt out of) and then into operator-facing
categories.

Single source of truth shared by:

  * the interactive setup TUI ([hercules_setup.py]) — to render one opt-out
    toggle per capability and estimate the context-token cost of the registered
    tool surface;
  * the server ([hercules/main.py]) — to decide which tools to register, honoring
    the operator's opt-out selection while NEVER skipping the *core* tools the
    agent depends on (``shell_exec`` is the universal fallback for anything you
    opt out of).

**Opt-out granularity is the capability, not the individual MCP tool.** Opting
out of (say) ``metasploit`` automatically opts out of every ``metasploit_*``
subtool; opting out of ``nmap`` drops ``nmap_scan`` + the NSE author/run tools.
The capability's subtools are removed from MCP *registration*, so their
name/description/JSON-schema never enter the model's context (that is the token
saving). The underlying binary stays baked into the image, so the agent can
still drive it through ``shell_exec`` / ``shell_exec_background``.

This module is deliberately dependency-free (only the standard library) so it is
cheap and safe to import from both the server and the host-side setup script.
The flattened tool list is asserted to match the live registered surface by
``tests/test_tool_selection.py`` (and the counts by ``ToolInventoryTests``), so
drift is caught in CI rather than silently desyncing token estimates.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass


@dataclass(frozen=True)
class Capability:
    """One opt-out unit — an underlying binary/tool and the MCP subtools it powers."""

    key: str                       # stable id used in the UI (e.g. "metasploit")
    label: str                     # human label (e.g. "Metasploit")
    binary: str                    # underlying container binary (reachable via shell_exec)
    tools: tuple[str, ...]         # MCP tool names this capability registers
    note: str = ""                 # optional one-liner shown in the UI
    metasploit: bool = False       # subtools additionally gated by SKIP_METASPLOIT


@dataclass(frozen=True)
class ToolCategory:
    """A user-facing group of capabilities shown as one section in the setup TUI."""

    key: str
    title: str
    emoji: str
    blurb: str
    capabilities: tuple[Capability, ...]
    core: bool = False             # core categories are always registered (locked)


# Dotted ``module:function`` paths for every tool registrar, in the same order
# main.py registers them. Used by the setup script to capture the live tool
# surface (name + description + signature) on a throwaway MCP object.
REGISTRARS: tuple[str, ...] = (
    "hercules.tools.network.nmap_tool:register_nmap_tools",
    "hercules.tools.exploitation.metasploit_tool:register_metasploit_tools",
    "hercules.tools.exploitation.sqlmap_tool:register_sqlmap_tools",
    "hercules.tools.web.nuclei_tool:register_nuclei_tools",
    "hercules.tools.exploitation.searchsploit_tool:register_searchsploit_tools",
    "hercules.tools.system.shell_tool:register_shell_tools",
    "hercules.tools.system.file_tool:register_file_tools",
    "hercules.tools.system.system_tool:register_system_tools",
    "hercules.tools.recon.recon_tool:register_recon_tools",
    "hercules.tools.web.web_scanner_tool:register_web_scanner_tools",
    "hercules.tools.network.network_tool:register_network_tools",
    "hercules.tools.cracking.cracking_tool:register_cracking_tools",
    "hercules.tools.ctf.ctf_tool:register_ctf_tools",
    "hercules.tools.browser.browser_tool:register_browser_tools",
)


CATEGORIES: tuple[ToolCategory, ...] = (
    ToolCategory(
        key="core",
        title="Core / System",
        emoji="🧩",
        blurb=(
            "Always included — the container shell, session control, and workspace I/O. "
            "shell_exec is the universal fallback that can run ANY capability you opt out of below."
        ),
        core=True,
        capabilities=(
            Capability("shell", "Container shell + jobs", "bash",
                       ("shell_exec", "shell_exec_background", "shell_check_job", "shell_kill_job")),
            Capability("session", "Session / container control", "hercules session manager",
                       ("system_start_new_session", "system_list_sessions",
                        "system_stop_container", "system_network_info")),
            Capability("workspace", "Workspace file I/O", "host bind-mount",
                       ("workspace_read_file", "workspace_write_file")),
        ),
    ),
    ToolCategory(
        key="recon",
        title="Reconnaissance",
        emoji="🛰",
        blurb="DNS, WHOIS, and subdomain/ASN enumeration to map the target's footprint.",
        capabilities=(
            Capability("dns", "DNS lookups", "dnsx / dig", ("recon_dns",)),
            Capability("whois", "WHOIS", "whois", ("recon_whois",)),
            Capability("amass", "Subdomain / ASN enum", "amass", ("recon_amass",)),
        ),
    ),
    ToolCategory(
        key="network",
        title="Network / Port Scanning",
        emoji="📡",
        blurb="Port/service discovery, NSE scripting, raw HTTP, banner grabbing, and packet crafting.",
        capabilities=(
            Capability("nmap", "Nmap (+ NSE authoring)", "nmap",
                       ("nmap_scan", "nmap_write_nse_script", "nmap_run_nse_script"),
                       note="drops the scan tool AND the NSE write/run subtools"),
            Capability("curl", "HTTP client", "curl", ("network_curl",)),
            Capability("ncat", "Netcat (ban/listen/connect)", "ncat", ("ncat",)),
            Capability("hping3", "Packet crafting", "hping3", ("network_hping3",)),
        ),
    ),
    ToolCategory(
        key="web",
        title="Web Scanning",
        emoji="🕸",
        blurb="Tech fingerprinting, content discovery, XSS/command-injection, Nuclei templates, and SQLi.",
        capabilities=(
            Capability("whatweb", "Web fingerprint", "whatweb / nikto / wafw00f", ("web_scan",)),
            Capability("fuzz", "Content discovery", "ffuf / gobuster", ("fuzz_dirs",)),
            Capability("webvuln", "XSS / command injection", "dalfox / commix", ("web_vuln_scan",)),
            Capability("nuclei", "Nuclei (+ templates)", "nuclei",
                       ("nuclei_run", "nuclei_write_template")),
            Capability("sqlmap", "SQL injection", "sqlmap", ("sqlmap_run",)),
        ),
    ),
    ToolCategory(
        key="exploitation",
        title="Exploitation",
        emoji="💥",
        blurb=(
            "Exploit search plus the full Metasploit workflow. Opting out of Metasploit "
            "drops all 5 metasploit_* subtools (search/run/sessions/payloads/listeners)."
        ),
        capabilities=(
            Capability("searchsploit", "Exploit-DB search", "searchsploit", ("searchsploit",)),
            Capability("metasploit", "Metasploit framework",
                       "metasploit-framework (msfconsole/msfvenom/msfrpcd)",
                       ("metasploit_search", "metasploit_run_module", "metasploit_manage",
                        "metasploit_generate_payload", "metasploit_start_listener"),
                       note="also requires SKIP_METASPLOIT=false to function",
                       metasploit=True),
        ),
    ),
    ToolCategory(
        key="cracking",
        title="Password Cracking",
        emoji="🔓",
        blurb="Online brute-forcing (Hydra) and offline hash cracking (John the Ripper).",
        capabilities=(
            Capability("hydra", "Hydra (online brute-force)", "hydra", ("bruteforce_hydra",)),
            Capability("john", "John the Ripper (offline)", "john", ("crack_john",)),
        ),
    ),
    ToolCategory(
        key="ctf",
        title="CTF / Forensics",
        emoji="🚩",
        blurb="Firmware/file carving and stego extraction for CTF and forensics tasks.",
        capabilities=(
            Capability("binwalk", "Binwalk (carving)", "binwalk", ("ctf_binwalk",)),
            Capability("steghide", "Steghide (stego)", "steghide", ("ctf_steghide",)),
        ),
    ),
    ToolCategory(
        key="browser",
        title="Stealth Browser",
        emoji="🌐",
        blurb=(
            "Drive a bot-evading Chromium: navigate, snapshot the a11y tree, click/type, "
            "screenshot, run JS, capture HAR. The single biggest token block — opt out if "
            "you won't test JS-heavy / anti-bot sites (raw control still works via shell_exec → agent-browser)."
        ),
        capabilities=(
            Capability("browser", "Stealth browser",
                       "agent-browser + cloakbrowser (stealth Chromium)",
                       ("browser_open", "browser_snapshot", "browser_act", "browser_read",
                        "browser_screenshot", "browser_eval", "browser_wait",
                        "browser_session", "browser_skill", "browser_cmd"),
                       note="one toggle opts out of every browser_* subtool"),
        ),
    ),
)


# ---------------------------------------------------------------------------
# Flattened views + convenience frozensets
# ---------------------------------------------------------------------------

def iter_capabilities() -> Iterator[tuple[ToolCategory, Capability]]:
    """Yield (category, capability) for every capability in catalog order."""
    for cat in CATEGORIES:
        for cap in cat.capabilities:
            yield cat, cap


def all_tool_names() -> tuple[str, ...]:
    """Every MCP tool name across all capabilities, in catalog order."""
    names: list[str] = []
    for _cat, cap in iter_capabilities():
        names.extend(cap.tools)
    return tuple(names)


CORE_TOOLS: frozenset[str] = frozenset(
    t for cat, cap in iter_capabilities() if cat.core for t in cap.tools
)

CORE_CAPABILITIES: frozenset[str] = frozenset(
    cap.key for cat, cap in iter_capabilities() if cat.core
)

METASPLOIT_TOOLS: frozenset[str] = frozenset(
    t for _cat, cap in iter_capabilities() if cap.metasploit for t in cap.tools
)

OPTIONAL_TOOLS: frozenset[str] = frozenset(all_tool_names()) - CORE_TOOLS


def capability_of(tool_name: str) -> Capability | None:
    """Return the capability that owns an MCP tool name, or None."""
    for _cat, cap in iter_capabilities():
        if tool_name in cap.tools:
            return cap
    return None


def tools_for_capabilities(keys: Iterable[str]) -> frozenset[str]:
    """Expand a set of capability keys to the union of their MCP tool names."""
    keyset = set(keys)
    out: set[str] = set()
    for _cat, cap in iter_capabilities():
        if cap.key in keyset:
            out.update(cap.tools)
    return frozenset(out)


def disabled_capabilities(disabled_tools: Iterable[str]) -> frozenset[str]:
    """Given a set of disabled MCP tool names, return the keys of capabilities
    that are fully disabled (every subtool present in the set). Core capabilities
    are never reported as disabled."""
    dset = set(disabled_tools)
    out: set[str] = set()
    for cat, cap in iter_capabilities():
        if cat.core:
            continue
        if cap.tools and all(t in dset for t in cap.tools):
            out.add(cap.key)
    return frozenset(out)


def parse_disabled(value: str) -> frozenset[str]:
    """Parse a comma/space separated ``HERCULES_DISABLED_TOOLS`` value into a set
    of MCP tool names. Core tools can never be disabled, so they are filtered out
    defensively. Unknown names are kept (a renamed tool stays disabled
    harmlessly)."""
    if not value or not value.strip():
        return frozenset()
    raw = {
        part.strip()
        for chunk in value.split(",")
        for part in chunk.split()
        if part.strip()
    }
    return frozenset(raw) - CORE_TOOLS


def format_disabled(names: "set[str] | frozenset[str] | list[str]") -> str:
    """Serialize a disabled-tool set to the ``HERCULES_DISABLED_TOOLS`` form."""
    return ",".join(sorted(set(names) - CORE_TOOLS))
