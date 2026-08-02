"""
Hercules configuration — loaded from environment variables / .env file.

All settings have sensible defaults and can be overridden via a `.env` file
in the project root or by setting environment variables directly.
"""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import os
import re
import secrets
import socket
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv

from hercules.core.build_info import (
    CLOAKBROWSER_VERSION,
    CLOAKBROWSER_WHEEL_SHA256,
    CLOAKBROWSER_WHEEL_URL,
)

logger = logging.getLogger("hercules.config")
_legacy_headed_warning_emitted = False
# Reverse listeners are the one deliberately public service surface. RPC and
# browser streaming remain loopback-only.
_EXTERNAL_LISTENER_BIND = "0.0.0.0"  # nosec B104

# ---------------------------------------------------------------------------
# Load .env from project root (two levels up from this file)
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_ENV_PATH = _PROJECT_ROOT / ".env"
if _ENV_PATH.exists():
    load_dotenv(_ENV_PATH)


def _parse_bool(value: str) -> bool:
    return value.strip().lower() in ("true", "1", "yes")


def _parse_csv(value: str) -> list[str]:
    """Parse a comma-separated string into a list of stripped, non-empty values."""
    if not value or not value.strip():
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


def _parse_disabled_tools(value: str) -> frozenset[str]:
    """Parse HERCULES_DISABLED_TOOLS, filtering out core tools (delegated to the
    tool catalog so the never-disable-core rule lives in exactly one place)."""
    from hercules.core.tool_catalog import parse_disabled

    return parse_disabled(value)


def _parse_ports(value: str) -> tuple[int, ...]:
    """Parse comma-separated ports and inclusive ranges."""
    ports: set[int] = set()
    for item in _parse_csv(value):
        if "-" in item:
            start_text, end_text = item.split("-", 1)
            start = _parse_int(start_text, -1, minimum=1, maximum=65_535)
            end = _parse_int(end_text, -1, minimum=1, maximum=65_535)
            if start < 1 or end < start or end - start > 1_024:
                raise ValueError(f"invalid listener port range: {item!r}")
            ports.update(range(start, end + 1))
        else:
            port = _parse_int(item, -1, minimum=1, maximum=65_535)
            if port < 1:
                raise ValueError(f"invalid listener port: {item!r}")
            ports.add(port)
    return tuple(sorted(ports))


def _parse_docker_network(value: str) -> str:
    """Validate an optional Docker network name without shell interpretation."""
    value = (value or "").strip()
    if not value:
        return ""
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", value):
        raise ValueError("invalid HERCULES_DOCKER_NETWORK name")
    return value


def _parse_bind_host(value: str) -> str:
    value = (value or "").strip()
    if value not in {_EXTERNAL_LISTENER_BIND, "127.0.0.1", "::1"}:
        raise ValueError(
            "HERCULES_LISTENER_BIND_HOST must be 0.0.0.0, 127.0.0.1, or ::1"
        )
    return value


def _parse_float(value: str, default: float = 0.0) -> float:
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def _parse_int(value: str, default: int, *, minimum: int = 0, maximum: int | None = None) -> int:
    """Parse and range-check an integer environment variable."""
    try:
        parsed = int(value)
    except (ValueError, TypeError):
        return default
    if parsed < minimum or (maximum is not None and parsed > maximum):
        return default
    return parsed


def _default_msf_password() -> str:
    """Create an ephemeral secret when an agent has not persisted one yet."""
    return secrets.token_urlsafe(32)


