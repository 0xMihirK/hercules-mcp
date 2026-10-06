"""Validate complete native captures before copying public playback assets."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

from run import CLIENTS, SCENARIOS, IMAGE

def main():
    root = Path(__file__).resolve().parent
    source = root.parent / "test-results" / "capture"
    destination = root.parent / "assets" / "recordings"
    approved = []
    for client in CLIENTS:
        for scenario in SCENARIOS:
            for cols, rows in ((120, 36), (80, 28)):
                name = f"{client}-{scenario}-{cols}"
                status = json.loads((source / (name + ".json")).read_text())
                recording = source / (name + ".cast")
                header = json.loads(recording.read_text(encoding="utf-8").splitlines()[0])
                calls = [call["name"] for call in status.get("mcpCalls", [])]
                operation = {"scan": "nmap_scan", "ctf": "ctf_binwalk", "web": "web_scan"}[scenario]
                expected = ["system_start_container", operation, "workspace_read_file", "workspace_write_file"]
                if not status["completed"] or not all(tool in calls for tool in expected):
                    raise ValueError(f"{name}: incomplete native model/tool session")
                if status["accountAccess"] or status["externalNetwork"]:
                    raise ValueError(f"{name}: capture isolation failed")
                if (header["width"], header["height"]) != (cols, rows):
                    raise ValueError(f"{name}: incorrect terminal geometry")
                if client == "codex" and "MCP Tools" not in recording.read_text(encoding="utf-8"):
                    raise ValueError(f"{name}: native MCP inventory was not captured")
                approved.append((recording, {"file": name + ".cast", "client": client, "version": status["version"], "scenario": scenario, "columns": cols, "rows": rows, "duration": header["duration"], "timestamp": header["timestamp"], "chapters": header["chapters"], "tools": calls, "sha256": hashlib.sha256(recording.read_bytes()).hexdigest()}))
    # Validate the entire matrix before writing any public files.
    destination.mkdir(parents=True, exist_ok=True)
    for recording, _ in approved:
        shutil.copyfile(recording, destination / recording.name)
    manifest = {"format": "asciicast-v2", "playbackSpeed": 1, "nativeUI": True, "scriptedModelAndToolResults": True, "accountAccess": False, "externalNetwork": False, "term": "xterm-256color", "theme": "native dark", "font": "IBM Plex Mono", "reproductionImage": subprocess.check_output(["docker", "image", "inspect", IMAGE, "--format", "{{.Id}}"], text=True).strip(), "herculesSourceCommit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root.parent.parent, text=True).strip(), "schemaSha256": hashlib.sha256((root / "hercules-surface.json").read_bytes()).hexdigest(), "recordings": [metadata for _, metadata in approved]}
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Published {len(approved)} validated native recordings to {destination}")

if __name__ == "__main__":
    main()
