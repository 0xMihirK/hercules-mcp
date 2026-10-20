"""Repack retained native masters without rerunning or altering terminal output."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time

from pixels import pack


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("directories",nargs="+",type=Path)
    args=parser.parse_args()
    results=Path(__file__).resolve().parents[1]/"test-results/labs"
    for directory in args.directories:
        directory=directory.resolve()
        if directory.parent!=results.resolve() or directory.is_symlink():
            raise ValueError("Repacking is restricted to owned lab result directories")
        for cast in (directory/"recordings").glob("*.cast"):
            pixels=cast.with_name(cast.stem+"-pixels")
            index=json.loads((pixels/"index.json").read_text())
            with cast.open(encoding="utf-8") as source:
                header=json.loads(source.readline())
            if index["width"]<header["width"]*6 or index["height"]<header["height"]*12:
                raise ValueError("The retained master has invalid native geometry; recapture it")
            master=cast.parent/index["verification"]["master"]
            profile=index["profile"]
            codec=subprocess.check_output(["ffprobe","-v","error","-select_streams","v:0","-show_entries","stream=codec_name","-of","default=nw=1:nk=1",str(master)],text=True).strip()
            profile["masterEncoding"]="FFV1 lossless RGB" if codec=="ffv1" else "libx264rgb CRF 0; lossless RGB, no chroma subsampling"
            profile["postprocessorSha256"]=hashlib.sha256(Path(__file__).with_name("pixels.py").read_bytes()).hexdigest()
            archived=pixels.with_name(pixels.name+"-previous-"+str(time.time_ns()))
            if archived.parent!=pixels.parent or pixels.is_symlink():
                raise ValueError("Invalid native-pixel archive target")
            pixels.rename(archived)
            try:
                pack(master,cast,profile)
            except BaseException:
                # Retain a failed pack for diagnosis and restore the validated
                # original bundle so an interrupted repack never destroys it.
                if pixels.exists():pixels.rename(pixels.with_name(pixels.name+"-failed-"+str(time.time_ns())))
                archived.rename(pixels)
                raise
            print(json.dumps({"repacked":str(cast),"previous":str(archived)}),flush=True)


if __name__=="__main__":main()
