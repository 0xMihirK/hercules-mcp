"""Atomic, secret-safe installer state persistence."""

from __future__ import annotations

import json
import os
import re
import stat
import uuid
from pathlib import Path
from typing import Any

SECRET_KEY = re.compile(
    r"(?:^|_)(?:password|passwd|token|secret|cookie|proxy_url|api_key)(?:$|_)",
    re.IGNORECASE,
)
DOTENV_ASSIGNMENT = re.compile(
    r"^\s*(?P<key>[A-Za-z_][A-Za-z0-9_]*)\s*=(?P<value>.*)$"
)


def atomic_write_private_bytes(
    path: Path,
    content: bytes,
    *,
    dry_run: bool = False,
) -> None:
    """Atomically replace a file through a private, exclusively-created temp."""
    if dry_run:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    descriptor = os.open(
        temporary,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        stat.S_IRUSR | stat.S_IWUSR,
    )
    try:
        with os.fdopen(descriptor, "wb", closefd=True) as destination:
            descriptor = -1
            destination.write(content)
            destination.flush()
            os.fsync(destination.fileno())
        os.replace(temporary, path)
        if os.name != "nt":
            path.chmod(stat.S_IRUSR | stat.S_IWUSR)
            directory = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if temporary.exists():
            temporary.unlink()


def atomic_write_private_text(
    path: Path,
    text: str,
    *,
    dry_run: bool = False,
) -> None:
    atomic_write_private_bytes(path, text.encode("utf-8"), dry_run=dry_run)


def read_dotenv_value(path: Path, key: str) -> str | None:
    """Read one dotenv assignment while accepting whitespace and quoted values."""
    if not path.is_file():
        return None
    found: str | None = None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = DOTENV_ASSIGNMENT.fullmatch(line)
        if match is None or match.group("key") != key:
            continue
        found = match.group("value").strip()
        if len(found) >= 2 and found[0] == found[-1] and found[0] in {"'", '"'}:
            found = found[1:-1]
    return found


def upsert_dotenv(
    path: Path,
    updates: dict[str, str],
    *,
    dry_run: bool = False,
    comment: str = "# Managed preferences from hercules-install",
) -> None:
    """Update dotenv keys without changing unrelated values or comments."""
    lines = (
        path.read_text(encoding="utf-8", errors="replace").splitlines()
        if path.is_file()
        else []
    )
    remaining = dict(updates)
    output: list[str] = []
    for line in lines:
        match = DOTENV_ASSIGNMENT.fullmatch(line)
        key = match.group("key") if match is not None else ""
        if key in updates:
            output.append(f"{key}={updates[key]}")
            remaining.pop(key, None)
        else:
            output.append(line)
    if remaining:
        if output and output[-1].strip():
            output.append("")
        if comment:
            output.append(comment)
        output.extend(f"{key}={value}" for key, value in remaining.items())
    atomic_write_private_text(
        path,
        "\n".join(output).rstrip("\n") + "\n",
        dry_run=dry_run,
    )


def load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): sanitize(item)
            for key, item in value.items()
            if not SECRET_KEY.search(str(key))
        }
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    return value


def save(path: Path, state: dict[str, Any], *, dry_run: bool = False) -> None:
    atomic_write_private_text(
        path,
        json.dumps(sanitize(state), indent=2, sort_keys=True) + "\n",
        dry_run=dry_run,
    )
