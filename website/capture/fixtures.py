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
import base64
import io
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SURFACE = json.loads(Path("/capture/hercules-surface.json").read_text())
PROMPTS = {
    "scan": "Scan scanme.nmap.org for me and prepare a report. Use Hercules MCP.",
    "ctf": "Solve the local CTF challenge in challenge.png and save a write-up. Use Hercules MCP.",
    "web": "Scan http://shop.lab.test for vulnerabilities and prepare a report. Use Hercules MCP.",
}
PHASES = {
    "scan": ["Discover services", "Review the evidence", "Write the report"],
    "ctf": ["Inspect the challenge", "Recover the flag", "Write the solution"],
    "web": ["Inspect the website", "Check sample findings", "Write the report"],
}
REPORTS = {
    "scan": "# Network assessment\n\nIllustrative fixture results, not a scan of scanme.nmap.org.\n\n22/tcp: SSH. 80/tcp: HTTP. 9929/tcp: nping.\nNo vulnerability is established by an open port alone.\n\nEvidence: artifacts/scan.xml\nNext: verify exposed services against your authorized scope.\n",
    "ctf": "# CTF solution\n\nLocal demonstration challenge.\n\n1. Inspected the PNG and found an appended ZIP signature.\n2. Read the recovered note.\n3. Decoded the clue and recovered HERCULES{keep_the_evidence}.\n\nEvidence: artifacts/challenge-analysis.txt\n",
    "web": "# Web assessment\n\nIllustrative results for the fictional shop.lab.test lab.\n\nMedium: a sample development endpoint exposes debug metadata.\nLow: Content-Security-Policy is absent from the sample response.\n\nRecommendations: disable debug endpoints and configure a tested CSP.\nEvidence: artifacts/web-findings.json\n",
}

EVIDENCE = {
    "scan": '<nmaprun scanner="scripted-fixture"><host><ports><port protocol="tcp" portid="22"><state state="open"/><service name="ssh"/></port><port protocol="tcp" portid="80"><state state="open"/><service name="http"/></port><port protocol="tcp" portid="9929"><state state="open"/><service name="nping"/></port></ports></host></nmaprun>\n',
    "ctf": "Scripted binwalk fixture: PNG signature at 0; appended ZIP signature.\nRecovered note: HERCULES{keep_the_evidence}\n",
    "web": json.dumps({"fictional_lab": "shop.lab.test", "fixture": True, "findings": [{"severity": "medium", "title": "Sample debug endpoint"}, {"severity": "low", "title": "Missing Content-Security-Policy"}]}, indent=2) + "\n",
}

def prepare_workspace(home):
    """Supply a tiny local PNG/ZIP challenge and real files for fixture evidence."""
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as package:
        package.writestr("note.txt", "HERCULES{keep_the_evidence}\n")
    png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")
    (home / "challenge.png").write_bytes(png + archive.getvalue())
    (home / "artifacts").mkdir(exist_ok=True)
    (home / "reports").mkdir(exist_ok=True)
    (home / "artifacts" / "scan.xml").write_text(EVIDENCE["scan"])
    (home / "artifacts" / "challenge-analysis.txt").write_text(EVIDENCE["ctf"])
    (home / "artifacts" / "web-findings.json").write_text(EVIDENCE["web"])

def mcp_result(name, args, scenario):
    if name == "system_start_container":
        return {"status": "success", "start_mode": "created", "session_id": "d3e0a123", "workspace": "/opt/workspace", "demonstration": True}
    if name == "nmap_scan":
        return {"status": "success", "target": "scanme.nmap.org", "ports": [{"port": 22, "protocol": "tcp", "state": "open", "service": "ssh"}, {"port": 80, "protocol": "tcp", "state": "open", "service": "http"}, {"port": 9929, "protocol": "tcp", "state": "open", "service": "nping"}], "stdout_artifact": "/opt/workspace/artifacts/scan.xml", "evidence_complete": True, "demonstration": True}
    if name == "ctf_binwalk":
        return {"status": "success", "signatures": [{"offset": 0, "description": "PNG image data"}, {"offset": 8192, "description": "Zip archive data"}], "artifact": "/opt/workspace/artifacts/challenge-analysis.txt", "demonstration": True}
    if name in ("web_scan", "nuclei_run"):
        return {"status": "success", "target": "http://shop.lab.test", "findings": [{"severity": "medium", "title": "Sample debug endpoint"}, {"severity": "low", "title": "Missing Content-Security-Policy"}], "stdout_artifact": "/opt/workspace/artifacts/web-findings.json", "demonstration": True}
    if name == "workspace_read_file":
        return {"status": "success", "content": EVIDENCE[scenario], "output_complete": True, "evidence_complete": True, "demonstration": True}
    if name == "workspace_write_file":
        Path("/home/capture/session/reports", scenario + ".md").write_text(REPORTS[scenario])
        return {"status": "success", "path": "/opt/workspace/reports/" + scenario + ".md", "bytes_written": len(REPORTS[scenario]), "demonstration": True}
    return {"status": "success", "demonstration": True, "message": "Offline illustrative fixture"}

def stdio():
    scenario = os.environ.get("CAPTURE_SCENARIO", "scan")
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
            operation, arguments = {"scan": ("nmap_scan", {"mode": "port", "target": "scanme.nmap.org", "ports": "22,80,9929"}), "ctf": ("ctf_binwalk", {"filepath": "challenge.png", "extract": False}), "web": ("web_scan", {"target": "http://shop.lab.test", "tool": "nikto"})}[cls.scenario]
            def invoke(suffix, args):
                return 'const tool = ALL_TOOLS.find(t => t.name.endsWith("__' + suffix + '")); if (!tool) throw new Error("Hercules tool unavailable"); text(await tools[tool.name](' + json.dumps(args) + '));'
            code = [
                'text(ALL_TOOLS.filter(t => t.name.includes("hercules")).map(t => ({name: t.name, description: t.description.slice(0, 90)})));',
                'text(await tools.update_plan(' + json.dumps({"plan": [{"step": title, "status": "pending" if i else "in_progress"} for i, title in enumerate(phase)]}) + '));',
                invoke("system_start_container", {}),
                invoke(operation, arguments),
                invoke("workspace_read_file", {"path": "artifacts/" + {"scan": "scan.xml", "ctf": "challenge-analysis.txt", "web": "web-findings.json"}[cls.scenario], "encoding": "text"}),
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
        operation = {"scan": ("nmap_scan", {"mode": "port", "target": "scanme.nmap.org", "ports": "22,80,9929"}), "ctf": ("ctf_binwalk", {"filepath": "challenge.png", "extract": False}), "web": ("web_scan", {"target": "http://shop.lab.test", "tool": "nikto"})}[cls.scenario]
        queue.append((find(operation[0]), operation[1]))
        queue.append((find("workspace_read_file"), {"path": "artifacts/" + ("challenge-analysis.txt" if cls.scenario == "ctf" else "scan.xml" if cls.scenario == "scan" else "web-findings.json"), "file_path": "artifacts/evidence.txt", "encoding": "text"}))
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
