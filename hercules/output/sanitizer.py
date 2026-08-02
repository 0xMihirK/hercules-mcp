"""Conservative terminal rendering for agent-facing command output."""

from __future__ import annotations

import re

_CSI_FINAL_MIN = 0x40
_CSI_FINAL_MAX = 0x7E
_STRING_ESCAPES = {"]", "P", "X", "^", "_"}  # OSC, DCS, SOS, PM, APC
_STRING_C1 = {"\x90", "\x98", "\x9d", "\x9e", "\x9f"}
_BIDI_CONTROLS_RE = re.compile(
    "[\u061c\u200e\u200f\u202a-\u202e\u2066-\u2069]"
)
MAX_TERMINAL_COLUMNS = 32_768
MAX_RENDERED_CHARACTERS = 2 * 1024 * 1024


def _consume_control_string(text: str, start: int, *, c1: bool = False) -> int:
    """Return the first index after an OSC/DCS/SOS/PM/APC string."""
    index = start + (1 if c1 else 2)
    while index < len(text):
        char = text[index]
        if char in {"\x07", "\x9c"}:
            return index + 1
        if char == "\x1b" and index + 1 < len(text) and text[index + 1] == "\\":
            return index + 2
        index += 1
    return len(text)


def _consume_csi(text: str, start: int, *, c1: bool = False) -> tuple[int, str, str]:
    index = start + (1 if c1 else 2)
    parameter_start = index
    while index < len(text):
        code = ord(text[index])
        if _CSI_FINAL_MIN <= code <= _CSI_FINAL_MAX:
            return index + 1, text[parameter_start:index], text[index]
        index += 1
    return len(text), text[parameter_start:], ""


def _csi_number(parameters: str, default: int) -> int:
    first = parameters.lstrip("?").split(";", 1)[0]
    try:
        return int(first) if first else default
    except ValueError:
        return default


def _write_character(
    line: list[str],
    cursor: int,
    char: str,
    *,
    max_columns: int,
) -> int:
    cursor = min(max(0, cursor), max_columns - 1)
    if cursor < len(line):
        line[cursor] = char
    else:
        if cursor > len(line):
            line.extend([" "] * min(cursor - len(line), max_columns - len(line)))
        line.append(char)
    return min(cursor + 1, max_columns)


def render_terminal(
    text: str,
    *,
    max_columns: int = MAX_TERMINAL_COLUMNS,
    max_characters: int = MAX_RENDERED_CHARACTERS,
) -> str:
    """Render the final visible terminal state without deleting ordinary text."""
    if not text:
        return text
    max_columns = max(1, min(int(max_columns), MAX_TERMINAL_COLUMNS))
    max_characters = max(1, min(int(max_characters), MAX_RENDERED_CHARACTERS))

    output: list[str] = []
    line: list[str] = []
    cursor = 0
    index = 0
    rendered_characters = 0

    def flush_line(*, newline: bool) -> None:
        nonlocal line, cursor, rendered_characters
        remaining = max_characters - rendered_characters
        if remaining <= 0:
            line = []
            cursor = 0
            return
        visible = "".join(line)[:remaining]
        output.append(visible)
        rendered_characters += len(visible)
        if newline and rendered_characters < max_characters:
            output.append("\n")
            rendered_characters += 1
        line = []
        cursor = 0

    while index < len(text) and rendered_characters + len(line) < max_characters:
        char = text[index]

        if char == "\r":
            if index + 1 < len(text) and text[index + 1] == "\n":
                flush_line(newline=True)
                index += 2
                continue
            cursor = 0
            index += 1
            continue
        if char == "\n":
            flush_line(newline=True)
            index += 1
            continue
        if char == "\b":
            cursor = max(0, cursor - 1)
            index += 1
            continue
        if char == "\t":
            cursor = _write_character(
                line,
                cursor,
                char,
                max_columns=max_columns,
            )
            index += 1
            continue
        if char == "\x1b":
            if index + 1 >= len(text):
                break
            kind = text[index + 1]
            if kind == "[":
                index, parameters, final = _consume_csi(text, index)
                if final == "K":
                    mode = _csi_number(parameters, 0)
                    if mode == 0:
                        del line[cursor:]
                    elif mode == 1:
                        upto = min(cursor + 1, len(line))
                        line[:upto] = [" "] * upto
                    elif mode == 2:
                        line.clear()
                        cursor = 0
                elif final == "G":
                    cursor = min(
                        max_columns,
                        max(0, _csi_number(parameters, 1) - 1),
                    )
                elif final == "C":
                    cursor = min(
                        max_columns,
                        cursor + max(0, _csi_number(parameters, 1)),
                    )
                elif final == "D":
                    cursor = max(0, cursor - max(0, _csi_number(parameters, 1)))
                continue
            if kind in _STRING_ESCAPES:
                index = _consume_control_string(text, index)
                continue
            index += 2
            continue
        if char == "\x9b":
            index, parameters, final = _consume_csi(text, index, c1=True)
            if final == "K":
                mode = _csi_number(parameters, 0)
                if mode == 0:
                    del line[cursor:]
                elif mode == 2:
                    line.clear()
                    cursor = 0
            continue
        if char in _STRING_C1:
            index = _consume_control_string(text, index, c1=True)
            continue

        code = ord(char)
        if code == 0 or code == 0x7F or code < 0x20 or 0x80 <= code <= 0x9F:
            index += 1
            continue
        cursor = _write_character(
            line,
            cursor,
            char,
            max_columns=max_columns,
        )
        index += 1

    if line:
        flush_line(newline=False)
    return "".join(output)


def strip_ansi(text: str) -> str:
    """Remove terminal controls while retaining the final visible characters."""
    return render_terminal(text)


def collapse_carriage_returns(text: str) -> str:
    """Compatibility wrapper for the terminal renderer."""
    return render_terminal(text)


def compress_whitespace(text: str) -> str:
    """Explicit opt-in whitespace compaction; not part of universal sanitation."""
    return re.sub(r"\n{3,}", "\n\n", text)


def sanitize(text: str) -> str:
    """Remove terminal-only controls without globally rewriting whitespace."""
    return render_terminal(text)


def escape_display_controls(text: str) -> str:
    """Make control and bidi characters visible in logs/returned command text."""
    rendered: list[str] = []
    for char in text:
        code = ord(char)
        if (
            code < 0x20
            or code == 0x7F
            or 0x80 <= code <= 0x9F
            or _BIDI_CONTROLS_RE.fullmatch(char)
        ):
            rendered.append(f"\\u{code:04x}")
        else:
            rendered.append(char)
    return "".join(rendered)
