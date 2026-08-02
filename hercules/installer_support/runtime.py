"""Capability-aware Docker image, asset, secret, and readiness services.

This module contains the non-interactive host work formerly owned by the setup
facade. It deliberately has no UI policy: the installer confirms a selection,
then calls these deterministic operations.
"""

from __future__ import annotations

import os
import secrets
import shutil
import tempfile
import urllib.request
import uuid
from collections.abc import Iterable
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlsplit

from hercules.core.build_info import (
    IMAGE_CAPABILITIES_LABEL,
    IMAGE_FINGERPRINT_LABEL,
    image_identity,
)
from hercules.core.tool_catalog import (
    ALL_CAPABILITIES,
    format_capabilities,
    normalize_capabilities,
    required_backends,
    required_wordlists,
)
from hercules.core.wordlists import (
    WORDLIST_SOURCES,
    ensure_extracted_wordlists,
    validate_wordlist_archive,
)
from hercules.installer_support.state import read_dotenv_value


class CommandRunner(Protocol):
    dry_run: bool

    def run(
        self,
        args: Iterable[str | os.PathLike[str]],
        *,
        cwd: Path | None = None,
        timeout: int = 600,
        check: bool = False,
        env: dict[str, str] | None = None,
    ) -> Any: ...

    def run_streaming(
        self,
        args: Iterable[str | os.PathLike[str]],
        *,
        cwd: Path | None = None,
        timeout: int = 600,
        check: bool = False,
    ) -> Any: ...


WORDLIST_FILES = {
    "seclists": "SecLists.zip",
    "rockyou": "rockyou.txt.tar.gz",
}


def ensure_msf_secret(env_path: Path) -> tuple[str, bool, bool]:
    """Return (secret, generated, historical_default) without logging it."""
    current = read_dotenv_value(env_path, "MSF_PASSWORD")
    if current:
        return current, False, current == "hercules"
    return secrets.token_urlsafe(32), True, False


def expected_image(capabilities: Iterable[str], source: Path) -> tuple[str, str, str]:
    selected = normalize_capabilities(capabilities)
    tag, fingerprint = image_identity(source, selected)
    return tag, fingerprint, format_capabilities(selected)


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
            headers={"User-Agent": "hercules-mcp-installer/1"},
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


def provision_wordlists(
    source: Path,
    capabilities: Iterable[str],
    *,
    dry_run: bool,
) -> dict[str, object]:
    """Provision only assets required by the selected capability bundles."""
    selected = normalize_capabilities(capabilities)
    required = required_wordlists(selected)
    if not required:
        return {"required": [], "ready": True, "status": "not_required", "paths": {}}
    wordlists_dir = source / "wordlists"
    if dry_run:
        return {"required": list(required), "ready": True, "status": "dry_run", "paths": {}}
    wordlists_dir.mkdir(parents=True, exist_ok=True)
    for logical_name in required:
        filename = WORDLIST_FILES[logical_name]
        destination = wordlists_dir / filename
        if not validate_wordlist_archive(filename, destination):
            destination.unlink(missing_ok=True)
            _download_wordlist(wordlists_dir, filename)
    prepared = ensure_extracted_wordlists(wordlists_dir)
    missing = sorted(set(required) - set(prepared))
    if missing:
        raise RuntimeError("required wordlist caches are incomplete: " + ", ".join(missing))
    return {
        "required": list(required),
        "ready": True,
        "status": "ready",
        "paths": {key: str(prepared[key]) for key in required},
    }


