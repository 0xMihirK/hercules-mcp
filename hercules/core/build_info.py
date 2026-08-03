"""Deterministic fingerprints for Docker runtime inputs."""

from __future__ import annotations

import hashlib
import platform
import re
from collections.abc import Iterable
from pathlib import Path

from hercules.core.tool_catalog import (
    ALL_CAPABILITIES,
    format_capabilities,
    normalize_capabilities,
    required_backends,
)

IMAGE_INPUTS = ("Dockerfile", "docker/entrypoint.sh")
IMAGE_FINGERPRINT_LABEL = "hercules.build_fingerprint"
IMAGE_CAPABILITIES_LABEL = "hercules.capabilities"
IMAGE_BUILD_CA_LABEL = "hercules.build_ca_sha256"
IMAGE_CLOAKBROWSER_VERSION_LABEL = "hercules.cloakbrowser.version"
IMAGE_CLOAKBROWSER_SHA256_LABEL = "hercules.cloakbrowser.sha256"
IMAGE_BASE_REPOSITORY_LABEL = "hercules.base.repository"
IMAGE_BASE_DIGEST_LABEL = "hercules.base.digest"
IMAGE_APT_SUITE_LABEL = "hercules.apt.suite"
IMAGE_PLATFORM_LABEL = "hercules.platform"
IMAGE_CAPABILITY_MANIFEST_LABEL = "hercules.capability_manifest_sha256"

KALI_BASE_REPOSITORY = "kalilinux/kali-last-release"
KALI_BASE_DIGEST = (
    "sha256:01a402ec78a2b3bd86394f34f8c3d6adefe3c593ae259ac0779c4d1f971c8ff5"
)
KALI_APT_SUITE = "kali-last-snapshot"
SUPPORTED_IMAGE_PLATFORMS = ("linux/amd64", "linux/arm64")

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


def default_image_platform() -> str:
    """Return the supported Linux image platform matching the host CPU."""
    machine = platform.machine().strip().lower()
    if machine in {"amd64", "x86_64", "x64"}:
        return "linux/amd64"
    if machine in {"arm64", "aarch64"}:
        return "linux/arm64"
    raise ValueError(
        "unsupported host architecture; set HERCULES_IMAGE_PLATFORM to "
        "linux/amd64 or linux/arm64 when Docker provides compatible emulation"
    )


def normalize_image_platform(value: str | None) -> str:
    """Validate one Docker image platform, defaulting to the host CPU."""
    normalized = (value or "").strip().lower() or default_image_platform()
    if normalized not in SUPPORTED_IMAGE_PLATFORMS:
        supported = ", ".join(SUPPORTED_IMAGE_PLATFORMS)
        raise ValueError(f"unsupported Hercules image platform; expected {supported}")
    return normalized


def capability_manifest_payload(capabilities: Iterable[str]) -> bytes:
    """Return the canonical manifest specification baked into an image."""
    selected = normalize_capabilities(capabilities)
    lines = [
        f"capabilities={format_capabilities(selected)}",
        *[f"binary={binary}" for binary in required_backends(selected)],
    ]
    return ("\n".join(lines) + "\n").encode("utf-8")


def capability_manifest_sha256(capabilities: Iterable[str]) -> str:
    """Hash the canonical capability manifest specification."""
    return hashlib.sha256(capability_manifest_payload(capabilities)).hexdigest()


def _canonical_build_input(path: Path) -> bytes:
    """Return platform-independent bytes for repository text build inputs.

    Git may materialize these files with CRLF on Windows even though Docker
    executes them as Linux text. The Dockerfile already strips a trailing CR
    from the copied entrypoint; fingerprinting the semantic LF representation
    keeps one verified image usable from equivalent Windows and POSIX checkouts.
    """
    return path.read_bytes().replace(b"\r\n", b"\n")


