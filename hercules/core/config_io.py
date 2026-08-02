"""Atomic local configuration I/O and non-secret setup-state validation."""

from __future__ import annotations

import json
import os
import re
import stat
import uuid
from pathlib import Path
from typing import Any

SETUP_STATE_SCHEMA_VERSION = 4
SECRET_KEY = re.compile(
    r"(?:^|_)(?:password|passwd|token|secret|cookie|proxy_url|api_key|"
    r"authorization|credential|private_key|certificate|pem|bearer)(?:$|_)",
    re.IGNORECASE,
)
DOTENV_ASSIGNMENT = re.compile(
    r"^\s*(?P<key>[A-Za-z_][A-Za-z0-9_]*)\s*=(?P<value>.*)$"
)


def atomic_write_private_bytes(path: Path, content: bytes) -> None:
    """Atomically replace a file through a private, exclusively created temp."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.tmp")
    descriptor = os.open(
        temporary,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        stat.S_IRUSR | stat.S_IWUSR,
    )
    try:
        with os.fdopen(descriptor, "wb", closefd=True) as output:
            descriptor = -1
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, destination)
        if os.name != "nt":
            destination.chmod(stat.S_IRUSR | stat.S_IWUSR)
            directory = os.open(destination.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)


def atomic_write_private_text(path: Path, text: str) -> None:
    atomic_write_private_bytes(path, text.encode("utf-8"))


def read_dotenv_value(path: Path, key: str) -> str | None:
    """Read one dotenv assignment while accepting whitespace and quotes."""
    if not path.is_file():
        return None
    found: str | None = None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = DOTENV_ASSIGNMENT.fullmatch(line)
        if match is None or match.group("key") != key:
            continue
        raw_value = match.group("value").strip()
        if (
            len(raw_value) >= 2
            and raw_value[0] == raw_value[-1]
            and raw_value[0] in {"'", '"'}
        ):
            raw_value = raw_value[1:-1]
        found = raw_value
    return found


def upsert_dotenv(path: Path, updates: dict[str, str]) -> None:
    """Update selected dotenv keys without changing unrelated assignments."""
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
        output.append("# Agent-maintained Hercules preferences")
        output.extend(f"{key}={value}" for key, value in remaining.items())
    atomic_write_private_text(path, "\n".join(output).rstrip("\n") + "\n")


def _secret_paths(value: Any, prefix: str = "") -> list[str]:
    paths: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            name = str(key)
            path = f"{prefix}.{name}" if prefix else name
            if SECRET_KEY.search(name):
                paths.append(path)
            else:
                paths.extend(_secret_paths(item, path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            paths.extend(_secret_paths(item, f"{prefix}[{index}]"))
    return paths


def load_setup_state(path: Path) -> tuple[dict[str, Any], list[str]]:
    """Read and validate agent-maintained schema-4 non-secret setup metadata."""
    candidate = Path(path)
    if not candidate.is_file():
        return {}, []
    try:
        value = json.loads(candidate.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {}, [f"state is not valid UTF-8 JSON: {exc.__class__.__name__}"]
    if not isinstance(value, dict):
        return {}, ["state root must be a JSON object"]
    errors: list[str] = []
    secret_paths = _secret_paths(value)
    if secret_paths:
        errors.append("state contains forbidden secret-like keys: " + ", ".join(secret_paths))
    schema = value.get("schema_version")
    if schema != SETUP_STATE_SCHEMA_VERSION:
        errors.append(
            f"state schema must be {SETUP_STATE_SCHEMA_VERSION}; found {schema!r}"
        )
    capabilities = value.get("installed_capabilities")
    if capabilities is not None and (
        not isinstance(capabilities, list)
        or not all(isinstance(item, str) for item in capabilities)
    ):
        errors.append("installed_capabilities must be a string list")
    return value, errors
