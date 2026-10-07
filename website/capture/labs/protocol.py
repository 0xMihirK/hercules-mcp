"""Loopback scripted provider protocols; no MCP server or tool result fixtures."""
import json, re, threading, time, uuid
from pathlib import Path
from http.server import BaseHTTPRequestHandler

class ScriptedProtocol(BaseHTTPRequestHandler):
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
        raise NotImplementedError

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
            if custom or call[0]=="wait": item["namespace"] = "functions"
            item["input" if custom else "arguments"] = ""
            event("response.output_item.added", output_index=len(output), item=item)
            value = call[1]["__code"] if custom else json.dumps(call[1])
            item["input" if custom else "arguments"] = value
            event("response.custom_tool_call_input.delta" if custom else "response.function_call_arguments.delta", output_index=len(output), item_id=item["id"], delta=value)
            event("response.custom_tool_call_input.done" if custom else "response.function_call_arguments.done", output_index=len(output), item_id=item["id"], **{"input" if custom else "arguments": value})
            event("response.output_item.done", output_index=len(output), item=item); output.append(item)
        response.update(status="completed", output=output, usage={"input_tokens": 4200, "output_tokens": 180, "total_tokens": 4380, "input_tokens_details": {"cached_tokens": 0}})
        event("response.completed", response=response)
