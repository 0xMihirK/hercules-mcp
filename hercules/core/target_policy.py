"""Dependency-free target policy shared with the container browser gateway."""

from __future__ import annotations

import ipaddress
import logging
import re
import socket
from dataclasses import dataclass, field
from urllib.parse import urlsplit

logger = logging.getLogger("hercules.policy")


@dataclass(frozen=True)
class TargetPolicy:
    allowed_targets: list[str] = field(default_factory=list)
    blocked_targets: list[str] = field(default_factory=list)

    def validate_target(self, target: str, *, resolved: list[str] | None = None) -> None:
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
                    resolved_addresses = resolved if resolved is not None else sorted(
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
                if _target_matches(clean, pattern, blocked=True) or any(
                    _target_matches(address, pattern, blocked=True) for address in policy_targets
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

    def resolve_destination(self, host: str, port: int) -> list[str]:
        """Resolve once, validate every address, and return only pinned IPs."""
        clean = _extract_host(host)
        if "/" in clean or not 1 <= port <= 65535:
            raise ValueError("invalid connection destination")
        addresses = sorted({ipaddress.ip_address(info[4][0]).compressed.lower()
                            for info in socket.getaddrinfo(clean, port, type=socket.SOCK_STREAM)})
        if not addresses:
            raise ValueError("destination has no addresses")
        self.validate_target(clean, resolved=addresses)
        # Browsing always requires explicit private-IP authorization, including
        # when ordinary unrestricted shell/network tools have no allow-list.
        for address in addresses:
            if _is_special_address(address) and not any(
                _is_ip_policy(pattern) and _target_matches(address, pattern)
                for pattern in self.allowed_targets
            ):
                raise ValueError("browser private destination requires explicit IP/CIDR authorization")
        return addresses


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


def _target_matches(target: str, pattern: str, *, blocked: bool = False) -> bool:
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

    if blocked and target_network is not None:
        try:
            policy_network = ipaddress.ip_network(normalized_pattern, strict=False)
        except ValueError:
            return False
        return target_network.version == policy_network.version and target_network.overlaps(policy_network)

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


