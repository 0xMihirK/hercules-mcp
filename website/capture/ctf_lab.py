"""Construct and solve the local file-forensics fixture; standard library only."""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import random
import struct
import zipfile
import zlib

FLAG = b"HERCULES{evidence_before_answers}"
FLAG_DIGEST = hashlib.sha256(FLAG).hexdigest()
ROUTE = [13, 14, 17, 19, 7]
KEY = bytes(65 + value for value in ROUTE)

def chunk(kind, data):
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)

def xor(data, key):
    return bytes(value ^ key[index % len(key)] for index, value in enumerate(data))

def create_challenge(home):
    rng = random.Random(731)
    pixels = b"".join(b"\x00" + bytes((x * 37 ^ y * 71 ^ rng.randrange(64)) % 256 for x in range(64)) for y in range(64))
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 64, 64, 8, 0, 0, 0, 0))
    png += chunk(b"tEXt", b"Challenge\x00route=13,14,17,19,7") + chunk(b"IDAT", zlib.compress(pixels)) + chunk(b"IEND", b"")
    entries = {
        "README.md": "# Signal route\n\nThe PNG's route numbers use a zero-based alphabet.\nConvert them to ASCII letters to recover the repeating XOR key.\nXOR payload.bin with that key, then base64-decode the result.\nOnly a flag matching manifest.json's SHA-256 is accepted.\n",
        "decoy.txt": "HERCULES{not_the_flag}\n",
        "manifest.json": json.dumps({"payload": "payload.bin", "sha256": FLAG_DIGEST}, indent=2),
        "payload.bin": xor(base64.b64encode(FLAG), KEY),
    }
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as package:
        for name, value in entries.items():
            info = zipfile.ZipInfo(name, date_time=(2026, 10, 7, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            package.writestr(info, value)
    (home / "challenge.png").write_bytes(png + archive.getvalue())
    (home / "ctf_lab.py").write_text(Path(__file__).read_text())

def archive_offset(image):
    return image.read_bytes().index(b"PK\x03\x04")

def read_route(image):
    raw = image.read_bytes()
    offset = 8
    while offset + 12 <= len(raw):
        size = struct.unpack(">I", raw[offset:offset + 4])[0]
        kind, data = raw[offset + 4:offset + 8], raw[offset + 8:offset + 8 + size]
        if kind == b"tEXt" and data.startswith(b"Challenge\x00route="):
            return [int(value) for value in data.split(b"=", 1)[1].split(b",")]
        offset += size + 12
    raise ValueError("PNG route clue missing")

def extract(image, out):
    out.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(image) as archive:
        names = archive.namelist()
        if set(names) != {"README.md", "decoy.txt", "manifest.json", "payload.bin"}:
            raise ValueError("Unexpected challenge archive contents")
        for name in names:
            (out / name).write_bytes(archive.read(name))
    print(f"Appended ZIP begins at byte {archive_offset(image)}")
    print("Extracted: " + ", ".join(names))
    print("Decoy candidate: " + (out / "decoy.txt").read_text().strip())

def solve(image, out):
    route = read_route(image)
    key = bytes(65 + value for value in route)
    decoded = base64.b64decode(xor((out / "payload.bin").read_bytes(), key), validate=True)
    manifest = json.loads((out / "manifest.json").read_text())
    digest = hashlib.sha256(decoded).hexdigest()
    if digest != manifest["sha256"]:
        raise ValueError("Decoded flag failed SHA-256 verification")
    decoy = (out / "decoy.txt").read_bytes().strip()
    result = {"archive_offset": archive_offset(image), "route": route, "key": key.decode(), "encoding": "repeating-key XOR, then base64", "flag": decoded.decode(), "sha256": digest, "checksum_match": True, "decoy_sha256_match": hashlib.sha256(decoy).hexdigest() == manifest["sha256"]}
    (out / "solution.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("extract", "solve"))
    parser.add_argument("image", type=Path)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    (extract if args.mode == "extract" else solve)(args.image, args.out)
