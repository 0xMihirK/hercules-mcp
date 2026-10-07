"""STDIO MCP bridge; pass raw JSON-RPC to the real Hercules process.

The journal observes actual results. It cannot supply or alter tool results.
"""
import json
import os
from pathlib import Path
import socket
import sys
import threading
import time

config = json.loads(Path("/capture-session/relay.json").read_text())
connection = socket.create_connection((config["host"], 8766), timeout=30)
connection.settimeout(None)
pending = {}
started = time.monotonic()
lock = threading.Lock()


def send_requests():
    for line in sys.stdin.buffer:
        message = json.loads(line)
        if "id" in message:
            with lock:
                pending[message["id"]] = (message, time.monotonic())
        connection.sendall(line)
    connection.shutdown(socket.SHUT_WR)


threading.Thread(target=send_requests, daemon=True).start()
with connection.makefile("rb") as responses:
    for line in responses:
        response = json.loads(line)
        with lock:
            request, requested_at = pending.pop(response.get("id"), ({}, started))
        if request.get("method") == "tools/call":
            value = {"name": request["params"]["name"], "arguments": request["params"].get("arguments", {}),
                     "result": response.get("result"), "error": response.get("error"),
                     "requestedAt": requested_at, "completedAt": time.monotonic(),
                     "elapsed": time.monotonic() - requested_at}
            with open("/tmp/mcp-calls.jsonl", "a", encoding="utf-8") as journal:
                journal.write(json.dumps(value, ensure_ascii=False) + "\n")
        elif request.get("method") == "tools/list" and response.get("result", {}).get("tools"):
            Path("/tmp/mcp-ready.json").write_text(json.dumps({"tools": len(response["result"]["tools"]), "readyAt": time.monotonic()}))
        sys.stdout.buffer.write(line)
        sys.stdout.buffer.flush()
