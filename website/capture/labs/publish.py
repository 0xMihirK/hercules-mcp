"""Verify and stage native recordings and real artifacts for static playback."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import time

from .batch import CLIENTS, GEOMETRIES, VERSIONS
from .cases import CASES, catalog
from .program import Program, payload
from .run import CAPTURE, IMAGE, RESULTS, ROOT


def result_excerpt(data):
    """Readable observed values, never an authored pre-call plan."""
    if not isinstance(data,dict):
        return str(data)[:550]
    values={key:data[key] for key in ("status","message","session_id","container_running","parsed","findings","results","stdout","stderr","content","job_id","truncated","next_offset","bytes_written") if data.get(key) not in (None,"")}
    if not values:
        values={key:value for key,value in data.items() if key not in ("command","tool","workspace")}
    return json.dumps(values,ensure_ascii=False,indent=2)[:550]


def artifact_time(path, status, validation):
    for call,record in zip(status["mcpCalls"],validation["verified"]):
        references=json.dumps({"arguments":call["arguments"],"result":record["data"]},ensure_ascii=False)
        if path in references or "/opt/workspace/"+path in references:
            return call["completedAt"],"observed tool reference"
    # The final index proves this file exists, even when its creation path was
    # implicit in a tool. Do not imply it was available earlier.
    index_call=next(call for call in reversed(status["mcpCalls"]) if call["name"]=="shell_exec")
    return index_call["completedAt"],"verified final evidence index"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value,indent=2,ensure_ascii=False)+"\n",encoding="utf-8",newline="\n")


def captured_image_suffix(path):
    # Browser providers may return PNG or JPEG. Preserve the captured bytes and
    # publish their actual format rather than assigning a misleading extension.
    with Path(path).open("rb") as stream:
        signature=stream.read(8)
    if signature == b"\x89PNG\r\n\x1a\n": return ".png"
    if signature.startswith(b"\xff\xd8\xff"): return ".jpg"
    raise ValueError(str(path)+": unsupported browser screenshot format")


def approved(directory, client, scenario, cols, rows):
    name = f"{client}-{scenario}-{cols}"
    source = directory / "recordings"
    status = json.loads((source / (name+".json")).read_text(encoding="utf-8"))
    validation = json.loads((source / (client+"-"+scenario+"-validation.json")).read_text(encoding="utf-8"))
    transaction = json.loads((directory / "transaction.json").read_text(encoding="utf-8"))
    recording = source / (name+".cast")
    with recording.open(encoding="utf-8", newline="") as stream:
        header = json.loads(stream.readline())
    expected = Program(scenario).steps
    names = [call["name"] for call in status["mcpCalls"]]
    if not status["completed"] or not validation["complete"] or not transaction["cleanupComplete"]:
        raise ValueError(name+": incomplete tool validation or cleanup")
    if names != [s["tool"] for s in expected] or len(validation["verified"]) != len(expected):
        raise ValueError(name+": unexpected tool sequence")
    if status["version"] != VERSIONS[client] or (header["width"],header["height"]) != (cols,rows):
        raise ValueError(name+": wrong native version or geometry")
    if not header.get("realTools") or header.get("fixture") or status["accountAccess"] or status["externalNetwork"]:
        raise ValueError(name+": incompatible provenance")
    workspace = Path(transaction["session"])
    report = workspace / f"reports/{scenario}.md"
    html = report.with_suffix(".html")
    index = workspace / "reports/evidence-index.json"
    if not all(p.is_file() for p in (report,html,index)) or "Verified observations" not in report.read_text(encoding="utf-8"):
        raise ValueError(name+": report artifacts missing")
    for entry in json.loads(index.read_text(encoding="utf-8")):
        path = (workspace / entry["path"]).resolve()
        if not path.is_relative_to(workspace.resolve()) or not path.is_file() or sha(path) != entry["sha256"]:
            raise ValueError(name+": evidence index checksum mismatch")
    if scenario == "forensics":
        data = json.loads((workspace/"artifacts/forensics/verification.json").read_text())
        if not data["checksum_match"] or data["decoy_match"]:
            raise ValueError(name+": CTF verification failed")
    return status,header,validation,workspace,recording


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--development",action="store_true",help="Write a separate local preview bundle; never replace public assets")
    args = parser.parse_args()
    matrix=[]
    for index in sorted(RESULTS.glob("*matrix.json")):
        matrix+=json.loads(index.read_text(encoding="utf-8"))
    def capture_order(directory):
        suffix=Path(directory).name.rsplit("-",1)[-1]
        return int(suffix) if suffix.isdigit() else Path(directory).stat().st_mtime_ns
    lookup = {}
    for r in sorted((r for r in matrix if r["completed"]),key=lambda r:capture_order(r["directory"])):
        key=(r["client"],r["scenario"],r["columns"],r["rows"])
        directory=Path(r["directory"])
        try: approved(directory,*key)
        except (ValueError,OSError,KeyError): continue
        lookup[key]=directory
    # Development can use independently completed smoke investigations. The
    # public publisher requires all 120 validated recordings before any copy.
    if args.development:
        for directory in sorted(RESULTS.iterdir(),key=capture_order):
            if not directory.is_dir() or not (directory/"recordings").is_dir(): continue
            for file in (directory/"recordings").glob("*-validation.json"):
                for statusfile in (directory/"recordings").glob("*.json"):
                    if statusfile.name.endswith("-validation.json") or statusfile.name=="provider-failure.json": continue
                    status = json.loads(statusfile.read_text(encoding="utf-8"))
                    if isinstance(status,dict) and status.get("completed"):
                        key=(status["client"],status["scenario"],status["cols"],status["rows"])
                        try: approved(directory,*key)
                        except (ValueError,OSError,KeyError): continue
                        if key not in lookup or capture_order(directory)>capture_order(lookup[key]): lookup[key]=directory
    wanted = [(c,s,cols,rows) for c in CLIENTS for s in CASES for cols,rows in GEOMETRIES]
    missing = [key for key in wanted if key not in lookup]
    if missing and not args.development:
        raise ValueError(f"Missing {len(missing)} of 120 validated native recordings")
    approved_items = []
    for key in wanted:
        if key not in lookup: continue
        try:
            approved_items.append((key,approved(lookup[key],*key)))
        except ValueError as error:
            if not args.development: raise
            print("Preview excludes invalid capture: " + str(error))
    stage = RESULTS / ("preview-assets" if args.development else "publish-assets")
    if stage.exists():
        previous=stage.with_name(stage.name+"-previous-"+str(time.time_ns()))
        if stage.is_symlink() or stage.resolve().parent != RESULTS.resolve() or previous.resolve().parent != RESULTS.resolve():
            raise ValueError("Refusing to archive a stage outside capture results")
        stage.rename(previous)
    stage.mkdir(exist_ok=True)
    metadata = []
    for key,(status,header,validation,workspace,recording) in approved_items:
        c,s,cols,rows=key
        name=recording.stem
        shutil.copyfile(recording,stage/recording.name)
        # Human-readable transcript from actual VT output; native ANSI source
        # remains in the untouched cast. No line-ending normalization of casts.
        transcript=name+".txt"
        shutil.copyfile(recording.with_suffix(".txt"),stage/transcript)
        artifacts=stage/"evidence"/name
        artifacts.mkdir(parents=True,exist_ok=True)
        links=[]
        for prefix in ("artifacts","reports","logs","challenge"):
            root=workspace/prefix
            if not root.is_dir(): continue
            for file in sorted(root.rglob("*")):
                if not file.is_file() or file.is_symlink() or not file.resolve().is_relative_to(workspace.resolve()): continue
                relative=file.relative_to(workspace)
                target=artifacts/relative
                target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(file,target)
                available_at,availability=artifact_time(relative.as_posix(),status,validation)
                links.append({"path":relative.as_posix(),"file":target.relative_to(stage).as_posix(),"bytes":file.stat().st_size,"sha256":sha(file),"availableAt":available_at,"availabilitySource":availability})
        synchronized=[]
        metrics=[]
        for call,record in zip(status["mcpCalls"],validation["verified"]):
            data=record["data"]
            synchronized.append({"at":call["completedAt"],"tool":call["name"],"observation":result_excerpt(data),"scriptedObservation":False,"exitCode":data.get("exit_code") if isinstance(data,dict) else None})
            if isinstance(data,dict) and data.get("raw_artifact"):
                raw_chars=int(data.get("stdout_chars",0))+int(data.get("stderr_chars",0))
                # Count the entire serialized structured response, including
                # metadata. Never claim 100% savings when findings moved to JSON.
                inline_chars=len(json.dumps(data,ensure_ascii=False))
                metrics.append({"tool":call["name"],"rawCharacters":raw_chars,"inlineResponseCharacters":inline_chars,
                    "characterReduction":round(100*(1-inline_chars/raw_chars),1) if raw_chars else 0,
                    "rawTokenEstimate":math.ceil(raw_chars/4),"inlineTokenEstimate":math.ceil(inline_chars/4),
                    "tokenEstimateMethod":"ceil(characters / 4); approximate, not model tokenizer counts",
                    "outputComplete":data.get("output_complete"),"evidenceComplete":data.get("evidence_complete"),
                    "outputFiltered":data.get("output_filtered"),"rawArtifact":data["raw_artifact"].replace("/opt/workspace/","")})
        report_link=next(i["file"] for i in links if i["path"]==f"reports/{s}.md")
        metadata.append({"file":recording.name,"client":c,"version":status["version"],"scenario":s,"columns":cols,"rows":rows,
            "duration":header["duration"],"timestamp":header["timestamp"],"chapters":status["chapters"],"tools":[v["name"] for v in status["mcpCalls"]],
            "sha256":sha(recording),"transcript":transcript,"transcriptSha256":sha(stage/transcript),"synchronized":synchronized,
            "captureConfiguration":{"command":status["command"],"term":"xterm-256color","truecolor":True,"freshConfiguration":True,"environmentAllowlisted":True,"provider":"container loopback scripted provider","mcpTransport":"STDIO bridge through transaction-owned private relay","agentDockerSocket":False,"nativeTiming":True,"inputDelaySeconds":0.065,"cleanupVerified":True},
            "validationSha256":sha(recording.parent/(c+"-"+s+"-validation.json")),
            "artifacts":links,"report":report_link,"reportHtml":report_link.replace(".md",".html"),"reportPreview":(workspace/f"reports/{s}.md").read_text(encoding="utf-8")[:1800],"reportAvailableAt":next(call["completedAt"] for call in reversed(status["mcpCalls"]) if call["name"]=="workspace_read_file"),"metrics":metrics,
            "scriptedModel":True,"scriptedToolResults":False,"realTools":True,"holdSeconds":6})
    if metadata:
        frames=json.loads(subprocess.check_output(["node",str(CAPTURE/"first-frame.mjs"),*[str(stage/m["file"]) for m in metadata]],text=True))
        for m in metadata: m["displayStart"]=frames[str(stage/m["file"])]
    case_catalog=catalog()
    write_json(CAPTURE/"lab-cases.json",case_catalog)
    shutil.copyfile(CAPTURE/"lab-surface.json",stage/"mcp-surface.json")
    manifest={"schemaVersion":2,"format":"asciicast-v2","nativeUI":True,"playbackSpeed":1,"realTools":True,"scriptedModel":True,
        "scriptedToolResults":False,"scriptedUsageCounters":True,"accountAccess":False,"externalNetwork":False,"developmentOnly":args.development,
        "term":"xterm-256color","theme":"native dark","font":"IBM Plex Mono","recordings":metadata,
        "clients":{c:{"version":v,"renderer":"standard conversation" if c=="claude" else "modern TUI" if c=="hermes" else "native default"} for c,v in VERSIONS.items()},
        "cases":{k:{"title":v["title"],"prompt":v["prompt"],"summary":v["summary"]} for k,v in CASES.items()},
        "caseCatalogSha256":sha(CAPTURE/"lab-cases.json"),"reproductionImage":subprocess.check_output(["docker","image","inspect",IMAGE,"--format","{{.Id}}"],text=True).strip(),
        "mcpSurface":"mcp-surface.json","mcpSurfaceSha256":sha(stage/"mcp-surface.json"),
        "herculesSourceCommit":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
        "captureProfile":"shell,session,workspace,dns,nmap,curl,ncat,whatweb,fuzz,nuclei,searchsploit,binwalk,steghide,browser"}
    write_json(stage/"manifest.json",manifest)
    stills=RESULTS/"browser-stills"
    for entry in metadata:
        frame=stills/(entry["sha256"]+".png")
        if not frame.is_file():
            if not args.development: raise ValueError(entry["file"]+": actual browser-rendered native still missing")
            continue
        proof=json.loads(frame.with_suffix(".json").read_text(encoding="utf-8"))
        if proof["sha256"]!=entry["sha256"] or proof["file"]!=entry["file"] or abs(proof["at"]-entry["displayStart"])>.000001:
            raise ValueError(entry["file"]+": native still provenance does not match its recording frame")
        entry["still"]=entry["file"].replace(".cast","-still"+captured_image_suffix(frame))
        entry["stillAt"]=entry["displayStart"]
        entry["stillRenderer"]="Chromium + xterm 6 / Unicode 11; screenshot of captured ANSI, no authored terminal content"
        shutil.copyfile(frame,stage/entry["still"])
        entry["stillSha256"]=sha(frame)
        completed_frame=stills/(entry["sha256"]+"-report.png")
        if not completed_frame.is_file():
            if not args.development: raise ValueError(entry["file"]+": actual completed native still missing")
            continue
        completed_proof=json.loads(completed_frame.with_suffix(".json").read_text(encoding="utf-8"))
        completed_at=max(0,entry["duration"]-1)
        if completed_proof["sha256"]!=entry["sha256"] or completed_proof["file"]!=entry["file"] or abs(completed_proof["at"]-completed_at)>.000001:
            raise ValueError(entry["file"]+": completed native still provenance mismatch")
        entry["completedStill"]=entry["file"].replace(".cast","-report-still"+captured_image_suffix(completed_frame))
        entry["completedStillAt"]=completed_at
        entry["completedStillSha256"]=sha(completed_frame)
        shutil.copyfile(completed_frame,stage/entry["completedStill"])
    write_json(stage/"manifest.json",manifest)
    if not args.development:
        # Only validated full matrices reach the public assets. Stage first;
        # the manifest is copied last so readers never reference missing files.
        target=ROOT/"website/assets/recordings"
        if target.exists():
            archive=RESULTS/("public-recordings-previous-"+str(time.time_ns()))
            if target.is_symlink() or not target.resolve().is_relative_to((ROOT/"website/assets").resolve()) or archive.resolve().parent!=RESULTS.resolve():
                raise ValueError("Refusing to archive a public recording directory outside the website")
            target.rename(archive)
        target.mkdir(exist_ok=True)
        for file in sorted(stage.rglob("*")):
            if file.is_file() and file != stage/"manifest.json":
                relative=file.relative_to(stage); (target/relative).parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(file,target/relative)
        shutil.copyfile(stage/"manifest.json",target/"manifest.json")
    print(f"Staged {len(metadata)} validated native sessions at {stage}")


if __name__=="__main__":
    main()
