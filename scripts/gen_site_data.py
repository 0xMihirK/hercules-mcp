"""Emit the website's committed site-facts.json (catalog + install prompt).

Derives the data from source (`hercules.core.tool_catalog` + `README.md`) and
writes a single JSON file. The site-sync workflow runs this on `main` and commits
the result to the standalone `website` branch, whose decoupled build reuses it
instead of importing the Hercules package.

Usage: python scripts/gen_site_data.py [output_path]
       (default output: website/src/site-facts.json under the repo root)
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from hercules.core.tool_catalog import CATEGORIES, catalog_payload

catalog = catalog_payload()
catalog["categories"] = [{"key": item.key, "title": item.title} for item in CATEGORIES]
for capability in catalog["capabilities"]:
    capability.pop("estimated_context_tokens", None)
readme = (ROOT / "README.md").read_text(encoding="utf-8")
match = re.search(r"## Install with your AI agent.*?```text\n(.*?)\n```", readme, re.S)
if not match:
    raise RuntimeError("Canonical installation prompt missing from README.md")
facts = {"catalog": catalog, "installationPrompt": match.group(1)}
out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "website/src/site-facts.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(facts, ensure_ascii=False), encoding="utf-8", newline="\n")
print(f"Wrote {out} ({catalog['full_tool_count']} tools, {len(catalog['capabilities'])} bundles)")
