"""Safe, one-time extraction of host-cached wordlist archives."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import tarfile
import urllib.request
import uuid
import zipfile
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

from hercules.core.tool_catalog import normalize_capabilities, required_wordlists

# SecLists does not publish a release archive checksum. Hercules pins the exact
# audited commit archive and its locally verified digest.
WORDLIST_SOURCES: dict[str, dict[str, str]] = {
    "SecLists.zip": {
        "url": (
            "https://codeload.github.com/danielmiessler/SecLists/zip/"
            "6c7d5449fe944e35e8593b3fe45b433228239bf4"
        ),
        "sha256": "68865ee09cc32b43b00c5e29287e07ea6ea62eed2db8bbc71ae156f00a51993c",
    },
    "rockyou.txt.tar.gz": {
        "url": (
            "https://raw.githubusercontent.com/danielmiessler/SecLists/"
            "6c7d5449fe944e35e8593b3fe45b433228239bf4/"
            "Passwords/Leaked-Databases/rockyou.txt.tar.gz"
        ),
        "sha256": "47c070a029bcdb4cbd0e02c69fed136ef46dce4048ddbadf177daa5e885b8172",
    },
}

WORDLIST_FILES = {
    "seclists": "SecLists.zip",
    "rockyou": "rockyou.txt.tar.gz",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_wordlist_archive(filename: str, path: Path) -> bool:
    """Validate archive structure and the exact pinned SHA-256 digest."""
    source = WORDLIST_SOURCES.get(filename)
    if source is None or not path.is_file() or path.stat().st_size == 0:
        return False
    if filename.endswith(".zip") and not zipfile.is_zipfile(path):
        return False
    if filename.endswith(".tar.gz") and not tarfile.is_tarfile(path):
        return False
    return sha256_file(path) == source["sha256"]


def _download_wordlist(wordlists_dir: Path, filename: str) -> None:
    source = WORDLIST_SOURCES[filename]
    parsed = urlsplit(source["url"])
    if parsed.scheme != "https" or parsed.hostname not in {
        "codeload.github.com",
        "raw.githubusercontent.com",
    }:
        raise ValueError("wordlist source is not an approved pinned HTTPS URL")
    destination = wordlists_dir / filename
    if destination.resolve().parent != wordlists_dir.resolve():
        raise ValueError("wordlist destination escapes its managed directory")
    temporary = destination.with_name(f".{filename}.{uuid.uuid4().hex}.download")
    try:
        request = urllib.request.Request(
            source["url"],
            headers={"User-Agent": "hercules-mcp/1"},
        )
        with (
            urllib.request.urlopen(request, timeout=180) as response,  # nosec B310
            temporary.open("xb") as output,
        ):
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
        if not validate_wordlist_archive(filename, temporary):
            raise ValueError(f"{filename} failed pinned checksum/format validation")
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def _within(root: Path, candidate: Path) -> bool:
    try:
        candidate.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _filesystem_path(path: Path) -> str:
    """Return a Windows extended-length path when long archive members need it."""
    resolved = str(path.resolve())
    if os.name == "nt" and not resolved.startswith("\\\\?\\"):
        return "\\\\?\\" + resolved
    return resolved


def _validate_archive_names(root: Path, names: list[str]) -> None:
    for name in names:
        if not _within(root, root / name):
            raise ValueError(f"archive member escapes extraction directory: {name!r}")


@contextmanager
def _extraction_lock(wordlists_dir: Path) -> Iterator[None]:
    """Serialize setup/server extraction across processes on all host OSes."""
    lock_path = wordlists_dir / ".hercules-extraction.lock"
    with lock_path.open("a+b") as lock:
        lock.seek(0, os.SEEK_END)
        if lock.tell() == 0:
            lock.write(b"\0")
            lock.flush()
        lock.seek(0)
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(lock.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def _read_ready_manifest(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_ready_manifest(path: Path, payload: dict) -> None:
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _seclists_ready(target: Path, marker: Path, archive: Path) -> bool:
    payload = _read_ready_manifest(marker)
    return bool(
        payload.get("schema_version") == 1
        and payload.get("archive_sha256") == WORDLIST_SOURCES["SecLists.zip"]["sha256"]
        and validate_wordlist_archive("SecLists.zip", archive)
        and (target / "Discovery").is_dir()
        and (target / "Passwords").is_dir()
    )


def _rockyou_ready(target: Path, marker: Path, archive: Path) -> bool:
    payload = _read_ready_manifest(marker)
    try:
        size = target.stat().st_size
    except OSError:
        return False
    return bool(
        size > 0
        and payload.get("schema_version") == 1
        and payload.get("archive_sha256")
        == WORDLIST_SOURCES["rockyou.txt.tar.gz"]["sha256"]
        and payload.get("extracted_bytes") == size
        and validate_wordlist_archive("rockyou.txt.tar.gz", archive)
    )


def _can_adopt_existing_seclists(target: Path, archive_path: Path) -> bool:
    """Verify a legacy extraction against the pinned archive's file metadata."""
    if not validate_wordlist_archive("SecLists.zip", archive_path):
        return False
    try:
        with zipfile.ZipFile(archive_path) as archive:
            members = [member for member in archive.infolist() if not member.is_dir()]
            if len(members) < 100:
                return False
            roots = {
                Path(member.filename.replace("\\", "/")).parts[0]
                for member in members
                if Path(member.filename.replace("\\", "/")).parts
            }
            if len(roots) != 1:
                return False
            root_name = next(iter(roots))
            for member in members:
                mode = (member.external_attr >> 16) & 0xFFFF
                if stat.S_ISLNK(mode):
                    return False
                parts = Path(member.filename.replace("\\", "/")).parts
                if not parts or parts[0] != root_name:
                    return False
                candidate = target.joinpath(*parts[1:])
                info = os.lstat(_filesystem_path(candidate))
                attributes = getattr(info, "st_file_attributes", 0)
                reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
                if (
                    not stat.S_ISREG(info.st_mode)
                    or stat.S_ISLNK(info.st_mode)
                    or attributes & reparse_flag
                    or info.st_size != member.file_size
                ):
                    return False
    except (OSError, ValueError, zipfile.BadZipFile):
        return False
    return True


