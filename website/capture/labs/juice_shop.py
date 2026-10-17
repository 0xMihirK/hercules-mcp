"""Capture a real, internal-only Hercules browser session against Juice Shop."""
from __future__ import annotations

import json
import subprocess
import time

from .program import payload
from .run import Lab, docker

JUICE_SHOP = "bkimminich/juice-shop@sha256:8739101ade29358abb5469ee66ae78e582c97ed0a5543a4ad102e5fa5193526b"
FFMPEG_IMAGE = "mwader/static-ffmpeg@sha256:e8a512d3ffb5204ab662f1394e1d8237def95f93db2709cd763d79902ae292fd"
SOURCE_FPS = 10
SHOWCASE_FPS = 30
SHOWCASE_SPEED = 2.5


def install_recorder(lab, session_id: str):
    """Add the pinned static encoder to this disposable Hercules runtime only."""
    encoder = lab.directory.parent / "ffmpeg-static"
    if not encoder.is_file():
        container = docker("create", "--entrypoint", "/ffmpeg", FFMPEG_IMAGE,
                           stdout=subprocess.PIPE, text=True).stdout.strip()
        try:
            docker("cp", f"{container}:/ffmpeg", encoder, stdout=subprocess.DEVNULL)
        finally:
            docker("rm", container, stdout=subprocess.DEVNULL)
    docker("cp", encoder, f"hercules-{session_id}:/usr/local/bin/ffmpeg", stdout=subprocess.DEVNULL)
    check = lab.call_data("shell_exec", {"command": "chmod +x /usr/local/bin/ffmpeg && ffmpeg -version | head -n 1", "timeout": 15})
    if check.get("exit_code") != 0 or "ffmpeg version" not in check.get("stdout", ""):
        raise RuntimeError("Could not install the pinned static video encoder in the disposable runtime")