@dataclass(frozen=True)
class HerculesConfig:
    """Immutable configuration object for the Hercules MCP server."""

    # Metasploit
    msf_password: str = field(default_factory=_default_msf_password)
    skip_metasploit: bool = False
    msf_rpc_port: int = 55_553

    # Container lifecycle
    preserve_container: bool = False
    use_privileged: bool = False
    docker_network: str = ""
    # Deprecated compatibility field. Selective images use
    # HERCULES_INSTALLED_CAPABILITIES; this legacy value has no build effect.
    tool_install_mode: str = ""

    # Concurrency
    max_concurrent_heavy: int = 3
    max_concurrent_light: int = 10

    # Safety controls
    allowed_targets: list[str] = field(default_factory=list)
    blocked_targets: list[str] = field(default_factory=list)

    # Operator tool selection. Names listed here are NOT registered as MCP tools
    # (their description/schema is dropped from the model's context to save
    # tokens). The agent can still invoke an independently hidden backend via
    # shell_exec when its capability is installed. Set through
    # HERCULES_DISABLED_TOOLS in .env. Core tools can never be disabled.
    disabled_tools: frozenset[str] = field(default_factory=frozenset)
    operator_disabled_tools: frozenset[str] = field(default_factory=frozenset)
    installed_capabilities: frozenset[str] = field(default_factory=frozenset)

    # Container resource limits
    container_cpu_limit: float = 0.0  # 0 = unlimited
    container_mem_limit: str = "0"    # 0 = unlimited, or e.g. "4g"

    # Timeouts
    default_timeout: int = 300
    # Hard ceiling applied to EVERY exec_command, regardless of caller. Stops an
    # unbounded internal call (background-job plumbing) from pinning a tool for
    # the full default timeout against a wedged container. Set above the longest
    # legitimate scan (nmap aggressive 600s, amass ~20min).
    max_exec_timeout: int = 1200
    max_captured_output_bytes: int = 2 * 1024 * 1024
    max_inline_response_chars: int = 12_000
    max_inline_file_bytes: int = 8 * 1024 * 1024
    max_background_jobs: int = 8

    # Proactive watchdog: poll container health every N seconds and recover
    # before the next tool call. 0 disables the watchdog.
    watchdog_interval: int = 20

    # Stealth browser (cloakbrowser stealth Chromium + agent-browser controller)
    browser_stream_port: int = 0        # 0 = disabled; >0 exposes the loopback stream relay
    browser_proxy: str = ""             # default upstream proxy for browser sessions (e.g. http://host:8080)
    browser_disable_non_proxied_udp: bool = True
    browser_timezone: str = ""          # default stealth timezone (e.g. America/New_York)
    browser_locale: str = ""            # default stealth locale (e.g. en-US)

    # Paths
    project_root: Path = field(default_factory=lambda: _PROJECT_ROOT)
    workspace_root: Path | None = None
    wordlist_root: Path | None = None
    build_ca_sha256: str = ""
    cloakbrowser_version: str = CLOAKBROWSER_VERSION
    cloakbrowser_wheel_url: str = CLOAKBROWSER_WHEEL_URL
    cloakbrowser_sha256: str = CLOAKBROWSER_WHEEL_SHA256

    # Workspace retention. Zero disables each limit; automatic pruning is off
    # unless explicitly enabled.
    workspace_auto_prune: bool = False
    workspace_retention_days: int = 0
    workspace_max_sessions: int = 0
    workspace_max_bytes: int = 0

    # Reverse-listener ports remain externally reachable by design.
    listener_ports: tuple[int, ...] = tuple(range(4444, 4465))
    listener_bind_host: str = _EXTERNAL_LISTENER_BIND

    @classmethod
    def from_env(cls) -> HerculesConfig:
        """Create a config instance from environment variables."""
        global _legacy_headed_warning_emitted
        from hercules.core.tool_catalog import (
            ALL_CAPABILITIES,
            OPTIONAL_CAPABILITIES,
            parse_capabilities,
            tools_for_capabilities,
        )

        msf_password = os.getenv("MSF_PASSWORD", "").strip() or _default_msf_password()
        persisted_capabilities = os.getenv("HERCULES_INSTALLED_CAPABILITIES")
        try:
            installed_capabilities = parse_capabilities(
                persisted_capabilities,
                legacy_all=True,
            )
        except ValueError as exc:
            raise ValueError("invalid HERCULES_INSTALLED_CAPABILITIES") from exc
        unavailable_tools = tools_for_capabilities(
            OPTIONAL_CAPABILITIES - installed_capabilities
        )
        operator_disabled_tools = _parse_disabled_tools(
            os.getenv("HERCULES_DISABLED_TOOLS", "")
        )
        disabled_tools = operator_disabled_tools | unavailable_tools
        skip_metasploit = (
            _parse_bool(os.getenv("SKIP_METASPLOIT", "false"))
            or "metasploit" not in installed_capabilities
        )
        legacy_headless = os.getenv("BROWSER_HEADLESS")
        if (
            legacy_headless is not None
            and not _parse_bool(legacy_headless)
            and not _legacy_headed_warning_emitted
        ):
            logger.warning(
                "BROWSER_HEADLESS=false is deprecated and ignored; Hercules "
                "always runs browser sessions headlessly."
            )
            _legacy_headed_warning_emitted = True
        legacy_install_mode = os.getenv("TOOL_INSTALL_MODE", "").strip()
        if legacy_install_mode:
            logger.warning(
                "TOOL_INSTALL_MODE is deprecated and has no build effect; "
                "use HERCULES_INSTALLED_CAPABILITIES instead."
            )
        return cls(
            msf_password=msf_password,
            skip_metasploit=skip_metasploit,
            msf_rpc_port=_parse_int(
                os.getenv("MSF_RPC_PORT", "55553"),
                55_553,
                minimum=1,
                maximum=65_535,
            ),
            preserve_container=_parse_bool(os.getenv("PRESERVE_CONTAINER", "false")),
            use_privileged=_parse_bool(os.getenv("USE_PRIVILEGED", "false")),
            docker_network=_parse_docker_network(
                os.getenv("HERCULES_DOCKER_NETWORK", "")
            ),
            tool_install_mode=legacy_install_mode,
            max_concurrent_heavy=_parse_int(
                os.getenv("MAX_CONCURRENT_HEAVY", "3"), 3, minimum=1, maximum=128
            ),
            max_concurrent_light=_parse_int(
                os.getenv("MAX_CONCURRENT_LIGHT", "10"), 10, minimum=1, maximum=512
            ),
            allowed_targets=_parse_csv(os.getenv("ALLOWED_TARGETS", "")),
            blocked_targets=_parse_csv(os.getenv("BLOCKED_TARGETS", "")),
            disabled_tools=disabled_tools,
            operator_disabled_tools=operator_disabled_tools,
            installed_capabilities=(installed_capabilities or ALL_CAPABILITIES),
            wordlist_root=(
                Path(os.environ["HERCULES_WORDLIST_ROOT"]).expanduser().resolve()
                if os.getenv("HERCULES_WORDLIST_ROOT", "").strip()
                else None
            ),
            build_ca_sha256=os.getenv("HERCULES_BUILD_CA_SHA256", "").strip().lower(),
            cloakbrowser_version=os.getenv(
                "HERCULES_CLOAKBROWSER_VERSION",
                CLOAKBROWSER_VERSION,
            ).strip(),
            cloakbrowser_wheel_url=os.getenv(
                "HERCULES_CLOAKBROWSER_WHEEL_URL",
                CLOAKBROWSER_WHEEL_URL,
            ).strip(),
            cloakbrowser_sha256=os.getenv(
                "HERCULES_CLOAKBROWSER_SHA256",
                CLOAKBROWSER_WHEEL_SHA256,
            ).strip().lower(),
            container_cpu_limit=_parse_float(os.getenv("CONTAINER_CPU_LIMIT", "0")),
            container_mem_limit=os.getenv("CONTAINER_MEM_LIMIT", "0"),
            default_timeout=_parse_int(
                os.getenv("DEFAULT_TIMEOUT", "300"), 300, minimum=1, maximum=86_400
            ),
            max_exec_timeout=_parse_int(
                os.getenv("MAX_EXEC_TIMEOUT", "1200"), 1200, minimum=1, maximum=86_400
            ),
            max_captured_output_bytes=_parse_int(
                os.getenv(
                    "HERCULES_MAX_CAPTURED_OUTPUT_BYTES",
                    str(2 * 1024 * 1024),
                ),
                2 * 1024 * 1024,
                minimum=64 * 1024,
                maximum=512 * 1024 * 1024,
            ),
            max_inline_response_chars=_parse_int(
                os.getenv("HERCULES_MAX_INLINE_RESPONSE_CHARS", "12000"),
                12_000,
                minimum=256,
                maximum=1_000_000,
            ),
            max_inline_file_bytes=_parse_int(
                os.getenv("HERCULES_MAX_INLINE_FILE_BYTES", str(8 * 1024 * 1024)),
                8 * 1024 * 1024,
                minimum=64 * 1024,
                maximum=512 * 1024 * 1024,
            ),
            max_background_jobs=_parse_int(
                os.getenv("HERCULES_MAX_BACKGROUND_JOBS", "8"),
                8,
                minimum=1,
                maximum=128,
            ),
            watchdog_interval=_parse_int(
                os.getenv("WATCHDOG_INTERVAL", "20"), 20, minimum=0, maximum=3_600
            ),
            browser_stream_port=_parse_int(
                os.getenv("BROWSER_STREAM_PORT", "0") or "0",
                0,
                minimum=0,
                maximum=65_535,
            ),
            browser_proxy=(
                os.getenv("BROWSER_PROXY_URL", "").strip()
                or os.getenv("BROWSER_PROXY", "").strip()
            ),
            browser_disable_non_proxied_udp=_parse_bool(
                os.getenv("BROWSER_DISABLE_NON_PROXIED_UDP", "true")
            ),
            browser_timezone=os.getenv("BROWSER_TIMEZONE", ""),
            browser_locale=os.getenv("BROWSER_LOCALE", ""),
            workspace_root=(
                Path(os.environ["HERCULES_WORKSPACE_ROOT"]).expanduser()
                if os.getenv("HERCULES_WORKSPACE_ROOT", "").strip()
                else None
            ),
            workspace_auto_prune=_parse_bool(
                os.getenv("HERCULES_WORKSPACE_AUTO_PRUNE", "false")
            ),
            workspace_retention_days=_parse_int(
                os.getenv("HERCULES_WORKSPACE_RETENTION_DAYS", "0"),
                0,
                minimum=0,
                maximum=365_000,
            ),
            workspace_max_sessions=_parse_int(
                os.getenv("HERCULES_WORKSPACE_MAX_SESSIONS", "0"),
                0,
                minimum=0,
                maximum=1_000_000,
            ),
            workspace_max_bytes=_parse_int(
                os.getenv("HERCULES_WORKSPACE_MAX_BYTES", "0"),
                0,
                minimum=0,
            ),
            listener_ports=_parse_ports(
                os.getenv("HERCULES_LISTENER_PORTS", "4444-4464")
            ),
            listener_bind_host=_parse_bind_host(
                os.getenv("HERCULES_LISTENER_BIND_HOST", _EXTERNAL_LISTENER_BIND)
            ),
        )

    @property
    def resolved_workspace_root(self) -> Path:
        """Return the configured root or the legacy checkout-local location."""
        root = self.workspace_root or (self.project_root / "workspace")
        return Path(root).expanduser().resolve()

    # ------------------------------------------------------------------
    # Target validation
    # ------------------------------------------------------------------

    def validate_target(self, target: str) -> None:
        """
        Validate a target string against allowed / blocked lists.

        Raises ValueError if the target is denied by safety controls.
        A target can be an IP address, CIDR range, hostname, or URL.
        """
        clean = _extract_host(target)
        resolved_addresses: list[str] = []
        literal_targets: list[str] = []
        if (self.allowed_targets or self.blocked_targets) and "/" not in clean:
            try:
                literal_targets = [ipaddress.ip_address(clean).compressed.lower()]
            except ValueError:
                try:
                    resolved_addresses = sorted(
                        {
                            ipaddress.ip_address(info[4][0]).compressed.lower()
                            for info in socket.getaddrinfo(
                                clean,
                                None,
                                type=socket.SOCK_STREAM,
                            )
                        }
                    )
                except (OSError, ValueError) as exc:
                    raise ValueError(
                        f"Target '{target}' could not be resolved while target scopes are active"
                    ) from exc
        elif self.allowed_targets or self.blocked_targets:
            try:
                literal_targets = [
                    str(ipaddress.ip_network(clean, strict=False)).lower()
                ]
            except ValueError:
                literal_targets = []

        policy_targets = [*literal_targets, *resolved_addresses]

        # Check blocked list first — always takes priority
        if self.blocked_targets:
            for pattern in self.blocked_targets:
                if _target_matches(clean, pattern) or any(
                    _target_matches(address, pattern) for address in policy_targets
                ):
                    raise ValueError(
                        f"Target '{target}' is blocked by safety controls "
                        f"(matched blocked pattern '{pattern}')"
                    )

        # If an allow-list is configured, the target must match at least one entry
        if self.allowed_targets:
            hostname_allowed = any(
                _target_matches(clean, pattern) for pattern in self.allowed_targets
            )
            addresses_allowed = bool(policy_targets) and all(
                any(
                    _target_matches(address, pattern)
                    for pattern in self.allowed_targets
                )
                for address in policy_targets
            )
            special_targets = [
                address
                for address in policy_targets
                if _is_special_target(address)
            ]
            explicitly_allowed_special = all(
                any(
                    _is_ip_policy(pattern) and _target_matches(address, pattern)
                    for pattern in self.allowed_targets
                )
                for address in special_targets
            )
            if special_targets and not explicitly_allowed_special:
                raise ValueError(
                    f"Target '{target}' uses or resolves to special/private address(es) "
                    f"{special_targets}; explicitly allow those IPs or CIDRs"
                )
            if addresses_allowed or (
                hostname_allowed and explicitly_allowed_special
            ):
                return
            raise ValueError(
                f"Target '{target}' is not in the allowed targets list. "
                f"Allowed: {self.allowed_targets}"
            )

        # No allow-list and not blocked → permitted
        logger.debug("Target '%s' passed validation (no restrictions).", target)

    async def validate_target_async(self, target: str) -> None:
        """Run parsing and DNS policy checks without blocking the event loop."""
        await asyncio.to_thread(self.validate_target, target)

    def browser_allowed_domains(self, current_target: str = "") -> list[str]:
        """Return a conservative navigation allowlist understood by agent-browser."""
        domains: list[str] = []
        wildcard_allowed = False
        for pattern in self.allowed_targets:
            normalized = _normalize_pattern(pattern)
            if normalized == "*":
                wildcard_allowed = True
                continue
            if "/" not in normalized:
                domains.append(normalized)
        if wildcard_allowed and not self.blocked_targets:
            return []
        # CIDRs cannot be represented by agent-browser's domain patterns. The
        # structured browser_open validation has already checked every resolved
        # address, so admit that exact initial host without admitting neighbors.
        # With only block rules, this also prevents cross-host redirects.
        if current_target and (self.allowed_targets or self.blocked_targets):
            current_host = _extract_host(current_target)
            if "/" not in current_host:
                domains.append(current_host)
        return list(dict.fromkeys(domains))


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_HOST_LABEL_RE = re.compile(r"^[a-z0-9_](?:[a-z0-9._-]*[a-z0-9_])?$", re.IGNORECASE)


