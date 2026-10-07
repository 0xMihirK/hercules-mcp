"""Offline model and MCP fixtures. All findings are authored demo data.

The unmodified clients render their own UI. This module supplies protocol events,
not terminal artwork. Capture containers have no external network or credentials.
"""
import json
import os
from pathlib import Path
import re
import sys
import threading
import time
import uuid
import subprocess
from ctf_lab import create_challenge, archive_offset, FLAG_DIGEST
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SURFACE = json.loads(Path("/capture/hercules-surface.json").read_text())
CASES = json.loads(Path(__file__).with_name("cases.json").read_text())
PROMPTS = {key: case["prompt"] for key, case in CASES.items()}
PHASES = {key: case["phases"] for key, case in CASES.items()}
REPORTS = {
    "scan": "# Network assessment\n\nIllustrative fixture results, not a scan of scanme.nmap.org.\n\n22/tcp: SSH. 80/tcp: HTTP. 9929/tcp: nping.\nNo vulnerability is established by an open port alone.\n\nEvidence: artifacts/scan.xml\nNext: verify exposed services against your authorized scope.\n",
    "ctf": f"# CTF write-up: Signal route\n\nLocal, reproducible file-forensics challenge.\n\n1. Found a ZIP appended after a valid 64x64 PNG.\n2. Read the PNG metadata clue: route=13,14,17,19,7.\n3. Extracted README.md, decoy.txt, manifest.json and payload.bin.\n4. Converted the zero-based route to the repeating XOR key NORTH.\n5. XOR-decoded the payload, then decoded its base64 layer.\n6. Rejected the decoy and verified the recovered flag against the manifest.\n\nFlag: HERCULES{{evidence_before_answers}}\nSHA-256: {FLAG_DIGEST}\nChecksum match: true. Decoy match: false.\n\nEvidence: artifacts/ctf/solution.json and artifacts/ctf/manifest.json\nReproduce: python ctf_lab.py extract challenge.png artifacts/ctf\nThen: python ctf_lab.py solve challenge.png artifacts/ctf\n",
    "web": "# Web assessment\n\nIllustrative results for the fictional shop.lab.test lab.\n\nMedium: a sample development endpoint exposes debug metadata.\nLow: Content-Security-Policy is absent from the sample response.\n\nRecommendations: disable debug endpoints and configure a tested CSP.\nEvidence: artifacts/web-findings.json\n",
    "dns": "# DNS report\n\nIllustrative DNS answers for the fictional shop.lab.test lab.\n\nA record: 192.0.2.20. TTL: 300 seconds.\nThe sample query completed with NOERROR.\nThis address is fixture data, not a discovered external host.\n\nEvidence: artifacts/dns-records.json\n",
    "headers": "# HTTP header review\n\nIllustrative response from the fictional portal.lab.test lab.\n\nPresent: Strict-Transport-Security with max-age=31536000.\nAbsent in the sample: Content-Security-Policy and a frame policy.\n\nReview the app's resource and embedding requirements before configuring CSP.\nEvidence: artifacts/response-headers.txt\n",
    "browser": "# Login page review\n\nIllustrative snapshot of the fictional portal.lab.test login page.\n\nThe email field has an accessible name. The password field has none.\nAssociate a visible label with the password field, then verify keyboard focus.\nNo credentials were entered and no form was submitted.\n\nEvidence: artifacts/login-snapshot.txt\n",
}

