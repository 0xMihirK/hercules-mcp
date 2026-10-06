"""Generate public facts from source without importing the Hercules runtime."""
from pathlib import Path
import json
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "website"
sys.path.insert(0, str(ROOT))
from hercules.core.tool_catalog import CATEGORIES, catalog_payload

public = SITE / "public"
public.mkdir(exist_ok=True)
shutil.copytree(SITE / "assets", public / "assets", dirs_exist_ok=True)
catalog = catalog_payload()
catalog["categories"] = [{"key": item.key, "title": item.title} for item in CATEGORIES]
for capability in catalog["capabilities"]:
    capability.pop("estimated_context_tokens", None)
(public / "catalog.json").write_text(json.dumps(catalog, indent=2), encoding="utf-8")
readme = (ROOT / "README.md").read_text(encoding="utf-8")
match = re.search(r"## Install with your AI agent.*?```text\n(.*?)\n```", readme, re.S)
if not match:
    raise RuntimeError("Canonical installation prompt missing")
(public / "install.txt").write_text(match.group(1), encoding="utf-8")
(public / ".nojekyll").touch()
print(f"Prepared {catalog['full_tool_count']} tools / {len(catalog['capabilities'])} bundles")
