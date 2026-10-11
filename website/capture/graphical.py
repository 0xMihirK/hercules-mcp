"""Capture actual XTerm pixels, with the same PTY output retained separately.

The recorder is a transparent PTY interposer. Terminal queries are answered by
XTerm itself, never by this harness. A start gate prevents losing the entrance.
"""
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time

from pixels import pack
from readiness import wait_first_frame

OUT = Path("/out")
PROFILES = json.loads(Path("/capture/profiles.json").read_text())
HARNESS_HASHES={str(path.relative_to(Path("/capture"))):__import__("hashlib").sha256(path.read_bytes()).hexdigest() for path in [Path("/capture/graphical.py"),Path("/capture/readiness.py"),Path("/capture/record.py"),Path("/capture/pixels.py"),Path("/capture/profiles.json"),Path("/capture/labs/provider.py"),Path("/capture/labs/protocol.py")]}


def command(*args):
    return subprocess.check_output(args, text=True).strip()


def child():
    while not (OUT / "capture-ready").exists():
        time.sleep(.01)
    try:
        result = subprocess.run([sys.executable, "/capture/record.py", *sys.argv[2:]])
        (OUT / "terminal-exit.json").write_text(json.dumps({"code": result.returncode}))
    except BaseException as error:
        (OUT / "terminal-exit.json").write_text(json.dumps({"error": str(error)}))
        raise


