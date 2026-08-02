"""
Canonical catalog of Hercules MCP tools, grouped by the underlying *capability*
(the binary/tool you actually opt out of) and then into operator-facing
categories.

Single source of truth shared by:

  * ``hercules-install catalog`` and the selective image builder;
  * the server ([hercules/main.py]) — to decide which tools to register, honoring
    the operator's selection while NEVER skipping the *core* tools the agent
    depends on. ``shell_exec`` remains the raw-command escape hatch, but it
    cannot invoke a backend binary from an omitted capability.

**Opt-out granularity is the capability, not the individual MCP tool.** Opting
out of (say) ``metasploit`` automatically opts out of every ``metasploit_*``
subtool; opting out of ``nmap`` drops ``nmap_scan`` + the NSE author/run tools.
The capability's subtools are removed from MCP *registration*, so their
name/description/JSON-schema never enter the model's context (that is the token
saving). New managed images contain only confirmed capability bundles.
Independently hidden tools remain installed but are omitted from registration.

This module is deliberately dependency-free (only the standard library) so it is
cheap and safe to import from both the server and the host-side installer.
The flattened tool list is asserted to match the live registered surface by the
local-only acceptance suite so drift cannot silently desync token estimates.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass


@dataclass(frozen=True)
class Capability:
    """One opt-out unit — an underlying binary/tool and the MCP subtools it powers."""

    key: str                       # stable id used in the UI (e.g. "metasploit")
    label: str                     # human label (e.g. "Metasploit")
    binary: str                    # backend installed when this bundle is selected
    tools: tuple[str, ...]         # MCP tool names this capability registers
    note: str = ""                 # optional one-liner shown in the UI
    metasploit: bool = False       # subtools additionally gated by SKIP_METASPLOIT


@dataclass(frozen=True)
class ToolCategory:
    """A user-facing group of capabilities shown by the installer catalog."""

    key: str
    title: str
    emoji: str
    blurb: str
    capabilities: tuple[Capability, ...]
    core: bool = False             # core categories are always registered (locked)


@dataclass(frozen=True)
class ToolRegistrar:
    """One registration module with its top-level capability gate."""

    path: str
    metasploit: bool = False


@dataclass(frozen=True)
class CapabilityInstall:
    """Exact install/readiness metadata for one optional bundle."""

    backends: tuple[str, ...] = ()
    wordlists: tuple[str, ...] = ()
    browser: bool = False


# Dotted ``module:function`` paths for every tool registrar, in the same order
# main.py registers them. Used by installer validation to capture the live tool
# surface (name + description + signature) on a throwaway MCP object.
TOOL_REGISTRARS: tuple[ToolRegistrar, ...] = (
    ToolRegistrar("hercules.tools.network.nmap_tool:register_nmap_tools"),
    ToolRegistrar(
        "hercules.tools.exploitation.metasploit_tool:register_metasploit_tools",
        metasploit=True,
    ),
    ToolRegistrar("hercules.tools.exploitation.sqlmap_tool:register_sqlmap_tools"),
    ToolRegistrar("hercules.tools.web.nuclei_tool:register_nuclei_tools"),
    ToolRegistrar(
        "hercules.tools.exploitation.searchsploit_tool:register_searchsploit_tools"
    ),
    ToolRegistrar("hercules.tools.system.shell_tool:register_shell_tools"),
    ToolRegistrar("hercules.tools.system.file_tool:register_file_tools"),
    ToolRegistrar("hercules.tools.system.system_tool:register_system_tools"),
    ToolRegistrar("hercules.tools.recon.recon_tool:register_recon_tools"),
    ToolRegistrar("hercules.tools.web.web_scanner_tool:register_web_scanner_tools"),
    ToolRegistrar("hercules.tools.network.network_tool:register_network_tools"),
    ToolRegistrar("hercules.tools.cracking.cracking_tool:register_cracking_tools"),
    ToolRegistrar("hercules.tools.ctf.ctf_tool:register_ctf_tools"),
    ToolRegistrar("hercules.tools.browser.browser_tool:register_browser_tools"),
)

# Backward-compatible flattened view used by installer validation.
REGISTRARS: tuple[str, ...] = tuple(item.path for item in TOOL_REGISTRARS)


CATEGORIES: tuple[ToolCategory, ...] = (
    ToolCategory(
        key="core",
        title="Core / System",
        emoji="🧩",
        blurb=(
            "Always included — the container shell, session control, and workspace I/O. "
            "shell_exec can run arbitrary commands, but optional binaries exist only when "
            "their capability bundle is installed."
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
                       note="includes the scan tool and NSE write/run subtools"),
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
            "Drive cloakbrowser Chromium: navigate, snapshot the a11y tree, click/type, "
            "return native screenshots, run JS, capture HAR. Fingerprint reduction can "
            "improve consistency but does not guarantee bot-detection avoidance."
        ),
        capabilities=(
            Capability("browser", "Stealth browser",
                       "agent-browser + cloakbrowser (stealth Chromium)",
                       ("browser_open", "browser_snapshot", "browser_act", "browser_read",
                        "browser_screenshot", "browser_eval", "browser_wait",
                        "browser_session", "browser_skill", "browser_cmd"),
                       note="headless-only bundle containing every browser_* subtool"),
        ),
    ),
)

# Installation metadata stays separate from operator-facing labels so the
# public catalog remains readable while image/runtime checks use exact command
# names. Core commands are supplied by the base image and are always present.
CAPABILITY_INSTALL: dict[str, CapabilityInstall] = {
    "shell": CapabilityInstall(("bash", "python3")),
    "session": CapabilityInstall(("ip", "ps")),
    "workspace": CapabilityInstall(("base64", "sha256sum")),
    "dns": CapabilityInstall(("dig", "dnsx")),
    "whois": CapabilityInstall(("whois",)),
    "amass": CapabilityInstall(("amass",)),
    "nmap": CapabilityInstall(("nmap",)),
    "curl": CapabilityInstall(("curl",)),
    "ncat": CapabilityInstall(("ncat",)),
    "hping3": CapabilityInstall(("hping3",)),
    "whatweb": CapabilityInstall(
        ("httpx", "whatweb", "wafw00f", "nikto", "wpscan", "arjun")
    ),
    "fuzz": CapabilityInstall(("ffuf", "gobuster"), ("seclists",)),
    "webvuln": CapabilityInstall(("dalfox", "commix")),
    "nuclei": CapabilityInstall(("nuclei",)),
    "sqlmap": CapabilityInstall(("sqlmap",)),
    "searchsploit": CapabilityInstall(("searchsploit",)),
    "metasploit": CapabilityInstall(("msfconsole", "msfrpcd", "msfvenom")),
    "hydra": CapabilityInstall(("hydra",), ("rockyou",)),
    "john": CapabilityInstall(("john",), ("rockyou",)),
    "binwalk": CapabilityInstall(("binwalk",)),
    "steghide": CapabilityInstall(("steghide", "exiftool", "xxd")),
    # ncat is an internal stream-relay dependency. Installing it here does not
    # register the separate ncat MCP tool unless the ncat bundle is selected.
    "browser": CapabilityInstall(("agent-browser", "ncat"), browser=True),
}

# Informational estimates only. They help an agent compare profiles without
# claiming a model-specific tokenizer or replacing live schema validation.
CAPABILITY_CONTEXT_TOKENS: dict[str, int] = {
    "shell": 700, "session": 350, "workspace": 300,
    "dns": 170, "whois": 130, "amass": 170, "nmap": 660, "curl": 250,
    "ncat": 310, "hping3": 180, "whatweb": 470, "fuzz": 260,
    "webvuln": 280, "nuclei": 480, "sqlmap": 450, "searchsploit": 180,
    "metasploit": 1200, "hydra": 280, "john": 240, "binwalk": 180,
    "steghide": 210, "browser": 2500,
}


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
ALL_CAPABILITIES: frozenset[str] = frozenset(
    cap.key for _cat, cap in iter_capabilities()
)
OPTIONAL_CAPABILITIES: frozenset[str] = ALL_CAPABILITIES - CORE_CAPABILITIES
FULL_TOOL_COUNT = len(all_tool_names())
LIGHT_TOOL_COUNT = FULL_TOOL_COUNT - len(METASPLOIT_TOOLS)

if (FULL_TOOL_COUNT, LIGHT_TOOL_COUNT) != (45, 40):
    raise RuntimeError(
        "Hercules public tool catalog changed unexpectedly: "
        f"{FULL_TOOL_COUNT}/{LIGHT_TOOL_COUNT}, expected 45/40"
    )

# Structured selectors that installable agent guidance must describe.
TOOL_SELECTORS: dict[str, dict[str, tuple[str, ...]]] = {
    "nmap_scan": {
        "mode": ("quick", "aggressive", "port", "script", "custom"),
    },
    "web_scan": {
        "tool": ("httpx", "whatweb", "wafw00f", "nikto", "wpscan", "arjun"),
    },
    "fuzz_dirs": {"tool": ("gobuster", "ffuf")},
    "web_vuln_scan": {"tool": ("dalfox", "commix")},
    "ncat": {"action": ("connect", "listen", "interact")},
    "recon_dns": {"tool": ("dig", "dnsx")},
    "searchsploit": {"action": ("search", "get")},
    "sqlmap_run": {
        "action": ("scan_basic", "scan_custom", "enumerate", "dump", "os_cmd"),
        "enum_what": ("dbs", "tables", "columns", "users", "privileges", "passwords"),
    },
    "ctf_steghide": {"action": ("info", "extract")},
    "workspace_read_file": {"encoding": ("text", "base64")},
    "metasploit_run_module": {
        "module_type": ("exploit", "auxiliary", "post"),
    },
    "metasploit_manage": {
        "action": (
            "list_sessions",
            "interact_session",
            "close_session",
            "list_jobs",
            "stop_job",
        ),
    },
    "browser_act": {
        "action": (
            "click",
            "fill",
            "type",
            "press",
            "hover",
            "select",
            "check",
            "uncheck",
        ),
        "target_type": ("ref", "css", "role", "text", "label"),
    },
    "browser_read": {
        "what": ("text", "html", "value", "url", "title"),
        "target_type": ("ref", "css", "role", "text", "label"),
    },
    "browser_wait": {
        "condition": ("selector", "ms", "text", "url", "load"),
    },
    "browser_session": {
        "action": ("current", "list", "close", "close_all", "stream"),
    },
}


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


def normalize_capabilities(keys: Iterable[str]) -> frozenset[str]:
    """Validate a selection and always include mandatory core bundles."""
    requested = {str(key).strip().lower() for key in keys if str(key).strip()}
    unknown = requested - ALL_CAPABILITIES
    if unknown:
        raise ValueError("unknown Hercules capabilities: " + ", ".join(sorted(unknown)))
    return frozenset(requested | CORE_CAPABILITIES)


def parse_capabilities(value: str | None, *, legacy_all: bool = True) -> frozenset[str]:
    """Parse persisted capabilities; an absent legacy value means full."""
    if value is None or not value.strip():
        return ALL_CAPABILITIES if legacy_all else CORE_CAPABILITIES
    text = value.strip().lower()
    if text == "all":
        return ALL_CAPABILITIES
    if text == "core":
        return CORE_CAPABILITIES
    # Accept ``core`` as a readable alias inside a custom list as well as by
    # itself (for example ``core,nmap,nuclei``). Core is mandatory either way.
    parts = [part for part in text.split(",") if part.strip() != "core"]
    return normalize_capabilities(parts)


def format_capabilities(keys: Iterable[str]) -> str:
    selected = normalize_capabilities(keys)
    return ",".join(
        cap.key for _cat, cap in iter_capabilities() if cap.key in selected
    )


def required_backends(keys: Iterable[str]) -> tuple[str, ...]:
    selected = normalize_capabilities(keys)
    return tuple(dict.fromkeys(
        str(backend)
        for _cat, cap in iter_capabilities()
        if cap.key in selected
        for backend in CAPABILITY_INSTALL.get(cap.key, CapabilityInstall()).backends
    ))


def required_wordlists(keys: Iterable[str]) -> tuple[str, ...]:
    selected = normalize_capabilities(keys)
    return tuple(dict.fromkeys(
        str(item)
        for _cat, cap in iter_capabilities()
        if cap.key in selected
        for item in CAPABILITY_INSTALL.get(cap.key, CapabilityInstall()).wordlists
    ))


def catalog_payload() -> dict[str, object]:
    """Return the stable, secret-free capability catalog."""
    rows: list[dict[str, object]] = []
    for category, cap in iter_capabilities():
        metadata = CAPABILITY_INSTALL.get(cap.key, CapabilityInstall())
        rows.append({
            "key": cap.key,
            "category": category.key,
            "description": cap.label,
            "mandatory": category.core,
            "mcp_tools": list(cap.tools),
            "backend_binaries": list(metadata.backends),
            "wordlists": list(metadata.wordlists),
            "metasploit": cap.metasploit,
            "browser": metadata.browser,
            "estimated_context_tokens": CAPABILITY_CONTEXT_TOKENS.get(cap.key, 0),
            "note": cap.note,
        })
    return {
        "schema_version": 1,
        "selection_granularity": "capability_bundle",
        "core_capabilities": sorted(CORE_CAPABILITIES),
        "all_capabilities": [cap.key for _cat, cap in iter_capabilities()],
        "capabilities": rows,
        "full_tool_count": FULL_TOOL_COUNT,
        "without_metasploit_tool_count": LIGHT_TOOL_COUNT,
        "resource_count": 7,
    }


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


def format_disabled(names: set[str] | frozenset[str] | list[str]) -> str:
    """Serialize a disabled-tool set to the ``HERCULES_DISABLED_TOOLS`` form."""
    return ",".join(sorted(set(names) - CORE_TOOLS))
