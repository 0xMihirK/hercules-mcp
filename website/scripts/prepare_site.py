"""Generate public facts from source without importing the Hercules runtime."""
from pathlib import Path
import json
import re
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "website"
sys.path.insert(0, str(ROOT))
from hercules.core.tool_catalog import CATEGORIES, catalog_payload

public = SITE / "public"
public.mkdir(exist_ok=True)
# Rebuild copied assets so production cannot retain a local preview or obsolete
# recordings. Archive the exact verified tree recoverably before replacing it.
copied_assets = public / "assets"
archives = SITE / "test-results/site-assets"
if "--development" not in sys.argv and copied_assets.exists():
    archives.mkdir(parents=True, exist_ok=True)
    destination = archives / str(time.time_ns())
    if copied_assets.is_symlink() or copied_assets.resolve().parent != public.resolve() or destination.resolve().parent != archives.resolve():
        raise ValueError("Refusing to archive copied assets outside the website")
    copied_assets.rename(destination)
shutil.copytree(SITE / "assets", public / "assets", dirs_exist_ok=True)
# A local development preview remains separate from the public recordings.
preview = SITE / "test-results/labs/preview-assets"
if "--development" in sys.argv and (preview / "manifest.json").is_file():
    shutil.copytree(preview, public / "assets/preview-recordings", dirs_exist_ok=True)
recording_root = public / "assets" / ("preview-recordings" if "--development" in sys.argv and (preview / "manifest.json").is_file() else "recordings")
native_manifest = json.loads((recording_root / "manifest.json").read_text(encoding="utf-8"))
bootstrap = {**native_manifest, "recordings": [{**r,"synchronized":[],"metrics":[],"artifacts":[],"reportPreview":""} for r in native_manifest["recordings"]]}
bootstrap["assetDirectory"] = recording_root.name
(SITE / "src/bootstrap.json").write_text(json.dumps(bootstrap), encoding="utf-8", newline="\n")
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
(SITE / "src/site-facts.json").write_text(json.dumps({"catalog":catalog,"installationPrompt":match.group(1)},ensure_ascii=False),encoding="utf-8",newline="\n")
(public / ".nojekyll").touch()
print(f"Prepared {catalog['full_tool_count']} tools / {len(catalog['capabilities'])} bundles")
