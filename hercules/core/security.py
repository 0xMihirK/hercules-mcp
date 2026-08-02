"""Shared validation and redaction helpers for structured MCP tools."""

from __future__ import annotations

import asyncio
import re
import shlex
from urllib.parse import SplitResult, urlsplit, urlunsplit

_CONTROL_RE = re.compile(
    r"[\x00-\x1f\x7f-\x9f\u061c\u200e\u200f\u202a-\u202e\u2066-\u2069]"
)
_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9_.:-]+$")
_FILENAME_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
_SECRET_KEY = (
    r"(?:password|passwd|pass|token|access[_-]?token|refresh[_-]?token|"
    r"api[_-]?key|secret|client[_-]?secret|cookie|authorization|proxy)"
)
_UNQUOTED_SECRET_KEY = (
    r"(?:password|passwd|pass|token|access[_-]?token|refresh[_-]?token|"
    r"api[_-]?key|secret|client[_-]?secret|cookie|proxy)"
)
_SECRET_ASSIGNMENT_RE = re.compile(
    rf"(?i)(\b{_UNQUOTED_SECRET_KEY}\b\s*[:=]\s*)([^\s,;&}}]+)"
)
_SECRET_QUOTED_ASSIGNMENT_RE = re.compile(
    rf"""(?ix)
    (?P<prefix>["']?{_SECRET_KEY}["']?\s*:\s*)
    (?P<quote>["'])
    .*?
    (?P=quote)
    """
)
_SECRET_OPTION_RE = re.compile(
    rf"""(?ix)
    (?P<prefix>--{_SECRET_KEY}(?:=|\s+))
    (?:
        "(?:[^"\\]|\\.)*"
        |
        '(?:[^'\\]|\\.)*'
        |
        [^\s]+
    )
    """
)
_AUTH_HEADER_RE = re.compile(
    r"(?im)(?P<prefix>\bauthorization\s*:\s*)(?P<scheme>bearer|basic)\s+\S+"
)
_COOKIE_HEADER_RE = re.compile(
    r"(?im)(?P<prefix>\b(?:cookie|set-cookie)\s*:\s*)[^\r\n]+"
)
_QUERY_SECRET_RE = re.compile(
    rf"(?i)(?P<prefix>[?&]{_SECRET_KEY}=)[^&#\s]*"
)
_URL_CREDENTIAL_RE = re.compile(r"(?P<scheme>[a-z][a-z0-9+.-]*://)(?P<userinfo>[^/@\s]+)@", re.IGNORECASE)


async def validate_target_async(config, target: str) -> None:
    """Run target validation off-loop, including compatibility config objects."""
    async_validator = getattr(config, "validate_target_async", None)
    if callable(async_validator):
        await async_validator(target)
        return
    await asyncio.to_thread(config.validate_target, target)


def reject_control_chars(value: str, *, label: str = "value") -> str:
    """Reject terminal, newline, and bidi controls in a named parameter."""
    if not isinstance(value, str):
        # Tool parameter validators intentionally expose one ValueError contract.
        raise ValueError(f"{label} must be a string")  # noqa: TRY004
    if _CONTROL_RE.search(value):
        raise ValueError(f"{label} contains forbidden control characters")
    return value


def shell_quote(value: str, *, label: str = "value") -> str:
    """Validate and quote a named parameter for a POSIX shell command."""
    return shlex.quote(reject_control_chars(value, label=label))


def safe_identifier(
    value: str,
    *,
    label: str = "identifier",
    maximum: int = 128,
    allow_empty: bool = False,
) -> str:
    """Validate identifiers used in filenames, job IDs, and option keys."""
    clean = reject_control_chars(value, label=label).strip()
    if not clean and allow_empty:
        return ""
    if not clean or len(clean) > maximum or not _IDENTIFIER_RE.fullmatch(clean):
        raise ValueError(
            f"{label} must contain only letters, digits, '.', '_', ':', or '-' "
            f"and be at most {maximum} characters"
        )
    return clean


def safe_filename(
    value: str,
    *,
    label: str = "filename",
    maximum: int = 128,
) -> str:
    """Validate a portable single-component filename or file-backed ID."""
    clean = reject_control_chars(value, label=label).strip()
    reserved = {
        "aux",
        "con",
        "nul",
        "prn",
        *(f"com{number}" for number in range(1, 10)),
        *(f"lpt{number}" for number in range(1, 10)),
    }
    base = clean.casefold().split(".", 1)[0]
    if (
        not clean
        or len(clean) > maximum
        or clean.endswith((".", " "))
        or not _FILENAME_RE.fullmatch(clean)
        or base in reserved
    ):
        raise ValueError(
            f"{label} must be a portable filename containing only letters, "
            f"digits, '.', '_', or '-' and be at most {maximum} characters"
        )
    return clean


def validate_proxy_url(value: str) -> tuple[str, str]:
    """Validate a browser proxy URL and return it plus a credential-free host."""
    proxy = reject_control_chars(value, label="proxy URL").strip()
    if not proxy:
        return "", ""
    try:
        parsed = urlsplit(proxy)
        port = parsed.port
    except ValueError as exc:
        raise ValueError("proxy URL has an invalid port") from exc
    if parsed.scheme.lower() not in {"http", "https", "socks5", "socks5h"}:
        raise ValueError("proxy URL scheme must be http, https, socks5, or socks5h")
    if not parsed.hostname:
        raise ValueError("proxy URL must include a hostname")
    display_host = parsed.hostname
    if ":" in display_host:
        display_host = f"[{display_host}]"
    if port is not None:
        display_host = f"{display_host}:{port}"
    return proxy, display_host


def redact_url(value: str) -> str:
    """Remove userinfo and common query secrets from a display URL."""
    try:
        parsed = urlsplit(value)
    except ValueError:
        return _QUERY_SECRET_RE.sub(r"\g<prefix>***", _URL_CREDENTIAL_RE.sub(r"\g<scheme>***@", value))
    if not parsed.scheme or not parsed.hostname:
        return _QUERY_SECRET_RE.sub(r"\g<prefix>***", _URL_CREDENTIAL_RE.sub(r"\g<scheme>***@", value))
    host = parsed.hostname
    if ":" in host:
        host = f"[{host}]"
    if parsed.port is not None:
        host = f"{host}:{parsed.port}"
    sanitized = urlunsplit(
        SplitResult(parsed.scheme, host, parsed.path, parsed.query, parsed.fragment)
    )
    return _QUERY_SECRET_RE.sub(r"\g<prefix>***", sanitized)


def redact_secrets(value: str, secrets: tuple[str, ...] | list[str] = ()) -> str:
    """Best-effort redaction for logs, returned commands, and artifact headers."""
    redacted = _URL_CREDENTIAL_RE.sub(r"\g<scheme>***@", value)
    redacted = _AUTH_HEADER_RE.sub(
        lambda match: f"{match.group('prefix')}{match.group('scheme')} ***",
        redacted,
    )
    redacted = _COOKIE_HEADER_RE.sub(r"\g<prefix>***", redacted)
    redacted = _SECRET_OPTION_RE.sub(r"\g<prefix>***", redacted)
    redacted = _SECRET_QUOTED_ASSIGNMENT_RE.sub(r"\g<prefix>***", redacted)
    redacted = _SECRET_ASSIGNMENT_RE.sub(r"\1***", redacted)
    redacted = _QUERY_SECRET_RE.sub(r"\g<prefix>***", redacted)
    for secret in sorted((str(item) for item in secrets if item), key=len, reverse=True):
        if secret:
            redacted = redacted.replace(secret, "***")
    return redacted