class RuntimeProvisioner:
    """Build and validate one immutable capability-specific Docker image."""

    def __init__(self, runner: CommandRunner, source: Path) -> None:
        self.runner = runner
        self.source = Path(source).resolve()

    def identity(self, capabilities: Iterable[str]) -> tuple[str, str, str]:
        return expected_image(capabilities, self.source)

    def image_status(self, capabilities: Iterable[str]) -> dict[str, Any]:
        selected = normalize_capabilities(capabilities)
        image, fingerprint, encoded = self.identity(selected)
        inspect = self.runner.run(
            [
                "docker", "image", "inspect", image, "--format",
                "{{json .Config.Labels}}",
            ],
            timeout=30,
        )
        exists = inspect.returncode == 0
        labels_ok = (
            exists
            and f'"{IMAGE_FINGERPRINT_LABEL}":"{fingerprint}"' in inspect.stdout
            and f'"{IMAGE_CAPABILITIES_LABEL}":"{encoded}"' in inspect.stdout
        )
        runtime_ready = False
        detail = "image is missing"
        if labels_ok:
            checks = ["test -x /entrypoint.sh", "test -s /opt/hercules-capabilities.txt"]
            checks.extend(f"command -v {name} >/dev/null" for name in required_backends(selected))
            if "browser" in selected:
                checks.extend((
                    "python3 -c 'import cloakbrowser'",
                    "python3 -m cloakbrowser info 2>/dev/null | grep -qi 'Installed: *True'",
                ))
            result = self.runner.run(
                ["docker", "run", "--rm", "--entrypoint", "/bin/sh", image, "-c", " && ".join(checks)],
                timeout=120,
            )
            runtime_ready = result.returncode == 0
            detail = "ready" if runtime_ready else (result.stderr.strip() or result.stdout.strip() or "runtime validation failed")
        elif exists:
            detail = "image labels do not match the confirmed selection/source"
        return {
            "image": image,
            "fingerprint": fingerprint,
            "capabilities": sorted(selected),
            "required_binaries": list(required_backends(selected)),
            "exists": exists,
            "labels_ok": labels_ok,
            "runtime_ready": runtime_ready,
            "detail": detail,
        }

    def build(
        self,
        capabilities: Iterable[str],
        *,
        rebuild: bool = False,
    ) -> dict[str, Any]:
        selected = normalize_capabilities(capabilities)
        current = self.image_status(selected)
        if current["runtime_ready"] and not rebuild:
            return current
        dockerfile = self.source / "Dockerfile"
        entrypoint = self.source / "docker" / "entrypoint.sh"
        if not dockerfile.is_file() or not entrypoint.is_file():
            raise FileNotFoundError("Dockerfile or docker/entrypoint.sh is missing")
        image, fingerprint, encoded = self.identity(selected)
        if self.runner.dry_run:
            context_path = self.source
            cleanup = None
        else:
            cleanup = tempfile.TemporaryDirectory(prefix="hercules-docker-build-")
            context_path = Path(cleanup.name)
            (context_path / "docker").mkdir()
            shutil.copy2(dockerfile, context_path / "Dockerfile")
            shutil.copy2(entrypoint, context_path / "docker" / "entrypoint.sh")
        try:
            command: list[str | os.PathLike[str]] = ["docker", "build"]
            if rebuild:
                command.append("--no-cache")
            command.extend((
                "--build-arg", f"HERCULES_BUILD_FINGERPRINT={fingerprint}",
                "--build-arg", f"HERCULES_CAPABILITIES={encoded}",
                "-t", image, context_path,
            ))
            stream = getattr(self.runner, "run_streaming", self.runner.run)
            stream(command, cwd=self.source, timeout=7200, check=True)
        finally:
            if cleanup is not None:
                cleanup.cleanup()
        status = self.image_status(selected)
        if not self.runner.dry_run and not status["runtime_ready"]:
            raise RuntimeError(f"new Docker image failed readiness: {status['detail']}")
        return status

    def status(self, capabilities: Iterable[str]) -> dict[str, Any]:
        selected = normalize_capabilities(capabilities)
        image = self.image_status(selected)
        required = required_wordlists(selected)
        wordlists = {"required": list(required), "ready": True, "status": "not_required"}
        if required:
            prepared = ensure_extracted_wordlists(self.source / "wordlists") if (self.source / "wordlists").is_dir() else {}
            wordlists = {
                "required": list(required),
                "ready": set(required).issubset(prepared),
                "status": "ready" if set(required).issubset(prepared) else "missing",
            }
        return {
            **image,
            "wordlists": wordlists,
            "ready": bool(image["runtime_ready"] and wordlists["ready"]),
        }


def full_capabilities() -> frozenset[str]:
    return ALL_CAPABILITIES
