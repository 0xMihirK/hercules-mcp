"""Verify and stage native recordings and real artifacts for static playback."""
import argparse
from bisect import bisect_right
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import time
import zipfile

from PIL import Image
from ..pixels import validate_capture_times

from .batch import CLIENTS, geometries, VERSIONS, PROFILES
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


def call_phase(scenario,position):
    if position<2:return "setup"
    return "investigation" if position<2+len(CASES[scenario]["steps"]) else "reporting"


def report_preview(report):
    sections=list(re.finditer(r"(?m)^### \d+\.[^\n]*$",report))
    if len(sections)<=2:return report
    # Show the final verified results instead of filling the preview with an
    # early guidance/tool-inventory excerpt. The original report is untouched.
    lead=report.split("## Verified observations",1)[0]
    return lead+"## Verified observations (selected excerpt)\n\n"+report[sections[-2].start():]


def investigation_transcript(status, validation):
    lines=[f"{status['client']} {status['version']} — {CASES[status['scenario']]['title']}",
        "Investigation transcript: recorded tool journal and the scripted model text sent to this client.",
        "Tools ran in an isolated local lab. No public target was contacted.",
        "Native menus, task UI and animation remain in the untouched ANSI and timestamped recordings.",
        "", "User prompt", CASES[status['scenario']]["prompt"], ""]
    for call,record in zip(status["mcpCalls"],validation["verified"]):
        lines.extend([f"[{call['requestedAt']:.3f}s → {call['completedAt']:.3f}s] {call['name']}",
            "Scripted model: " + record["step"]["observation"],
            "Actual arguments:",json.dumps(call["arguments"],ensure_ascii=False,indent=2),
            "Actual Hercules result:",json.dumps(record["data"],ensure_ascii=False,indent=2),""])
    lines.extend(["Verified completion",f"Report: reports/{status['scenario']}.md",
        f"HTML report: reports/{status['scenario']}.html","Evidence index: reports/evidence-index.json",
        f"{len(status['mcpCalls'])} real Hercules calls passed their evidence checks. The owned runtime is stopped.",""])
    return "\n".join(lines)


def artifact_time(path, status, validation):
    for call,record in zip(status["mcpCalls"],validation["verified"]):
        references=json.dumps({"arguments":call["arguments"],"result":record["data"]},ensure_ascii=False)
        if path in references or "/opt/workspace/"+path in references:
            return call["completedAt"],"observed tool reference"
    # The final index proves this file exists, even when its creation path was
    # implicit in a tool. Do not imply it was available earlier.
    index_call=next(call for call in reversed(status["mcpCalls"]) if call["name"]=="shell_exec")
    return index_call["completedAt"],"verified final evidence index"


_hashes={}
RECORDER_NEWLINE_EQUIVALENTS={
    # Preserve original Windows byte hashes; only identical source text after
    # Git newline normalization can reuse those captures. Never normalize ANSI.
    "b7ef891ff2afcd9eed639bbd4f0b6a81bd50b4d644cf69b63d710a8579d26366":"aa25f1c0afbf144f064757835014a37f5d4bfdb87abb2bca606f3a6c3de0f9fd",
}
# Both encoders hash decoded native RGB and compare all composed deltas to the
# independent master. Preserve the original encoder fingerprint when only
# postprocessing performance changes; record/configuration fidelity is strict.
VALIDATED_ENCODER_HASHES={"f8875141030494307763c561f96dc5f650d15e0df5d0c554cf7141899a709a67","907f1342f925d4012a9ee4108f1911cd3a9bc3c5f47e688180bcaf878d6ed657","d00e975d99edacf5960d3286a79d3e920ffaf5ac435351d7f28f74c661e87d41","1f6944a780dc100cb43a68631de5f929070f56d48bca9eadb4e2b5fc59504e02","d3df8f0877d04bef3518b234a12e3f5b2e151762a3b6f91feab48b3e962138bc"}
_intervals={}