EVIDENCE = {
    "scan": '<nmaprun scanner="scripted-fixture"><host><ports><port protocol="tcp" portid="22"><state state="open"/><service name="ssh"/></port><port protocol="tcp" portid="80"><state state="open"/><service name="http"/></port><port protocol="tcp" portid="9929"><state state="open"/><service name="nping"/></port></ports></host></nmaprun>\n',
    "web": json.dumps({"fictional_lab": "shop.lab.test", "fixture": True, "findings": [{"severity": "medium", "title": "Sample debug endpoint"}, {"severity": "low", "title": "Missing Content-Security-Policy"}]}, indent=2) + "\n",
    "dns": json.dumps({"fixture": True, "question": {"name": "shop.lab.test", "type": "A"}, "status": "NOERROR", "answers": [{"name": "shop.lab.test", "type": "A", "ttl": 300, "value": "192.0.2.20"}]}, indent=2) + "\n",
    "headers": "HTTP/2 200\ncontent-type: text/html; charset=utf-8\nstrict-transport-security: max-age=31536000\nx-hercules-fixture: true\n\nContent-Security-Policy: absent from the sample\nFrame policy: absent from the sample\n",
    "browser": "Illustrative browser snapshot: https://portal.lab.test\nheading: Sign in\ntextbox: Email\ntextbox: [password field; accessible name missing]\nbutton: Sign in\nlink: Forgot password?\n",
}

def prepare_workspace(home, scenario):
    """Supply a real layered challenge and evidence files for the other fixtures."""
    create_challenge(home)
    (home / "capture-scenario.txt").write_text(scenario)
    (home / "artifacts").mkdir(exist_ok=True)
    (home / "reports").mkdir(exist_ok=True)
    for scenario, case in CASES.items():
        if scenario == "ctf":
            continue  # Its evidence is created by extraction and verified decoding.
        (home / "artifacts" / case["artifact"]).write_text(EVIDENCE[scenario])
    (home / "lab-login.html").write_text('<!doctype html><html lang="en"><title>Lab login</title><h1>Sign in</h1><form><label for="email">Email</label><input id="email" type="email"><input type="password"><button>Sign in</button></form><a href="#reset">Forgot password?</a></html>')

def mcp_result(name, args, scenario):
    if name == "system_start_container":
        return {"status": "success", "start_mode": "created", "session_id": "d3e0a123", "workspace": "/opt/workspace", "demonstration": True}
    if name == "nmap_scan":
        return {"status": "success", "target": "scanme.nmap.org", "ports": [{"port": 22, "protocol": "tcp", "state": "open", "service": "ssh"}, {"port": 80, "protocol": "tcp", "state": "open", "service": "http"}, {"port": 9929, "protocol": "tcp", "state": "open", "service": "nping"}], "stdout_artifact": "/opt/workspace/artifacts/scan.xml", "evidence_complete": True, "demonstration": True}
    if name == "ctf_binwalk":
        return {"status": "success", "signatures": [{"offset": 0, "description": "PNG image data, 64 x 64, grayscale"}, {"offset": archive_offset(Path("/home/capture/session/challenge.png")), "description": "Zip archive data"}], "demonstration": True}
    if name == "shell_exec" and scenario == "ctf":
        commands = {"strings -a challenge.png": ["strings", "-a", "challenge.png"], "python ctf_lab.py extract challenge.png artifacts/ctf": [sys.executable, "ctf_lab.py", "extract", "challenge.png", "artifacts/ctf"], "python ctf_lab.py solve challenge.png artifacts/ctf": [sys.executable, "ctf_lab.py", "solve", "challenge.png", "artifacts/ctf"]}
        completed = subprocess.run(commands[args["command"]], cwd="/home/capture/session", capture_output=True, text=True, timeout=30, check=False)
        return {"exit_code": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr, "output_complete": True, "evidence_complete": True, "demonstration": True}
    if name in ("web_scan", "nuclei_run"):
        return {"status": "success", "target": "http://shop.lab.test", "findings": [{"severity": "medium", "title": "Sample debug endpoint"}, {"severity": "low", "title": "Missing Content-Security-Policy"}], "stdout_artifact": "/opt/workspace/artifacts/web-findings.json", "demonstration": True}
    if name == "recon_dns":
        return {"status": "success", **json.loads(EVIDENCE["dns"]), "stdout_artifact": "/opt/workspace/artifacts/dns-records.json", "demonstration": True}
    if name == "network_curl":
        return {"status": "success", "url": "https://portal.lab.test", "http_status": 200, "stdout": EVIDENCE["headers"], "stdout_artifact": "/opt/workspace/artifacts/response-headers.txt", "demonstration": True}
    if name == "browser_open":
        return {"status": "success", "session": "showcase", "url": "https://portal.lab.test", "title": "Lab login", "demonstration": True}
    if name == "browser_snapshot":
        return {"status": "success", "session": "showcase", "snapshot": EVIDENCE["browser"], "artifact": "/opt/workspace/artifacts/login-snapshot.txt", "demonstration": True}
    if name == "workspace_read_file":
        home = Path("/home/capture/session")
        path = (home / args["path"]).resolve()
        if not path.is_relative_to(home):
            raise ValueError("Fixture evidence path outside the disposable workspace")
        return {"status": "success", "content": path.read_text(), "output_complete": True, "evidence_complete": True, "demonstration": True}
    if name == "workspace_write_file":
        home = Path("/home/capture/session")
        path = (home / args["path"]).resolve()
        if not path.is_relative_to(home):
            raise ValueError("Fixture report path outside the disposable workspace")
        if scenario == "ctf":
            solution = json.loads((home / "artifacts/ctf/solution.json").read_text())
            if not solution["checksum_match"] or solution["decoy_sha256_match"]:
                raise ValueError("CTF report requires verified evidence")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(args["content"])
        return {"status": "success", "path": "/opt/workspace/" + args["path"], "bytes_written": len(args["content"].encode()), "demonstration": True}
    return {"status": "success", "demonstration": True, "message": "Offline illustrative fixture"}

