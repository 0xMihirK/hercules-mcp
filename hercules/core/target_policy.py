"""Dependency-free target policy shared with the container browser gateway."""

from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass
from urllib.parse import urlsplit

# Bidi / RTL-override and related invisible formatting codepoints (Trojan-Source
# class). Expressed as codepoints so the source carries no literal controls.
_BIDI_CONTROL_CODEPOINTS = frozenset(
    {0x061C, 0x200E, 0x200F, 0x202A, 0x202B, 0x202C, 0x202D, 0x202E, 0x2066, 0x2067, 0x2068, 0x2069}
)


@dataclass(frozen=True)
class TargetPolicy:
    """Structural target validation only.

    There is no allow/block list and no browser SSRF boundary (the runtime uses
    host networking and the browser launches directly). Tools accept any
    syntactically valid target; malformed or unresolvable targets raise ValueError.
    """

    def validate_target(self, target: str) -> None:
        """Reject a malformed target; impose no scope. Raises ValueError."""
        _extract_host(target)


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
        or ord(ch) in _BIDI_CONTROL_CODEPOINTS
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
