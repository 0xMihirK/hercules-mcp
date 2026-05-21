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

    # Reserve space for the truncation notice itself (~120 chars)
    notice_budget = 150
    available = max_chars - notice_budget

    head_size = int(available * head_ratio)
    tail_size = available - head_size
    omitted = len(text) - head_size - tail_size

    notice = _TRUNCATION_NOTICE.format(
        omitted=omitted,
        artifact=artifact_path or "<log file>",
    )

    truncated = text[:head_size] + notice + text[-tail_size:]
    return truncated, True
