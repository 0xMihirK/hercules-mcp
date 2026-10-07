"""Capture the complete native matrix; never treat a failed run as publishable."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import importlib.util
from pathlib import Path
import time

from .cases import CASES
from .run import Lab, RESULTS

CLIENTS = ("claude", "codex", "opencode", "hermes")
GEOMETRIES = ((120, 36), (80, 28), (48, 28))
VERSIONS = {"claude":"2.1.292", "codex":"0.160.1", "opencode":"1.18.35", "hermes":"0.21.5"}


def capture(item, slot):
    client, scenario, cols, rows = item
    name = f"{client}-{scenario}-{cols}-{time.time_ns()}"
    with Lab(name, 80 + slot) as lab:
        status = lab.capture(client, scenario, cols, rows)
    from .publish import approved
    approved(lab.directory,client,scenario,cols,rows)
    return {"client":client, "scenario":scenario, "columns":cols, "rows":rows,
            "directory":str(lab.directory), "completed":status["completed"]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--clients", nargs="+", choices=CLIENTS, default=list(CLIENTS))
    parser.add_argument("--cases", nargs="+", choices=CASES, default=list(CASES))
    parser.add_argument("--workers", type=int, choices=(1,2,3,4), default=2)
    parser.add_argument("--geometries", nargs="+", type=int, choices=(120,80,48), default=[120,80,48])
    parser.add_argument("--index",default="native-matrix.json")
    parser.add_argument("--subnet-base",type=int,default=80)
    args = parser.parse_args()
    if Path(args.index).name != args.index or not args.index.endswith("matrix.json"):
        parser.error("The index must be a plain filename ending in matrix.json")
    matrix = [(c,s,cols,rows) for c in args.clients for s in args.cases for cols,rows in GEOMETRIES if cols in args.geometries]
    index = RESULTS / args.index
    records = json.loads(index.read_text(encoding="utf-8")) if index.exists() else []
    from .publish import approved
    # Independently completed retries are reusable only after the same strict
    # artifact and cleanup validation. Concurrent captures are never reused.
    for directory in RESULTS.iterdir():
        if not directory.is_dir() or not (directory/"recordings").is_dir():
            continue
        for file in (directory/"recordings").glob("*.cast"):
            status_path=file.with_suffix(".json")
            if not status_path.is_file():
                continue
            r=json.loads(status_path.read_text(encoding="utf-8"))
            if not r.get("completed") or r.get("client") not in CLIENTS:
                continue
            key=(r["client"],r["scenario"],r["cols"],r["rows"])
            try:
                approved(directory,*key)
            except (ValueError,OSError,KeyError):
                continue
            records.append({"client":key[0],"scenario":key[1],"columns":key[2],"rows":key[3],"directory":str(directory),"completed":True})
    verified = set()
    for r in records:
        if not r["completed"]:
            continue
        key = (r["client"],r["scenario"],r["columns"],r["rows"])
        try:
            approved(Path(r["directory"]), *key)
            verified.add(key)
        except (ValueError, OSError, KeyError) as error:
            print(json.dumps({"excluded":str(r.get("directory")),"reason":str(error)}),flush=True)
    remaining = [item for item in matrix if item not in verified]
    if remaining and importlib.util.find_spec("fastmcp") is None:
        raise SystemExit("Capture requires Hercules dependencies. Run with the repository Python environment: uv run python -m website.capture.labs.batch")
    index.write_text(json.dumps(records,indent=2)+"\n",encoding="utf-8",newline="\n")
    # A worker owns a distinct subnet for its entire queue, never overlapping a
    # live transaction. Startup is serialized separately by the capture lock.
    queues = [remaining[i::args.workers] for i in range(args.workers)]
    def worker(slot, work):
        for item in work:
            try:
                result = capture(item, args.subnet_base - 80 + slot)
            except Exception as error:
                result = {"client":item[0],"scenario":item[1],"columns":item[2],"rows":item[3],"completed":False,"error":str(error)}
            print(json.dumps(result), flush=True)
            yield result
    # Publish progress in the parent so concurrent workers never race the index.
    import queue
    updates = queue.Queue()
    def collect(slot, work):
        for result in worker(slot, work):
            updates.put(result)
        updates.put(None)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        jobs = [pool.submit(collect,i,q) for i,q in enumerate(queues)]
        done = 0
        while done < len(jobs):
            result = updates.get()
            if result is None:
                done += 1
            else:
                records.append(result)
                index.write_text(json.dumps(records,indent=2)+"\n",encoding="utf-8",newline="\n")
        for job in jobs:
            job.result()
    successes = {(r["client"],r["scenario"],r["columns"],r["rows"]) for r in records if r["completed"]}
    missing = [item for item in matrix if item not in successes]
    if missing:
        raise SystemExit(f"{len(missing)} native sessions failed validation; none are substituted.")


if __name__ == "__main__":
    main()