def stdio():
    # Codex deliberately filters inherited environment variables for MCP children.
    scenario = Path("/home/capture/session/capture-scenario.txt").read_text().strip()
    for line in sys.stdin:
        request = json.loads(line)
        if "id" not in request:
            continue
        method = request.get("method")
        params = request.get("params", {})
        if method == "initialize":
            time.sleep(1.2)
            result = {"protocolVersion": params.get("protocolVersion", "2025-11-25"), "capabilities": {"tools": {}, "resources": {}}, "serverInfo": {"name": "Hercules MCP", "version": "0.1.0"}, "instructions": "Offline showcase fixture. All operations and findings are illustrative."}
        elif method == "tools/list":
            result = {"tools": SURFACE["tools"]}
        elif method == "resources/list":
            result = {"resources": SURFACE["resources"]}
        elif method == "resources/templates/list":
            result = {"resourceTemplates": []}
        elif method == "tools/call":
            time.sleep(2.4 if params["name"] == "system_start_container" else 3.8)
            value = mcp_result(params["name"], params.get("arguments", {}), scenario)
            result = {"content": [{"type": "text", "text": json.dumps(value, indent=2)}], "structuredContent": value, "isError": False}
            with open("/tmp/mcp-calls.jsonl", "a") as log:
                log.write(json.dumps({"name": params["name"], "arguments": params.get("arguments", {})}) + "\n")
        elif method == "resources/read":
            result = {"contents": [{"uri": params["uri"], "mimeType": "text/plain", "text": "Hercules MCP capture fixture: use explicit lifecycle calls and retain workspace evidence."}]}
        else:
            result = {}
        print(json.dumps({"jsonrpc": "2.0", "id": request["id"], "result": result}), flush=True)