def encode_showcase_assets(directory):
    """Keep native pixels; speed the long scripted RPC gaps for a useful loop."""
    mount = f"type=bind,source={directory.resolve()},target=/work"
    try:
        docker("run", "--rm", "--network", "none", "--mount", mount, "--entrypoint", "/ffmpeg", FFMPEG_IMAGE,
               "-y", "-i", "/work/juice-shop-session-native.mp4",
               "-vf", f"setpts={1 / SHOWCASE_SPEED}*PTS,fps={SHOWCASE_FPS}",
               "-an", "-c:v", "libx264", "-crf", "20", "-preset", "fast", "-pix_fmt", "yuv420p",
               "-movflags", "+faststart", "/work/juice-shop-session.mp4",
               capture_output=True, text=True)
        docker("run", "--rm", "--network", "none", "--mount", mount, "--entrypoint", "/ffmpeg", FFMPEG_IMAGE,
               "-y", "-sseof", "-0.1", "-i", "/work/juice-shop-session.mp4",
               "-frames:v", "1", "-update", "1", "/work/juice-shop-poster.png",
               capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        diagnostic = (exc.stderr or exc.stdout or "").strip()[-1800:]
        raise RuntimeError("Pinned browser-video encoding failed: " + diagnostic) from exc
    for name, minimum in (("juice-shop-session.mp4", 100_000), ("juice-shop-poster.png", 10_000)):
        if not (directory / name).is_file() or (directory / name).stat().st_size < minimum:
            raise RuntimeError("Encoded showcase asset is missing or implausibly small: " + name)


class JuiceShopLab(Lab):
    """Reuse the transaction-owned Hercules harness with one local target."""

    def __enter__(self):
        try:
            docker("network", "create", "--internal", "--subnet", self.subnet,
                   "--label", "hercules.capture.owner=" + self.owner, self.network, stdout=subprocess.DEVNULL)
            self.created.append(("network", self.network))
            # No published host ports, host mounts, capabilities, or Docker socket.
            docker("run", "-d", "--pull", "never", "--name", self.fixture,
                   "--network", self.network, "--ip", self.address,
                   "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
                   "--memory", "1g", "--pids-limit", "512",
                   "--label", "hercules.capture.owner=" + self.owner,
                   JUICE_SHOP, stdout=subprocess.DEVNULL)
            self.created.append(("container", self.fixture))
            (self.directory / "inputs").mkdir()
            for _ in range(120):
                check = subprocess.run(["docker", "exec", self.fixture, "/nodejs/bin/node", "-e",
                    "fetch('http://127.0.0.1:3000').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"],
                    check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if check.returncode == 0:
                    break
                time.sleep(.5)
            else:
                raise RuntimeError("Pinned local Juice Shop image did not become ready")

            environment = self._host_environment()
            self._start_server(environment)
            return self
        except BaseException:
            self.close()
            raise

    def _host_environment(self):
        from .sandbox import host_environment
        return host_environment(self.source, self.workspace, self.network)

    def _start_server(self, environment):
        import threading
        import subprocess
        from .sandbox import server_command
        self.process = subprocess.Popen(server_command(self.source), env=environment, cwd=self.source,
                                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        threading.Thread(target=self.log_errors, args=(self.process.stderr, "hercules.stderr.log"), daemon=True).start()
        threading.Thread(target=self.read_responses, daemon=True).start()

    def call(self, name: str, arguments: dict | None = None):
        result = self.rpc("tools/call", {"name": name, "arguments": arguments or {}})
        value = payload(result)
        if result.get("isError") or (isinstance(value, dict) and value.get("status") in {
            "error", "invalid_parameter", "invalid_target", "blocked", "not_found", "backend_unavailable"
        }):
            raise RuntimeError(f"{name} failed: {json.dumps(value, ensure_ascii=False)[:1800]}")
        return result

    def call_data(self, name: str, arguments: dict | None = None):
        result = self.call(name, arguments)
        value = payload(result)
        (self.directory / "tool-results.jsonl").open("a", encoding="utf-8").write(
            json.dumps({"name": name, "arguments": arguments or {}, "result": value},
                       ensure_ascii=False) + "\n")
        return value

    def close(self):
        """Stop this MCP runtime first, then remove only resources with our label."""
        if self.process and self.process.poll() is None and self.session and not getattr(self, "runtime_stopped", False):
            try:
                self.call("system_stop_container")
            except Exception:
                pass
        if self.process:
            try:
                self.process.stdin.close()
                self.process.wait(timeout=30)
            except (OSError, subprocess.TimeoutExpired):
                self.process.terminate()
                self.process.wait(timeout=10)
        for kind, name in reversed(self.created):
            inspected = subprocess.run(["docker", kind, "inspect", name], capture_output=True,
                                       text=True, encoding="utf-8", errors="replace")
            if inspected.returncode:
                missing = (f"no such {kind}: {name}", f"{kind} {name} not found")
                if any(marker in inspected.stderr.lower() for marker in missing):
                    continue
                raise RuntimeError("Cleanup could not verify Docker resource " + name + ": " + inspected.stderr[-1000:])
            if not inspected.stdout:
                raise RuntimeError("Docker returned an empty inspect result; cleanup refused")
            item = json.loads(inspected.stdout)[0]
            labels = item.get("Labels", {}) if kind == "network" else item.get("Config", {}).get("Labels", {})
            if labels.get("hercules.capture.owner") != self.owner:
                raise RuntimeError("Cleanup refused an unowned resource: " + name)
            docker(kind, "rm", *(["-f"] if kind == "container" else []), name,
                   stdout=subprocess.DEVNULL)
        (self.directory / "transaction.json").write_text(json.dumps({
            "owner": self.owner, "internalNetwork": self.network, "labAddress": self.address,
            "juiceShopImage": JUICE_SHOP, "noPublishedPorts": True, "noHostDockerSocketInAgents": True,
            "personalCredentials": False, "cleanupComplete": True,
            "session": str(self.session) if self.session else None
        }, indent=2) + "\n", encoding="utf-8", newline="\n")


def main():
    name = f"juice-shop-local-{time.time_ns()}"
    with JuiceShopLab(name, subnet=78) as lab:
        surface = lab.initialize()
        tools = {item["name"]: item["inputSchema"] for item in surface["tools"]["tools"]}
        required = ("system_start_container", "system_stop_container", "browser_skill", "browser_open",
                    "browser_snapshot", "browser_act", "browser_cmd", "browser_screenshot",
                    "network_curl", "nmap_scan", "workspace_write_file", "workspace_read_file")
        missing = sorted(set(required) - tools.keys())
        if missing:
            raise RuntimeError("Required real Hercules tools are unavailable: " + ", ".join(missing))
        (lab.directory / "capture-profile.json").write_text(json.dumps({
            "juiceShopImage": JUICE_SHOP, "juiceShopVersion": "20.2.0", "platform": "linux/amd64",
            "videoEncoderImage": FFMPEG_IMAGE,
            "agentBrowser": "0.33.1", "sourceFrameRateFps": SOURCE_FPS,
            "showcasePlaybackSpeed": SHOWCASE_SPEED, "showcaseOutputFrameRateFps": SHOWCASE_FPS,
            "network": "Docker internal network; no published ports", "agent": "real Hercules MCP calls",
            "modelNarration": "scripted", "publicTargets": False
        }, indent=2) + "\n", encoding="utf-8", newline="\n")
        started = lab.call_data("system_start_container")
        if started.get("status") != "success" or not started.get("session_id"):
            raise RuntimeError("Hercules did not start the disposable runtime")
        lab.session = lab.workspace / started["session_id"]
        lab.runtime_stopped = False
        print("Started real Hercules runtime " + started["session_id"], flush=True)
        install_recorder(lab, started["session_id"])
        skill = lab.call_data("browser_skill", {"name": "core", "full": True})
        (lab.directory / "browser-skill.json").write_text(json.dumps(skill, indent=2), encoding="utf-8")
        runtime_check = lab.call_data("shell_exec", {"command": "command -v ffmpeg || true; agent-browser --version", "timeout": 15})
        (lab.directory / "runtime-check.json").write_text(json.dumps(runtime_check, indent=2), encoding="utf-8")
        nmap = lab.call_data("nmap_scan", {"mode": "port", "target": lab.address,
                                           "ports": "3000", "extra_args": "-Pn -sT"})
        if "open" not in json.dumps(nmap, ensure_ascii=False).lower() or "3000" not in json.dumps(nmap):
            raise RuntimeError("The scoped service discovery did not confirm Juice Shop on port 3000")
        http = lab.call_data("network_curl", {"url": f"http://{lab.address}:3000/",
                                               "extra_args": "--max-time 5 -o /opt/workspace/artifacts/juice-shop-home.html"})
        if http.get("exit_code") != 0:
            raise RuntimeError("The real HTTP check did not complete successfully")
        opened = lab.call_data("browser_open", {"url": f"http://{lab.address}:3000/",
                                                 "session": "juice-shop-review"})
        if not opened.get("browser_result", {}).get("success"):
            raise RuntimeError("CloakBrowser did not open the local application")

        first = lab.call_data("browser_snapshot", {"session": "juice-shop-review", "interactive": True})
        initial_snapshot = first.get("stdout", "")
        if "OWASP Juice Shop" not in initial_snapshot:
            raise RuntimeError("The real browser snapshot did not identify OWASP Juice Shop")
        acted = lab.call_data("browser_act", {"action": "click", "target": "button", "target_type": "role",
                                             "name": "Close Welcome Banner", "exact": True,
                                             "session": "juice-shop-review"})
        if acted.get("exit_code") != 0:
            raise RuntimeError("Could not dismiss the real application welcome banner")
        after_dismiss = lab.call_data("browser_snapshot", {"session": "juice-shop-review", "interactive": True})
        if "Close Welcome Banner" in after_dismiss.get("stdout", ""):
            raise RuntimeError("The fresh snapshot shows the welcome banner was not dismissed")
        if "dismiss cookie message" in after_dismiss.get("stdout", "").lower():
            consent = lab.call_data("browser_act", {"action": "click", "target": "button", "target_type": "role",
                                                    "name": "dismiss cookie message", "exact": True,
                                                    "session": "juice-shop-review"})
            if consent.get("exit_code") != 0:
                raise RuntimeError("Could not dismiss the training app's cookie overlay")
            after_dismiss = lab.call_data("browser_snapshot", {"session": "juice-shop-review", "interactive": True})
            if "dismiss cookie message" in after_dismiss.get("stdout", "").lower():
                raise RuntimeError("The fresh snapshot shows the cookie overlay was not dismissed")

        # Start after the first-run UI is cleared so the public loop opens on
        # the usable application, while the recorded challenge remains native.
        record_path = "/opt/workspace/artifacts/juice-shop-session.mp4"
        started_recording = lab.call_data("browser_cmd", {
            "args": f"record start {record_path}", "session": "juice-shop-review", "timeout": 30
        })
        if started_recording.get("exit_code") != 0:
            raise RuntimeError("Native browser video recording failed to start")
        app_board = lab.call_data("browser_open", {"url": f"http://{lab.address}:3000/#/score-board",
                                                   "session": "juice-shop-review"})
        if not app_board.get("browser_result", {}).get("success"):
            raise RuntimeError("The local challenge board did not open")
        board = lab.call_data("browser_snapshot", {"session": "juice-shop-review", "detailed": True})
        board_text = board.get("stdout", "")
        if "dismiss cookie message" in board_text.lower():
            consent = lab.call_data("browser_act", {"action": "click", "target": "button", "target_type": "role",
                                                    "name": "dismiss cookie message", "exact": True,
                                                    "session": "juice-shop-review"})
            if consent.get("exit_code") != 0:
                raise RuntimeError("Could not dismiss the training app's cookie overlay")
            board = lab.call_data("browser_snapshot", {"session": "juice-shop-review", "detailed": True})
            board_text = board.get("stdout", "")
        solved_marker = "You successfully solved a challenge: Score Board"
        if solved_marker not in board_text or "1/186" not in board_text:
            raise RuntimeError("Juice Shop did not report the Score Board challenge as solved")
        screenshot = lab.call_data("browser_screenshot", {
            "path": "artifacts/juice-shop-scoreboard.png", "session": "juice-shop-review", "full": False
        })
        if screenshot.get("exit_code") != 0:
            raise RuntimeError("Could not save the real Juice Shop browser evidence")
        retained = lab.call_data("shell_exec", {"command":
            "python3 -c \"from pathlib import Path; source=Path('/opt/workspace/browser/juice-shop-review/artifacts/juice-shop-scoreboard.png'); target=Path('/opt/workspace/artifacts/juice-shop-scoreboard.png'); target.write_bytes(source.read_bytes()); print(target.stat().st_size)\"",
            "timeout": 15})
        if retained.get("exit_code") != 0:
            raise RuntimeError("Could not retain the native browser screenshot with the session artifacts")
        (lab.directory / "browser-observations.json").write_text(json.dumps({
            "initialSnapshot": initial_snapshot, "afterDismiss": after_dismiss.get("stdout", ""),
            "scoreboard": board_text, "appTitle": opened.get("browser_result", {}).get("data", {}).get("title"),
            "screenshot": screenshot
        }, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")
        report = "\n".join([
            "# OWASP Juice Shop local walkthrough", "",
            "The Hercules MCP runtime inspected only this transaction-owned Juice Shop on a Docker internal network.",
            "No host port was published and no public target was contacted. The model narration is scripted; Hercules tool results are real.", "",
            "## Verified sequence", "",
            "- Nmap identified the scoped Juice Shop service on port 3000.",
            "- A separate HTTP request confirmed the application response and retained the page under `artifacts/juice-shop-home.html`.",
            "- Hercules opened the application in its CloakBrowser-backed browser session and inspected the accessibility snapshot.",
            "- The welcome banner and cookie overlay were dismissed; opening the application's hidden challenge board solved the Score Board challenge, confirmed by Juice Shop itself.",
            "- Juice Shop reported 1 of 186 challenges solved in the captured state.",
            "- Browser evidence is retained at `artifacts/juice-shop-scoreboard.png`.", "",
            "## Scope and limits", "",
            "This recording shows an authorized walkthrough of the deliberately vulnerable local training app. It does not claim CAPTCHA bypass or exploitation of an external site.",
            "CloakBrowser reduces common automation signals; bot-detection outcomes are not guaranteed.", ""
        ])
        write = lab.call_data("workspace_write_file", {"path": "reports/juice-shop-walkthrough.md", "content": report})
        if write.get("status") not in (None, "success"):
            raise RuntimeError("The walkthrough report could not be written")
        verified = lab.call_data("workspace_read_file", {"path": "reports/juice-shop-walkthrough.md"})
        if "OWASP Juice Shop local walkthrough" not in json.dumps(verified, ensure_ascii=False):
            raise RuntimeError("The saved report could not be reread")
        stopped_recording = lab.call_data("browser_cmd", {
            "args": "record stop", "session": "juice-shop-review", "timeout": 30
        })
        if stopped_recording.get("exit_code") != 0:
            raise RuntimeError("Native browser video recording did not stop cleanly")
        host_recording = lab.session / "artifacts/juice-shop-session.mp4"
        host_poster = lab.session / "artifacts/juice-shop-scoreboard.png"
        if not host_recording.is_file() or host_recording.stat().st_size < 100_000:
            raise RuntimeError("The native browser recording is missing or implausibly small")
        if not host_poster.is_file() or host_poster.stat().st_size < 10_000:
            raise RuntimeError("The native browser screenshot artifact is missing")
        stop = lab.call_data("system_stop_container")
        if stop.get("status") != "success":
            raise RuntimeError("The owned Hercules runtime did not stop cleanly")
        lab.runtime_stopped = True
        retained_report = lab.session / "reports/juice-shop-walkthrough.md"
        if not retained_report.is_file() or "OWASP Juice Shop local walkthrough" not in retained_report.read_text(encoding="utf-8"):
            raise RuntimeError("The report did not remain readable after runtime shutdown")
        native_master = lab.directory / "juice-shop-session-native.mp4"
        native_master.write_bytes(host_recording.read_bytes())
        destination = lab.directory / "public-assets"
        destination.mkdir()
        (destination / "juice-shop-session-native.mp4").write_bytes(native_master.read_bytes())
        encode_showcase_assets(destination)
        (lab.directory / "capture-result.json").write_text(json.dumps({
            "complete": True, "toolCalls": len(lab.calls), "image": JUICE_SHOP,
            "nativeMaster": str(native_master), "recording": str(destination / "juice-shop-session.mp4"),
            "poster": str(destination / "juice-shop-poster.png"),
            "playbackSpeed": SHOWCASE_SPEED, "outputFrameRateFps": SHOWCASE_FPS,
            "reportAfterStopVerified": True, "verifiedChallenge": "Score Board",
            "challengeCount": "1/186", "challengeBoardSnapshot": board_text
        }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
        print(json.dumps({"capture": str(lab.directory), "owner": lab.owner,
                          "toolCalls": len(lab.calls), "videoBytes": (destination / "juice-shop-session.mp4").stat().st_size,
                          "posterBytes": (destination / "juice-shop-poster.png").stat().st_size,
                          "reportAfterStopVerified": True}, indent=2), flush=True)


if __name__ == "__main__":
    main()
