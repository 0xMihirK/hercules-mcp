"""Package-manager and init-system neutral platform diagnostics."""

from __future__ import annotations

import json
import os
import platform
import re
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

PACKAGE_MANAGERS = (
    "apt-get",
    "dnf",
    "yum",
    "zypper",
    "pacman",
    "apk",
    "xbps-install",
    "emerge",
    "nix-env",
)
INIT_COMMANDS = (
    ("systemd", "systemctl"),
    ("openrc", "rc-service"),
    ("runit", "sv"),
    ("s6", "s6-svscanctl"),
)
INIT_ALIASES = {
    "systemd": "systemd",
    "openrc": "openrc",
    "openrc-init": "openrc",
    "runit": "runit",
    "runsvdir": "runit",
    "s6-svscan": "s6",
    "dinit": "dinit",
    "launchd": "launchd",
}
FAMILY_ALIASES = {
    "alpine": "alpine",
    "arch": "arch",
    "centos": "rhel",
    "debian": "debian",
    "fedora": "rhel",
    "gentoo": "gentoo",
    "nixos": "nixos",
    "opensuse": "suse",
    "opensuse-leap": "suse",
    "opensuse-tumbleweed": "suse",
    "rhel": "rhel",
    "ubuntu": "debian",
    "void": "void",
}


def _clean(value: object, maximum: int = 256) -> str:
    text = str(value or "").replace("\r", " ").replace("\n", " ").strip()
    return text[:maximum]


def normalize_architecture(machine: str) -> str:
    value = machine.strip().lower()
    if value in {"amd64", "x64", "x86_64"}:
        return "x86_64"
    if value in {"aarch64", "arm64"}:
        return "arm64"
    return value or "unknown"


def parse_os_release(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[key.strip().lower()] = _clean(value)
    return values


def linux_family(distribution_id: str, id_like: str) -> str:
    candidates = [distribution_id, *id_like.split()]
    for candidate in candidates:
        family = FAMILY_ALIASES.get(candidate.lower())
        if family:
            return family
    return "unknown"


def _read_optional(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def detect_platform(
    *,
    system_name: str | None = None,
    machine: str | None = None,
    environ: dict[str, str] | None = None,
    os_release_text: str | None = None,
    init_name: str | None = None,
    which: Callable[[str], str | None] = shutil.which,
) -> dict[str, Any]:
    """Return sanitized platform metadata without performing any mutation."""
    env = environ if environ is not None else os.environ
    system = system_name or platform.system()
    architecture = normalize_architecture(machine or platform.machine())
    result: dict[str, Any] = {
        "system": _clean(system),
        "architecture": architecture,
        "distribution_id": "",
        "distribution_version": "",
        "distribution_family": "",
        "package_manager": "",
        "init_system": "",
        "service_managers": [],
        "wsl": False,
        "docker_context": _clean(env.get("DOCKER_CONTEXT", "")),
        "docker_rootless": False,
    }
    if system == "Windows":
        result["distribution_family"] = "windows"
        result["init_system"] = "windows-service-manager"
        return result
    if system == "Darwin":
        result["distribution_family"] = "macos"
        result["init_system"] = "launchd"
        result["package_manager"] = "brew" if which("brew") else ""
        return result
    if system != "Linux":
        result["distribution_family"] = "unknown"
        result["init_system"] = "unknown"
        return result

    release = parse_os_release(
        os_release_text
        if os_release_text is not None
        else _read_optional(Path("/etc/os-release"))
    )
    distribution_id = release.get("id", "")
    id_like = release.get("id_like", "")
    result.update(
        {
            "distribution_id": distribution_id,
            "distribution_version": release.get("version_id", ""),
            "distribution_family": linux_family(distribution_id, id_like),
            "package_manager": next(
                (name for name in PACKAGE_MANAGERS if which(name)),
                "",
            ),
        }
    )
    version_text = " ".join(
        (
            _clean(env.get("WSL_DISTRO_NAME", "")),
            _read_optional(Path("/proc/sys/kernel/osrelease")),
            _read_optional(Path("/proc/version")),
        )
    )
    result["wsl"] = bool(
        env.get("WSL_DISTRO_NAME")
        or re.search(r"(?:microsoft|wsl)", version_text, re.IGNORECASE)
    )
    detected_init = _clean(init_name or _read_optional(Path("/proc/1/comm"))).lower()
    result["init_system"] = INIT_ALIASES.get(
        detected_init,
        detected_init or "unknown",
    )
    result["service_managers"] = [
        name for name, command in INIT_COMMANDS if which(command)
    ]
    return result


def apply_docker_details(
    snapshot: dict[str, Any],
    *,
    context_output: str = "",
    info_output: str = "",
) -> dict[str, Any]:
    """Merge sanitized Docker context/rootless facts into a platform snapshot."""
    result = dict(snapshot)
    if context_output.strip():
        result["docker_context"] = _clean(context_output)
    if info_output.strip():
        try:
            document = json.loads(info_output)
        except (TypeError, ValueError):
            document = {}
        if isinstance(document, dict):
            security_options = document.get("SecurityOptions", [])
            if not isinstance(security_options, list):
                security_options = []
            rootless = document.get("Rootless", False)
            result["docker_rootless"] = bool(
                rootless
                or any(
                    "rootless" in str(item).lower()
                    for item in security_options
                )
            )
    return result


def prerequisite_guidance(snapshot: dict[str, Any], component: str) -> str:
    """Return official, non-privileged remediation for a missing prerequisite."""
    if component == "git":
        return "Install Git from https://git-scm.com/downloads using your platform's supported method."
    if component == "uv":
        return "Install uv from https://docs.astral.sh/uv/getting-started/installation/."
    if component == "docker":
        return "Install a Docker-compatible CLI and daemon from https://docs.docker.com/get-started/get-docker/."
    if component == "docker_daemon":
        system = snapshot.get("system")
        if system in {"Windows", "Darwin"}:
            return (
                "Start Docker Desktop or your configured Docker-compatible context, "
                "then verify `docker info` succeeds."
            )
        init_system = snapshot.get("init_system") or "your distribution's init system"
        rootless = " rootless" if snapshot.get("docker_rootless") else ""
        return (
            f"Start or authorize the{rootless} Docker daemon using {init_system}; "
            "verify the selected Docker context with `docker info`. Use your "
            "distribution's official Docker documentation for privileged steps."
        )
    return "Follow the component's official installation documentation."
