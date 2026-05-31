"""
Hercules configuration — loaded from environment variables / .env file.

All settings have sensible defaults and can be overridden via a `.env` file
in the project root or by setting environment variables directly.
"""

from __future__ import annotations

import ipaddress
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger("hercules.config")

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


def _parse_float(value: str, default: float = 0.0) -> float:
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


@dataclass(frozen=True)
class HerculesConfig:
    """Immutable configuration object for the Hercules MCP server."""

    # Metasploit
    msf_password: str = "hercules"
    skip_metasploit: bool = False

    # Container lifecycle
    preserve_container: bool = False
    use_privileged: bool = False
    tool_install_mode: str = "minimal"  # "minimal" | "headless" | "large"

    # Concurrency
    max_concurrent_heavy: int = 3
    max_concurrent_light: int = 10

    # Safety controls
    allowed_targets: list[str] = field(default_factory=list)
    blocked_targets: list[str] = field(default_factory=list)

    # Container resource limits
    container_cpu_limit: float = 0.0  # 0 = unlimited
    container_mem_limit: str = "0"    # 0 = unlimited, or e.g. "4g"

    # Timeouts
    default_timeout: int = 300

    # Paths
    project_root: Path = field(default_factory=lambda: _PROJECT_ROOT)

    @classmethod
    def from_env(cls) -> HerculesConfig:
        """Create a config instance from environment variables."""
        return cls(
            msf_password=os.getenv("MSF_PASSWORD", "hercules"),
            skip_metasploit=_parse_bool(os.getenv("SKIP_METASPLOIT", "false")),
            preserve_container=_parse_bool(os.getenv("PRESERVE_CONTAINER", "false")),
            use_privileged=_parse_bool(os.getenv("USE_PRIVILEGED", "false")),
            tool_install_mode=os.getenv("TOOL_INSTALL_MODE", "minimal"),
            max_concurrent_heavy=int(os.getenv("MAX_CONCURRENT_HEAVY", "3")),
            max_concurrent_light=int(os.getenv("MAX_CONCURRENT_LIGHT", "10")),
            allowed_targets=_parse_csv(os.getenv("ALLOWED_TARGETS", "")),
            blocked_targets=_parse_csv(os.getenv("BLOCKED_TARGETS", "")),
            container_cpu_limit=_parse_float(os.getenv("CONTAINER_CPU_LIMIT", "0")),
            container_mem_limit=os.getenv("CONTAINER_MEM_LIMIT", "0"),
            default_timeout=int(os.getenv("DEFAULT_TIMEOUT", "300")),
        )

    # ------------------------------------------------------------------
    # Target validation
    # ------------------------------------------------------------------

    def validate_target(self, target: str) -> None:
        """
        Validate a target string against allowed / blocked lists.

        Raises ValueError if the target is denied by safety controls.
        A target can be an IP address, CIDR range, hostname, or URL.
        """
        # Extract the host portion if target looks like a URL
        clean = _extract_host(target)

        # Check blocked list first — always takes priority
        if self.blocked_targets:
            for pattern in self.blocked_targets:
                if _target_matches(clean, pattern):
                    raise ValueError(
                        f"Target '{target}' is blocked by safety controls "
                        f"(matched blocked pattern '{pattern}')"
                    )

        # If an allow-list is configured, the target must match at least one entry
        if self.allowed_targets:
            for pattern in self.allowed_targets:
                if _target_matches(clean, pattern):
                    return  # Allowed
            raise ValueError(
                f"Target '{target}' is not in the allowed targets list. "
                f"Allowed: {self.allowed_targets}"
            )

        # No allow-list and not blocked → permitted
        logger.debug("Target '%s' passed validation (no restrictions).", target)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_URL_HOST_RE = re.compile(r"^https?://([^/:]+)", re.IGNORECASE)


def _extract_host(target: str) -> str:
    """Strip scheme/port/path from a target to get the raw host or IP."""
    m = _URL_HOST_RE.match(target)
    if m:
        return m.group(1)
    # Remove trailing port if present (e.g. "10.10.10.10:8080")
    if ":" in target and not target.startswith("["):
        parts = target.rsplit(":", 1)
        if parts[1].isdigit():
            return parts[0]
    return target


def _target_matches(target: str, pattern: str) -> bool:
    """
    Check if a target matches a pattern. Supports:
    - Exact hostname / IP match
    - CIDR network match (e.g. "10.10.10.0/24")
    - Wildcard suffix match (e.g. "*.example.com")
    """
    # Wildcard suffix match
    if pattern.startswith("*."):
        suffix = pattern[1:]  # e.g. ".example.com"
        return target.endswith(suffix) or target == pattern[2:]

    # Try CIDR match
    if "/" in pattern:
        try:
            network = ipaddress.ip_network(pattern, strict=False)
            addr = ipaddress.ip_address(target)
            return addr in network
        except ValueError:
            pass  # Not a valid IP/CIDR — fall through to exact match

    # Exact match
    return target.lower() == pattern.lower()
