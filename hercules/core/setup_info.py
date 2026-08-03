"""Read-only, declarative setup metadata for capable installation agents."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import inspect
import os
import platform
import re
import shutil
import ssl
import stat
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from hercules.core.build_info import (
    CLOAKBROWSER_PROJECT_URL,
    CLOAKBROWSER_REPOSITORY_URL,
    CLOAKBROWSER_VERSION,
    CLOAKBROWSER_WHEEL_SHA256,
    CLOAKBROWSER_WHEEL_URL,
    IMAGE_APT_SUITE_LABEL,
    IMAGE_BASE_DIGEST_LABEL,
    IMAGE_BASE_REPOSITORY_LABEL,
    IMAGE_BUILD_CA_LABEL,
    IMAGE_CAPABILITIES_LABEL,
    IMAGE_CAPABILITY_MANIFEST_LABEL,
    IMAGE_CLOAKBROWSER_SHA256_LABEL,
    IMAGE_CLOAKBROWSER_VERSION_LABEL,
    IMAGE_FINGERPRINT_LABEL,
    IMAGE_INPUTS,
    IMAGE_PLATFORM_LABEL,
    KALI_APT_SUITE,
    KALI_BASE_DIGEST,
    KALI_BASE_REPOSITORY,
    SUPPORTED_IMAGE_PLATFORMS,
    capability_manifest_sha256,
    default_image_platform,
    image_identity,
    legacy_raw_image_identity,
    normalize_image_platform,
)
from hercules.core.config_io import SETUP_STATE_SCHEMA_VERSION, load_setup_state
from hercules.core.tool_catalog import (
    METASPLOIT_TOOLS,
    REGISTRARS,
    TOOL_SELECTORS,
    all_tool_names,
    catalog_payload,
    format_capabilities,
    parse_capabilities,
    parse_disabled,
    required_backends,
    required_wordlists,
    tools_for_capabilities,
)
from hercules.core.wordlists import WORDLIST_FILES, WORDLIST_SOURCES

MAX_BUILD_CA_BYTES = 1024 * 1024
RESOURCE_COUNT = 7
SETUP_INFORMATION_SCHEMA_VERSION = 3
_CERTIFICATE_BLOCK = re.compile(
    rb"-----BEGIN CERTIFICATE-----\s+.+?\s+-----END CERTIFICATE-----",
    re.DOTALL,
)
_PRIVATE_KEY_MARKER = re.compile(
    rb"-----BEGIN [^-]*(?:PRIVATE KEY|OPENSSH PRIVATE KEY)-----"
)


class SourceAssociationError(ValueError):
    """The launcher is not imported from a complete durable source checkout."""


def validate_source_association(root: Path) -> None:
    """Require the runtime package and build inputs to share one checkout."""
    source = Path(root).resolve()
    package_root = Path(__file__).resolve().parents[1]
    required = (
        source / "pyproject.toml",
        source / "uv.lock",
        source / "Dockerfile",
        source / "docker" / "entrypoint.sh",
        source / "skills" / "hercules-mcp" / "SKILL.md",
    )
    if package_root.parent != source or any(not path.is_file() for path in required):
        raise SourceAssociationError(
            "The Hercules launcher is not associated with a complete durable "
            "source checkout. Install it as a locked editable tool from the "
            "checkout, then verify that the imported hercules package resolves "
            "inside that same checkout before building."
        )


def capture_surface() -> dict[str, Any]:
    """Capture the declarative tool/resource contract without starting Docker."""
    tools: list[str] = []
    tool_parameters: dict[str, list[str]] = {}
    resources: list[str] = []

    class Capture:
        def tool(self, *args: Any, **_kwargs: Any):
            def decorate(function: Any):
                tools.append(function.__name__)
                tool_parameters[function.__name__] = [
                    name
                    for name in inspect.signature(function).parameters
                    if name != "ctx"
                ]
                return function

            if args and callable(args[0]):
                return decorate(args[0])
            return decorate

        def resource(self, uri: str, *_args: Any, **_kwargs: Any):
            def decorate(function: Any):
                resources.append(uri)
                return function

            return decorate

    capture = Capture()
    errors: list[str] = []
    for path in REGISTRARS:
        module_name, function_name = path.split(":", 1)
        try:
            registrar = getattr(importlib.import_module(module_name), function_name)
            registrar(capture)
        except Exception as exc:  # pragma: no cover - diagnostic boundary
            errors.append(f"{path}: {exc.__class__.__name__}: {exc}")
    try:
        from hercules.resources.agent_skills import register_agent_skill_resources
        from hercules.resources.post_exploitation import (
            register_post_exploitation_resources,
        )

        register_agent_skill_resources(capture)  # type: ignore[arg-type]
        register_post_exploitation_resources(capture)  # type: ignore[arg-type]
    except Exception as exc:  # pragma: no cover - diagnostic boundary
        errors.append(f"resources: {exc.__class__.__name__}: {exc}")
    unique_tools = list(dict.fromkeys(tools))
    unique_resources = list(dict.fromkeys(resources))
    return {
        "full_tools": len(unique_tools),
        "without_metasploit_tools": len(
            [name for name in unique_tools if name not in METASPLOIT_TOOLS]
        ),
        "resources": len(unique_resources),
        "tool_names": unique_tools,
        "tool_parameters": tool_parameters,
        "resource_uris": unique_resources,
        "catalog_matches": set(unique_tools) == set(all_tool_names()),
        "errors": errors,
    }


def validate_skill_routing(
    source: Path,
    surface: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Verify canonical guidance covers live tools, parameters, and resources."""
    skill_root = Path(source) / "skills" / "hercules-mcp"
    path = skill_root / "references" / "tool-routing.md"
    try:
        documents = [
            skill_root / "SKILL.md",
            *sorted((skill_root / "references").glob("*.md")),
        ]
        text = "\n".join(
            document.read_text(encoding="utf-8") for document in documents
        )
    except OSError as exc:
        return {
            "ok": False,
            "path": str(path),
            "missing_tools": list(all_tool_names()),
            "missing_parameters": [],
            "missing_selectors": [],
            "missing_resources": [],
            "error": f"skill guidance is unavailable ({exc.__class__.__name__})",
        }
    live_surface = surface or capture_surface()
    missing_tools = [
        name for name in all_tool_names() if f"`{name}`" not in text
    ]
    missing_parameters: list[str] = []
    lines = text.splitlines()
    for tool_name, parameters in live_surface.get("tool_parameters", {}).items():
        tool_lines = [line for line in lines if f"`{tool_name}`" in line]
        for parameter in parameters:
            pattern = re.compile(rf"`{re.escape(parameter)}(?:`|=)")
            if not any(pattern.search(line) for line in tool_lines):
                missing_parameters.append(f"{tool_name}.{parameter}")
    missing_selectors: list[str] = []
    for tool_name, fields in TOOL_SELECTORS.items():
        for field_name, values in fields.items():
            for value in values:
                if not re.search(rf"(?<![\w-]){re.escape(value)}(?![\w-])", text):
                    missing_selectors.append(f"{tool_name}.{field_name}={value}")
    missing_resources = [
        uri
        for uri in live_surface.get("resource_uris", [])
        if f"`{uri}`" not in text
    ]
    return {
        "ok": not (
            missing_tools
            or missing_parameters
            or missing_selectors
            or missing_resources
        ),
        "path": str(path),
        "missing_tools": missing_tools,
        "missing_parameters": missing_parameters,
        "missing_selectors": missing_selectors,
        "missing_resources": missing_resources,
        "error": "",
    }


