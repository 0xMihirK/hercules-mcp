"""Deterministic fingerprints for Docker runtime inputs."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from pathlib import Path

from hercules.core.tool_catalog import ALL_CAPABILITIES, format_capabilities

IMAGE_INPUTS = ("Dockerfile", "docker/entrypoint.sh")
IMAGE_FINGERPRINT_LABEL = "hercules.build_fingerprint"
IMAGE_CAPABILITIES_LABEL = "hercules.capabilities"


def image_build_fingerprint(
    project_root: Path,
    capabilities: Iterable[str] = ALL_CAPABILITIES,
) -> str:
    """Hash the build inputs whose changes require a new runtime image."""
    root = Path(project_root).resolve()
    digest = hashlib.sha256()
    normalized = format_capabilities(capabilities)
    digest.update(b"capabilities\0")
    digest.update(normalized.encode("ascii"))
    digest.update(b"\0")
    for relative in IMAGE_INPUTS:
        path = root / relative
        digest.update(relative.encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def image_identity(
    project_root: Path,
    capabilities: Iterable[str] = ALL_CAPABILITIES,
) -> tuple[str, str]:
    """Return the deterministic managed image tag and full fingerprint."""
    fingerprint = image_build_fingerprint(project_root, capabilities)
    return f"hercules-kali:{fingerprint[:16]}", fingerprint
