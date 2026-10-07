"""Scripted reasoning and report authoring, gated by actual Hercules responses."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import re
import shlex

from .cases import CASES, HOST, START, SCOPE, shell, step


def payload(result):
    if result.get("structuredContent") is not None:
        return result["structuredContent"]
    blocks = result.get("content", [])
    for block in blocks:
        if block.get("type") == "text":
            try:
                return json.loads(block["text"])
            except (ValueError, TypeError):
                pass
    return result


def searchable(value):
    if isinstance(value, dict):
        return "\n".join(str(k) + ": " + searchable(v) for k, v in value.items())
    if isinstance(value, list):
        return "\n".join(map(searchable, value))
    return str(value)


def fields(value, name):
    found = []
    if isinstance(value, dict):
        if name in value:
            found.append(value[name])
        for child in value.values():
            found.extend(fields(child, name))
    elif isinstance(value, list):
        for child in value:
            found.extend(fields(child, name))
    return found


class Program:
    def __init__(self, scenario, address=HOST):
        self.scenario = scenario
        self.case = CASES[scenario]
        operations = json.loads(json.dumps([START, SCOPE, *self.case["steps"]]).replace(HOST, address))
        self.steps = operations + [
            step("workspace_write_file", {"path": f"reports/{scenario}.md", "content": "$report"},
                 "success|bytes_written", "All investigation checks have passed. I will write a report that links the observed evidence and states the limits of this scripted local investigation.", dynamic="report"),
            shell(self.render_command(), "evidence_files", "I will render the verified Markdown as readable HTML and index the real workspace artifacts with SHA-256 hashes."),
            step("workspace_read_file", {"path": f"reports/{scenario}.md"}, "Verified observations",
                 "I will reread the saved report before declaring completion. A completed inline response and a complete evidence collection are separate properties."),
            step("system_stop_container", {}, "stopped and removed",
                 "The report and evidence index are verified. I will stop only this client's owned runtime; workspace evidence remains available.")]
        self.index = 0
        self.verified = []
        self.pending = None

    def render_command(self):
        return "python3 - <<'PY'\n" + "\n".join([
            "import hashlib,html,json", "from pathlib import Path",
            "p=Path('/opt/workspace'); report=p/'reports'/'" + self.scenario + ".md'",
            "assert report.is_file() and 'Verified observations' in report.read_text()",
            "items=[{'path':f.relative_to(p).as_posix(),'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()} for f in sorted(p.rglob('*')) if f.is_file() and f.relative_to(p).parts[0] in ('artifacts','reports','logs','challenge') and f.name!='evidence-index.json']",
            "(p/'reports/evidence-index.json').write_text(json.dumps(items,indent=2))",
            "content='<!doctype html><html lang=\"en\"><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"><title>Hercules local lab report</title><style>body{font:16px system-ui;max-width:900px;margin:40px auto;padding:24px;background:#171b1e;color:#e9e5de}pre{white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.6}</style><h1>Hercules local lab report</h1><pre>'+html.escape(report.read_text())+'</pre></html>'",
            "report.with_suffix('.html').write_text(content)",
            "print(json.dumps({'report':str(report),'evidence_files':len(items),'verified':True}))", "PY"])

    def report(self):
        lines = ["# " + self.case["title"], "", "Real Hercules tools in a disposable local lab. Model decisions and this report are scripted.",
                 "", "## Verified observations", ""]
        for number, record in enumerate(self.verified, 1):
            operation = record["step"]
            if operation["tool"] in ("system_start_container", "workspace_read_file") and number <= 2:
                continue
            lines.extend([f"### {number}. {operation['tool']}", operation["observation"], "",
                          "Actual response excerpt:", "```text", searchable(record["data"])[:1100], "```", ""])
        lines.extend(["## Scope and limitations", "",
                      "Only the internal fixture was assessed. No public target was contacted. Inputs are authored lab fixtures; tool results are real.",
                      "This is an evidence-linked demonstration, not a complete security assessment. A reference match, open port or missing header alone does not establish exploitability.",
                      "Raw diagnostics and workspace artifacts are retained. Inline output completeness does not prove investigation completeness.",
                      "", "## Evidence", "See evidence-index.json for artifact paths, byte counts and SHA-256 hashes.", ""])
        return "\n".join(lines)

    def next(self):
        if self.pending is not None:
            raise RuntimeError("Previous tool response has not been verified")
        if self.index == len(self.steps):
            return None
        operation = copy.deepcopy(self.steps[self.index])
        dynamic = operation.get("dynamic")
        if dynamic == "report":
            operation["arguments"]["content"] = self.report()
        elif dynamic == "job":
            ids = [v for r in self.verified for v in fields(r["data"], "job_id")]
            if not ids:
                raise ValueError("No observed background job ID")
            operation["arguments"]["job_id"] = ids[0]
        elif dynamic == "reference":
            candidates = [v for r in self.verified for key in ("EDB-ID", "edb_id", "id") for v in fields(r["data"], key) if str(v).isdigit()]
            if not candidates:
                text = "\n".join(searchable(r["data"]) for r in self.verified)
                candidates = re.findall(r"(?:EDB-ID|edb_id)\W+(\d+)", text)
            if not candidates:
                raise ValueError("No SearchSploit reference ID in actual results")
            operation["arguments"]["query_or_id"] = str(candidates[0])
        elif dynamic == "decrypt":
            fragments = []
            for record in self.verified:
                fragments.extend(re.findall(r'"route_fragment"\s*:\s*"([\w-]+)"', searchable(record["data"])))
            if len(fragments) != 3:
                raise ValueError("Expected three observed packet fragments")
            key = "-".join(fragments)
            operation["arguments"]["command"] = "openssl enc -d -aes-256-cbc -pbkdf2 -iter 10000 -in /opt/workspace/artifacts/forensics/payload.enc -out /opt/workspace/artifacts/forensics/decrypted.bin -pass " + shlex.quote("pass:" + key)
        self.pending = operation
        return operation

    def accept(self, response):
        operation = self.pending
        if operation is None:
            raise RuntimeError("No pending operation")
        data = payload(response)
        text = searchable(data)
        if not re.search(operation["expect"], text, re.I | re.S):
            raise ValueError(f"{operation['tool']}: expected {operation['expect']!r}; actual: {text[:1500]}")
        error = response.get("isError") or (isinstance(data, dict) and data.get("status") in ("error", "invalid_parameter", "invalid_target", "not_found", "blocked"))
        exits = fields(data, "exit_code")
        expected_exit = operation.get("exit_code", 0)
        if not operation.get("allow_error") and (error or any(v not in (0, None) for v in exits)):
            raise ValueError(f"{operation['tool']}: unexpected failed result: {text[:1500]}")
        if "exit_code" in operation and exits and exits[0] != expected_exit:
            raise ValueError(f"{operation['tool']}: expected exit {expected_exit}, got {exits[0]}")
        self.verified.append({"step": operation, "data": data})
        self.index += 1
        self.pending = None

    def save(self, path):
        Path(path).write_text(json.dumps({"scenario": self.scenario, "verified": self.verified,
                                         "complete": self.index == len(self.steps)}, indent=2), encoding="utf-8")
