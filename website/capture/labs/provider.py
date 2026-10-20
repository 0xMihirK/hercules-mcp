"""Loopback scripted models. Every investigation advances from real MCP evidence."""
import json
import re
from pathlib import Path
import threading
from http.server import ThreadingHTTPServer

from .cases import CASES, HOST
from .program import Program
from .protocol import ScriptedProtocol

PROMPTS = {key: value["prompt"] for key, value in CASES.items()}
PHASES = ["Establish scope and start the owned runtime", "Investigate, reject alternatives and verify evidence", "Write the report and clean up the owned runtime"]


def prepare_workspace(home, scenario):
    # Only instructions enter the agent's local working directory. Challenge
    # inputs and reports are reachable exclusively through real Hercules MCP.
    (home / "CAPTURE.md").write_text("Real tools in an isolated local lab. Scripted model reasoning. No public targets or personal accounts.\n", encoding="utf-8")


class LabProvider(ScriptedProtocol):
    lock = threading.Lock()
    program = None
    initialized = False
    native_queue = []
    journal_count = 0
    failed = None
    pending_native = False
    closing_plan = False
    final_sent = False
    phase = 0
    inventory_sent = False
    native_names = []

    def do_POST(self):
        super().do_POST()
        cls = type(self)
        if cls.final_sent and not cls.failed:
            # Start the completion hold after the native final stream finishes.
            cls.completed.set()

    def choose(self, body):
        with type(self).lock:
            return self.advance(body)

    def advance(self, body):
        cls = type(self)
        # Codex sends its automatic task-title request concurrently with the
        # conversation. It must never advance the investigation or consume a
        # pending MCP result.
        user_text = "\n".join(part.get("text", "") for item in body.get("input", [])
                              if item.get("role") == "user" for part in item.get("content", [])
                              if isinstance(part, dict))
        if "Generate a concise, single-line task title" in user_text:
            return "Investigate the local lab", None
        tools = body.get("tools", [])
        additional = [namespace for item in body.get("input", []) if item.get("type") == "additional_tools" for namespace in item.get("tools", [])]
        custom = cls.client == "codex" and any(t.get("type") == "custom" and t.get("name") == "exec" for namespace in additional for t in namespace.get("tools", []))
        if not tools and not custom:
            return "Hercules local lab investigation", None
        specs = [(t.get("function", t).get("name", ""), t.get("function", t)) for t in tools]
        names = [name for name, _ in specs]

        def find(suffix):
            return next((name for name in names if name == suffix or name.endswith("__" + suffix) or name.endswith("_" + suffix)), None)

        def invoke(name, arguments, builtin=False):
            if custom:
                resolved=next((n for n in cls.native_names if n==name or n.endswith("__"+name)), None)
                if not resolved:
                    raise ValueError("Native inventory did not advertise " + name)
                code = "text(await tools["+json.dumps(resolved)+"]("+json.dumps(arguments)+"));"
                return ("exec", {"__code": code})
            resolved = name if builtin else find(name)
            if not resolved:
                raise ValueError("Native provider did not advertise the real tool " + name)
            schema = next((s.get("parameters", s.get("input_schema", {})) for n, s in specs if n == resolved), {})
            properties = schema.get("properties", {})
            unknown = set(arguments) - set(properties)
            if unknown and not schema.get("additionalProperties"):
                raise ValueError(f"Unexpected arguments for {resolved}: {unknown}")
            return resolved, arguments

        def plan(completed=False, updating=False):
            todos = [{"id": str(i+1), "content": title, "status": "completed" if completed or i < cls.phase else "in_progress" if i == cls.phase else "pending", "priority": "medium"} for i, title in enumerate(PHASES)]
            if "update_plan" in names or any(n=="update_plan" or n.endswith("__update_plan") for n in cls.native_names):
                return [("update_plan", {"plan": [{"step": t["content"], "status": t["status"]} for t in todos]})]
            if "TaskCreate" in names:
                if completed or updating:
                    return [("TaskUpdate", {"taskId": t["id"], "status": t["status"]}) for t in todos]
                return [("TaskCreate", {"subject": t["content"], "description": t["content"] + ". Real Hercules tools; scripted model decisions.", "activeForm": t["content"]}) for t in todos] + [("TaskUpdate", {"taskId": "1", "status": "in_progress"})]
            for name in ("todowrite", "TodoWrite", "todo_list"):
                if name in names:
                    return [(name, {"todos": [{k:v for k,v in t.items() if k != "priority"} for t in todos], "merge": completed or updating} if name == "todo_list" else {"todos": todos})]
            return []

        try:
            if custom:
                for item in body.get("input",[]):
                    if item.get("type")=="custom_tool_call_output":
                        for output in item.get("output",[]) if isinstance(item.get("output"),list) else []:
                            text=output.get("text", "").strip()
                            if text.startswith("["):
                                try:
                                    inventory=json.loads(text)
                                except json.JSONDecodeError:
                                    continue
                                if isinstance(inventory,list) and inventory and all(isinstance(t,dict) and "name" in t for t in inventory):
                                    cls.native_names=[t["name"] for t in inventory]
            if cls.failed:
                return "Capture stopped: " + cls.failed + ". No verified completion report is claimed.", None
            if not cls.initialized:
                cls.initialized = True
                cls.native_queue = plan()
            if custom and not cls.inventory_sent:
                cls.inventory_sent = True
                return "I will inspect the native tool inventory before planning this local investigation.", ("exec", {"__code":"text(ALL_TOOLS.map(t=>({name:t.name,description:t.description.slice(0,140)})));"})
            if custom and cls.program.pending:
                outputs=[item for item in body.get("input",[]) if item.get("type") in ("custom_tool_call_output","function_call_output")]
                if outputs:
                    output=outputs[-1].get("output", "")
                    text=output if isinstance(output,str) else "\n".join(part.get("text", "") for part in output if isinstance(part,dict))
                    running=re.search(r"Script running with cell ID ([\w-]+)",text)
                    if running:
                        # Codex's native code runner yields long MCP calls.
                        # Drain the actual yielded cell before validating it.
                        return "", ("wait", {"cell_id":running.group(1),"yield_time_ms":10000,"max_tokens":3000})
            if cls.program.pending:
                journal = Path("/tmp/mcp-calls.jsonl")
                rows = [json.loads(line) for line in journal.read_text().splitlines()] if journal.exists() else []
                if len(rows) != cls.journal_count + 1:
                    raise ValueError(f"Expected one actual Hercules result, observed {len(rows)-cls.journal_count}")
                actual = rows[-1]
                expected = cls.program.pending
                if actual["name"] != expected["tool"] or actual["arguments"] != expected["arguments"]:
                    raise ValueError("Observed tool call differs from the scripted investigation step")
                if actual.get("error"):
                    raise ValueError(actual["error"])
                cls.program.accept(actual["result"])
                cls.program.save("/out/" + cls.client + "-" + cls.scenario + "-validation.json")
                cls.journal_count = len(rows)
            if cls.native_queue:
                name, arguments = cls.native_queue.pop(0)
                return "" if cls.initialized else "I will keep the investigation plan visible.", invoke(name, arguments, True)
            phase = 2 if cls.program.index >= len(cls.program.steps) - 4 else 1 if cls.program.index >= 2 else 0
            if phase > cls.phase:
                cls.phase = phase
                cls.native_queue = plan(updating=True)
                if cls.native_queue:
                    name, arguments = cls.native_queue.pop(0)
                    return "The previous phase passed its evidence checks. I will update the plan before continuing.", invoke(name, arguments, True)
            operation = cls.program.next()
            if operation:
                return operation["observation"], invoke(operation["tool"], operation["arguments"])
            if not cls.closing_plan:
                cls.closing_plan = True
                cls.native_queue = plan(True)
                if cls.native_queue:
                    name, arguments = cls.native_queue.pop(0)
                    return "The saved report was reread and the owned runtime was stopped. I will mark the verified plan complete.", invoke(name, arguments, True)
            cls.final_sent = True
            return f"Verified report: reports/{cls.scenario}.md\nHTML report: reports/{cls.scenario}.html\nEvidence index: reports/evidence-index.json\n\n{cls.program.index} real Hercules calls passed their evidence checks. The owned runtime is stopped. Model decisions are scripted; no public target was contacted.", None
        except (ValueError, RuntimeError) as error:
            cls.failed = str(error)
            Path("/out/provider-failure.json").write_text(json.dumps({"client": cls.client, "scenario": cls.scenario, "error": cls.failed}, indent=2))
            return "Capture validation stopped: " + cls.failed + ". I will not invent the missing evidence.", None


def start(scenario, client, port=8765):
    cls = LabProvider
    cls.scenario, cls.client = scenario, client
    cls.requests = []
    cls.completed = threading.Event()
    cls.native_queue, cls.journal_count = [], 0
    cls.initialized = cls.closing_plan = cls.final_sent = False
    cls.failed = None
    cls.phase = 0
    cls.inventory_sent = False
    cls.native_names = []
    configuration = json.loads(Path("/capture-session/relay.json").read_text())
    cls.program = Program(scenario, configuration.get("labAddress", HOST))
    server = ThreadingHTTPServer(("127.0.0.1", port), cls)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


ModelFixture = LabProvider
