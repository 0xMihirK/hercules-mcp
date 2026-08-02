"""
Output truncation with head+tail preservation.

The tail of tool output often contains the most critical results (found
credentials, discovered ports, successful injections). A naive head-only
truncation discards exactly the data the agent needs most. This module
implements a head+tail split with a clear truncation notice that includes
the artifact path so the agent can retrieve the full output on demand.
"""

from __future__ import annotations

_TRUNCATION_NOTICE = "\n[truncated: {omitted} chars; artifact: {artifact}]\n"


def _head_at_record_boundary(text: str, size: int) -> str:
    """Return a bounded head, preferring a complete line/JSONL record."""
    if size <= 0:
        return ""
    if len(text) <= size:
        return text
    candidate = text[:size]
    boundary = candidate.rfind("\n")
    # Do not throw away nearly the whole allocation for one very long line.
    if boundary >= max(1, size // 3):
        return candidate[: boundary + 1]
    return candidate


def _tail_at_record_boundary(text: str, size: int) -> str:
    """Return a bounded tail, preferring to start at a line boundary."""
    if size <= 0:
        return ""
    if len(text) <= size:
        return text
    candidate = text[-size:]
    boundary = candidate.find("\n")
    if 0 <= boundary < (size * 2) // 3:
        return candidate[boundary + 1 :]
    return candidate


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
        notice = f"[truncated; artifact: {artifact}]"
        if len(notice) >= max_chars:
            return notice[:max_chars], True

    available = max_chars - len(notice)
    head_size = max(0, int(available * head_ratio))
    tail_size = max(0, available - head_size)
    head = _head_at_record_boundary(text, head_size)
    tail = _tail_at_record_boundary(text, tail_size)
    omitted = max(0, len(text) - len(head) - len(tail))

    # The omitted-count width can change the notice length. Recompute once and
    # trim the retained segments, never by using text[-0:] (which is all text).
    notice = _TRUNCATION_NOTICE.format(omitted=omitted, artifact=artifact)
    overflow = len(head) + len(notice) + len(tail) - max_chars
    if overflow > 0:
        trim_tail = min(len(tail), overflow)
        tail = tail[trim_tail:]
        overflow -= trim_tail
        if overflow > 0:
            head = head[: max(0, len(head) - overflow)]
        omitted = max(0, len(text) - len(head) - len(tail))
        notice = _TRUNCATION_NOTICE.format(omitted=omitted, artifact=artifact)

    truncated = head + notice + tail
    if len(truncated) > max_chars:
        truncated = truncated[:max_chars]
    return truncated, True
