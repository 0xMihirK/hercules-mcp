"""Read-only, declarative setup metadata for capable installation agents."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import inspect
import os
import platform
import re
import ssl
import stat
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from hercules.core.build_info import (
    CLOAKBROWSER_PROJECT_URL,
    CLOAKBROWSER_REPOSITORY_URL,
    CLOAKBROWSER_VERSION,
    CLOAKBROWSER_WHEEL_SHA256,
    CLOAKBROWSER_WHEEL_URL,
    IMAGE_BUILD_CA_LABEL,
    IMAGE_CAPABILITIES_LABEL,
    IMAGE_CLOAKBROWSER_SHA256_LABEL,
    IMAGE_CLOAKBROWSER_VERSION_LABEL,
    IMAGE_FINGERPRINT_LABEL,
    IMAGE_INPUTS,
    image_identity,
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
_CERTIFICATE_BLOCK = re.compile(
    rb"-----BEGIN CERTIFICATE-----\s+.+?\s+-----END CERTIFICATE-----",
    re.DOTALL,
)
_PRIVATE_KEY_MARKER = re.compile(
    rb"-----BEGIN [^-]*(?:PRIVATE KEY|OPENSSH PRIVATE KEY)-----"
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


def setup_information(
    project_root: Path,
    *,
    capabilities: str | None = None,
    build_ca_bundle: Path | None = None,
    state_path: Path | None = None,
    cloakbrowser_version: str | None = None,
    cloakbrowser_wheel_url: str | None = None,
    cloakbrowser_sha256: str | None = None,
) -> dict[str, Any]:
    """Return deterministic setup facts; this function performs no mutation."""
    root = Path(project_root).resolve()
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
    surface = capture_surface()
    skill_validation = validate_skill_routing(root, surface)
    environment_values = {
        "HERCULES_INSTALLED_CAPABILITIES": formatted,
        "SKIP_METASPLOIT": "true" if skip_metasploit else "false",
        "HERCULES_BUILD_CA_SHA256": ca_sha256,
        "HERCULES_CLOAKBROWSER_VERSION": cloak_version,
        "HERCULES_CLOAKBROWSER_WHEEL_URL": cloak_url,
        "HERCULES_CLOAKBROWSER_SHA256": cloak_sha,
    }
    return {
        "schema_version": 1,
        "read_only": True,
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
            "build_inputs": list(IMAGE_INPUTS),
            "build_arguments": {
                "HERCULES_CAPABILITIES": formatted,
                "HERCULES_BUILD_FINGERPRINT": fingerprint,
                "HERCULES_BUILD_CA_SHA256": ca_sha256,
                "CLOAKBROWSER_PY_VERSION": cloak_version,
                "CLOAKBROWSER_WHEEL_URL": cloak_url,
                "CLOAKBROWSER_WHEEL_SHA256": cloak_sha,
            },
            "labels": {
                IMAGE_FINGERPRINT_LABEL: fingerprint,
                IMAGE_CAPABILITIES_LABEL: formatted,
                IMAGE_BUILD_CA_LABEL: ca_sha256,
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
            "No external target is contacted during setup",
        ],
    }


def setup_information_from_argv(project_root: Path, argv: list[str]) -> dict[str, Any]:
    parser = argparse.ArgumentParser(prog="hercules --setup-info-json")
    parser.add_argument("--capabilities")
    parser.add_argument("--build-ca-bundle", type=Path)
    parser.add_argument("--state", type=Path)
    parser.add_argument("--cloakbrowser-version")
    parser.add_argument("--cloakbrowser-wheel-url")
    parser.add_argument("--cloakbrowser-sha256")
    arguments = parser.parse_args(argv)
    return setup_information(
        project_root,
        capabilities=arguments.capabilities,
        build_ca_bundle=arguments.build_ca_bundle,
        state_path=arguments.state,
        cloakbrowser_version=arguments.cloakbrowser_version,
        cloakbrowser_wheel_url=arguments.cloakbrowser_wheel_url,
        cloakbrowser_sha256=arguments.cloakbrowser_sha256,
    )
