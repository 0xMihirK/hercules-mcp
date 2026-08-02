"""Deterministic fingerprints for Docker runtime inputs."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable
from pathlib import Path

from hercules.core.tool_catalog import (
    ALL_CAPABILITIES,
    format_capabilities,
    normalize_capabilities,
)

IMAGE_INPUTS = ("Dockerfile", "docker/entrypoint.sh")
IMAGE_FINGERPRINT_LABEL = "hercules.build_fingerprint"
IMAGE_CAPABILITIES_LABEL = "hercules.capabilities"
IMAGE_BUILD_CA_LABEL = "hercules.build_ca_sha256"
IMAGE_CLOAKBROWSER_VERSION_LABEL = "hercules.cloakbrowser.version"
IMAGE_CLOAKBROWSER_SHA256_LABEL = "hercules.cloakbrowser.sha256"

CLOAKBROWSER_VERSION = "0.5.3"
CLOAKBROWSER_WHEEL_SHA256 = (
    "9082cfd2f104342fd718d9882984da7674ef6616308dd7932bff4b8bd5cf3cfe"
)
CLOAKBROWSER_WHEEL_URL = (
    "https://files.pythonhosted.org/packages/93/e8/"
    "f0d86ca18b3a1e132ffd965268f621897f60c47ea8c61b1ee9a786fffb36/"
    "cloakbrowser-0.5.3-py3-none-any.whl"
)
CLOAKBROWSER_PROJECT_URL = "https://pypi.org/project/cloakbrowser/"
CLOAKBROWSER_REPOSITORY_URL = "https://github.com/CloakHQ/cloakbrowser"


def image_build_fingerprint(
    project_root: Path,
    capabilities: Iterable[str] = ALL_CAPABILITIES,
    *,
    build_ca_sha256: str = "",
    cloakbrowser_version: str = CLOAKBROWSER_VERSION,
    cloakbrowser_sha256: str = CLOAKBROWSER_WHEEL_SHA256,
) -> str:
    """Hash the build inputs whose changes require a new runtime image."""
    root = Path(project_root).resolve()
    digest = hashlib.sha256()
    selected = normalize_capabilities(capabilities)
    normalized = format_capabilities(selected)
    normalized_ca = build_ca_sha256.strip().lower()
    if normalized_ca and not re.fullmatch(r"[0-9a-f]{64}", normalized_ca):
        raise ValueError("build CA fingerprint must be a SHA-256 hex digest")
    digest.update(b"capabilities\0")
    digest.update(normalized.encode("ascii"))
    digest.update(b"\0")
    digest.update(b"build-ca\0")
    digest.update(normalized_ca.encode("ascii"))
    digest.update(b"\0")
    if "browser" in selected:
        normalized_cloak_version = cloakbrowser_version.strip()
        normalized_cloak_sha = cloakbrowser_sha256.strip().lower()
        if not re.fullmatch(r"\d+\.\d+\.\d+", normalized_cloak_version):
            raise ValueError("CloakBrowser version must be an exact stable release")
        if not re.fullmatch(r"[0-9a-f]{64}", normalized_cloak_sha):
            raise ValueError("CloakBrowser fingerprint must be a SHA-256 hex digest")
        digest.update(b"cloakbrowser\0")
        digest.update(normalized_cloak_version.encode("ascii"))
        digest.update(b"\0")
        digest.update(normalized_cloak_sha.encode("ascii"))
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
    *,
    build_ca_sha256: str = "",
    cloakbrowser_version: str = CLOAKBROWSER_VERSION,
    cloakbrowser_sha256: str = CLOAKBROWSER_WHEEL_SHA256,
) -> tuple[str, str]:
    """Return the deterministic managed image tag and full fingerprint."""
    fingerprint = image_build_fingerprint(
        project_root,
        capabilities,
        build_ca_sha256=build_ca_sha256,
        cloakbrowser_version=cloakbrowser_version,
        cloakbrowser_sha256=cloakbrowser_sha256,
    )
    return f"hercules-kali:{fingerprint[:16]}", fingerprint
