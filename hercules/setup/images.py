"""Digest-only release catalog from the candidate's trusted source checkout."""

import json
import re
from pathlib import Path

from hercules.setup.transaction import SetupError


def prebuilt_references(facts):
    if facts["image"]["custom_ca"]["configured"]:
        return []
    catalog = Path(facts["source"]["checkout"]) / "hercules/core/prebuilt_images.json"
    if not catalog.is_file():
        return []
    data = json.loads(catalog.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or not isinstance(data.get("images"), list):
        raise SetupError("image_catalog_invalid", "Unsupported prebuilt image catalog")
    selected = []
    for entry in data["images"]:
        if entry.get("fingerprint") != facts["image"]["fingerprint"] or entry.get("platform") != facts["image"]["target_platform"]:
            continue
        references = entry.get("references")
        if (not re.fullmatch(r"[0-9a-f]{40}", entry.get("source_revision", ""))
                or not isinstance(references, list) or not references
                or any(not isinstance(ref, str) or not re.fullmatch(r"[a-z0-9][a-z0-9./_-]+@sha256:[0-9a-f]{64}", ref) for ref in references)
                or len({ref.rsplit("@", 1)[1] for ref in references}) != 1):
            raise SetupError("image_catalog_invalid", "Prebuilt image entry has an invalid identity or mirror digest")
        selected.extend(references)
    return list(dict.fromkeys(selected))