def _image_build_fingerprint(
    project_root: Path,
    capabilities: Iterable[str] = ALL_CAPABILITIES,
    *,
    build_ca_sha256: str = "",
    target_platform: str | None = None,
    cloakbrowser_version: str = CLOAKBROWSER_VERSION,
    cloakbrowser_sha256: str = CLOAKBROWSER_WHEEL_SHA256,
    canonical_build_inputs: bool,
) -> str:
    """Hash the build inputs whose changes require a new runtime image."""
    root = Path(project_root).resolve()
    digest = hashlib.sha256()
    selected = normalize_capabilities(capabilities)
    normalized = format_capabilities(selected)
    normalized_platform = normalize_image_platform(target_platform)
    normalized_ca = build_ca_sha256.strip().lower()
    if normalized_ca and not re.fullmatch(r"[0-9a-f]{64}", normalized_ca):
        raise ValueError("build CA fingerprint must be a SHA-256 hex digest")
    digest.update(b"capabilities\0")
    digest.update(normalized.encode("ascii"))
    digest.update(b"\0")
    digest.update(b"build-ca\0")
    digest.update(normalized_ca.encode("ascii"))
    digest.update(b"\0")
    digest.update(b"base-image\0")
    digest.update(KALI_BASE_REPOSITORY.encode("ascii"))
    digest.update(b"\0")
    digest.update(KALI_BASE_DIGEST.encode("ascii"))
    digest.update(b"\0")
    digest.update(KALI_APT_SUITE.encode("ascii"))
    digest.update(b"\0")
    digest.update(normalized_platform.encode("ascii"))
    digest.update(b"\0")
    digest.update(capability_manifest_payload(selected))
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
        digest.update(
            _canonical_build_input(path)
            if canonical_build_inputs
            else path.read_bytes()
        )
        digest.update(b"\0")
    return digest.hexdigest()


def image_build_fingerprint(
    project_root: Path,
    capabilities: Iterable[str] = ALL_CAPABILITIES,
    *,
    build_ca_sha256: str = "",
    target_platform: str | None = None,
    cloakbrowser_version: str = CLOAKBROWSER_VERSION,
    cloakbrowser_sha256: str = CLOAKBROWSER_WHEEL_SHA256,
) -> str:
    """Hash semantic build inputs independently of checkout line endings."""
    return _image_build_fingerprint(
        project_root,
        capabilities,
        build_ca_sha256=build_ca_sha256,
        target_platform=target_platform,
        cloakbrowser_version=cloakbrowser_version,
        cloakbrowser_sha256=cloakbrowser_sha256,
        canonical_build_inputs=True,
    )


def legacy_raw_image_identity(
    project_root: Path,
    capabilities: Iterable[str] = ALL_CAPABILITIES,
    *,
    build_ca_sha256: str = "",
    target_platform: str | None = None,
    cloakbrowser_version: str = CLOAKBROWSER_VERSION,
    cloakbrowser_sha256: str = CLOAKBROWSER_WHEEL_SHA256,
) -> tuple[str, str]:
    """Return the pre-canonicalization identity for one-release reuse."""
    fingerprint = _image_build_fingerprint(
        project_root,
        capabilities,
        build_ca_sha256=build_ca_sha256,
        target_platform=target_platform,
        cloakbrowser_version=cloakbrowser_version,
        cloakbrowser_sha256=cloakbrowser_sha256,
        canonical_build_inputs=False,
    )
    return f"hercules-kali:{fingerprint[:16]}", fingerprint


def image_identity(
    project_root: Path,
    capabilities: Iterable[str] = ALL_CAPABILITIES,
    *,
    build_ca_sha256: str = "",
    target_platform: str | None = None,
    cloakbrowser_version: str = CLOAKBROWSER_VERSION,
    cloakbrowser_sha256: str = CLOAKBROWSER_WHEEL_SHA256,
) -> tuple[str, str]:
    """Return the deterministic managed image tag and full fingerprint."""
    fingerprint = image_build_fingerprint(
        project_root,
        capabilities,
        build_ca_sha256=build_ca_sha256,
        target_platform=target_platform,
        cloakbrowser_version=cloakbrowser_version,
        cloakbrowser_sha256=cloakbrowser_sha256,
    )
    return f"hercules-kali:{fingerprint[:16]}", fingerprint