def _reject_unsafe_text(value: str, *, label: str = "target") -> str:
    if not isinstance(value, str):
        # Public target validators intentionally expose one ValueError contract.
        raise ValueError(f"{label} must be a string")  # noqa: TRY004
    clean = value.strip()
    if not clean:
        raise ValueError(f"{label} must not be empty")
    if any(
        ord(ch) < 0x20
        or ord(ch) == 0x7F
        or 0x80 <= ord(ch) <= 0x9F
        or ch in "\u061c\u200e\u200f\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069"
        for ch in clean
    ):
        raise ValueError(f"{label} contains forbidden control characters")
    return clean


def _normalize_hostname(host: str) -> str:
    """Normalize a DNS name or IP literal for policy comparison."""
    host = host.strip().strip("[]").rstrip(".")
    if not host:
        raise ValueError("target host must not be empty")
    try:
        return ipaddress.ip_address(host).compressed.lower()
    except ValueError:
        pass
    try:
        normalized = host.encode("idna").decode("ascii").lower()
    except UnicodeError as exc:
        raise ValueError(f"invalid internationalized hostname: {host!r}") from exc
    if not _HOST_LABEL_RE.fullmatch(normalized):
        raise ValueError(f"invalid hostname: {host!r}")
    return normalized


def _extract_host(target: str) -> str:
    """Extract and normalize a host from a URL, host:port, IP, or CIDR."""
    clean = _reject_unsafe_text(target)

    # CIDR targets are policy values in their own right. Plain IP literals must
    # remain literals rather than becoming implicit /32 or /128 networks.
    if "/" in clean:
        try:
            return str(ipaddress.ip_network(clean, strict=False)).lower()
        except ValueError:
            pass

    # urlsplit treats an unbracketed IPv6 literal such as ``::1`` as malformed
    # host/port syntax. Recognize a complete literal first; brackets remain
    # required only when an explicit port is also present.
    if "://" not in clean:
        try:
            return ipaddress.ip_address(clean.strip("[]")).compressed.lower()
        except ValueError:
            pass

    parsed = urlsplit(clean if "://" in clean else f"//{clean}")
    try:
        host = parsed.hostname
        # Accessing .port validates malformed/out-of-range ports.
        _ = parsed.port
    except ValueError as exc:
        raise ValueError(f"invalid target URL or port: {target!r}") from exc
    if host:
        return _normalize_hostname(host)
    return _normalize_hostname(clean)


