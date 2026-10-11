"""Release the native recorder only after FFmpeg encodes an actual frame."""
import re
import time


def wait_first_frame(process, progress, timeout=30):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        if process.poll() is not None:
            raise RuntimeError("Lossless graphical capture stopped before its first frame")
        if progress.is_file():
            counts=re.findall(r"^frame=(\d+)$",progress.read_text(),re.MULTILINE)
            if counts and int(counts[-1])>0:
                return int(counts[-1])
        time.sleep(.05)
    raise RuntimeError("Lossless graphical capture did not encode its first frame")