class ModelFixture(BaseHTTPRequestHandler):
    scenario = "scan"
    client = "codex"
    turn = 0
    requests = []
    completed = threading.Event()
    protocol = ""

    def log_message(self, *_):
        pass

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"object": "list", "data": [{"id": "capture-demo", "object": "model", "owned_by": "local-fixture"}]}).encode())

    def event(self, data, event=None):
        payload = (f"event: {event}\n" if event else "") + "data: " + (data if isinstance(data, str) else json.dumps(data)) + "\n\n"
        self.wfile.write(payload.encode())
        self.wfile.flush()

    def choose(self, body):
        cls = type(self)
        tools = body.get("tools", [])
        additional = [namespace for item in body.get("input", []) if item.get("type") == "additional_tools" for namespace in item.get("tools", [])]
        if cls.client == "codex" and any(t.get("type") == "custom" and t.get("name") == "exec" for namespace in additional for t in namespace.get("tools", [])):
            phase = PHASES[cls.scenario]
            def invoke(suffix, args):
                return 'const tool = ALL_TOOLS.find(t => t.name.endsWith("__' + suffix + '")); if (!tool) throw new Error("Hercules tool unavailable"); text(await tools[tool.name](' + json.dumps(args) + '));'
            code = [
                'text(ALL_TOOLS.filter(t => t.name.includes("hercules")).map(t => ({name: t.name, description: t.description.slice(0, 90)})));',
                'text(await tools.update_plan(' + json.dumps({"plan": [{"step": title, "status": "pending" if i else "in_progress"} for i, title in enumerate(phase)]}) + '));',
                invoke("system_start_container", {}),
                *[invoke(operation["tool"], operation["arguments"]) for operation in CASES[cls.scenario]["operations"]],
                invoke("workspace_read_file", {"path": "artifacts/" + CASES[cls.scenario]["artifact"], "encoding": "text"}),
                invoke("workspace_write_file", {"path": "reports/" + cls.scenario + ".md", "content": REPORTS[cls.scenario]}),
                'text(await tools.update_plan(' + json.dumps({"plan": [{"step": title, "status": "completed"} for title in phase]}) + '));',
            ]
            index = cls.turn; cls.turn += 1
            if index < len(code):
                return "I’ll keep a plan, use Hercules, and save the evidence." if index == 0 else "", ("exec", {"__code": code[index]})
            cls.completed.set()
            return "Report saved to reports/" + cls.scenario + ".md\n\n" + REPORTS[cls.scenario], None
        if not tools:
            return "Hercules showcase", None
        specs = [(tool.get("function", tool).get("name", ""), tool.get("function", tool)) for tool in tools]
        names = [name for name, _ in specs]
        def find(suffix):
            return next((name for name in names if name == suffix or name.endswith("__" + suffix) or name.endswith("_" + suffix)), None)
        def args_for(name, values):
            schema = next((spec.get("parameters", spec.get("input_schema", {})) for n, spec in specs if n == name), {})
            # Keep supplied fields only where the advertised schema accepts them.
            props = schema.get("properties", {})
            result = {k: v for k, v in values.items() if k in props}
            for required in schema.get("required", []):
                if required not in result:
                    p = props.get(required, {})
                    result[required] = p.get("default", p.get("enum", [None])[0] or (False if p.get("type") == "boolean" else [] if p.get("type") == "array" else 30 if p.get("type") in ("number", "integer") else "demo"))
            return result
        phase = PHASES[cls.scenario]
        index = cls.turn
        cls.turn += 1
        tasks = [{"id": str(i + 1), "content": title, "status": "pending", "priority": "medium"} for i, title in enumerate(phase)]
        tasks[0]["status"] = "in_progress"
        plan_name = next((name for name in names if name in ("update_plan", "todowrite", "todo_list", "TaskCreate", "TodoWrite")), None)
        queue = []
        if plan_name:
            if plan_name == "update_plan":
                queue.append((plan_name, {"plan": [{"step": title, "status": "pending" if i else "in_progress"} for i, title in enumerate(phase)]}))
            elif plan_name == "TaskCreate":
                for title in phase:
                    queue.append((plan_name, {"subject": title, "description": title + " using Hercules MCP in the illustrative capture.", "activeForm": title}))
                if "TaskUpdate" in names:
                    queue.append(("TaskUpdate", {"taskId": "1", "status": "in_progress"}))
            elif plan_name == "todo_list":
                queue.append((plan_name, {"todos": [{k: v for k, v in task.items() if k != "priority"} for task in tasks], "merge": False}))
            else:
                queue.append((plan_name, {"todos": tasks}))
        queue.append((find("system_start_container"), {}))
        queue.extend((find(operation["tool"]), operation["arguments"]) for operation in CASES[cls.scenario]["operations"])
        queue.append((find("workspace_read_file"), {"path": "artifacts/" + CASES[cls.scenario]["artifact"], "file_path": "artifacts/evidence.txt", "encoding": "text"}))
        queue.append((find("workspace_write_file"), {"path": "reports/" + cls.scenario + ".md", "file_path": "reports/" + cls.scenario + ".md", "content": REPORTS[cls.scenario], "encoding": "text"}))
        if plan_name == "update_plan":
            queue.append((plan_name, {"plan": [{"step": title, "status": "completed"} for title in phase]}))
        elif plan_name in ("todowrite", "TodoWrite"):
            queue.append((plan_name, {"todos": [dict(task, status="completed") for task in tasks]}))
        elif plan_name == "todo_list":
            queue.append((plan_name, {"todos": [{"id": task["id"], "content": task["content"], "status": "completed"} for task in tasks], "merge": True}))
        elif plan_name == "TaskCreate" and "TaskUpdate" in names:
            for i in range(3):
                queue.append(("TaskUpdate", {"taskId": str(i + 1), "status": "completed"}))
        queue = [(name, args_for(name, args)) for name, args in queue if name]
        if index < len(queue):
            name, arguments = queue[index]
            return "I’ll keep a plan, use Hercules, and save the evidence." if index == 0 else "", (name, arguments)
        cls.completed.set()
        return "Report saved to reports/" + cls.scenario + ".md\n\n" + REPORTS[cls.scenario], None

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        cls = type(self)
        cls.requests.append({"path": self.path, "body": body})
        Path("/tmp/model-requests.json").write_text(json.dumps(cls.requests, indent=2))
        # Native clients may request token counts, title generation or other metadata.
        if "count_tokens" in self.path:
            self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(b'{"input_tokens":4200}'); return
        text, call = self.choose(body)
        self.send_response(200)
        if not body.get("stream", False):
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            message = {"role": "assistant", "content": text}
            if call:
                message["tool_calls"] = [{"id": "call_" + uuid.uuid4().hex[:12], "type": "function", "function": {"name": call[0], "arguments": json.dumps(call[1])}}]
            response = {"id": "fixture", "object": "chat.completion", "created": 1780000000, "model": body.get("model", "capture-demo"), "choices": [{"index": 0, "message": message, "finish_reason": "tool_calls" if call else "stop"}], "usage": {"prompt_tokens": 4200, "completion_tokens": 180, "total_tokens": 4380}}
            self.wfile.write(json.dumps(response).encode())
            return
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        time.sleep(1.5)
        call_id = "call_" + uuid.uuid4().hex[:12]
        try:
            if "messages" in self.path:
                self.messages(text, call, call_id, body.get("model", "capture-demo"))
            elif "responses" in self.path:
                self.responses_stream(text, call, call_id)
            else:
                self.completions(text, call, call_id)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def completions(self, text, call, call_id):
        def chunk(delta, finish=None):
            self.event({"id": "demo-" + call_id, "object": "chat.completion.chunk", "created": 1780000000, "model": "capture-demo", "choices": [{"index": 0, "delta": delta, "finish_reason": finish}]})
        chunk({"role": "assistant"})
        for part in re.findall(r".{1,18}|\n", text):
            chunk({"content": part}); time.sleep(.06)
        if call:
            chunk({"tool_calls": [{"index": 0, "id": call_id, "type": "function", "function": {"name": call[0], "arguments": json.dumps(call[1])}}]})
        chunk({}, "tool_calls" if call else "stop")
        self.event("[DONE]")

    def messages(self, text, call, call_id, model):
        def event(kind, **data):
            self.event({"type": kind, **data}, kind)
        event("message_start", message={"id": "msg_" + call_id, "type": "message", "role": "assistant", "model": model, "content": [], "stop_reason": None, "stop_sequence": None, "usage": {"input_tokens": 4200, "output_tokens": 0}})
        index = 0
        if text:
            event("content_block_start", index=index, content_block={"type": "text", "text": ""})
            for part in re.findall(r".{1,18}|\n", text):
                event("content_block_delta", index=index, delta={"type": "text_delta", "text": part}); time.sleep(.06)
            event("content_block_stop", index=index); index += 1
        if call:
            event("content_block_start", index=index, content_block={"type": "tool_use", "id": call_id, "name": call[0], "input": {}})
            event("content_block_delta", index=index, delta={"type": "input_json_delta", "partial_json": json.dumps(call[1])})
            event("content_block_stop", index=index)
        event("message_delta", delta={"stop_reason": "tool_use" if call else "end_turn", "stop_sequence": None}, usage={"output_tokens": 180})
        event("message_stop")

    def responses_stream(self, text, call, call_id):
        response_id = "resp_" + call_id
        response = {"id": response_id, "object": "response", "created_at": 1780000000, "status": "in_progress", "model": "capture-demo", "output": []}
        seq = 0
        def event(kind, **data):
            nonlocal seq
            self.event({"type": kind, "sequence_number": seq, **data}, kind); seq += 1
        event("response.created", response=response)
        output = []
        if text:
            item = {"id": "msg_" + call_id, "type": "message", "role": "assistant", "status": "in_progress", "content": []}
            event("response.output_item.added", output_index=0, item=item)
            event("response.content_part.added", item_id=item["id"], output_index=0, content_index=0, part={"type": "output_text", "text": "", "annotations": []})
            for part in re.findall(r".{1,18}|\n", text):
                event("response.output_text.delta", item_id=item["id"], output_index=0, content_index=0, delta=part); time.sleep(.06)
            item.update(status="completed", content=[{"type": "output_text", "text": text, "annotations": []}])
            event("response.output_text.done", item_id=item["id"], output_index=0, content_index=0, text=text)
            event("response.content_part.done", item_id=item["id"], output_index=0, content_index=0, part=item["content"][0])
            event("response.output_item.done", output_index=0, item=item); output.append(item)
        if call:
            custom = "__code" in call[1]
            item = {"id": "fc_" + call_id, "type": "custom_tool_call" if custom else "function_call", "call_id": call_id, "name": call[0]}
            if custom: item["namespace"] = "functions"
            item["input" if custom else "arguments"] = ""
            event("response.output_item.added", output_index=len(output), item=item)
            value = call[1]["__code"] if custom else json.dumps(call[1])
            item["input" if custom else "arguments"] = value
            event("response.custom_tool_call_input.delta" if custom else "response.function_call_arguments.delta", output_index=len(output), item_id=item["id"], delta=value)
            event("response.custom_tool_call_input.done" if custom else "response.function_call_arguments.done", output_index=len(output), item_id=item["id"], **{"input" if custom else "arguments": value})
            event("response.output_item.done", output_index=len(output), item=item); output.append(item)
        response.update(status="completed", output=output, usage={"input_tokens": 4200, "output_tokens": 180, "total_tokens": 4380, "input_tokens_details": {"cached_tokens": 0}})
        event("response.completed", response=response)

def start(scenario, client, port=8765):
    ModelFixture.scenario = scenario
    ModelFixture.client = client
    ModelFixture.turn = 0
    server = ThreadingHTTPServer(("127.0.0.1", port), ModelFixture)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server

if __name__ == "__main__":
    stdio()
