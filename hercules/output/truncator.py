"""
Output truncation with head+tail preservation.

The tail of tool output often contains the most critical results (found
credentials, discovered ports, successful injections). A naive head-only
truncation discards exactly the data the agent needs most. This module
implements a head+tail split with a clear truncation notice that includes
the artifact path so the agent can retrieve the full output on demand.
"""

from __future__ import annotations

_TRUNCATION_NOTICE = (
    "\n\n[OUTPUT TRUNCATED: {omitted} chars omitted. "
    "Full output saved to {artifact} — use workspace_read_file to inspect.]\n\n"
)


def truncate_output(
    text: str,
    max_chars: int = 8000,
    head_ratio: float = 0.4,
    tail_ratio: float = 0.6,
    artifact_path: str = "",
) -> tuple[str, bool]:
    """
    Truncate text using a head+tail strategy.

    Returns:
        (processed_text, was_truncated)
    """
    if len(text) <= max_chars:
        return text, False

    if max_chars <= 0:
        return "", True

    artifact = artifact_path or "<log file>"
    notice = _TRUNCATION_NOTICE.format(omitted=len(text), artifact=artifact)
    if len(notice) >= max_chars:
        notice = f"\n[OUTPUT TRUNCATED: full output saved to {artifact}]\n"
        if len(notice) >= max_chars:
            return notice[:max_chars], True

    available = max_chars - len(notice)
    head_size = max(0, int(available * head_ratio))
    tail_size = max(0, available - head_size)
    omitted = len(text) - head_size - tail_size

    notice = _TRUNCATION_NOTICE.format(omitted=omitted, artifact=artifact)
    if len(notice) >= max_chars:
        notice = f"\n[OUTPUT TRUNCATED: full output saved to {artifact}]\n"
        if len(notice) >= max_chars:
            return notice[:max_chars], True
    if len(notice) + head_size + tail_size > max_chars:
        available = max_chars - len(notice)
        head_size = max(0, int(available * head_ratio))
        tail_size = max(0, available - head_size)

    truncated = text[:head_size] + notice + text[-tail_size:]
    return truncated, True
