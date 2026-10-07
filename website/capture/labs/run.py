"""Transaction-owned local labs and private STDIO relay to real host Hercules."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import sys
import threading
import time
import uuid

from .cases import CASES
from .program import Program, payload
from .sandbox import ROOT, fresh_source, host_environment, server_command

IMAGE = "hercules-showcase-capture:20261007-v2"
FIXTURE = "hercules-showcase-lab:20261007"
CAPTURE = ROOT / "website/capture"
RESULTS = ROOT / "website/test-results/labs"


def docker(*args, **options):
    return subprocess.run(["docker", *map(str, args)], check=True, **options)


class Lab:
    def __init__(self, name, subnet=42):
        self.owner = "hercules-capture-" + uuid.uuid4().hex[:12]
        self.network = self.owner + "-net"
        self.fixture = self.owner + "-fixture"
        self.relay_name = self.owner + "-relay"
        self.agent_name = self.owner + "-agent"
        self.address = f"172.30.{subnet}.10"
        self.subnet = f"172.30.{subnet}.0/24"
        self.directory = RESULTS / name
        if self.directory.exists():
            raise FileExistsError(f"Capture result already exists: {self.directory}")
        self.directory.mkdir(parents=True)
        self.workspace = self.directory / "workspace"
        self.config = self.directory / "config"
        self.config.mkdir()
        (self.config / "relay.json").write_text(json.dumps({"host": self.relay_name, "labAddress": self.address}), encoding="utf-8")
        self.source = fresh_source(self.directory / "source")
        self.process = self.relay = None
        self.calls = []
        self.session = None
        self.rpc_id = 0
        self.responses = queue.Queue()
        self.pending = {}
        self.created = []
        self.errors = []
        self.startup_lock = None

    def __enter__(self):
        try:
            docker("network", "create", "--internal", "--subnet", self.subnet,
                   "--label", "hercules.capture.owner=" + self.owner, self.network, stdout=subprocess.DEVNULL)
            self.created.append(("network", self.network))
            docker("run", "-d", "--name", self.fixture, "--network", self.network,
                   "--ip", self.address, "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
                   "--label", "hercules.capture.owner=" + self.owner, FIXTURE, stdout=subprocess.DEVNULL)
            self.created.append(("container", self.fixture))
            for _ in range(30):
                output = docker("logs", self.fixture, capture_output=True, text=True).stdout
                if "services ready" in output:
                    break
                time.sleep(.2)
            else:
                raise RuntimeError("Lab services did not become ready")
            docker("exec", self.fixture, "python", "/lab/inputs.py", "/tmp/inputs", stdout=subprocess.DEVNULL)
            docker("cp", self.fixture + ":/tmp/inputs", self.directory / "inputs", stdout=subprocess.DEVNULL)
            docker("cp", self.fixture + ":/lab/tls/cert.pem", self.directory / "inputs/lab-cert.pem", stdout=subprocess.DEVNULL)
            environment = host_environment(self.source, self.workspace, self.network)
            self.process = subprocess.Popen(server_command(self.source), env=environment, cwd=self.source,
                                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            threading.Thread(target=self.log_errors, args=(self.process.stderr, "hercules.stderr.log"), daemon=True).start()
            threading.Thread(target=self.read_responses, daemon=True).start()
            return self
        except BaseException:
            self.close()
            raise

    def log_errors(self, stream, name):
        with (self.directory / name).open("wb") as target:
            for line in stream:
                target.write(line)
                target.flush()

    def send(self, message):
        if message.get("method") == "tools/call" and message.get("params", {}).get("name") == "system_start_container":
            # Windows' native LK_LOCK retries for only ten seconds. Runtime
            # verification can take longer, so the capture orchestrator queues
            # startup requests before they enter Hercules's existing lock.
            lock = (RESULTS / "capture-startup.lock").open("a+b")
            lock.seek(0, os.SEEK_END)
            if lock.tell() == 0:
                lock.write(b"\0")
                lock.flush()
            deadline = time.monotonic() + 240
            while True:
                try:
                    lock.seek(0)
                    if os.name == "nt":
                        import msvcrt
                        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
                    else:
                        import fcntl
                        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    self.startup_lock = lock
                    break
                except OSError:
                    if time.monotonic() > deadline:
                        lock.close()
                        raise TimeoutError("Capture startup queue")
                    time.sleep(.2)
        if "id" in message:
            self.pending[message["id"]] = message
        self.process.stdin.write(json.dumps(message, ensure_ascii=False).encode() + b"\n")
        self.process.stdin.flush()

    def read_responses(self):
        for line in self.process.stdout:
            try:
                response = json.loads(line)
                request = self.pending.pop(response.get("id"), {})
                if request.get("method") == "tools/call":
                    params = request["params"]
                    record = {**params, "response": response, "receivedAt": time.time()}
                    self.calls.append(record)
                    (self.directory / "host-journal.json").write_text(json.dumps(self.calls, indent=2), encoding="utf-8")
                    if params["name"] == "system_start_container":
                        result = payload(response.get("result", {}))
                        if result.get("status") == "success":
                            session = self.workspace / result["session_id"]
                            session = session.resolve()
                            if not session.is_relative_to(self.workspace.resolve()) or not session.is_dir():
                                raise RuntimeError("Host session directory escaped the transaction workspace")
                            self.session = session
                            shutil.copytree(self.directory / "inputs", session, dirs_exist_ok=True)
                            (session / "artifacts").mkdir(exist_ok=True)
                self.responses.put((response, line))
                if request.get("params", {}).get("name") == "system_start_container":
                    self.release_startup()
            except BaseException as exc:
                self.errors.append(str(exc))
                self.responses.put(({"error": {"message": str(exc)}}, b""))
                self.release_startup()

    def release_startup(self):
        if self.startup_lock:
            lock, self.startup_lock = self.startup_lock, None
            lock.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
            lock.close()

    def rpc(self, method, params=None):
        self.rpc_id += 1
        message = {"jsonrpc": "2.0", "id": self.rpc_id, "method": method, "params": params or {}}
        self.send(message)
        deadline = time.monotonic() + 240
        while time.monotonic() < deadline:
            response, _ = self.responses.get(timeout=max(.1, deadline - time.monotonic()))
            if "error" in response:
                raise RuntimeError(response["error"])
            if response.get("id") == self.rpc_id:
                return response.get("result", {})
        raise TimeoutError(method)

    def initialize(self):
        self.rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "capture-validation", "version": "1"}})
        self.send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        surface = {"tools": self.rpc("tools/list"), "resources": self.rpc("resources/list")}
        (self.directory / "surface.json").write_text(json.dumps(surface, indent=2), encoding="utf-8")
        return surface

    def validate(self, scenario):
        surface = self.initialize()
        available = {t["name"]: t["inputSchema"] for t in surface["tools"]["tools"]}
        program = Program(scenario, self.address)
        while operation := program.next():
            name = operation["tool"]
            if name not in available:
                raise ValueError("Real tool unavailable: " + name)
            print(f"{scenario}: {program.index + 1}/{len(program.steps)} {name}", flush=True)
            response = self.rpc("tools/call", {"name": name, "arguments": operation["arguments"]})
            program.accept(response)
            program.save(self.directory / "validation.json")
        print(f"{scenario}: verified {program.index} real calls", flush=True)

    def capture(self, client, scenario, cols, rows, smoke=False):
        self.relay = subprocess.Popen(["docker", "run", "--rm", "-i", "--name", self.relay_name,
             "--network", self.network, "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
             "--label", "hercules.capture.owner=" + self.owner,
             "--mount", f"type=bind,source={CAPTURE},target=/capture,readonly",
             "--entrypoint", "python", IMAGE, "/capture/labs/relay.py"],
             stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.created.append(("container", self.relay_name))
        threading.Thread(target=self.log_errors, args=(self.relay.stderr, "relay.stderr.log"), daemon=True).start()
        def forward_requests():
            for line in self.relay.stdout:
                self.send(json.loads(line))
        def forward_responses():
            while self.relay.poll() is None:
                _, line = self.responses.get()
                if line:
                    self.relay.stdin.write(line)
                    self.relay.stdin.flush()
        threading.Thread(target=forward_requests, daemon=True).start()
        threading.Thread(target=forward_responses, daemon=True).start()
        output = self.directory / "recordings"
        output.mkdir()
        args = ["run", "--rm", "--name", self.agent_name, "--network", self.network,
                "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
                "--label", "hercules.capture.owner=" + self.owner,
                "--mount", f"type=bind,source={CAPTURE},target=/capture,readonly",
                "--mount", f"type=bind,source={self.config},target=/capture-session,readonly",
                "--mount", f"type=bind,source={output},target=/out", IMAGE, client, scenario,
                "--cols", str(cols), "--rows", str(rows), "--duration", "420", "--real-lab"]
        if smoke:
            args.append("--smoke")
        self.created.append(("container", self.agent_name))
        docker(*args, stdout=(self.directory / "capture.stdout.log").open("w", encoding="utf-8"),
               stderr=(self.directory / "capture.stderr.log").open("w", encoding="utf-8"))
        status = json.loads((output / f"{client}-{scenario}-{cols}.json").read_text())
        if not smoke and not status["completed"]:
            raise ValueError("Native client did not complete the validated investigation")
        if self.errors:
            raise ValueError(self.errors)
        return status

    def close(self):
        self.release_startup()
        if self.process:
            try:
                self.process.stdin.close()
                self.process.wait(timeout=30)
            except (OSError, subprocess.TimeoutExpired):
                self.process.terminate()
                self.process.wait(timeout=10)
        for kind, name in reversed(self.created):
            # Exact names with an ownership label. Never prune Docker globally.
            inspect = subprocess.run(["docker", kind, "inspect", name], capture_output=True, text=True)
            if inspect.returncode:
                continue
            item = json.loads(inspect.stdout)[0]
            labels = item.get("Labels", {}) if kind == "network" else item.get("Config", {}).get("Labels", {})
            if labels.get("hercules.capture.owner") != self.owner:
                raise RuntimeError("Cleanup refused an unowned resource: " + name)
            docker(kind, "rm", *(["-f"] if kind == "container" else []), name, stdout=subprocess.DEVNULL)
        (self.directory / "transaction.json").write_text(json.dumps({"owner": self.owner, "internalNetwork": self.network,
            "labAddress": self.address, "noHostDockerSocketInAgents": True, "personalCredentials": False,
            "cleanupComplete": True, "session": str(self.session) if self.session else None}, indent=2), encoding="utf-8")

    def __exit__(self, *_):
        self.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario", choices=CASES)
    parser.add_argument("--client", choices=("claude", "codex", "opencode", "hermes"))
    parser.add_argument("--cols", type=int, default=120)
    parser.add_argument("--rows", type=int, default=36)
    parser.add_argument("--subnet", type=int, default=42)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    name = f"{args.client or 'validate'}-{args.scenario}-{args.cols}-{time.time_ns()}"
    with Lab(name, args.subnet) as lab:
        print(str(lab.directory), flush=True)
        if args.client:
            lab.capture(args.client, args.scenario, args.cols, args.rows, args.smoke)
        else:
            lab.validate(args.scenario)


if __name__ == "__main__":
    main()
