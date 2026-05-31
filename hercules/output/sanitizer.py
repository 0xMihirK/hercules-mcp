"""
Terminal-noise stripping and whitespace compression.

These functions are safe to apply universally: they remove bytes and terminal
control sequences that are invisible or superseded before output reaches a
human or an LLM.
"""

from __future__ import annotations

import re

# CSI, OSC, and one-byte ESC sequences used for color, titles, cursor movement,
# bracketed paste, alternate screens, and similar terminal-only effects.
_ANSI_RE = re.compile(
    r"\x1b(?:"
    r"\[[0-?]*[ -/]*[@-~]"
    r"|\][^\x07]*(?:\x07|\x1b\\)"
    r"|[@-Z\\-_]"
    r")"
)


def strip_ansi(text: str) -> str:
    """Remove ANSI/OSC terminal escape sequences from text."""
    return _ANSI_RE.sub("", text)


def collapse_carriage_returns(text: str) -> str:
    """Keep the final visible state of carriage-return progress updates."""
    if "\r" not in text:
        return text
    normalized = text.replace("\r\n", "\n")
    return "\n".join(line.split("\r")[-1] for line in normalized.split("\n"))


def compress_whitespace(text: str) -> str:
    """Collapse 3+ consecutive newlines into 2, reducing vertical padding."""
    return re.sub(r"\n{3,}", "\n\n", text)


def sanitize(text: str) -> str:
    """Apply safe universal sanitization without removing semantic content."""
    text = text.replace("\x00", "")
    text = strip_ansi(text)
    text = collapse_carriage_returns(text)
    return compress_whitespace(text)
