"""The focused playbooks remain discoverable without loading every topic."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from hercules.core.guidance import SERVER_INSTRUCTIONS
from hercules.setup.engine import SKILL_NAMES


ROOT = Path(__file__).resolve().parents[1]
TOPIC_COUNTS = {
    "hercules-operator": 2,
    "hercules-application-testing": 21,
    "hercules-infrastructure": 12,
    "hercules-wireless-embedded": 16,
    "hercules-binary-analysis": 12,
    "hercules-assessment-operations": 16,
}


@pytest.mark.parametrize(("name", "expected"), TOPIC_COUNTS.items())
def test_topic_references_are_complete_and_loaded_on_demand(name, expected):
    folder = ROOT / "skills" / name
    entry = (folder / "SKILL.md").read_text(encoding="utf-8")
    links = re.findall(r"\]\(references/([^)]+\.md)\)", entry)
    files = sorted(path.name for path in (folder / "references").glob("*.md"))
    assert len(links) == expected
    assert sorted(links) == files
    assert len(set(links)) == expected
    assert len(entry.split()) < 600
    for file in files:
        content = (folder / "references" / file).read_text(encoding="utf-8")
        assert "Positive control:" in content
        assert "Negative control:" in content


def test_skill_pack_is_additive_and_mcp_guidance_stays_compact():
    assert len(SKILL_NAMES) == 9
    assert set(TOPIC_COUNTS).issubset(SKILL_NAMES)
    assert sum(TOPIC_COUNTS.values()) == 79
    assert len(SERVER_INSTRUCTIONS) < 2500
    assert "Reuse workspace evidence" in SERVER_INSTRUCTIONS
    assert "CSP is NOT enforced" in SERVER_INSTRUCTIONS
    assert "NO SSRF boundary" in SERVER_INSTRUCTIONS