def validate_build_ca_bundle(path: Path) -> tuple[bytes, str]:
    """Safely read a bounded certificate-only PEM and return normalized bytes/hash."""
    supplied = Path(path).expanduser().absolute()
    supplied_stat = supplied.lstat()
    attributes = int(getattr(supplied_stat, "st_file_attributes", 0))
    reparse_flag = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    if supplied.is_symlink() or attributes & reparse_flag:
        raise ValueError("build CA bundle must not be a symlink or reparse point")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(supplied, flags)
    try:
        opened = os.fstat(descriptor)
        if (opened.st_dev, opened.st_ino) != (
            supplied_stat.st_dev,
            supplied_stat.st_ino,
        ):
            raise ValueError("build CA bundle changed while it was being opened")
        if not stat.S_ISREG(opened.st_mode):
            raise ValueError("build CA bundle must be a regular file")
        if opened.st_size <= 0 or opened.st_size > MAX_BUILD_CA_BYTES:
            raise ValueError("build CA bundle must be between 1 byte and 1 MiB")
        chunks: list[bytes] = []
        remaining = MAX_BUILD_CA_BYTES + 1
        while remaining:
            chunk = os.read(descriptor, min(64 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        content = b"".join(chunks)
        if len(content) > MAX_BUILD_CA_BYTES:
            raise ValueError("build CA bundle must be between 1 byte and 1 MiB")
    finally:
        os.close(descriptor)
    if _PRIVATE_KEY_MARKER.search(content):
        raise ValueError("build CA bundle must not contain a private key")
    blocks = _CERTIFICATE_BLOCK.findall(content)
    remainder = _CERTIFICATE_BLOCK.sub(b"", content)
    remainder = re.sub(rb"(?m)^\s*(?:#.*)?$", b"", remainder).strip()
    if not blocks or remainder:
        raise ValueError("build CA bundle must contain only PEM certificates")
    normalized: list[bytes] = []
    for block in blocks:
        text = block.decode("ascii", errors="strict")
        try:
            ssl.PEM_cert_to_DER_cert(text)
        except ValueError as exc:
            raise ValueError("build CA bundle contains an invalid certificate") from exc
        normalized.append(block.strip())
    payload = b"\n".join(normalized) + b"\n"
    return payload, hashlib.sha256(payload).hexdigest()


def setup_state_locations(project_dir: Path) -> dict[str, str]:
    """Return platform-native user and project state destinations without writes."""
    home = Path.home()
    system = platform.system()
    if system == "Windows":
        root = Path(os.getenv("APPDATA", home / "AppData" / "Roaming"))
    elif system == "Darwin":
        root = home / "Library" / "Preferences"
    else:
        root = Path(os.getenv("XDG_CONFIG_HOME", home / ".config"))
    return {
        "user": str((root / "hercules-mcp" / "install.json").resolve()),
        "project": str((project_dir / ".hercules" / "install.json").resolve()),
    }


def _cloakbrowser_values(
    version: str,
    wheel_url: str,
    wheel_sha256: str,
) -> tuple[str, str, str]:
    normalized_version = version.strip()
    normalized_url = wheel_url.strip()
    normalized_sha = wheel_sha256.strip().lower()
    if not re.fullmatch(r"\d+\.\d+\.\d+", normalized_version):
        raise ValueError("CloakBrowser must use an exact stable release")
    if not re.fullmatch(r"[0-9a-f]{64}", normalized_sha):
        raise ValueError("CloakBrowser wheel SHA-256 is invalid")
    parsed = urlsplit(normalized_url)
    expected_name = f"cloakbrowser-{normalized_version}-py3-none-any.whl"
    if (
        parsed.scheme != "https"
        or parsed.hostname != "files.pythonhosted.org"
        or Path(parsed.path).name != expected_name
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("CloakBrowser wheel must be the exact official PyPI artifact")
    return normalized_version, normalized_url, normalized_sha


def _saved_text(state: dict[str, Any], errors: list[str], key: str) -> str:
    """Return one validated, non-empty string from setup state."""
    if errors:
        return ""
    value = state.get(key)
    return value.strip() if isinstance(value, str) else ""


def _resolved_text(
    explicit: str | None,
    environment_key: str,
    state: dict[str, Any],
    state_errors: list[str],
    state_key: str,
    default: str,
) -> str:
    """Resolve one non-secret setting: explicit, environment, state, default."""
    if explicit is not None:
        return explicit
    environment_value = os.getenv(environment_key, "").strip()
    if environment_value:
        return environment_value
    return _saved_text(state, state_errors, state_key) or default


def _environment_true(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"true", "1", "yes"}


def _run_read_only(arguments: list[str], *, cwd: Path | None = None) -> str:
    """Run one bounded discovery command and return stdout, or an empty string."""
    try:
        completed = subprocess.run(
            arguments,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return completed.stdout.strip() if completed.returncode == 0 else ""


def _source_facts(root: Path) -> dict[str, Any]:
    git = shutil.which("git")
    revision = _run_read_only([git, "rev-parse", "HEAD"], cwd=root) if git else ""
    status = (
        _run_read_only(
            [git, "status", "--porcelain", "--untracked-files=normal"],
            cwd=root,
        )
        if git
        else ""
    )
    return {
        "checkout": str(root),
        "revision": revision,
        "revision_recording_required": True,
        "clean": bool(revision) and not status,
        "release_policy": "latest stable release; otherwise exact default-branch commit",
        "update_policy": "fast-forward only; refuse modified or diverged checkouts",
    }


def _python_environment_facts(root: Path) -> dict[str, Any]:
    pyproject = root / "pyproject.toml"
    requires_python = ">=3.11"
    if pyproject.is_file():
        try:
            payload = tomllib.loads(pyproject.read_text(encoding="utf-8"))
            requires_python = str(
                payload.get("project", {}).get("requires-python", requires_python)
            )
        except (OSError, tomllib.TOMLDecodeError):
            pass
    lockfile = root / "uv.lock"
    lock_sha256 = (
        hashlib.sha256(lockfile.read_bytes()).hexdigest()
        if lockfile.is_file()
        else ""
    )
    uv = shutil.which("uv")
    uv_bin = _run_read_only([uv, "tool", "dir", "--bin"]) if uv else ""
    launcher_name = "hercules.exe" if os.name == "nt" else "hercules"
    launcher = str(Path(uv_bin) / launcher_name) if uv_bin else ""
    return {
        "requires_python": requires_python,
        "recommended_python": "3.12",
        "lockfile": "uv.lock",
        "lockfile_sha256": lock_sha256,
        "durable_editable_source_required": True,
        "uv_available": bool(uv),
        "uv_tool_bin": uv_bin,
        "absolute_launcher_candidate": launcher,
        "launcher_exists": bool(launcher and Path(launcher).is_file()),
        "path_inheritance_required": False,
        "running_python": sys.version.split()[0],
    }


def _failure_diagnostics() -> list[dict[str, Any]]:
    return [
        {
            "code": "source_association_invalid",
            "retryable": False,
            "resolution": (
                "associate the absolute launcher with the complete durable "
                "checkout through a locked editable tool environment"
            ),
        },
        {
            "code": "prerequisite_missing",
            "retryable": False,
            "resolution": "obtain operator-approved Git, uv, or Docker support",
        },
        {
            "code": "docker_daemon_unavailable",
            "retryable": True,
            "resolution": "repair or select the intended Docker context, then recheck",
        },
        {
            "code": "docker_platform_emulation_unavailable",
            "retryable": False,
            "resolution": (
                "use a native supported platform or an operator-approved Docker "
                "context with binfmt/QEMU emulation"
            ),
        },
        {
            "code": "docker_tls_trust_failed",
            "retryable": False,
            "resolution": "supply approved certificate-only trust through the BuildKit secret",
        },
        {
            "code": "docker_source_defect",
            "retryable": False,
            "resolution": "do not retry unchanged inputs; report the failing build layer",
        },
        {
            "code": "capability_manifest_mismatch",
            "retryable": False,
            "resolution": "rebuild the confirmed profile without silently removing capabilities",
        },
        {
            "code": "mcp_registration_failed",
            "retryable": False,
            "resolution": "restore the prior Hercules entry and validate the active client only",
        },
        {
            "code": "client_unsupported",
            "retryable": False,
            "resolution": "require a terminal-capable client with local STDIO MCP support",
        },
        {
            "code": "runtime_initializing",
            "retryable": True,
            "resolution": "keep the MCP connection open and retry the tool shortly",
        },
        {
            "code": "runtime_unavailable",
            "retryable": False,
            "resolution": "correct the reported runtime bootstrap defect and restart Hercules",
        },
        {
            "code": "stale_container_reclaimed",
            "retryable": True,
            "resolution": "retry after Hercules confirms every owned port was released",
        },
        {
            "code": "runtime_ports_reallocated",
            "retryable": True,
            "resolution": (
                "read system_network_info and use the effective listener ports "
                "selected for this IDE instance"
            ),
        },
        {
            "code": "orphan_guardian_unavailable",
            "retryable": True,
            "resolution": (
                "repair local process spawning or Docker access; do not leave "
                "a force-terminated client container holding ports"
            ),
        },
    ]


def setup_information(
    project_root: Path,
    *,
    capabilities: str | None = None,
    build_ca_bundle: Path | None = None,
    state_path: Path | None = None,
    target_platform: str | None = None,
    cloakbrowser_version: str | None = None,
    cloakbrowser_wheel_url: str | None = None,
    cloakbrowser_sha256: str | None = None,
) -> dict[str, Any]:
    """Return deterministic setup facts; this function performs no mutation."""
    root = Path(project_root).resolve()
    validate_source_association(root)
    project_dir = Path.cwd().resolve()
    state: dict[str, Any] = {}
    state_errors: list[str] = []
    if state_path is not None:
        state, state_errors = load_setup_state(Path(state_path))

    requested = capabilities
    if requested is None:
        requested = os.getenv("HERCULES_INSTALLED_CAPABILITIES")
    if requested is None and not state_errors:
        saved = state.get("installed_capabilities")
        if isinstance(saved, list) and all(isinstance(item, str) for item in saved):
            requested = ",".join(saved)
    selected = parse_capabilities(requested, legacy_all=True)
    formatted = format_capabilities(selected)
    selected_platform = normalize_image_platform(
        _resolved_text(
            target_platform,
            "HERCULES_IMAGE_PLATFORM",
            state,
            state_errors,
            "image_platform",
            default_image_platform(),
        )
    )

    ca_sha256 = os.getenv("HERCULES_BUILD_CA_SHA256", "").strip().lower()
    if not ca_sha256:
        ca_sha256 = _saved_text(state, state_errors, "build_ca_sha256").lower()
    ca_secret_supplied = build_ca_bundle is not None
    if build_ca_bundle is not None:
        _, ca_sha256 = validate_build_ca_bundle(build_ca_bundle)
    elif ca_sha256 and not re.fullmatch(r"[0-9a-f]{64}", ca_sha256):
        raise ValueError("HERCULES_BUILD_CA_SHA256 must be a SHA-256 hex digest")
    ca_configured = bool(ca_sha256)

    cloak_version, cloak_url, cloak_sha = _cloakbrowser_values(
        _resolved_text(
            cloakbrowser_version,
            "HERCULES_CLOAKBROWSER_VERSION",
            state,
            state_errors,
            "cloakbrowser_version",
            CLOAKBROWSER_VERSION,
        ),
        _resolved_text(
            cloakbrowser_wheel_url,
            "HERCULES_CLOAKBROWSER_WHEEL_URL",
            state,
            state_errors,
            "cloakbrowser_wheel_url",
            CLOAKBROWSER_WHEEL_URL,
        ),
        _resolved_text(
            cloakbrowser_sha256,
            "HERCULES_CLOAKBROWSER_SHA256",
            state,
            state_errors,
            "cloakbrowser_sha256",
            CLOAKBROWSER_WHEEL_SHA256,
        ),
    )
    image, fingerprint = image_identity(
        root,
        selected,
        build_ca_sha256=ca_sha256,
        target_platform=selected_platform,
        cloakbrowser_version=cloak_version,
        cloakbrowser_sha256=cloak_sha,
    )
    legacy_image, legacy_fingerprint = legacy_raw_image_identity(
        root,
        selected,
        build_ca_sha256=ca_sha256,
        target_platform=selected_platform,
        cloakbrowser_version=cloak_version,
        cloakbrowser_sha256=cloak_sha,
    )
    tool_names = set(tools_for_capabilities(selected))
    skip_metasploit = "metasploit" not in selected or _environment_true(
        "SKIP_METASPLOIT"
    )
    if skip_metasploit:
        tool_names -= METASPLOIT_TOOLS
    disabled = parse_disabled(os.getenv("HERCULES_DISABLED_TOOLS", ""))
    tool_names -= set(disabled)

    wordlists = required_wordlists(selected)
    wordlist_metadata = {
        logical: {
            "filename": WORDLIST_FILES[logical],
            **WORDLIST_SOURCES[WORDLIST_FILES[logical]],
        }
        for logical in wordlists
    }
    browser_selected = "browser" in selected
    manifest_sha256 = capability_manifest_sha256(selected)
    surface = capture_surface()
    skill_validation = validate_skill_routing(root, surface)
    environment_values = {
        "HERCULES_INSTALLED_CAPABILITIES": formatted,
        "SKIP_METASPLOIT": "true" if skip_metasploit else "false",
        "HERCULES_BUILD_CA_SHA256": ca_sha256,
        "HERCULES_IMAGE_PLATFORM": selected_platform,
        "HERCULES_CLOAKBROWSER_VERSION": cloak_version,
        "HERCULES_CLOAKBROWSER_WHEEL_URL": cloak_url,
        "HERCULES_CLOAKBROWSER_SHA256": cloak_sha,
        "HERCULES_AUTO_ALLOCATE_PORTS": "true",
    }
    return {
        "schema_version": SETUP_INFORMATION_SCHEMA_VERSION,
        "read_only": True,
        "source": _source_facts(root),
        "python_environment": _python_environment_facts(root),
        "capability_catalog": catalog_payload(),
        "selection": {
            "capabilities": formatted.split(","),
            "formatted": formatted,
            "required_binaries": list(required_backends(selected)),
            "required_wordlists": wordlist_metadata,
        },
        "mcp_surface": {
            "tools": len(tool_names),
            "tool_names": sorted(tool_names),
            "resources": RESOURCE_COUNT,
            "full_tools": surface["full_tools"],
            "without_metasploit_tools": surface["without_metasploit_tools"],
            "resource_uris": surface["resource_uris"],
            "catalog_matches": surface["catalog_matches"],
            "errors": surface["errors"],
        },
        "image": {
            "tag": image,
            "fingerprint": fingerprint,
            "legacy_checkout_compatibility": {
                "enabled_for_one_release": legacy_image != image,
                "tag": legacy_image if legacy_image != image else "",
                "fingerprint": (
                    legacy_fingerprint if legacy_image != image else ""
                ),
                "requires_full_label_and_runtime_validation": True,
            },
            "context": str(root),
            "dockerfile": str(root / "Dockerfile"),
            "target_platform": selected_platform,
            "supported_platforms": list(SUPPORTED_IMAGE_PLATFORMS),
            "base": {
                "repository": KALI_BASE_REPOSITORY,
                "digest": KALI_BASE_DIGEST,
                "apt_suite": KALI_APT_SUITE,
                "update_policy": "pinned stable snapshot; no rolling channel",
            },
            "build_inputs": list(IMAGE_INPUTS),
            "build_arguments": {
                "HERCULES_CAPABILITIES": formatted,
                "HERCULES_BUILD_FINGERPRINT": fingerprint,
                "HERCULES_BUILD_CA_SHA256": ca_sha256,
                "HERCULES_TARGET_PLATFORM": selected_platform,
                "HERCULES_CAPABILITY_MANIFEST_SHA256": manifest_sha256,
                "CLOAKBROWSER_PY_VERSION": cloak_version,
                "CLOAKBROWSER_WHEEL_URL": cloak_url,
                "CLOAKBROWSER_WHEEL_SHA256": cloak_sha,
            },
            "labels": {
                IMAGE_FINGERPRINT_LABEL: fingerprint,
                IMAGE_CAPABILITIES_LABEL: formatted,
                IMAGE_BUILD_CA_LABEL: ca_sha256,
                IMAGE_BASE_REPOSITORY_LABEL: KALI_BASE_REPOSITORY,
                IMAGE_BASE_DIGEST_LABEL: KALI_BASE_DIGEST,
                IMAGE_APT_SUITE_LABEL: KALI_APT_SUITE,
                IMAGE_PLATFORM_LABEL: selected_platform,
                IMAGE_CAPABILITY_MANIFEST_LABEL: manifest_sha256,
                IMAGE_CLOAKBROWSER_VERSION_LABEL: cloak_version,
                IMAGE_CLOAKBROWSER_SHA256_LABEL: cloak_sha,
            },
            "custom_ca": {
                "configured": ca_configured,
                "sha256": ca_sha256,
                "secret_required": ca_configured,
                "secret_supplied": ca_secret_supplied,
                "buildkit_secret_id": "hercules_build_ca" if ca_configured else "",
                "maximum_bytes": MAX_BUILD_CA_BYTES,
            },
            "capability_manifest": {
                "path": "/opt/hercules-capability-manifest.spec",
                "sha256": manifest_sha256,
                "runtime_evidence": "/opt/hercules-capabilities.txt",
            },
        },
        "cloakbrowser": {
            "required": browser_selected,
            "package": "cloakbrowser",
            "package_source": "PyPI",
            "version": cloak_version,
            "wheel_url": cloak_url,
            "wheel_sha256": cloak_sha,
            "pypi": CLOAKBROWSER_PROJECT_URL,
            "repository": CLOAKBROWSER_REPOSITORY_URL,
            "allow_prerelease": False,
            "readiness": (
                [
                    "Python package version matches the image label",
                    "managed Chromium reports Installed: True",
                    "agent-browser is present and uses the CloakBrowser executable",
                    "browser remains headless-only",
                ]
                if browser_selected
                else []
            ),
        },
        "environment": {
            "non_secret_values": environment_values,
            "operator_paths": ["HERCULES_WORKSPACE_ROOT", "HERCULES_WORDLIST_ROOT"],
            "secret_values_not_returned": ["MSF_PASSWORD", "BROWSER_PROXY_URL"],
        },
        "client_registration": {
            "transport": "stdio",
            "active_client_only": True,
            "absolute_launcher_required": True,
            "checkout_relative_cwd_allowed": False,
            "secrets_allowed": False,
            "native_interface_preferred": True,
            "atomic_configuration_required": True,
            "portable_skill_independent": True,
            "agent_skills_optional": True,
            "unsupported_without_stdio": True,
            "templates_require_rendering": True,
            "cold_connection_required": True,
            "recommended_startup_timeout_milliseconds": 120_000,
            "startup_timeout_scope": (
                "use the active client's native local-STDIO timeout setting when supported"
            ),
            "opencode": {
                "type": "local",
                "command_shape": "absolute command array",
                "timeout_milliseconds": 120_000,
            },
        },
        "runtime": {
            "immediate_mcp_handshake": True,
            "background_bootstrap": True,
            "concurrent_stdio_clients": True,
            "checkout_singleton_required": False,
            "tool_wait_seconds": 120,
            "states": [
                "starting",
                "ready",
                "unavailable",
                "cancelled",
            ],
            "metasploit_initializes_after_core": True,
            "port_allocation": {
                "automatic_default": True,
                "selection_slots": 128,
                "serialized_across_checkouts": True,
                "exact_process_start_identity": True,
                "effective_ports_reported_by": "system_network_info",
                "disable_with": "HERCULES_AUTO_ALLOCATE_PORTS=false",
            },
            "abrupt_exit_guardian": {
                "enabled_by_default": True,
                "exact_container_id": True,
                "exact_owner_pid_and_start_time": True,
                "full_label_revalidation": True,
                "preserves_other_projects_and_workspaces": True,
                "disabled_when_preserve_container_is_true": True,
            },
            "cold_start_assertions": [
                "STDIO initialization and tool/resource listing complete before Docker readiness",
                "Docker-backed calls share one shielded bootstrap task",
                "a local tool call succeeds after core readiness",
                "graceful shutdown removes the owned container and releases its ports",
                "a second local STDIO client selects non-conflicting ports while the first remains live",
                "force-terminating a disposable client removes only its owned container",
            ],
        },
        "transaction_cleanup": {
            "mandatory_on_success_and_failure": True,
            "track": [
                "temporary paths",
                "background processes",
                "containers and ownership labels",
                "port bindings",
                "staging checkouts",
                "client backups",
            ],
            "remove_only_transaction_owned": True,
            "verify_ports_released": True,
            "verify_no_secrets_in_logs_or_client_configuration": True,
            "protected": [
                "committed checkout",
                ".env and generated secrets",
                "schema-4 state",
                "installed portable skill",
                "selected image and valid Docker cache",
                "verified wordlists",
                "workspace evidence",
                "unrelated client configuration",
            ],
        },
        "diagnostics": _failure_diagnostics(),
        "state": {
            "schema_version": SETUP_STATE_SCHEMA_VERSION,
            "locations": setup_state_locations(project_dir),
            "inspected": state_path is not None,
            "valid": state_path is None or not state_errors,
            "errors": state_errors,
            "metadata": (
                {
                    key: state[key]
                    for key in (
                        "schema_version",
                        "checkout",
                        "commit",
                        "version",
                        "scope",
                        "clients",
                        "launcher",
                        "installed_capabilities",
                        "image",
                        "image_fingerprint",
                        "image_platform",
                        "base_image",
                        "base_digest",
                        "apt_suite",
                        "expected_tool_count",
                        "workspace_root",
                        "wordlist_root",
                        "build_ca_configured",
                        "build_ca_sha256",
                        "cloakbrowser_version",
                        "cloakbrowser_wheel_url",
                        "cloakbrowser_sha256",
                        "skill_paths",
                        "config_paths",
                    )
                    if key in state
                }
                if state_path is not None and not state_errors
                else {}
            ),
        },
        "skill_guidance": skill_validation,
        "acceptance": [
            "Docker image labels exactly match this payload",
            "Every selected backend passes the image capability manifest check",
            "The MCP launcher is absolute and client configuration contains no secrets",
            "The portable skill exists independently from native plugin adapters",
            "MCP validation reports the expected tool count and seven resources",
            "Cold STDIO initialization succeeds before Docker bootstrap completes",
            "OpenCode uses a 120000 millisecond local-MCP timeout when selected",
            "Transaction-owned temporary files, processes, containers, and ports are cleaned",
            "No external target is contacted during setup",
        ],
    }


def setup_information_from_argv(project_root: Path, argv: list[str]) -> dict[str, Any]:
    parser = argparse.ArgumentParser(prog="hercules --setup-info-json")
    parser.add_argument("--capabilities")
    parser.add_argument("--build-ca-bundle", type=Path)
    parser.add_argument("--state", type=Path)
    parser.add_argument("--target-platform")
    parser.add_argument("--cloakbrowser-version")
    parser.add_argument("--cloakbrowser-wheel-url")
    parser.add_argument("--cloakbrowser-sha256")
    arguments = parser.parse_args(argv)
    return setup_information(
        project_root,
        capabilities=arguments.capabilities,
        build_ca_bundle=arguments.build_ca_bundle,
        state_path=arguments.state,
        target_platform=arguments.target_platform,
        cloakbrowser_version=arguments.cloakbrowser_version,
        cloakbrowser_wheel_url=arguments.cloakbrowser_wheel_url,
        cloakbrowser_sha256=arguments.cloakbrowser_sha256,
    )