def _can_adopt_existing_rockyou(target: Path, archive_path: Path) -> bool:
    """Verify a legacy rockyou extraction against its pinned tar member size."""
    if not validate_wordlist_archive("rockyou.txt.tar.gz", archive_path):
        return False
    try:
        target_info = os.lstat(_filesystem_path(target))
        if not stat.S_ISREG(target_info.st_mode) or stat.S_ISLNK(target_info.st_mode):
            return False
        with tarfile.open(archive_path, "r:gz") as archive:
            members = [
                member
                for member in archive.getmembers()
                if member.isfile()
                and not member.issym()
                and not member.islnk()
                and Path(member.name).name == "rockyou.txt"
            ]
        return len(members) == 1 and members[0].size == target_info.st_size
    except (OSError, ValueError, tarfile.TarError):
        return False


def wordlists_ready(wordlists_dir: Path) -> bool:
    """Verify both pinned archives and their extraction manifests."""
    return _seclists_ready(
        wordlists_dir / "SecLists",
        wordlists_dir / "SecLists" / ".hercules-ready",
        wordlists_dir / "SecLists.zip",
    ) and _rockyou_ready(
        wordlists_dir / "rockyou.txt",
        wordlists_dir / ".rockyou.hercules-ready.json",
        wordlists_dir / "rockyou.txt.tar.gz",
    )


def _extract_zip_regular_files(archive: zipfile.ZipFile, destination: Path) -> None:
    _validate_archive_names(destination, archive.namelist())
    for member in archive.infolist():
        mode = (member.external_attr >> 16) & 0xFFFF
        if stat.S_ISLNK(mode):
            raise ValueError(f"zip archive contains a symbolic link: {member.filename!r}")
        output = destination / member.filename
        if member.is_dir():
            os.makedirs(_filesystem_path(output), exist_ok=True)
            continue
        os.makedirs(_filesystem_path(output.parent), exist_ok=True)
        with (
            archive.open(member, "r") as source,
            open(_filesystem_path(output), "xb") as target,
        ):
            shutil.copyfileobj(source, target)


