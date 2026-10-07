"""Run a capture matrix in disposable, network-isolated Docker containers."""
import argparse
import json
from pathlib import Path
import subprocess

CLIENTS = ("claude", "codex", "opencode", "hermes")
CASES = json.loads(Path(__file__).with_name("cases.json").read_text())
SCENARIOS = tuple(CASES)
IMAGE = "hercules-showcase-capture:20261007"

def validate_session(status, scenario):
    """Require the ordered operation arguments, not merely matching tool names."""
    required = [{"tool": "system_start_container", "arguments": {}}, *CASES[scenario]["operations"], {"tool": "workspace_read_file", "arguments": {"path": "artifacts/" + CASES[scenario]["artifact"]}}, {"tool": "workspace_write_file", "arguments": {"path": "reports/" + scenario + ".md"}}]
    calls = iter(status.get("mcpCalls", []))
    for operation in required:
        if not any(call["name"] == operation["tool"] and all(call.get("arguments", {}).get(key) == value for key, value in operation["arguments"].items()) for call in calls):
            raise ValueError("Missing ordered Hercules call: " + operation["tool"])
    if not status["completed"] or status["accountAccess"] or status["externalNetwork"]:
        raise ValueError("Native session incomplete or capture isolation failed")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--client", choices=CLIENTS)
    parser.add_argument("--scenario", choices=SCENARIOS, nargs="+")
    parser.add_argument("--cols", type=int, choices=(80, 120))
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--duration", type=float, default=150)
    args = parser.parse_args()
    source = Path(__file__).resolve().parent
    output = source.parent / "test-results" / ("smoke" if args.smoke else "capture")
    output.mkdir(parents=True, exist_ok=True)
    for client in (args.client,) if args.client else CLIENTS:
        for scenario in args.scenario or (("scan",) if args.smoke else SCENARIOS):
            for cols in (args.cols,) if args.cols else (120, 80):
                name = f"hercules-capture-{client}-{scenario}-{cols}"
                command = ["docker", "run", "--rm", "--name", name, "--network", "none", "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--mount", f"type=bind,src={source},dst=/capture,readonly", "--mount", f"type=bind,src={output},dst=/out", IMAGE, client, scenario, "--cols", str(cols), "--rows", "36" if cols == 120 else "28", "--duration", str(args.duration)]
                if args.smoke:
                    command.append("--smoke")
                print(f"Recording {client} / {scenario} at {cols} columns", flush=True)
                subprocess.run(command, check=True)
                if not args.smoke:
                    status = json.loads((output / f"{client}-{scenario}-{cols}.json").read_text())
                    validate_session(status, scenario)

if __name__ == "__main__":
    main()