def capture_interval(master,epoch,duration):
    stat=master.stat();key=(str(master.resolve()),stat.st_size,stat.st_mtime_ns,epoch,duration)
    if key not in _intervals:
        # Inspect the retained master's original packet PTS as an additional
        # publication gate, including bundles encoded before this check.
        output=subprocess.check_output(["ffprobe","-v","error","-select_streams","v:0","-show_packets","-show_entries","packet=pts_time","-of","csv=p=0",str(master)],text=True)
        times=[float(line)-epoch for line in output.splitlines()]
        validate_capture_times(times,duration)
        _intervals[key]={"covered":True,"firstFrameAt":times[0],"lastFrameAt":times[-1],"recordingDuration":duration,"toleranceSeconds":1/60}
    return _intervals[key]
def sha(path):
    path=Path(path);stat=path.stat();key=(str(path.resolve()),stat.st_size,stat.st_mtime_ns)
    # A publication pass validates immutable masters repeatedly; hash each
    # unchanged file once without allocating a multi-gigabyte byte buffer.
    if key not in _hashes:
        digest=hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda:stream.read(1024*1024),b""):digest.update(chunk)
        _hashes[key]=digest.hexdigest()
    return _hashes[key]


def recorder_fingerprint_matches(path,captured):
    if captured==sha(path):return True
    expected=RECORDER_NEWLINE_EQUIVALENTS.get(captured)
    return expected is not None and hashlib.sha256(Path(path).read_bytes().replace(b"\r\n",b"\n")).hexdigest()==expected


def write_json(path, value):
    path=Path(path)
    encoded=(json.dumps(value,indent=2,ensure_ascii=False)+"\n").encode("utf-8")
    if path.exists() and path.read_bytes()==encoded: return
    temporary=path.with_name(path.name+".pending")
    temporary.write_bytes(encoded)
    temporary.replace(path)


def stage_artifact(file,stage,relative,capture):
    # Repeated geometries can retain byte-identical large tool output. Share
    # its original bytes, while every capture keeps its observed path and hash.
    digest=sha(file)
    target=stage/"evidence"/("shared" if file.stat().st_size>=1024*1024 else capture)
    target=target/(digest+file.suffix if file.stat().st_size>=1024*1024 else relative)
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():
        if sha(target)!=digest:raise ValueError("Shared evidence integrity mismatch: "+str(target))
    else:shutil.copyfile(file,target)
    return target