def _normalize_pattern(pattern: str) -> str:
    clean = _reject_unsafe_text(pattern, label="target pattern")
    if clean == "*":
        return clean
    if clean.startswith("*."):
        return "*." + _normalize_hostname(clean[2:])
    if "/" in clean:
        try:
            return str(ipaddress.ip_network(clean, strict=False)).lower()
        except ValueError:
            pass
    return _extract_host(clean)


def _target_matches(target: str, pattern: str) -> bool:
    """
    Check if a target matches a pattern. Supports:
    - Exact hostname / IP match
    - CIDR network match (e.g. "10.10.10.0/24")
    - Wildcard suffix match (e.g. "*.example.com")
    """
    normalized_pattern = _normalize_pattern(pattern)
    if normalized_pattern == "*":
        return True

    # A network target is allowed only when it is contained by a matching policy
    # network. Host targets continue through the hostname/IP checks below.
    target_network = None
    try:
        target_network = ipaddress.ip_network(target, strict=False)
    except ValueError:
        pass

    if normalized_pattern.startswith("*."):
        if target_network is not None:
            return False
        suffix = normalized_pattern[1:]
        return target.endswith(suffix) or target == normalized_pattern[2:]

    # Try CIDR match
    if "/" in normalized_pattern:
        try:
            network = ipaddress.ip_network(normalized_pattern, strict=False)
            if target_network is not None:
                if target_network.version != network.version:
                    return False
                return target_network.subnet_of(network)  # type: ignore[arg-type]
            return ipaddress.ip_address(target) in network
        except ValueError:
            pass  # Not a valid IP/CIDR — fall through to exact match

    # Exact match
    return target == normalized_pattern


