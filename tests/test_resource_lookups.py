"""Offline checks for the optional post-exploitation resource templates."""

import asyncio
import json
from pathlib import Path

import pytest
from fastmcp import Client

from hercules.resources import post_exploitation


@pytest.mark.parametrize(
    ("source", "name", "expected"),
    [
        ("gtfobins", "Find", {"functions": {"sudo": []}}),
        ("lolbas", "ADDINUTIL.exe", {"Name": "AddinUtil.exe", "Commands": []}),
    ],
)
def test_exact_lookup_uses_cached_catalog(monkeypatch, source, name, expected):
    catalogs = {
        "gtfobins": {"executables": {"find": expected}},
        "lolbas": [expected],
    }
    monkeypatch.setattr(
        post_exploitation,
        "_fetch_json_resource",
        lambda _label, _url, catalog: json.dumps(catalogs[catalog]),
    )
    assert json.loads(post_exploitation._lookup_resource(source, name)) == expected


@pytest.mark.parametrize("name", ["../passwd", "%2Fetc", "%252Fetc", "x\\y", "\n"])
def test_lookup_rejects_paths_and_control_characters(name):
    with pytest.raises(ValueError, match="executable name"):
        post_exploitation._lookup_name(name)


def test_lookup_missing_is_concise(monkeypatch):
    monkeypatch.setattr(
        post_exploitation,
        "_fetch_json_resource",
        lambda *_args: '{"executables": {}}',
    )
    with pytest.raises(ValueError, match="no exact match"):
        post_exploitation._lookup_resource("gtfobins", "absent")


def test_resource_template_reads_one_entry_without_docker(monkeypatch):
    from hercules import main

    monkeypatch.setattr(
        post_exploitation,
        "_fetch_json_resource",
        lambda *_args: '{"executables": {"find": {"functions": {"sudo": []}}}}',
    )

    async def scenario():
        async with Client(main.mcp) as client:
            content = await client.read_resource("resource://post_exploitation/gtfobins/find")
            return json.loads(content[0].text)

    assert asyncio.run(scenario()) == {"functions": {"sudo": []}}


def test_plugin_exposes_three_skills_without_duplicate_handbooks():
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / ".codex-plugin/plugin.json").read_text())
    assert manifest["skills"] == "./skills/"
    for name in ("hercules-nmap-nse", "hercules-nuclei"):
        skill = root / "skills" / name
        assert (skill / "SKILL.md").is_file()
        assert (skill / "references/handbook.md").is_file()
    for name in ("nmap-nse", "nuclei"):
        pointer = root / "skills/hercules-mcp/references" / f"{name}.md"
        assert len(pointer.read_text()) < 500
