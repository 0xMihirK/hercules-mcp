"""Lossless native-pixel atlas encoder. No terminal reconstruction or artwork.

Every delta is applied to a second RGB image and compared byte for byte with
the independently decoded graphical master before that frame is accepted.
"""
import hashlib
import json
import math
from pathlib import Path
import subprocess

import numpy as np
from PIL import Image


def sha(path):
    digest=hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b""):digest.update(chunk)
    return digest.hexdigest()


def rectangles(changes, tile=32):
    """Merge adjacent dirty tiles, avoiding one giant box around distant edits."""
    height,width=changes.shape
    padded=np.pad(changes,((0,(-height)%tile),(0,(-width)%tile)))
    dirty=padded.reshape(padded.shape[0]//tile,tile,padded.shape[1]//tile,tile).any(axis=(1,3))
    active={};result=[]
    for row in range(len(dirty)):
        xs=np.flatnonzero(dirty[row]);runs=[]
        if len(xs):
            start=previous=int(xs[0])
            for x in xs[1:]:
                if x!=previous+1:runs.append((start,previous+1));start=int(x)
                previous=int(x)
            runs.append((start,previous+1))
        following={}
        for left,right in runs:
            key=(left,right);top=active.pop(key,row)
            following[key]=top
        for (left,right),top in active.items():
            result.append((left*tile,top*tile,min(width,right*tile),min(height,row*tile)))
        active=following
    for (left,right),top in active.items():
        result.append((left*tile,top*tile,min(width,right*tile),height))
    return result


def interface_visible(image,background):
    # A client can paint its own flat background before mounting its UI. Use
    # the observed corner surface, not XTerm's configured background, so a
    # dark-grey OpenCode surface cannot be mistaken for its native entrance.
    corners=image[[0,0,-1,-1],[0,-1,0,-1]]
    surface=np.median(corners,axis=0)
    return np.count_nonzero(np.any(image!=surface,axis=2))>1000


def changed_indices(hashes):
    return [i for i,value in enumerate(hashes) if i==0 or value!=hashes[i-1]]


def selection_expression(indices):
    # A balanced expression stays below FFmpeg's parser depth limit even for
    # long captures. A file avoids Windows' command-line length restriction.
    terms=[f"eq(n,{i})" for i in indices]
    while len(terms)>1:
        terms=[f"({terms[i]}+{terms[i+1]})" if i+1<len(terms) else terms[i] for i in range(0,len(terms),2)]
    return "select='"+terms[0]+"'"


def validate_capture_times(times, duration):
    # Video starts before the recorder finishes fresh provider/configuration
    # setup. Empty pre-roll can exceed five seconds under load. Require the
    # original UTC timestamps to cover the actual recorder interval instead.
    tolerance=1/60
    if not times or any(not math.isfinite(at) for at in times) or times[0]>tolerance or times[-1]<duration-tolerance or any(b<a for a,b in zip(times,times[1:])):
        raise ValueError("Graphical timestamps do not cover the native recorder interval")


def pack(master, cast, profile):
    destination = cast.parent / (cast.stem + "-pixels")
    destination.mkdir()
    clock = json.loads((cast.parent / "clock.json").read_text())
    with cast.open(encoding="utf-8") as source:
        header = json.loads(source.readline())
    width, height = profile["pixelWidth"], profile["pixelHeight"]
    probe = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_frames",
        "-show_entries", "frame=best_effort_timestamp_time", "-of", "json", str(master)]))
    times = [float(f["best_effort_timestamp_time"])-clock["epoch"] for f in probe["frames"]]
    validate_capture_times(times,header["duration"])
    # Decode the independent master once and hash every RGB frame with
    # OpenSSL-backed hashlib. A 600-frame benchmark matched FFmpeg SHA-256
    # byte for byte, while avoiding its slower software-only hashing pass.
    decoder = subprocess.Popen(["ffmpeg", "-v", "fatal", "-threads", "2", "-i", str(master), "-vsync", "0", "-enc_time_base", "1:1000000", "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"], stdout=subprocess.PIPE)
    frame_bytes = width*height*3
    frames, sheets, checks = [], [], []
    atlas_size = 2048
    atlas = Image.new("RGB", (atlas_size, atlas_size))
    x = y = shelf = 0
    atlas_index = 0
    atlas_used = False
    canvas = np.zeros((height,width,3),dtype=np.uint8)
    last = None
    last_keyframe = -100
    first_visible = None
    background=np.array(tuple(bytes.fromhex(profile["terminal"]["background"].lstrip("#"))),dtype=np.uint8)
    opening_at = None
    opening_saved = False
    completed_saved = False
    completed_at = None
    entrance=max(0,header["chapters"].get("nativeIntro",header["chapters"].get("mcp",2)-2))
    capture_frames = 0
    last_digest=None
    tiles={};reused_patches=0
    review_targets={"startup":None,**{name:value+(4 if name=="mcp" else 1) for name,value in header["chapters"].items()},"completed":max(0,header["duration"]-1)}
    if "mcpInventory" in header["chapters"]:
        review_targets["mcp"]=header["chapters"]["mcpInventory"]+4
    review_frames={}
    def flush():
        nonlocal atlas, atlas_index, atlas_used, x, y, shelf
        if not atlas_used: return
        path = destination / f"atlas-{atlas_index:04}.png"
        atlas.crop((0,0,atlas_size,y+shelf)).save(path,compress_level=6)
        sheets.append({"file":path.name,"sha256":sha(path)})
        atlas_index += 1
        atlas = Image.new("RGB", (atlas_size,atlas_size))
        x=y=shelf=0;atlas_used=False
    try:
        for number,at in enumerate(times):
            raw = bytearray()
            while len(raw)<frame_bytes:
                chunk=decoder.stdout.read(frame_bytes-len(raw))
                if not chunk: break
                raw.extend(chunk)
            if len(raw)!=frame_bytes: raise ValueError("Truncated lossless graphical master")
            digest=hashlib.sha256(raw).hexdigest()
            image = np.frombuffer(raw,dtype=np.uint8).reshape((height,width,3))
            capture_frames += 1
            if at<0: continue
            if at>header["duration"]: continue
            # Opening and completion posters are native master frames, never VT
            # screenshots. Readiness is determined only from captured pixels.
            # The top-left pixel may be the native cursor. Comparing against it
            # mistakes a blank terminal for a fully rendered entrance.
            if first_visible is None and at>=entrance and interface_visible(image,background):
                first_visible=round(at,6)
                review_targets["startup"]=first_visible
            for label,target in review_targets.items():
                # Matroska can assign one millisecond PTS to several captured
                # frames. Playback presents the last frame at that timestamp.
                if target is not None and at>=target and (label not in review_frames or review_frames[label]["at"]==round(at,6)):
                    file="review-"+label+".png";Image.fromarray(image).save(destination/file)
                    review_frames[label]={"at":round(at,6),"file":file,"sha256":sha(destination/file)}
            if first_visible is not None and ((not opening_saved and at>=first_visible+2) or (opening_saved and round(at,6)==round(opening_at,6))):
                Image.fromarray(image).save(destination/"opening.png");opening_saved=True;opening_at=at
            if (not completed_saved and at>=max(0,header["duration"]-1)) or (completed_saved and round(at,6)==completed_at):
                Image.fromarray(image).save(destination/"completed.png");completed_saved=True;completed_at=round(at,6)
            keyframe = last is None or at-last_keyframe>=10
            if not keyframe and digest==last_digest: continue
            changes = np.any(image!=last,axis=2) if last is not None else np.ones((height,width),dtype=bool)
            if not keyframe and not changes.any(): continue
            if keyframe:
                areas=[(0,0,width,height)];last_keyframe=at
            else:
                areas=rectangles(changes)
            patches=[]
            for left,top,right,bottom in areas:
                w,h=right-left,bottom-top
                if w>atlas_size or h>atlas_size: raise ValueError("Native frame exceeds atlas size")
                data=image[top:bottom,left:right].tobytes()
                key=(w,h,hashlib.sha256(data).digest())
                saved=tiles.get(key)
                if saved is not None:
                    patches.append([*saved,left,top]);reused_patches+=1
                    canvas[top:bottom,left:right]=image[top:bottom,left:right]
                    continue
                if x+w>atlas_size: x=0;y+=shelf;shelf=0
                if y+h>atlas_size: flush()
                tile=Image.frombytes("RGB",(w,h),data)
                atlas.paste(tile,(x,y));atlas_used=True
                canvas[top:bottom,left:right]=image[top:bottom,left:right]
                patches.append([atlas_index,x,y,w,h,left,top])
                tiles[key]=[atlas_index,x,y,w,h]
                x+=w;shelf=max(shelf,h)
            if not np.array_equal(canvas,image): raise ValueError("Native pixel reconstruction differs from independent master")
            frames.append({"at":round(at,6),"patches":patches,"keyframe":keyframe,"sha256":digest})
            if keyframe: checks.append({"at":round(at,6),"rgbSha256":digest})
            last=image.copy()
            last_digest=digest
        flush()
    finally:
        decoder.stdout.close();decoder.terminate();decoder.wait()
    if not frames or not opening_saved or not completed_saved:
        raise ValueError("Actual native opening or completed frame was not captured")
    gaps=[b-a for a,b in zip(times,times[1:])]
    index={"schemaVersion":3,"width":width,"height":height,"fps":60,"duration":header["duration"],
        "profile":profile,"sheets":sheets,"frames":frames,"displayStart":first_visible,"openingAt":round(opening_at,6),"completedAt":completed_at,
        "reviewFrames":review_frames,"clock":{"nativeEpoch":clock["epoch"],"timestamps":"actual X11 capture presentation timestamps relative to native clock"},
        "verification":{"pixelExact":True,"comparedChangedFrames":len(frames),"capturedFrames":capture_frames,
            "largestCaptureGapSeconds":max(gaps,default=0),"checkpoints":checks,"masterSha256":sha(master),
            "master":master.name,"rgbFramesHashed":capture_frames,"reusedIdenticalPatches":reused_patches,"method":"OpenSSL SHA-256 of every decoded native RGB frame; changed RGB bytes compared to composed lossless PNG deltas; byte-identical patches share atlas pixels"}}
    (destination/"index.json").write_text(json.dumps(index,separators=(",",":"))+"\n")
    status_path=cast.with_suffix(".json")
    status=json.loads(status_path.read_text());status["pixels"]={"directory":destination.name,"indexSha256":sha(destination/"index.json"),"pixelExact":True}
    status_path.write_text(json.dumps(status,indent=2)+"\n")
