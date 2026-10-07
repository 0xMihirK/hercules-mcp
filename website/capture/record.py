"""Record unmodified native CLIs in an account-free, offline Docker PTY."""
import argparse
import codecs
import fcntl
import json
import os
from pathlib import Path
import pty
import re
import select
import signal
import struct
import time
import sys
import pyte

REAL_LAB = True
from labs.provider import ModelFixture, PROMPTS, start, prepare_workspace

VERSIONS = {"claude": "2.1.292", "codex": "0.160.1", "opencode": "1.18.35", "hermes": "0.21.5"}

def configure(client, scenario, home):
    home.mkdir(parents=True, exist_ok=True)
    env = {**{key:os.environ[key] for key in ("PATH", "LANG", "HERMES_TUI_DIR") if key in os.environ}, "HOME": str(home), "CAPTURE_SCENARIO": scenario, "TERM": "xterm-256color", "COLORTERM": "truecolor", "NO_TELEMETRY": "1", "DO_NOT_TRACK": "1", "CI": "", "DISABLE_AUTOUPDATER": "1"}
    for key in list(env):
        if key.endswith(("API_KEY", "AUTH_TOKEN", "ACCESS_TOKEN")):
            env.pop(key)
    command = ["python", "/capture/labs/bridge.py"]
    if client == "claude":
        # Declare the capture terminal's truecolor support explicitly; an
        # inherited CI flag otherwise makes Claude emit monochrome output.
        env.pop("CI", None)
        env["FORCE_COLOR"] = "3"
        env.update(CLAUDE_CONFIG_DIR=str(home / ".claude"), CLAUDE_CODE_USE_FOUNDRY="1", ANTHROPIC_FOUNDRY_BASE_URL="http://127.0.0.1:8765/anthropic", CLAUDE_CODE_SKIP_FOUNDRY_AUTH="1", CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC="1", CLAUDE_CODE_ENABLE_TASKS="1")
        env.update(CLAUDE_CODE_DISABLE_ALTERNATE_SCREEN="1", ENABLE_TOOL_SEARCH="false")
        (home / ".claude").mkdir()
        (home / ".claude" / "settings.json").write_text(json.dumps({"permissions": {"allow": ["mcp__hercules__*", "TaskCreate", "TaskGet", "TaskList", "TaskUpdate"]}, "skipDangerousModePermissionPrompt": False}))
        mcp = home / "mcp.json"
        mcp.write_text(json.dumps({"mcpServers": {"hercules": {"command": command[0], "args": command[1:]}}}))
        return ["claude", "--strict-mcp-config", "--mcp-config", str(mcp), "--model", "claude-sonnet-4-6"], env
    if client == "codex":
        env["CODEX_HOME"] = str(home / ".codex")
        Path(env["CODEX_HOME"]).mkdir()
        Path(env["CODEX_HOME"], "config.toml").write_text('''model = "gpt-6-sol"
model_provider = "fixture"
approval_policy = "on-request"
sandbox_mode = "workspace-write"
check_for_update_on_startup = false
disable_paste_burst = true
[model_providers.fixture]
name = "Local capture fixture"
base_url = "http://127.0.0.1:8765/v1"
wire_api = "responses"
requires_openai_auth = false
supports_websockets = false
[mcp_servers.hercules]
command = "python"
args = ["/capture/fixtures.py"]
startup_timeout_sec = 120
tool_timeout_sec = 240
'''.replace("/capture/fixtures.py", command[1]))
        return ["codex"], env
    if client == "opencode":
        for key, sub in (("XDG_CONFIG_HOME", "config"), ("XDG_DATA_HOME", "data"), ("XDG_CACHE_HOME", "cache"), ("XDG_STATE_HOME", "state"), ("OPENCODE_CONFIG_DIR", "opencode")):
            env[key] = str(home / sub); (home / sub).mkdir()
        env.update(OPENCODE_DISABLE_AUTOUPDATE="1", OPENCODE_DISABLE_MODELS_FETCH="1", OPENCODE_DISABLE_PROJECT_CONFIG="1", OPENCODE_PURE="1")
        config = {"$schema": "https://opencode.ai/config.json", "model": "fixture/capture-demo", "enabled_providers": ["fixture"], "provider": {"fixture": {"npm": "@ai-sdk/openai-compatible", "name": "Local capture fixture", "options": {"baseURL": "http://127.0.0.1:8765/v1"}, "models": {"capture-demo": {"name": "Capture demo", "limit": {"context": 128000, "output": 8192}}}}}, "mcp": {"hercules": {"type": "local", "command": command, "enabled": True}}}
        env["OPENCODE_CONFIG_CONTENT"] = json.dumps(config)
        return ["opencode"], env
    env.update(HERMES_HOME=str(home / ".hermes"), HERMES_SKIP_SETUP="1", HERMES_SKIP_UPDATE_CHECK="1", HERMES_GUEST_ONBOARDING="0")
    Path(env["HERMES_HOME"]).mkdir()
    Path(env["HERMES_HOME"], "config.yaml").write_text('''model:
  provider: custom
  default: capture-demo
  base_url: http://127.0.0.1:8765/v1
  api_key: ""
display:
  streaming: true
nous:
  guest: false
telemetry:
  shared_metrics:
    enabled: false
    send: false
    offer_version: 2
tools:
  tool_search:
    enabled: "off"
mcp_servers:
  hercules:
    command: python
    args: [/capture/fixtures.py]
    lazy: false
'''.replace("/capture/fixtures.py", command[1]))
    return ["hermes", "--tui", "--provider", "custom", "-m", "capture-demo", "-t", "todo,hercules"], env

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("client", choices=VERSIONS)
    parser.add_argument("scenario", choices=PROMPTS)
    parser.add_argument("--cols", type=int, default=120)
    parser.add_argument("--rows", type=int, default=36)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--real-lab", action="store_true", required=True)
    parser.add_argument("--duration", type=float, default=150)
    args = parser.parse_args()
    home = Path("/home/capture/session")
    command, env = configure(args.client, args.scenario, home)
    prepare_workspace(home, args.scenario)
    server = start(args.scenario, args.client)
    pid, master = pty.fork()
    if pid == 0:
        fcntl.ioctl(0, 0x5414, struct.pack("HHHH", args.rows, args.cols, 0, 0))
        os.chdir(home)
        os.execvpe(command[0], command, env)
    fcntl.ioctl(master, 0x5414, struct.pack("HHHH", args.rows, args.cols, 0, 0))
    timestamp = int(time.time())
    started = time.monotonic()
    decoder = codecs.getincrementaldecoder("utf-8")("replace")
    events, plain, chapters = [], "", {}
    screen = pyte.Screen(args.cols, args.rows)
    stream = pyte.Stream(screen)
    def diagnostic_rows():
        # Native wide/combining glyphs can leave empty continuation cells in
        # pyte. Read the diagnostic buffer without pyte's char[0] assumption.
        # This does not change the raw native output stored in the recording.
        return ["".join(screen.buffer[y][x].data for x in range(screen.columns))
                for y in range(screen.lines)]
    prompt_sent = False
    tour_started = False
    tour_at = None
    menu_seen_at = None
    menu_advanced = False
    claude_ready_at = None
    inputs = []
    finished_at = None
    failed_at = None
    approval_at = None
    onboarding = set()
    live_at = 0
    command_retry_at = 0
    command_retries = 0
    model_confirm_at = 0
    # Codex keeps its composer disabled until MCP startup has completed.
    boot_wait = 5 if args.client == "claude" else 20
    def send(data):
        events.append([round(time.monotonic() - started, 6), "i", data])
        os.write(master, data.encode())
    def schedule(delay, text):
        for i, char in enumerate(text):
            inputs.append((time.monotonic() + delay + i * .065 + (.4 if char == "\r" else 0), char))
    try:
        while time.monotonic() - started < args.duration:
            elapsed = time.monotonic() - started
            ready, _, _ = select.select([master], [], [], .025)
            if ready:
                try:
                    raw = os.read(master, 65536)
                except OSError:
                    break
                if not raw:
                    break
                text = decoder.decode(raw)
                if text:
                    events.append([round(elapsed, 6), "o", text])
                    # Pyte does not recognize private CSI keyboard-stack
                    # commands. Ignore them only in the diagnostic screen;
                    # recorded output remains byte-for-byte terminal text.
                    stream.feed(re.sub(r"\x1b\[[<>?][0-9;]*u", "", text))
                    plain += re.sub(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1b\\))", "", text)
                # Answer standard terminal capability probes; no application keys.
                if b"\x1b[6n" in raw: send(f"\x1b[{screen.cursor.y + 1};{screen.cursor.x + 1}R")
                if b"\x1b[c" in raw or b"\x1b[0c" in raw: send("\x1b[?1;2c")
                if b"\x1b[>c" in raw: send("\x1b[>0;276;0c")
                if b"\x1b[?u" in raw: send("\x1b[?0u")
                if b"\x1b[18t" in raw: send(f"\x1b[8;{args.rows};{args.cols}t")
                for code, rgb in ((10, "eeee/eeee/eeee"), (11, "0a0a/0a0a/0a0a")):
                    if f"\x1b]{code};?".encode() in raw: send(f"\x1b]{code};rgb:{rgb}\x1b\\")
            while inputs and inputs[0][0] <= time.monotonic():
                _, char = inputs.pop(0); send(char)
            # Only disposable workspace trust/onboarding is accepted. Never login.
            recent = "\n".join(diagnostic_rows())
            if elapsed > live_at + 2:
                Path("/out/live-screen.txt").write_text(recent)
                live_at = elapsed
            compact = re.sub(r"\s+", "", recent)
            # OpenCode's narrow onboarding dialog can mount after the first
            # composer paint. Select only the configured loopback model, then
            # resume the native inspection once the dialog has closed.
            if args.client == "opencode" and "Selectmodel" in compact and "Capturedemo" in compact and not inputs and elapsed > model_confirm_at + 2:
                send("\r")
                model_confirm_at = elapsed
                if tour_started and menu_seen_at is None:
                    tour_started = False
            if args.client == "claude" and not tour_started:
                if "theme" not in onboarding and ("Choosethetextstyle" in compact or "Choosethecolortheme" in compact):
                    onboarding.add("theme")
                    send("\r"); plain = ""; time.sleep(.2)
                elif "trust" not in onboarding and ("Yes,Itrustthisfolder" in compact or "Yes,Itrustthisdirectory" in compact):
                    onboarding.add("trust")
                    # The first painted menu can precede its input handler.
                    # Send the arrow atomically after mount; confirm only once
                    # the selected native row shows the disposable folder.
                    inputs.append((time.monotonic() + .6, "\x1b[B"))
                    plain = ""
                elif "trust" in onboarding and "trust-confirmed" not in onboarding and ("❯Yes,Itrustthisfolder" in compact or "❯Yes,Itrustthisdirectory" in compact):
                    onboarding.add("trust-confirmed")
                    schedule(.2, "\r")
                elif "notes" not in onboarding and "PressEntertocontinue" in compact:
                    onboarding.add("notes")
                    send("\r"); plain = ""; time.sleep(.2)
            if args.client == "hermes" and not tour_started and "HelpimproveHermes?" in compact:
                send("\x1b"); plain = ""; time.sleep(.2)
            if args.client == "codex" and not tour_started and "trust" not in onboarding and "trustthecontentsofthisdirectory" in compact.lower():
                onboarding.add("trust")
                send("\r"); plain = ""
            if args.client == "codex" and not tour_started and "model-choice" not in onboarding and "Useexistingmodel" in compact:
                onboarding.add("model-choice")
                send("\x1b[B")
                schedule(.3, "\r")
            # These are tool-specific approvals inside the offline fixture container.
            if args.client == "codex" and "AllowtheherculesMCPservertoruntool" in compact:
                if approval_at is None:
                    approval_at = time.monotonic() + 1.8
                elif time.monotonic() >= approval_at:
                    send("\r"); plain = ""; approval_at = None
            hermes_ready = "Hermes" in recent and ("capture-demo" in recent or "custom" in recent)
            client_ready = hermes_ready if args.client == "hermes" else "ctrl+pcommands" in compact and "Selectmodel" not in compact if args.client == "opencode" else "ClaudeCodev" in compact if args.client == "claude" else True
            if REAL_LAB:
                client_ready = client_ready and Path("/tmp/mcp-ready.json").exists()
            if args.client == "claude" and client_ready and claude_ready_at is None:
                claude_ready_at = elapsed
            intro_ready = args.client != "claude" or claude_ready_at is not None and elapsed > claude_ready_at + 2
            if not tour_started and elapsed > boot_wait and client_ready and intro_ready:
                tour_started = True; tour_at = elapsed; chapters["mcp"] = elapsed
                if args.client != "hermes":
                    schedule(0, "/mcps\r" if args.client == "opencode" else "/mcp verbose\r" if args.client == "codex" else "/mcp\r")
                else:
                    schedule(0, "/tools list\r")
            if args.client == "codex":
                # /mcp verbose is inline. At 48 columns its server heading
                # scrolls away before the final resource inventory is painted.
                menu_visible = ("MCP" in recent and "hercules" in recent.lower()) or (
                    "Resourcetemplates:(none)" in compact and "workspace_write_file" in compact and "get_lolbas" in compact)
            elif args.client == "opencode":
                menu_visible = "MCP" in recent and "hercules" in recent.lower() and "ToggleMCPs" not in compact
                # A mounted slash-completion menu is observable evidence that
                # the command was typed but its first Enter was not handled.
                if tour_started and menu_seen_at is None and not inputs and "/mcps" in compact and "ToggleMCPs" in compact and elapsed > command_retry_at + 2 and elapsed > tour_at + 3 and command_retries < 3:
                    send("\r")
                    command_retry_at = elapsed
                    command_retries += 1
            else:
                menu_visible = "MCP" in recent and "hercules" in recent.lower() if args.client != "hermes" else "Built-intoolsets" in compact
            if tour_started and menu_seen_at is None and menu_visible:
                menu_seen_at = elapsed
            if args.client == "hermes" and menu_seen_at is not None and not menu_advanced and elapsed > menu_seen_at + 3:
                send("G"); menu_advanced = True
            if tour_started and not prompt_sent and menu_seen_at is not None and elapsed > menu_seen_at + 8:
                send("\x1b")
                prompt_sent = True; chapters["query"] = elapsed + .8
                if not args.smoke:
                    schedule(.8, PROMPTS[args.scenario] + "\r")
            if args.smoke and prompt_sent and elapsed > menu_seen_at + 12:
                break
            if ModelFixture.completed.is_set() and finished_at is None:
                finished_at = elapsed; chapters["report"] = elapsed
            if getattr(ModelFixture, "failed", None) and failed_at is None:
                failed_at = elapsed
            if failed_at is not None and elapsed > failed_at + 8:
                break
            if finished_at is not None and elapsed > finished_at + 6:
                break
    finally:
        try:
            os.killpg(pid, signal.SIGTERM)
            for _ in range(30):
                if os.waitpid(pid, os.WNOHANG)[0]:
                    break
                time.sleep(.1)
            else:
                os.killpg(pid, signal.SIGKILL)
                os.waitpid(pid, 0)
        except (ProcessLookupError, ChildProcessError):
            pass
        os.close(master); server.shutdown()
    tail = decoder.decode(b"", final=True)
    if tail: events.append([round(time.monotonic() - started, 6), "o", tail])
    name = f"{args.client}-{args.scenario}-{args.cols}"
    target = Path("/out") / (name + ".cast")
    duration = round(time.monotonic() - started, 6)
    header = {"version": 2, "width": args.cols, "height": args.rows, "timestamp": timestamp, "duration": duration, "env": {"TERM": "xterm-256color", "SHELL": "/bin/sh"}, "title": args.client + " / " + args.scenario, "clientVersion": VERSIONS[args.client], "scenario": args.scenario, "chapters": chapters, "scriptedModel": True, "realTools": REAL_LAB, "fixture": not REAL_LAB}
    calls = [json.loads(line) for line in Path("/tmp/mcp-calls.jsonl").read_text().splitlines()] if Path("/tmp/mcp-calls.jsonl").exists() else []
    if REAL_LAB:
        for call in calls:
            call["requestedAt"] = round(call["requestedAt"] - started, 6)
            call["completedAt"] = round(call["completedAt"] - started, 6)
        if calls:
            chapters["runtime"] = calls[0]["requestedAt"]
            chapters["investigation"] = calls[min(2, len(calls)-1)]["requestedAt"]
            report_calls = [c for c in calls if c["name"] == "workspace_write_file"]
            if report_calls:
                chapters["reportWriting"] = report_calls[-1]["requestedAt"]
    target.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in [header, *events]) + "\n", encoding="utf-8")
    status = {"client": args.client, "version": VERSIONS[args.client], "scenario": args.scenario, "cols": args.cols, "rows": args.rows, "events": len(events), "duration": duration, "modelRequests": len(ModelFixture.requests), "mcpCalls": calls, "completed": finished_at is not None, "chapters": chapters, "command": command, "accountAccess": False, "externalNetwork": False}
    Path("/out", name + ".json").write_text(json.dumps(status, indent=2))
    Path("/out", name + ".txt").write_text(plain)
    Path("/out", name + "-screen.txt").write_text("\n".join(diagnostic_rows()))
    if Path("/tmp/model-requests.json").exists():
        Path("/out", name + "-requests.json").write_text(Path("/tmp/model-requests.json").read_text())
    print(json.dumps({key:status[key] for key in ("client", "version", "scenario", "cols", "rows", "duration", "completed", "modelRequests")}))

if __name__ == "__main__":
    main()
