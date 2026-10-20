"""Create evidence inputs, never a solver or synthetic scanner output."""
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import zipfile
import zlib

FLAG = b"HERCULES{packet_to_carrier_to_verified_evidence}"


def create_inputs(destination: Path):
    destination.mkdir(parents=True, exist_ok=True)
    challenge = destination / "challenge"
    challenge.mkdir(exist_ok=True)
    plaintext = zlib.compress(FLAG)
    with tempfile.TemporaryDirectory() as scratch:
        source = Path(scratch) / "plain.bin"
        source.write_bytes(plaintext)
        encrypted = subprocess.check_output(["openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-iter", "10000", "-salt", "-in", str(source), "-pass", "pass:north-gate-17"])
    archive = io.BytesIO()
    manifest = {"flag_sha256": hashlib.sha256(FLAG).hexdigest(), "cipher": "AES-256-CBC", "kdf": "PBKDF2", "iterations": 10000, "compression": "zlib", "password_rule": "Join the three route fragments from the capture with hyphens, in packet order."}
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
        bundle.writestr("manifest.json", json.dumps(manifest, indent=2))
        bundle.writestr("payload.enc", encrypted)
        bundle.writestr("decoy.txt", "HERCULES{the_first_flag_is_not_the_answer}\n")

    def chunk(kind, data):
        return struct.pack("!I", len(data)) + kind + data + struct.pack("!I", zlib.crc32(kind + data) & 0xffffffff)

    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack("!IIBBBBB", 32, 32, 8, 2, 0, 0, 0))
    png += chunk(b"tEXt", b"Comment\x00A valid image can have more than one ending. The route lives in the packets.")
    png += chunk(b"IDAT", zlib.compress((b"\x00" + b"\x22\x26\x29" * 32) * 32)) + chunk(b"IEND", b"")
    (challenge / "carrier.png").write_bytes(png + archive.getvalue())
    # Minimal real Ethernet/IPv4/UDP PCAP with a clue distributed over packets.
    pcap = struct.pack("<IHHIIII", 0xa1b2c3d4, 2, 4, 0, 0, 65535, 1)
    for index, fragment in enumerate(("north", "gate", "17")):
        payload = json.dumps({"sequence": index + 1, "route_fragment": fragment, "carrier": "carrier.png"}).encode()
        ethernet = b"\x02\x00\x00\x00\x00\x02\x02\x00\x00\x00\x00\x01\x08\x00"
        ip = b"\x45\x00" + struct.pack("!H", 28 + len(payload)) + b"\x00\x01\x00\x00\x40\x11\x00\x00\xac\x1e\x2a\x02\xac\x1e\x2a\x0a"
        checksum = sum(struct.unpack("!10H", ip))
        while checksum >> 16:
            checksum = (checksum & 0xffff) + (checksum >> 16)
        ip = ip[:10] + struct.pack("!H", (~checksum) & 0xffff) + ip[12:]
        udp = struct.pack("!HHHH", 45000, 9000, 8 + len(payload), 0)
        packet = ethernet + ip + udp + payload
        pcap += struct.pack("<IIII", 1791350000 + index, 0, len(packet), len(packet)) + packet
    (challenge / "route.pcap").write_bytes(pcap)
    (destination / "scope.md").write_text("# Capture lab scope\n\nOnly the lab fixture on the internal Docker network is authorized. No public targets. Synthetic inputs; real tools.\n\nStart Hercules explicitly, verify evidence, write a report, and stop your owned runtime.\n", encoding="utf-8")
    (destination / "paths.txt").write_text("robots.txt\ndebug\nadmin\nbackup\nhealth\nctf\napi/draft\n", encoding="utf-8")
    # Files for paging and reconciliation are authored inputs, not tool results.
    (destination / "review-log.ndjson").write_text("".join(json.dumps({"sequence": n, "source": "lab-input", "path": "/health" if n % 20 else "/debug", "status": 200}) + "\n" for n in range(160)), encoding="utf-8")
    (destination / "inputs.sha256").write_text("\n".join(hashlib.sha256(p.read_bytes()).hexdigest() + "  " + p.relative_to(destination).as_posix() for p in sorted(destination.rglob("*")) if p.is_file()) + "\n", encoding="utf-8")


if __name__ == "__main__":
    import sys
    create_inputs(Path(sys.argv[1]))