def _is_special_address(value: str) -> bool:
    address = ipaddress.ip_address(value)
    return any(
        (
            address.is_private,
            address.is_loopback,
            address.is_link_local,
            address.is_multicast,
            address.is_reserved,
            address.is_unspecified,
        )
    )


_SPECIAL_NETWORKS = tuple(
    ipaddress.ip_network(value)
    for value in (
        "0.0.0.0/8",
        "10.0.0.0/8",
        "100.64.0.0/10",
        "127.0.0.0/8",
        "169.254.0.0/16",
        "172.16.0.0/12",
        "192.0.0.0/24",
        "192.0.2.0/24",
        "192.168.0.0/16",
        "198.18.0.0/15",
        "198.51.100.0/24",
        "203.0.113.0/24",
        "224.0.0.0/4",
        "240.0.0.0/4",
        "::/128",
        "::1/128",
        "::ffff:0:0/96",
        "100::/64",
        "2001::/23",
        "2001:db8::/32",
        "fc00::/7",
        "fe80::/10",
        "ff00::/8",
    )
)


def _is_special_target(value: str) -> bool:
    """Return whether an IP literal/CIDR intersects a non-public address range."""
    try:
        network = ipaddress.ip_network(value, strict=False)
    except ValueError:
        return _is_special_address(value)
    return any(
        network.version == special.version and network.overlaps(special)
        for special in _SPECIAL_NETWORKS
    )


def _is_ip_policy(pattern: str) -> bool:
    normalized = _normalize_pattern(pattern)
    try:
        if "/" in normalized:
            ipaddress.ip_network(normalized, strict=False)
        else:
            ipaddress.ip_address(normalized)
    except ValueError:
        return False
    return True
