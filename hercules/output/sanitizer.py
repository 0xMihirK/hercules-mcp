"""
ANSI escape code stripping and whitespace compression.

These functions are safe to apply universally — they remove bytes that are
invisible to an LLM and consume tokens for zero informational value.
"""

from __future__ import annotations

import re

# Catches ALL ANSI escape sequences: color, cursor movement, bold, underline, etc.
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")


def strip_ansi(text: str) -> str:
    """Remove all ANSI escape sequences from text."""
    return _ANSI_RE.sub("", text)


def compress_whitespace(text: str) -> str:
    """Collapse 3+ consecutive newlines into 2, reducing vertical padding."""
    return re.sub(r"\n{3,}", "\n\n", text)


def sanitize(text: str) -> str:
    """Apply all safe, universal sanitization: ANSI stripping + whitespace compression."""
    return compress_whitespace(strip_ansi(text))
