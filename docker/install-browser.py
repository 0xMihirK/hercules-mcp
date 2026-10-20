"""Install locked native browser assets and CLI documentation; no npm runtime."""

import base64
import hashlib
import json
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path, PurePosixPath


def download(url, destination, expected, algorithm="sha256"):
    subprocess.run(["curl", "-fL", "--retry", "4", "--connect-timeout", "30", "--max-time", "600", url, "-o", str(destination)], check=True)
    with destination.open("rb") as stream:
        actual = hashlib.file_digest(stream, algorithm).digest()
    if actual != expected:
        raise ValueError(f"Checksum mismatch for {destination.name}")


def extract_files(archive, destination, select):
    with tarfile.open(archive) as bundle:
        for member in bundle:
            relative = select(PurePosixPath(member.name))
            if relative is None or member.isdir():
                continue
            if not member.isfile() or relative.is_absolute() or ".." in relative.parts:
                raise ValueError(f"Unsafe archive member: {member.name}")
            target = destination.joinpath(*relative.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with bundle.extractfile(member) as source, target.open("xb") as output:
                shutil.copyfileobj(source, output)


def main(platform):
    lock = json.loads(Path("/opt/hercules/browser-assets.json").read_text())
    assets = lock[platform]
    destination = Path("/opt/hercules/browser")
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="hercules-browser-") as scratch:
        scratch = Path(scratch)
        archive = scratch / "obscura.tar.gz"
        download(
            f"https://github.com/h4ckf0r0day/obscura/releases/download/v{lock['obscura_version']}/{assets['obscura_asset']}",
            archive, bytes.fromhex(assets["obscura_sha256"]),
        )
        extract_files(archive, destination, lambda p: PurePosixPath(p.name) if p.name in {"obscura", "obscura-worker"} else None)
        download(
            f"https://github.com/vercel-labs/agent-browser/releases/download/v{lock['controller_version']}/{assets['controller_asset']}",
            destination / "agent-browser", bytes.fromhex(assets["controller_sha256"]),
        )
        archive = scratch / "skills.tgz"
        download(
            f"https://registry.npmjs.org/agent-browser/-/agent-browser-{lock['controller_version']}.tgz",
            archive, base64.b64decode(lock["controller_skills_integrity"].removeprefix("sha512-")), "sha512",
        )
        extract_files(archive, destination, lambda p: PurePosixPath(*p.parts[1:]) if len(p.parts) > 1 and p.parts[0] == "package" and (p.parts[1] in {"skills", "skill-data", "LICENSE"}) else None)
    for name in ("obscura", "obscura-worker", "agent-browser"):
        (destination / name).chmod(0o755)
        Path("/usr/local/bin", name).symlink_to(destination / name)
    subprocess.run(["obscura", "--version"], check=True)
    subprocess.run(["agent-browser", "skills", "get", "core"], check=True, stdout=subprocess.DEVNULL)


if __name__ == "__main__":
    main(sys.argv[1])