def archive_recording(recording,stage):
    """Package the unchanged timestamped payload; pixels and ANSI stay direct."""
    data=Path(recording).read_bytes()
    target=Path(stage)/(Path(recording).name+".zip")
    entry=zipfile.ZipInfo(Path(recording).name,(1980,1,1,0,0,0))
    with zipfile.ZipFile(target,"w") as archive:
        archive.writestr(entry,data,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    with zipfile.ZipFile(target) as archive:
        if archive.namelist()!=[entry.filename] or archive.read(entry.filename)!=data:
            raise ValueError("Timestamped recording archive changed its original bytes")
    return {"file":target.name,"format":"zip-deflate","sha256":sha(target),
            "payloadFile":entry.filename,"payloadSha256":hashlib.sha256(data).hexdigest(),"payloadBytes":len(data)}


def captured_image_suffix(path):
    # Browser providers may return PNG or JPEG. Preserve the captured bytes and
    # publish their actual format rather than assigning a misleading extension.
    with Path(path).open("rb") as stream:
        signature=stream.read(8)
    if signature == b"\x89PNG\r\n\x1a\n": return ".png"
    if signature.startswith(b"\xff\xd8\xff"): return ".jpg"
    raise ValueError(str(path)+": unsupported browser screenshot format")


def validate_browser_artifacts(workspace, validation):
    for record in validation["verified"]:
        if record["step"]["tool"] != "browser_screenshot": continue
        data=record["data"]
        path=data.get("path", "")
        if not path.startswith("/opt/workspace/"):
            raise ValueError("Browser screenshot has no observed workspace path")
        file=(workspace/path.removeprefix("/opt/workspace/")).resolve()
        if not file.is_relative_to(workspace.resolve()) or not file.is_file():
            raise ValueError("Browser screenshot is missing or outside its workspace")
        if file.stat().st_size != data.get("bytes") or file.suffix != captured_image_suffix(file):
            raise ValueError("Browser screenshot bytes or format disagree with its tool result")
        with Image.open(file) as image:
            if image.size != (data.get("width"),data.get("height")):
                raise ValueError("Browser screenshot dimensions disagree with its tool result")


def approved(directory, client, scenario, cols, rows, require_current=True):
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
    pixels=status.get("pixels",{})
    pixel_index=source / pixels.get("directory","missing") / "index.json"
    if not pixel_index.is_file() or sha(pixel_index)!=pixels.get("indexSha256"):
        raise ValueError(name+": independent graphical capture missing or invalid")
    visual=json.loads(pixel_index.read_text())
    current_harness=visual["profile"].get("harnessSha256",{})
    # Recorder/configuration and pixel encoding must be current. The original
    # graphical-wrapper hash stays in provenance: retention-only changes do
    # not invalidate independently verified, unmodified terminal pixels.
    encoder=visual["profile"].get("postprocessorSha256",current_harness.get("pixels.py"))
    if require_current and (not recorder_fingerprint_matches(CAPTURE/"record.py",current_harness.get("record.py")) or current_harness.get("profiles.json")!=sha(CAPTURE/"profiles.json") or encoder not in VALIDATED_ENCODER_HASHES | {sha(CAPTURE/"pixels.py")} or not current_harness.get("graphical.py") or not visual["profile"].get("captureImageId") or "nativeIntro" not in status["chapters"] or "details" not in status["chapters"] or "completedAt" not in visual):
        raise ValueError(name+": native entrance and detail capture must use the current validated harness")
    clock=source/"clock-validation.json"
    if clock.exists() and not json.loads(clock.read_text())["valid"]:
        raise ValueError(name+": capture clock changed during the native session; recapture required")
    if visual.get("schemaVersion")!=3 or visual["fps"]!=60 or not visual["verification"]["pixelExact"]:
        raise ValueError(name+": native pixel reconstruction did not pass")
    if visual["width"]<cols*6 or visual["height"]<rows*12 or visual["profile"]["version"]!=VERSIONS[client] or visual["width"]!=cols*visual["profile"]["measuredCellWidth"] or visual["height"]!=rows*visual["profile"]["measuredCellHeight"]:
        raise ValueError(name+": graphical profile disagrees with native session")
    for sheet in visual["sheets"]:
        if sha(pixel_index.parent/sheet["file"])!=sheet["sha256"]:
            raise ValueError(name+": graphical atlas checksum mismatch")
    times=[frame["at"] for frame in visual["frames"]]
    for label in ("startup","nativeIntro","mcp","details","investigation","report","completed"):
        review=visual.get("reviewFrames",{}).get(label)
        if not review:
            raise ValueError(name+": independent native "+label+" frame missing")
        frame=visual["frames"][max(0,bisect_right(times,review["at"])-1)]
        with Image.open(pixel_index.parent/review["file"]) as native:
            digest=hashlib.sha256(native.convert("RGB").tobytes()).hexdigest()
        if digest!=frame["sha256"]:
            raise ValueError(name+": independent native "+label+" frame timestamp mismatch")
    for file,at in (("opening.png",visual["openingAt"]),("completed.png",visual["completedAt"])):
        with Image.open(pixel_index.parent/file) as native:
            digest=hashlib.sha256(native.convert("RGB").tobytes()).hexdigest()
        if digest!=visual["frames"][max(0,bisect_right(times,at)-1)]["sha256"]:
            raise ValueError(name+": native poster timestamp mismatch")
    master=source / visual["verification"]["master"]
    if not master.is_file() or sha(master)!=visual["verification"]["masterSha256"]:
        raise ValueError(name+": lossless graphical master missing or modified")
    capture_interval(master,visual["clock"]["nativeEpoch"],header["duration"])
    workspace = Path(transaction["session"])
    validate_browser_artifacts(workspace, validation)
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
    parser.add_argument("--current-only",action="store_true",help="Exclude all superseded harness profiles from the local preview")
    args = parser.parse_args()
    require_current=not args.development or args.current_only
    matrix=[]
    for index in sorted(RESULTS.glob("*matrix.json")):
        matrix+=json.loads(index.read_text(encoding="utf-8"))
    def capture_order(directory):
        suffix=Path(directory).name.rsplit("-",1)[-1]
        return int(suffix) if suffix.isdigit() else Path(directory).stat().st_mtime_ns
    lookup = {};examined=set()
    for r in sorted((r for r in matrix if r["completed"]),key=lambda r:capture_order(r["directory"])):
        key=(r["client"],r["scenario"],r["columns"],r["rows"])
        directory=Path(r["directory"])
        identity=(directory.resolve(),key)
        if identity in examined:continue
        examined.add(identity)
        try: approved(directory,*key,require_current=require_current)
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
                        identity=(directory.resolve(),key)
                        if identity in examined:continue
                        examined.add(identity)
                        try: approved(directory,*key,require_current=require_current)
                        except (ValueError,OSError,KeyError): continue
                        if key not in lookup or capture_order(directory)>capture_order(lookup[key]): lookup[key]=directory
    wanted = [(c,s,cols,rows) for c in CLIENTS for s in CASES for cols,rows in geometries(c)]
    missing = [key for key in wanted if key not in lookup]
    if missing and not args.development:
        raise ValueError(f"Missing {len(missing)} of 120 validated native recordings")
    approved_items = []
    for key in wanted:
        if key not in lookup: continue
        try:
            approved_items.append((key,approved(lookup[key],*key,require_current=require_current)))
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
        recording_archive=archive_recording(recording,stage)
        shutil.copyfile(recording.with_suffix(".ansi"),stage/recording.with_suffix(".ansi").name)
        pixel_source=recording.parent/status["pixels"]["directory"]
        shutil.copytree(pixel_source,stage/pixel_source.name)
        pixel_index=json.loads((pixel_source/"index.json").read_text())
        # Concatenated VT diffs are unreadable in full-screen clients. Export
        # the observed journal and text actually sent by the scripted provider.
        # The unmodified VT stream remains separately downloadable.
        transcript=name+".txt"
        (stage/transcript).write_text(investigation_transcript(status,validation),encoding="utf-8",newline="\n")
        artifacts=stage/"evidence"/name
        artifacts.mkdir(parents=True,exist_ok=True)
        links=[]
        for prefix in ("artifacts","reports","logs","challenge","browser","nuclei-templates"):
            root=workspace/prefix
            if not root.is_dir(): continue
            for file in sorted(root.rglob("*")):
                if not file.is_file() or file.is_symlink() or not file.resolve().is_relative_to(workspace.resolve()): continue
                relative=file.relative_to(workspace)
                target=stage_artifact(file,stage,relative,name)
                available_at,availability=artifact_time(relative.as_posix(),status,validation)
                links.append({"path":relative.as_posix(),"file":target.relative_to(stage).as_posix(),"bytes":file.stat().st_size,"sha256":sha(file),"availableAt":available_at,"availabilitySource":availability})
        synchronized=[]
        metrics=[]
        for position,(call,record) in enumerate(zip(status["mcpCalls"],validation["verified"])):
            data=record["data"]
            synchronized.append({"at":call["completedAt"],"tool":call["name"],"phase":call_phase(s,position),"observation":result_excerpt(data),"scriptedObservation":False,"exitCode":data.get("exit_code") if isinstance(data,dict) else None})
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
            "recordingArchive":recording_archive,
            "rawAnsi":recording.with_suffix(".ansi").name,"rawAnsiSha256":sha(recording.with_suffix(".ansi")),
            "pixels":{"index":pixel_source.name+"/index.json","indexSha256":sha(pixel_source/"index.json"),"width":pixel_index["width"],"height":pixel_index["height"],"fps":60,"profile":pixel_index["profile"],"pixelExact":True,"captureTiming":{"capturedFrames":pixel_index["verification"]["capturedFrames"],"maximumCaptureGapSeconds":pixel_index["verification"]["largestCaptureGapSeconds"],"clockValidation":json.loads((recording.parent/"clock-validation.json").read_text()) if (recording.parent/"clock-validation.json").exists() else None}},
            "displayStart":pixel_index["displayStart"],"still":pixel_source.name+"/opening.png","stillAt":pixel_index["openingAt"],"stillSha256":sha(pixel_source/"opening.png"),
            "stillRenderer":"Independent XTerm/Xvfb native graphical capture; original lossless pixels",
            "completedStill":pixel_source.name+"/completed.png","completedStillAt":pixel_index.get("completedAt",pixel_index["reviewFrames"]["completed"]["at"]),"completedStillSha256":sha(pixel_source/"completed.png"),
            "duration":header["duration"],"timestamp":header["timestamp"],"chapters":status["chapters"],"tools":[v["name"] for v in status["mcpCalls"]],
            "sha256":sha(recording),"transcript":transcript,"transcriptSha256":sha(stage/transcript),"transcriptSource":"Observed MCP journal and scripted provider text; native VT stream retained separately","synchronized":synchronized,
            "captureConfiguration":{"command":status["command"],"term":"xterm-256color","truecolor":True,"freshConfiguration":True,"environmentAllowlisted":True,"provider":"container loopback scripted provider","mcpTransport":"STDIO bridge through transaction-owned private relay","agentDockerSocket":False,"nativeTiming":True,"inputDelaySeconds":0.065,"cleanupVerified":True},
            "validationSha256":sha(recording.parent/(c+"-"+s+"-validation.json")),
            "artifacts":links,"report":report_link,"reportHtml":report_link.replace(".md",".html"),"reportPreview":report_preview((workspace/f"reports/{s}.md").read_text(encoding="utf-8")),"reportAvailableAt":next(call["completedAt"] for call in reversed(status["mcpCalls"]) if call["name"]=="workspace_read_file"),"metrics":metrics,
            "scriptedModel":True,"scriptedToolResults":False,"realTools":True,"holdSeconds":6})
    case_catalog=catalog()
    write_json(CAPTURE/"lab-cases.json",case_catalog)
    shutil.copyfile(CAPTURE/"lab-surface.json",stage/"mcp-surface.json")
    manifest={"schemaVersion":3,"format":"lossless-native-pixel-atlases","rawFormat":"asciicast-v2","nativeUI":True,"captureSpeed":1,"playbackSpeed":2.5,"realTools":True,"scriptedModel":True,
        "scriptedToolResults":False,"scriptedUsageCounters":True,"accountAccess":False,"externalNetwork":False,"developmentOnly":args.development,
        "term":"xterm-256color","theme":"native dark","font":"Cascadia Mono 2407.24","recordings":metadata,
        "clients":{c:{"version":v,"renderer":PROFILES["clients"][c]["renderer"]} for c,v in VERSIONS.items()},
        "cases":{k:{"title":v["title"],"prompt":v["prompt"],"summary":v["summary"]} for k,v in CASES.items()},
        "caseCatalogSha256":sha(CAPTURE/"lab-cases.json"),"reproductionImage":subprocess.check_output(["docker","image","inspect",IMAGE,"--format","{{.Id}}"],text=True).strip(),
        "mcpSurface":"mcp-surface.json","mcpSurfaceSha256":sha(stage/"mcp-surface.json"),
        "herculesSourceCommit":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
        "captureProfile":"shell,session,workspace,dns,nmap,curl,ncat,whatweb,fuzz,nuclei,searchsploit,binwalk,steghide,browser"}
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