def main():
    arguments = sys.argv[1:]
    client, scenario = arguments[:2]
    cols, rows = (int(arguments[arguments.index(key)+1]) for key in ("--cols", "--rows"))
    if [cols, rows] not in PROFILES["clients"][client]["geometries"]:
        raise ValueError("Geometry is not an explicit native capture profile")
    name = f"{client}-{scenario}-{cols}"
    # Keep live lossless capture on the container filesystem. Windows bind
    # mounts and OneDrive must not stall sampling; retain the master afterwards.
    master = Path("/tmp") / (name + "-master.mkv")
    environment = {**os.environ, "DISPLAY": ":99"}
    log = (OUT / "graphical.log").open("w")
    xvfb = subprocess.Popen(["Xvfb", ":99", "-screen", "0", "2048x1200x24", "-noreset", "-nolisten", "tcp"], stdout=log, stderr=log)
    terminal = capture = None
    try:
        display_deadline=time.monotonic()+30
        while time.monotonic()<display_deadline:
            if xvfb.poll() is not None:
                raise RuntimeError("The virtual display exited before readiness")
            if subprocess.run(["xdpyinfo"], env=environment, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
                break
            time.sleep(.05)
        else:
            raise RuntimeError("The virtual display did not become ready")
        font, palette = PROFILES["font"], PROFILES["terminal"]
        fallback=font["fallback"]
        if command("dpkg-query", "-W", "-f=${Version}", fallback["package"])!=fallback["version"] or __import__("hashlib").sha256(Path(fallback["file"]).read_bytes()).hexdigest()!=fallback["sha256"]:
            raise ValueError("Native symbol fallback differs from pinned capture profile")
        if fallback["family"] not in command("fc-list", ":charset=23f5", "family"):
            raise ValueError("Native progress glyph is absent from terminal fonts")
        emoji=font["emojiFallback"]
        if command("dpkg-query","-W","-f=${Version}",emoji["package"])!=emoji["version"] or __import__("hashlib").sha256(Path(emoji["file"]).read_bytes()).hexdigest()!=emoji["sha256"] or emoji["family"] not in command("fc-list",":charset=1f50c","family"):
            raise ValueError("Native emoji fallback differs from pinned capture profile")
        if command("xterm","-version")!=palette["version"]:
            raise ValueError("Graphical terminal version differs from pinned capture profile")
        terminal = subprocess.Popen(["xterm", "-hold", "-title", "Hercules native capture", "-geometry", f"{cols}x{rows}+0+0",
            "-fa", font["family"], "-fs", str(font["size"]), "-fg", palette["foreground"], "-bg", palette["background"],
            "-sh", str(palette["scaleHeight"]),
            "-b", "0", "-bw", "0", "+sb", "-xrm", "XTerm*allowWindowOps: true", "-xrm", "XTerm*allowFontOps: false",
            "-e", sys.executable, "/capture/graphical.py", "--child", *arguments], env=environment, stdout=log, stderr=log)
        for _ in range(100):
            tree = subprocess.check_output(["xwininfo", "-root", "-tree"], env=environment, text=True)
            found = re.search(r'(0x[0-9a-f]+) "Hercules native capture"', tree)
            if found:
                break
            time.sleep(.05)
        else:
            raise RuntimeError("The graphical terminal did not map")
        # XTerm creates a 1×1 window before Xft font metrics and geometry are
        # ready. A title alone proves neither mapping nor drawable dimensions.
        for _ in range(100):
            info = subprocess.check_output(["xwininfo", "-id", found[1]], env=environment, text=True)
            dimensions = {key: int(re.search(rf"{key}:\s+(\d+)", info)[1]) for key in ("Width", "Height")}
            if "IsViewable" in info and dimensions["Width"]>=cols*6 and dimensions["Height"]>=rows*12:
                break
            time.sleep(.05)
        else:
            raise RuntimeError("Native font geometry did not become drawable")
        x, y = (int(re.search(rf"Absolute upper-left {axis}:\s+(-?\d+)", info)[1]) for axis in ("X", "Y"))
        width, height = dimensions["Width"], dimensions["Height"]
        progress=Path("/tmp/capture-progress.txt")
        capture = subprocess.Popen(["ffmpeg", "-nostdin", "-y", "-loglevel", "warning", "-progress", str(progress), "-stats_period", "0.1", "-f", "x11grab", "-draw_mouse", "0",
            "-framerate", "60", "-video_size", f"{width}x{height}", "-use_wallclock_as_timestamps", "1",
            "-i", f":99.0+{x},{y}", "-copyts", "-vsync", "0", "-c:v", "libx264rgb", "-crf", "0", "-preset", "ultrafast", "-tune", "zerolatency", "-g", "60",
            "-pix_fmt", "bgr0", "-threads", "2", "-avoid_negative_ts", "disabled", str(master)], env=environment, stdout=log, stderr=log)
        first_frames=wait_first_frame(capture,progress)
        (OUT / "capture-readiness.json").write_text(json.dumps({"encodedFramesBeforeRelease":first_frames,"method":"FFmpeg encoded an actual graphical frame before the native recorder was released"})+"\n")
        (OUT / "capture-ready").touch()
        timeout = int(arguments[arguments.index("--duration")+1])+90
        deadline = time.monotonic()+timeout
        while not (OUT / "terminal-exit.json").exists():
            if time.monotonic()>deadline or terminal.poll() is not None or capture.poll() is not None:
                raise RuntimeError("Native terminal capture stopped before completion")
            time.sleep(.1)
        capture.send_signal(signal.SIGINT)
        capture.wait(timeout=30)
        capture = None
        exit_status = json.loads((OUT / "terminal-exit.json").read_text())
        if exit_status.get("code") != 0:
            raise RuntimeError(f"Native recorder failed: {exit_status}")
        font_path = Path("/usr/local/share/fonts/capture/CascadiaMono.ttf")
        profile = {**PROFILES["clients"][client], "font":font, "terminal":palette,
            "emulatorVersion":command("xterm", "-version"), "ffmpegVersion":command("ffmpeg", "-version").splitlines()[0],
            "xvfbPackage":command("dpkg-query", "-W", "-f=${Version}", "xvfb"),
            "measuredCellWidth":width/cols, "measuredCellHeight":height/rows,
            "pixelWidth":width, "pixelHeight":height, "fontSha256":__import__("hashlib").sha256(font_path.read_bytes()).hexdigest(),
            "masterEncoding":"libx264rgb CRF 0; lossless RGB, no chroma subsampling",
            "captureImageId":os.environ["CAPTURE_IMAGE_ID"],
            "graphicalReadiness":{"encodedFramesBeforeRelease":first_frames,"method":"FFmpeg first-frame handshake"},
            "harnessSha256":HARNESS_HASHES,
            "capabilityResponses":"Forwarded unchanged from actual XTerm; retained as input events in raw cast"}
        # Retain the untouched master even when packing/validation fails.
        (OUT / "capture-profile.json").write_text(json.dumps(profile,indent=2)+"\n")
        __import__("shutil").copyfile(master, OUT / master.name)
        pack(master, OUT / (name+".cast"), profile)
        print(json.dumps({"graphicalCapture":name,"pixels":[width,height],"emulator":profile["emulatorVersion"]}), flush=True)
    finally:
        for process in (capture, terminal, xvfb):
            if process and process.poll() is None:
                process.terminate()
                try: process.wait(timeout=10)
                except subprocess.TimeoutExpired: process.kill();process.wait()
        log.close()


if __name__ == "__main__":
    child() if sys.argv[1:2] == ["--child"] else main()