def ensure_extracted_wordlists(wordlists_dir: Path) -> dict[str, Path]:
    """
    Extract SecLists and rockyou once into stable host paths.

    Returns only successfully prepared paths. Incomplete temporary directories
    are removed, and completed data is atomically moved into place.
    """
    wordlists_dir.mkdir(parents=True, exist_ok=True)
    with _extraction_lock(wordlists_dir):
        prepared: dict[str, Path] = {}

        seclists_archive = wordlists_dir / "SecLists.zip"
        seclists_target = wordlists_dir / "SecLists"
        seclists_marker = seclists_target / ".hercules-ready"
        if (
            not _seclists_ready(seclists_target, seclists_marker, seclists_archive)
            and _can_adopt_existing_seclists(seclists_target, seclists_archive)
        ):
            _write_ready_manifest(
                seclists_marker,
                {
                    "schema_version": 1,
                    "archive_sha256": WORDLIST_SOURCES["SecLists.zip"]["sha256"],
                    "prepared_at": datetime.now(UTC).isoformat(),
                    "migration": "verified_legacy_extraction",
                },
            )
        if _seclists_ready(seclists_target, seclists_marker, seclists_archive):
            prepared["seclists"] = seclists_target
        elif validate_wordlist_archive("SecLists.zip", seclists_archive):
            if seclists_target.exists():
                shutil.rmtree(_filesystem_path(seclists_target))
            temp_root = wordlists_dir / f".extracting-seclists-{uuid.uuid4().hex}"
            try:
                temp_root.mkdir()
                with zipfile.ZipFile(seclists_archive) as archive:
                    _extract_zip_regular_files(archive, temp_root)
                candidates = [p for p in temp_root.iterdir() if p.is_dir()]
                if len(candidates) != 1:
                    raise ValueError("SecLists archive did not contain one root directory")
                if os.name == "nt":
                    shutil.move(
                        _filesystem_path(candidates[0]),
                        _filesystem_path(seclists_target),
                    )
                else:
                    os.replace(candidates[0], seclists_target)
                _write_ready_manifest(
                    seclists_marker,
                    {
                        "schema_version": 1,
                        "archive_sha256": WORDLIST_SOURCES["SecLists.zip"]["sha256"],
                        "prepared_at": datetime.now(UTC).isoformat(),
                    },
                )
                prepared["seclists"] = seclists_target
            finally:
                if temp_root.exists():
                    shutil.rmtree(_filesystem_path(temp_root))

        rockyou_target = wordlists_dir / "rockyou.txt"
        rockyou_archive = wordlists_dir / "rockyou.txt.tar.gz"
        rockyou_marker = wordlists_dir / ".rockyou.hercules-ready.json"
        if (
            not _rockyou_ready(rockyou_target, rockyou_marker, rockyou_archive)
            and _can_adopt_existing_rockyou(rockyou_target, rockyou_archive)
        ):
            _write_ready_manifest(
                rockyou_marker,
                {
                    "schema_version": 1,
                    "archive_sha256": WORDLIST_SOURCES[
                        "rockyou.txt.tar.gz"
                    ]["sha256"],
                    "extracted_bytes": rockyou_target.stat().st_size,
                    "prepared_at": datetime.now(UTC).isoformat(),
                    "migration": "verified_legacy_extraction",
                },
            )
        if _rockyou_ready(rockyou_target, rockyou_marker, rockyou_archive):
            prepared["rockyou"] = rockyou_target
        elif validate_wordlist_archive("rockyou.txt.tar.gz", rockyou_archive):
            temp_target = wordlists_dir / f".rockyou-{uuid.uuid4().hex}.tmp"
            try:
                with tarfile.open(rockyou_archive, "r:gz") as archive:
                    members = [
                        member
                        for member in archive.getmembers()
                        if member.isfile()
                        and not member.issym()
                        and not member.islnk()
                        and Path(member.name).name == "rockyou.txt"
                    ]
                    if len(members) != 1:
                        raise ValueError("rockyou archive did not contain one rockyou.txt")
                    source = archive.extractfile(members[0])
                    if source is None:
                        raise ValueError("rockyou archive member could not be read")
                    with temp_target.open("xb") as output:
                        shutil.copyfileobj(source, output)
                extracted_bytes = temp_target.stat().st_size
                if extracted_bytes == 0:
                    raise ValueError("extracted rockyou.txt was empty")
                os.replace(temp_target, rockyou_target)
                _write_ready_manifest(
                    rockyou_marker,
                    {
                        "schema_version": 1,
                        "archive_sha256": WORDLIST_SOURCES[
                            "rockyou.txt.tar.gz"
                        ]["sha256"],
                        "extracted_bytes": extracted_bytes,
                        "prepared_at": datetime.now(UTC).isoformat(),
                    },
                )
                prepared["rockyou"] = rockyou_target
            finally:
                if temp_target.exists():
                    temp_target.unlink()

        return prepared


def provision_wordlists(
    wordlists_dir: Path,
    capabilities: Iterable[str],
    *,
    dry_run: bool = False,
) -> dict[str, object]:
    """Provision only the checksum-pinned assets required by a capability set."""
    selected = normalize_capabilities(capabilities)
    required = required_wordlists(selected)
    if not required:
        return {
            "required": [],
            "ready": True,
            "status": "not_required",
            "paths": {},
        }
    root = Path(wordlists_dir).expanduser().resolve()
    if dry_run:
        return {
            "required": list(required),
            "ready": True,
            "status": "dry_run",
            "paths": {},
        }
    root.mkdir(parents=True, exist_ok=True)
    for logical_name in required:
        filename = WORDLIST_FILES[logical_name]
        destination = root / filename
        if not validate_wordlist_archive(filename, destination):
            destination.unlink(missing_ok=True)
            _download_wordlist(root, filename)
    prepared = ensure_extracted_wordlists(root)
    missing = sorted(set(required) - set(prepared))
    if missing:
        raise RuntimeError(
            "required wordlist caches are incomplete: " + ", ".join(missing)
        )
    return {
        "required": list(required),
        "ready": True,
        "status": "ready",
        "paths": {key: str(prepared[key]) for key in required},
    }
