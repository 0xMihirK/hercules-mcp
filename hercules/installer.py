"""Cross-platform installer and diagnostics for Hercules MCP.

The installer is intentionally host-side. It never scans a target or starts an
offensive tool; its only network operations are Git/package/image downloads
performed by Git, uv, Docker, or the optional Agent Skills installer.
"""

from __future__ import annotations

import argparse
import getpass
import importlib
import inspect
import json
import os
import platform
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import tomllib
import uuid
from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from hercules.core.tool_catalog import (
    ALL_CAPABILITIES,
    CORE_CAPABILITIES,
    FULL_TOOL_COUNT,
    LIGHT_TOOL_COUNT,
    METASPLOIT_TOOLS,
    REGISTRARS,
    TOOL_SELECTORS,
    all_tool_names,
    catalog_payload,
    format_capabilities,
    normalize_capabilities,
    parse_capabilities,
    parse_disabled,
    required_wordlists,
    tools_for_capabilities,
)
from hercules.installer_support.platform import (
    apply_docker_details,
    detect_platform,
    prerequisite_guidance,
)
from hercules.installer_support.runtime import (
    RuntimeProvisioner,
    ensure_msf_secret,
    provision_wordlists,
)
from hercules.installer_support.state import (
    atomic_write_private_bytes,
    atomic_write_private_text,
    read_dotenv_value,
    upsert_dotenv,
)
from hercules.installer_support.state import (
    load as load_installer_state,
)
from hercules.installer_support.state import (
    save as save_installer_state,
)

REPOSITORY_URL = "https://github.com/0xMihirK/hercules-mcp.git"
PLUGIN_NAME = "hercules-mcp"
SERVER_NAME = "hercules"
STATE_SCHEMA_VERSION = 3
EXPECTED_FULL_TOOLS = FULL_TOOL_COUNT
EXPECTED_LIGHT_TOOLS = LIGHT_TOOL_COUNT
EXPECTED_RESOURCES = 7
CLIENTS = ("codex", "claude", "cursor", "portable")
STABLE_TAG = re.compile(r"^v?\d+\.\d+\.\d+$")
SECTION_HEADER = re.compile(r"^\s*\[[^\]]+\]\s*(?:#.*)?$")
SENSITIVE_URL = re.compile(
    r"(?P<scheme>https?|socks5|socks5h)://(?P<userinfo>[^/@\s]+)@",
    re.IGNORECASE,
)
ANSI_ESCAPE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


class InstallerError(RuntimeError):
    """An actionable installation failure."""


def redact(value: str) -> str:
    """Redact URL userinfo and common inline secret assignments."""
    text = SENSITIVE_URL.sub(r"\g<scheme>://***:***@", str(value))
    text = re.sub(
        r"(?i)\b(password|passwd|token|api[_-]?key|cookie|secret)=([^\s&]+)",
        r"\1=***",
        text,
    )
    return text


def clean_detail(value: str) -> str:
    return ANSI_ESCAPE.sub("", redact(value))


@dataclass
class CommandResult:
    args: list[str]
    returncode: int
    stdout: str = ""
    stderr: str = ""


class Runner:
    """Subprocess runner with dry-run recording and secret-safe display."""

    def __init__(self, *, dry_run: bool = False, emit_progress: bool = True) -> None:
        self.dry_run = dry_run
        self.emit_progress = emit_progress
        self.commands: list[list[str]] = []

    def run(
        self,
        args: Iterable[str | os.PathLike[str]],
        *,
        cwd: Path | None = None,
        timeout: int = 600,
        check: bool = False,
        env: dict[str, str] | None = None,
    ) -> CommandResult:
        command = [str(part) for part in args]
        self.commands.append([redact(part) for part in command])
        if self.dry_run:
            return CommandResult(command, 0)
        try:
            completed = subprocess.run(
                command,
                cwd=str(cwd) if cwd else None,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                env=env,
                check=False,
            )
        except FileNotFoundError as exc:
            result = CommandResult(command, 127, "", str(exc))
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout if isinstance(exc.stdout, str) else ""
            stderr = exc.stderr if isinstance(exc.stderr, str) else ""
            result = CommandResult(command, 124, stdout, stderr or "Command timed out.")
        else:
            result = CommandResult(
                command,
                completed.returncode,
                completed.stdout,
                completed.stderr,
            )
        if check and result.returncode != 0:
            detail = redact(
                result.stderr.strip() or result.stdout.strip() or "no output"
            )
            raise InstallerError(
                f"Command failed ({result.returncode}): "
                f"{' '.join(redact(part) for part in command)}\n{detail}"
            )
        return result

    def run_streaming(
        self,
        args: Iterable[str | os.PathLike[str]],
        *,
        cwd: Path | None = None,
        timeout: int = 600,
        check: bool = False,
    ) -> CommandResult:
        """Stream sanitized progress and retain only a bounded diagnostic tail."""
        command = [str(part) for part in args]
        self.commands.append([redact(part) for part in command])
        if self.dry_run:
            return CommandResult(command, 0)
        tail: deque[str] = deque(maxlen=400)
        started = time.monotonic()
        process = subprocess.Popen(
            command,
            cwd=str(cwd) if cwd else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        assert process.stdout is not None
        stdout = process.stdout
        messages: queue.Queue[object] = queue.Queue()
        sentinel = object()

        def read_output() -> None:
            try:
                for line in stdout:
                    messages.put(line)
            finally:
                messages.put(sentinel)

        reader = threading.Thread(target=read_output, daemon=True)
        reader.start()
        timed_out = False
        try:
            while True:
                if time.monotonic() - started > timeout:
                    timed_out = True
                    process.kill()
                    break
                try:
                    message = messages.get(timeout=0.2)
                except queue.Empty:
                    if process.poll() is not None and not reader.is_alive():
                        break
                    continue
                if message is sentinel:
                    break
                cleaned = clean_detail(str(message).rstrip("\r\n"))
                tail.append(cleaned)
                if self.emit_progress and cleaned:
                    print(cleaned, file=sys.stderr, flush=True)
            process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.kill()
            process.wait(timeout=30)
        finally:
            reader.join(timeout=5)
            stdout.close()
        result = CommandResult(
            command,
            124 if timed_out else int(process.returncode or 0),
            "\n".join(tail),
            "Command timed out." if timed_out else "",
        )
        if check and result.returncode != 0:
            detail = result.stderr or result.stdout or "no output"
            raise InstallerError(
                f"Command failed ({result.returncode}): "
                f"{' '.join(redact(part) for part in command)}\n{detail}"
            )
        return result


def _home() -> Path:
    return Path.home().resolve()


def data_root(
    *,
    system_name: str | None = None,
    environ: dict[str, str] | None = None,
    home: Path | None = None,
) -> Path:
    env = environ if environ is not None else os.environ
    system = system_name or platform.system()
    base_home = home or _home()
    if system == "Windows":
        base = env.get("LOCALAPPDATA") or env.get("APPDATA")
        return (
            Path(base).expanduser() / "hercules-mcp"
            if base
            else base_home / "AppData" / "Local" / "hercules-mcp"
        )
    if system == "Darwin":
        return base_home / "Library" / "Application Support" / "hercules-mcp"
    base = env.get("XDG_DATA_HOME")
    return (
        Path(base).expanduser() / "hercules-mcp"
        if base
        else base_home / ".local" / "share" / "hercules-mcp"
    )


def config_root(
    *,
    system_name: str | None = None,
    environ: dict[str, str] | None = None,
    home: Path | None = None,
) -> Path:
    env = environ if environ is not None else os.environ
    system = system_name or platform.system()
    base_home = home or _home()
    if system == "Windows":
        base = env.get("APPDATA") or env.get("LOCALAPPDATA")
        return (
            Path(base).expanduser() / "hercules-mcp"
            if base
            else base_home / "AppData" / "Roaming" / "hercules-mcp"
        )
    if system == "Darwin":
        return base_home / "Library" / "Preferences" / "hercules-mcp"
    base = env.get("XDG_CONFIG_HOME")
    return (
        Path(base).expanduser() / "hercules-mcp"
        if base
        else base_home / ".config" / "hercules-mcp"
    )


def load_state(path: Path) -> dict[str, Any]:
    """Compatibility facade for the reusable state service."""
    return load_installer_state(path)


def project_version(source: Path) -> str:
    try:
        document = tomllib.loads(
            (source / "pyproject.toml").read_text(encoding="utf-8")
        )
        value = document["project"]["version"]
    except (OSError, KeyError, TypeError, tomllib.TOMLDecodeError):
        return "unknown"
    return str(value)


def atomic_write_text(path: Path, text: str, *, dry_run: bool = False) -> None:
    """Compatibility facade for atomic private installer writes."""
    atomic_write_private_text(path, text, dry_run=dry_run)


def save_state(path: Path, state: dict[str, Any], *, dry_run: bool = False) -> None:
    """Compatibility facade for atomic, recursively secret-safe state."""
    save_installer_state(path, state, dry_run=dry_run)


def validate_proxy_url(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme.lower() not in {"http", "https", "socks5", "socks5h"}:
        raise InstallerError(
            "Browser proxy must use http, https, socks5, or socks5h."
        )
    if not parsed.hostname:
        raise InstallerError("Browser proxy URL must include a host.")
    if any(char.isspace() for char in value):
        raise InstallerError("Browser proxy URL must not contain whitespace.")
    if parsed.fragment:
        raise InstallerError("Browser proxy URL must not contain a fragment.")
    try:
        _ = parsed.port
    except ValueError as exc:
        raise InstallerError("Browser proxy URL contains an invalid port.") from exc
    return value


def upsert_env(path: Path, updates: dict[str, str], *, dry_run: bool = False) -> None:
    upsert_dotenv(path, updates, dry_run=dry_run)


def read_env_value(path: Path, key: str) -> str | None:
    """Read one existing dotenv value without loading it into the process."""
    return read_dotenv_value(path, key)


def _mcp_output_has_command(output: str, expected: str) -> bool:
    """Verify a CLI JSON response contains the expected stdio command."""
    try:
        document = json.loads(output)
    except (TypeError, ValueError):
        return False

    def visit(value: Any) -> bool:
        if isinstance(value, dict):
            return any(
                (
                    str(item).strip() == expected
                    if str(key).lower() == "command"
                    else visit(item)
                )
                for key, item in value.items()
            )
        if isinstance(value, list):
            return any(visit(item) for item in value)
        return False

    return visit(document)


def _normalized_distribution_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def _locked_versions(requirements: Path) -> tuple[dict[str, str], set[str]]:
    """Return exact pins and the subset without environment markers."""
    pins: dict[str, str] = {}
    unconditional: set[str] = set()
    logical = ""
    for raw_line in requirements.read_text(
        encoding="utf-8",
        errors="strict",
    ).splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        logical = f"{logical} {stripped}".strip()
        if logical.endswith("\\"):
            logical = logical[:-1].rstrip()
            continue
        header = logical.split(" --hash=", 1)[0].strip()
        match = re.match(
            r"^(?P<name>[A-Za-z0-9_.-]+)==(?P<version>[^\s;]+)"
            r"(?P<marker>\s*;.*)?$",
            header,
        )
        logical = ""
        if match is None:
            continue
        name = _normalized_distribution_name(match.group("name"))
        pins[name] = match.group("version")
        if not match.group("marker"):
            unconditional.add(name)
    return pins, unconditional


def write_json_mcp(path: Path, *, dry_run: bool = False) -> None:
    document: dict[str, Any] = {}
    if path.is_file():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                document = loaded
        except (OSError, ValueError):
            raise InstallerError(
                f"Refusing to replace invalid JSON MCP configuration: {path}"
            )
    servers = document.setdefault("mcpServers", {})
    if not isinstance(servers, dict):
        raise InstallerError(f"Expected mcpServers to be an object in {path}")
    servers[SERVER_NAME] = {"command": "hercules", "args": []}
    atomic_write_text(
        path,
        json.dumps(document, indent=2, sort_keys=True) + "\n",
        dry_run=dry_run,
    )


def write_codex_toml(path: Path, *, dry_run: bool = False) -> None:
    text = path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""
    lines = text.splitlines()
    start = None
    end = None
    for index, line in enumerate(lines):
        if line.strip() == "[mcp_servers.hercules]":
            start = index
            end = len(lines)
            for next_index in range(index + 1, len(lines)):
                if SECTION_HEADER.match(lines[next_index]):
                    end = next_index
                    break
            break
    block = ["[mcp_servers.hercules]", 'command = "hercules"', "args = []"]
    if start is None:
        output = lines[:]
        if output and output[-1].strip():
            output.append("")
        output.extend(block)
    else:
        output = lines[:start] + block + lines[end:]
    atomic_write_text(path, "\n".join(output) + "\n", dry_run=dry_run)


def mcp_config_is_valid(path: Path, client: str) -> bool:
    if not path.is_file():
        return False
    if client == "codex" and path.suffix == ".toml":
        text = path.read_text(encoding="utf-8", errors="replace")
        match = re.search(
            r"(?ms)^\[mcp_servers\.hercules\]\s*$"
            r"(?P<body>.*?)(?=^\[[^\]]+\]\s*$|\Z)",
            text,
        )
        return bool(
            match
            and re.search(r'(?m)^\s*command\s*=\s*"hercules"\s*$', match.group("body"))
        )
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
        server = document["mcpServers"][SERVER_NAME]
    except (OSError, ValueError, TypeError, KeyError):
        return False
    return isinstance(server, dict) and server.get("command") == "hercules"


def _safe_replace_tree(source: Path, target: Path, *, dry_run: bool = False) -> None:
    if source.name != PLUGIN_NAME or target.name != PLUGIN_NAME:
        raise InstallerError(
            "Refusing to install a skill outside the hercules-mcp directory."
        )
    if dry_run:
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = target.parent / f".{PLUGIN_NAME}.{uuid.uuid4().hex}.tmp"
    backup = target.parent / f".{PLUGIN_NAME}.{uuid.uuid4().hex}.bak"
    shutil.copytree(source, staging)

    def remove_path(path: Path) -> None:
        if path.is_symlink() or path.is_file():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)

    try:
        if target.exists() or target.is_symlink():
            target.rename(backup)
        staging.rename(target)
        if backup.exists() or backup.is_symlink():
            remove_path(backup)
    except Exception:
        if (target.exists() or target.is_symlink()) and (
            backup.exists() or backup.is_symlink()
        ):
            remove_path(target)
        if backup.exists() or backup.is_symlink():
            backup.rename(target)
        if staging.exists() or staging.is_symlink():
            remove_path(staging)
        raise


def skill_target(client: str, scope: str, project_dir: Path) -> Path:
    home = _home()
    if scope == "project":
        if client == "claude":
            return project_dir / ".claude" / "skills" / PLUGIN_NAME
        if client == "cursor":
            return project_dir / ".cursor" / "skills" / PLUGIN_NAME
        return project_dir / ".agents" / "skills" / PLUGIN_NAME
    if client == "codex":
        codex_home = Path(os.getenv("CODEX_HOME", home / ".codex")).expanduser()
        return codex_home / "skills" / PLUGIN_NAME
    if client == "claude":
        return home / ".claude" / "skills" / PLUGIN_NAME
    if client == "cursor":
        return home / ".cursor" / "skills" / PLUGIN_NAME
    return home / ".agents" / "skills" / PLUGIN_NAME


def _parent_process_text() -> str:
    """Return a bounded parent-process chain for agent detection."""
    try:
        if os.name == "nt":
            import ctypes
            from ctypes import wintypes

            class ProcessEntry(ctypes.Structure):
                _fields_ = [
                    ("dwSize", wintypes.DWORD),
                    ("cntUsage", wintypes.DWORD),
                    ("th32ProcessID", wintypes.DWORD),
                    ("th32DefaultHeapID", ctypes.c_size_t),
                    ("th32ModuleID", wintypes.DWORD),
                    ("cntThreads", wintypes.DWORD),
                    ("th32ParentProcessID", wintypes.DWORD),
                    ("pcPriClassBase", wintypes.LONG),
                    ("dwFlags", wintypes.DWORD),
                    ("szExeFile", wintypes.WCHAR * 260),
                ]

            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.CreateToolhelp32Snapshot.argtypes = [
                wintypes.DWORD,
                wintypes.DWORD,
            ]
            kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
            kernel32.Process32FirstW.argtypes = [
                wintypes.HANDLE,
                ctypes.POINTER(ProcessEntry),
            ]
            kernel32.Process32FirstW.restype = wintypes.BOOL
            kernel32.Process32NextW.argtypes = [
                wintypes.HANDLE,
                ctypes.POINTER(ProcessEntry),
            ]
            kernel32.Process32NextW.restype = wintypes.BOOL
            kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
            kernel32.CloseHandle.restype = wintypes.BOOL
            snapshot = kernel32.CreateToolhelp32Snapshot(0x00000002, 0)
            if snapshot == wintypes.HANDLE(-1).value:
                return ""
            processes: dict[int, tuple[int, str]] = {}
            entry = ProcessEntry()
            entry.dwSize = ctypes.sizeof(entry)
            try:
                present = kernel32.Process32FirstW(snapshot, ctypes.byref(entry))
                while present:
                    processes[int(entry.th32ProcessID)] = (
                        int(entry.th32ParentProcessID),
                        str(entry.szExeFile),
                    )
                    present = kernel32.Process32NextW(snapshot, ctypes.byref(entry))
            finally:
                kernel32.CloseHandle(snapshot)
            names: list[str] = []
            process_id = os.getppid()
            for _ in range(8):
                parent, name = processes.get(process_id, (0, ""))
                if not name:
                    break
                names.append(name)
                process_id = parent
            return "\n".join(names)

        lines: list[str] = []
        process_id = os.getppid()
        for _ in range(8):
            result = subprocess.run(
                ["ps", "-o", "ppid=,comm=", "-p", str(process_id)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=2,
                check=False,
            )
            fields = result.stdout.strip().split(maxsplit=1)
            if result.returncode != 0 or len(fields) != 2:
                break
            process_id = int(fields[0])
            lines.append(fields[1])
        return "\n".join(lines)
    except (OSError, ValueError, subprocess.SubprocessError):
        return ""


def detect_active_clients(
    environ: dict[str, str] | None = None,
    *,
    process_text: str | None = None,
) -> list[str]:
    env = environ if environ is not None else os.environ
    detected: list[str] = []
    markers = {
        "codex": ("CODEX_HOME", "CODEX_SANDBOX", "CODEX_THREAD_ID"),
        "claude": ("CLAUDECODE", "CLAUDE_CODE", "CLAUDE_PROJECT_DIR"),
        "cursor": ("CURSOR_AGENT", "CURSOR_TRACE_ID", "CURSOR_SESSION_ID"),
    }
    for client, names in markers.items():
        if any(env.get(name) for name in names):
            detected.append(client)
    if detected and process_text is None:
        return detected
    chain = (
        process_text if process_text is not None else _parent_process_text()
    ).lower()
    process_patterns = {
        "codex": r"\bcodex(?:\.exe)?\b",
        "claude": r"\bclaude(?:\.exe)?\b",
        "cursor": r"\bcursor(?:-agent|\.exe)?\b",
    }
    for client, pattern in process_patterns.items():
        if client not in detected and re.search(pattern, chain):
            detected.append(client)
    return detected


def installed_clients() -> list[str]:
    commands = {"codex": "codex", "claude": "claude", "cursor": "cursor"}
    return [client for client, command in commands.items() if shutil.which(command)]


def prompt_choice(prompt: str, choices: tuple[str, ...], default: str) -> str:
    answer = (
        input(f"{prompt} [{'/'.join(choices)}] (default {default}): ").strip().lower()
    )
    return answer if answer in choices else default


def resolve_clients(requested: str, *, non_interactive: bool) -> list[str]:
    if requested in CLIENTS:
        return [requested]
    if requested == "all":
        return list(CLIENTS)
    active = detect_active_clients()
    if len(active) == 1:
        return active
    candidates = active or installed_clients()
    if len(candidates) == 1:
        return candidates
    if candidates and not non_interactive:
        choices = tuple(candidates + ["all", "portable"])
        selected = prompt_choice(
            f"Detected multiple compatible agents ({', '.join(candidates)}). Configure which",
            choices,
            "all",
        )
        return list(CLIENTS) if selected == "all" else [selected]
    if candidates:
        return candidates
    return ["portable"]


def _git_output(runner: Runner, source: Path, *args: str) -> str:
    result = runner.run(["git", "-C", source, *args], timeout=120, check=True)
    return result.stdout.strip()


def prepare_checkout(
    runner: Runner,
    destination: Path,
    *,
    explicit_source: Path | None = None,
    update: bool = True,
) -> tuple[Path, str]:
    if explicit_source:
        source = explicit_source.expanduser().resolve()
        if not source.is_dir() or not (source / "pyproject.toml").is_file():
            raise InstallerError(
                f"Explicit source is not a Hercules checkout: {source}"
            )
        return source, _git_output(runner, source, "rev-parse", "HEAD") if (
            source / ".git"
        ).exists() else "local"

    source = destination.expanduser().resolve()
    if not source.exists():
        runner.run(
            ["git", "clone", "--filter=blob:none", REPOSITORY_URL, source],
            timeout=600,
            check=True,
        )
        if runner.dry_run:
            return source, "dry-run"
    if not (source / ".git").is_dir():
        raise InstallerError(
            f"Managed source path exists but is not a Git checkout: {source}"
        )
    if update:
        dirty = _git_output(
            runner, source, "status", "--porcelain", "--untracked-files=normal"
        )
        if dirty:
            raise InstallerError(
                "Managed Hercules checkout has nonignored tracked or untracked "
                "modifications. "
                f"Preserve or commit them before upgrade: {source}"
            )
        runner.run(
            ["git", "-C", source, "fetch", "--tags", "origin"], timeout=300, check=True
        )
        remote_contains = runner.run(
            ["git", "-C", source, "branch", "-r", "--contains", "HEAD"],
            timeout=30,
        )
        exact_tags = runner.run(
            ["git", "-C", source, "tag", "--points-at", "HEAD"],
            timeout=30,
        )
        if (
            not runner.dry_run
            and not remote_contains.stdout.strip()
            and not exact_tags.stdout.strip()
        ):
            raise InstallerError(
                "Managed Hercules checkout history has diverged from its remote and "
                f"release tags. Preserve or move the local commits before upgrade: {source}"
            )
        tags = _git_output(
            runner, source, "tag", "--list", "--sort=-v:refname"
        ).splitlines()
        stable = next((tag for tag in tags if STABLE_TAG.fullmatch(tag.strip())), "")
        if stable:
            runner.run(
                ["git", "-C", source, "checkout", "--detach", stable],
                timeout=120,
                check=True,
            )
        else:
            head_result = runner.run(
                [
                    "git",
                    "-C",
                    source,
                    "symbolic-ref",
                    "--short",
                    "refs/remotes/origin/HEAD",
                ],
                timeout=30,
            )
            remote_head = (
                head_result.stdout.strip()
                if head_result.returncode == 0
                else "origin/main"
            )
            branch = remote_head.rsplit("/", 1)[-1] if remote_head else "main"
            runner.run(
                ["git", "-C", source, "checkout", branch], timeout=120, check=True
            )
            runner.run(
                ["git", "-C", source, "merge", "--ff-only", f"origin/{branch}"],
                timeout=180,
                check=True,
            )
    commit = _git_output(runner, source, "rev-parse", "HEAD")
    return source, commit


def capture_surface() -> dict[str, Any]:
    tools: list[str] = []
    tool_parameters: dict[str, list[str]] = {}
    resources: list[str] = []

    class Capture:
        def tool(self, *args: Any, **kwargs: Any):
            if args and callable(args[0]):
                function = args[0]
                tools.append(function.__name__)
                tool_parameters[function.__name__] = [
                    name
                    for name in inspect.signature(function).parameters
                    if name != "ctx"
                ]
                return args[0]

            def decorator(function):
                tools.append(function.__name__)
                tool_parameters[function.__name__] = [
                    name
                    for name in inspect.signature(function).parameters
                    if name != "ctx"
                ]
                return function

            return decorator

        def resource(self, uri: str, *args: Any, **kwargs: Any):
            def decorator(function):
                resources.append(uri)
                return function

            return decorator

    capture = Capture()
    errors: list[str] = []
    for path in REGISTRARS:
        module_name, function_name = path.split(":", 1)
        try:
            getattr(importlib.import_module(module_name), function_name)(capture)
        except Exception as exc:
            errors.append(f"{path}: {exc}")
    try:
        from hercules.resources.agent_skills import register_agent_skill_resources
        from hercules.resources.post_exploitation import (
            register_post_exploitation_resources,
        )

        register_agent_skill_resources(capture)  # type: ignore[arg-type]
        register_post_exploitation_resources(capture)  # type: ignore[arg-type]
    except Exception as exc:
        errors.append(f"resources: {exc}")
    unique_tools = list(dict.fromkeys(tools))
    unique_resources = list(dict.fromkeys(resources))
    return {
        "full_tools": len(unique_tools),
        "light_tools": len(
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
    """Verify canonical guidance covers live tools, parameters, selectors, resources."""
    skill_root = source / "skills" / PLUGIN_NAME
    path = skill_root / "references" / "tool-routing.md"
    try:
        documents = [skill_root / "SKILL.md", *sorted((skill_root / "references").glob("*.md"))]
        text = "\n".join(document.read_text(encoding="utf-8") for document in documents)
    except OSError as exc:
        return {
            "ok": False,
            "path": str(path),
            "missing_tools": list(all_tool_names()),
            "missing_parameters": [],
            "missing_selectors": [],
            "missing_resources": [],
            "error": str(exc),
        }
    live_surface = surface or capture_surface()
    missing_tools = [
        name for name in all_tool_names() if f"`{name}`" not in text
    ]
    missing_parameters: list[str] = []
    for tool_name, parameters in live_surface.get("tool_parameters", {}).items():
        tool_lines = [
            line for line in text.splitlines() if f"`{tool_name}`" in line
        ]
        for parameter in parameters:
            parameter_pattern = re.compile(
                rf"`{re.escape(parameter)}(?:`|=)"
            )
            if not any(parameter_pattern.search(line) for line in tool_lines):
                missing_parameters.append(f"{tool_name}.{parameter}")
    missing_selectors: list[str] = []
    for tool_name, fields in TOOL_SELECTORS.items():
        for field_name, values in fields.items():
            for value in values:
                if not re.search(
                    rf"(?<![\w-]){re.escape(value)}(?![\w-])",
                    text,
                ):
                    missing_selectors.append(
                        f"{tool_name}.{field_name}={value}"
                    )
    missing_resources = [
        uri for uri in live_surface.get("resource_uris", []) if f"`{uri}`" not in text
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


class HerculesInstaller:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.runner = Runner(
            dry_run=args.dry_run,
            emit_progress=not getattr(args, "json", False),
        )
        self.config_dir = config_root()
        self.state_path = self.config_dir / "install.json"
        self.state = load_state(self.state_path)
        self.project_dir = Path(args.project_dir or Path.cwd()).expanduser().resolve()

    def _prerequisites(self, *, require_git: bool = True) -> None:
        missing = []
        if require_git and not shutil.which("git"):
            missing.append("Git")
        if not shutil.which("uv"):
            missing.append("uv")
        if not shutil.which("docker"):
            missing.append("Docker")
        if missing:
            snapshot = detect_platform(which=shutil.which)
            details = "; ".join(
                prerequisite_guidance(snapshot, component.lower())
                for component in missing
            )
            raise InstallerError(
                "Missing prerequisite(s): "
                + ", ".join(missing)
                + f". {details} Hercules will not perform privileged installation."
            )
        daemon = self.runner.run(["docker", "info"], timeout=15)
        if daemon.returncode != 0:
            raise InstallerError(
                "Docker is installed but its daemon is not reachable. "
                + prerequisite_guidance(
                    detect_platform(which=shutil.which),
                    "docker_daemon",
                )
                + " Then rerun hercules-install."
            )

    def _scope(self) -> str:
        if self.args.scope:
            return self.args.scope
        existing = self.state.get("scope")
        if existing in {"user", "project"}:
            return existing
        if self.args.non_interactive:
            return "user"
        return prompt_choice(
            "Install for this user or only this project", ("user", "project"), "user"
        )

    def _capabilities(self, env_path: Path) -> frozenset[str]:
        """Resolve a confirmed bundle selection without surprising upgrades."""
        explicit = (self.args.capabilities or "").strip()
        if explicit:
            try:
                selected = parse_capabilities(explicit, legacy_all=False)
            except ValueError as exc:
                raise InstallerError(str(exc)) from exc
        else:
            saved = self.state.get("installed_capabilities")
            if isinstance(saved, list) and all(isinstance(key, str) for key in saved):
                try:
                    selected = normalize_capabilities(saved)
                except ValueError as exc:
                    raise InstallerError("Installer state contains an invalid capability key.") from exc
            else:
                persisted = read_env_value(env_path, "HERCULES_INSTALLED_CAPABILITIES")
                if persisted:
                    try:
                        selected = parse_capabilities(persisted)
                    except ValueError as exc:
                        raise InstallerError(".env contains an invalid capability selection.") from exc
                elif self.state or self.args.action == "upgrade":
                    # Schema-2 and checkout-local installations were full images.
                    selected = ALL_CAPABILITIES
                elif self.args.metasploit in {"enabled", "disabled"}:
                    # One-release compatibility: the historical unattended
                    # switch represented a full image with only MSF toggled.
                    selected = ALL_CAPABILITIES
                elif self.args.non_interactive:
                    raise InstallerError(
                        "A fresh unattended install requires --capabilities all, core, "
                        "or a comma-separated catalog selection. Run "
                        "'hercules-install catalog --json' to inspect valid keys."
                    )
                else:
                    mode = prompt_choice(
                        "Install every capability or choose a custom set",
                        ("all", "custom"),
                        "all",
                    )
                    if mode == "all":
                        selected = ALL_CAPABILITIES
                    else:
                        raw = input(
                            "Capability keys (comma-separated; run catalog for details): "
                        ).strip()
                        if not raw:
                            raise InstallerError("A custom installation needs at least one catalog key.")
                        try:
                            selected = parse_capabilities(raw, legacy_all=False)
                        except ValueError as exc:
                            raise InstallerError(str(exc)) from exc

        excludes = {
            item.strip().lower()
            for item in (self.args.exclude_capabilities or "").split(",")
            if item.strip()
        }
        unknown_excludes = excludes - ALL_CAPABILITIES
        if unknown_excludes:
            raise InstallerError(
                "Unknown excluded capabilities: " + ", ".join(sorted(unknown_excludes))
            )
        if excludes & CORE_CAPABILITIES:
            raise InstallerError("Core shell, session, and workspace capabilities cannot be excluded.")
        selected = normalize_capabilities(selected - excludes)

        # Compatibility for one release: the old switch modifies the bundle.
        if self.args.metasploit == "enabled":
            selected = normalize_capabilities(set(selected) | {"metasploit"})
        elif self.args.metasploit == "disabled":
            selected = normalize_capabilities(set(selected) - {"metasploit"})
        return selected

    def _metasploit(self, env_path: Path) -> bool:
        if self.args.metasploit == "enabled":
            return True
        if self.args.metasploit == "disabled":
            return False
        existing = self.state.get("metasploit_enabled")
        if isinstance(existing, bool):
            return existing
        env_choice = read_env_value(env_path, "SKIP_METASPLOIT")
        if env_choice is not None:
            return env_choice.strip().lower() not in {"true", "1", "yes"}
        if self.args.non_interactive:
            return True
        return prompt_choice("Enable Metasploit tools", ("yes", "no"), "yes") == "yes"

    def _proxy(self, env_path: Path, *, browser_selected: bool = True) -> tuple[bool, str | None]:
        if not browser_selected:
            existing_proxy = read_env_value(env_path, "BROWSER_PROXY_URL")
            return bool(existing_proxy and existing_proxy.strip()), None
        existing = self.state.get("browser_proxy_configured")
        if self.args.browser_proxy == "direct":
            return False, ""
        if self.args.browser_proxy == "keep" and isinstance(existing, bool):
            return existing, None
        if self.args.browser_proxy == "keep":
            existing_proxy = read_env_value(env_path, "BROWSER_PROXY_URL")
            if existing_proxy is not None:
                return bool(existing_proxy.strip()), None
        env_proxy = os.getenv("BROWSER_PROXY_URL", "").strip()
        if env_proxy:
            return True, validate_proxy_url(env_proxy)
        if self.args.non_interactive:
            return False, ""
        use_proxy = prompt_choice(
            "Configure an authenticated browser proxy", ("yes", "no"), "no"
        )
        if use_proxy != "yes":
            return False, ""
        value = getpass.getpass("Browser proxy URL (hidden): ").strip()
        return True, validate_proxy_url(value)

    def _install_runtime(self, source: Path) -> None:
        requirements = source / "requirements.txt"
        if not requirements.is_file() and not self.args.dry_run:
            raise InstallerError(
                f"Locked requirements export is missing: {requirements}"
            )
        self.runner.run(
            [
                "uv",
                "tool",
                "install",
                "--python",
                "3.12",
                "--upgrade",
                "--force",
                "--with-requirements",
                requirements,
                "--editable",
                source,
            ],
            timeout=600,
            check=True,
        )
        self._verify_locked_runtime(requirements)

    def _verify_locked_runtime(self, requirements: Path) -> None:
        """Confirm the managed uv tool contains exactly locked dependency versions."""
        if self.args.dry_run:
            return
        directory_result = self.runner.run(
            ["uv", "tool", "dir"],
            timeout=30,
            check=True,
        )
        tool_root = Path(directory_result.stdout.strip()).expanduser()
        tool_environment = tool_root / PLUGIN_NAME
        python = tool_environment / (
            "Scripts/python.exe" if os.name == "nt" else "bin/python"
        )
        if not python.is_file():
            raise InstallerError(
                f"Could not locate the managed Hercules Python environment: {python}"
            )
        script = (
            "import importlib.metadata as m,json;"
            "print(json.dumps([[d.metadata.get('Name',''),d.version] "
            "for d in m.distributions()]))"
        )
        installed_result = self.runner.run(
            [python, "-c", script],
            timeout=60,
            check=True,
        )
        try:
            installed_rows = json.loads(installed_result.stdout)
        except (TypeError, ValueError) as exc:
            raise InstallerError(
                "The managed Hercules environment returned invalid package metadata."
            ) from exc
        locked, unconditional = _locked_versions(requirements)
        installed = {
            _normalized_distribution_name(str(name)): str(version)
            for name, version in installed_rows
            if str(name).strip()
        }
        mismatches = [
            f"{name}=={version} (locked {locked.get(name, 'missing')})"
            for name, version in sorted(installed.items())
            if name != PLUGIN_NAME and locked.get(name) != version
        ]
        missing = sorted(
            name
            for name in unconditional
            if name != PLUGIN_NAME and name not in installed
        )
        if mismatches or missing:
            details = []
            if mismatches:
                details.append("version mismatches: " + ", ".join(mismatches))
            if missing:
                details.append("missing locked packages: " + ", ".join(missing))
            raise InstallerError(
                "Managed Hercules dependencies do not match requirements.txt: "
                + "; ".join(details)
            )

    def _configure_environment(
        self,
        source: Path,
        *,
        capabilities: frozenset[str],
        proxy_value: str | None,
        workspace_root: Path | None = None,
    ) -> None:
        metasploit = "metasploit" in capabilities
        updates = {
            "SKIP_METASPLOIT": "false" if metasploit else "true",
            "HERCULES_INSTALLED_CAPABILITIES": format_capabilities(capabilities),
        }
        if metasploit:
            secret, generated, historical_default = ensure_msf_secret(source / ".env")
            if generated:
                updates["MSF_PASSWORD"] = secret
            if historical_default:
                print(
                    "Warning: the historical default Metasploit RPC password is still configured; "
                    "replace it in .env. The value was not printed.",
                    file=sys.stderr,
                )
        if read_env_value(
            source / ".env",
            "BROWSER_DISABLE_NON_PROXIED_UDP",
        ) is None:
            updates["BROWSER_DISABLE_NON_PROXIED_UDP"] = "true"
        if proxy_value is not None:
            updates["BROWSER_PROXY_URL"] = proxy_value
        if workspace_root is not None:
            updates["HERCULES_WORKSPACE_ROOT"] = str(workspace_root)
        upsert_env(source / ".env", updates, dry_run=self.args.dry_run)

    def _platform_status(self) -> dict[str, Any]:
        snapshot = detect_platform(which=shutil.which)
        context_output = ""
        info_output = ""
        if shutil.which("docker"):
            context_result = self.runner.run(
                ["docker", "context", "show"],
                timeout=10,
            )
            if context_result.returncode == 0:
                context_output = context_result.stdout.strip()
            info_result = self.runner.run(
                ["docker", "info", "--format", "{{json .}}"],
                timeout=15,
            )
            if info_result.returncode == 0:
                info_output = info_result.stdout
        return apply_docker_details(
            snapshot,
            context_output=context_output,
            info_output=info_output,
        )

    def _provision_runtime(
        self,
        source: Path,
        capabilities: frozenset[str],
    ) -> dict[str, Any]:
        assets = provision_wordlists(
            source,
            capabilities,
            dry_run=self.args.dry_run,
        )
        image = RuntimeProvisioner(self.runner, source).build(
            capabilities,
            rebuild=self.args.rebuild,
        )
        return {"image": image, "wordlists": assets}

    def _install_skill(self, source: Path, client: str, scope: str) -> Path:
        canonical = source / "skills" / PLUGIN_NAME
        if not (canonical / "SKILL.md").is_file() and not self.args.dry_run:
            raise InstallerError(f"Canonical Hercules skill is missing: {canonical}")
        target = skill_target(client, scope, self.project_dir)
        if client == "portable" and shutil.which("npx"):
            command = [
                "npx",
                "--yes",
                "skills",
                "add",
                str(source),
                "--skill",
                PLUGIN_NAME,
                "--agent",
                "*",
                "-y",
            ]
            if scope == "user":
                command.insert(-1, "-g")
            result = self.runner.run(command, cwd=self.project_dir, timeout=300)
            if result.returncode != 0 and not self.args.dry_run:
                print(
                    "Portable Agent Skills installer failed; using the direct-copy fallback.",
                    file=sys.stderr,
                )
        _safe_replace_tree(canonical, target, dry_run=self.args.dry_run)
        return target

    def _configure_codex(self, scope: str) -> Path:
        codex_home = Path(os.getenv("CODEX_HOME", _home() / ".codex")).expanduser()
        config = (
            self.project_dir / ".codex" / "config.toml"
            if scope == "project"
            else codex_home / "config.toml"
        )
        if scope == "user" and shutil.which("codex"):
            self.runner.run(
                ["codex", "mcp", "add", SERVER_NAME, "--", "hercules"],
                timeout=30,
                check=True,
            )
            verification = self.runner.run(
                ["codex", "mcp", "get", SERVER_NAME, "--json"],
                timeout=30,
            )
            if (
                not self.args.dry_run
                and (
                    verification.returncode != 0
                    or not _mcp_output_has_command(
                        verification.stdout,
                        "hercules",
                    )
                )
            ):
                raise InstallerError(
                    "Codex accepted the MCP update but did not verify the "
                    "replacement command as `hercules`."
                )
        else:
            write_codex_toml(config, dry_run=self.args.dry_run)
        return config

    def _configure_claude(self, scope: str) -> Path:
        config = (
            self.project_dir / ".mcp.json"
            if scope == "project"
            else _home() / ".claude.json"
        )
        if shutil.which("claude"):
            cli_scope = "project" if scope == "project" else "user"
            snapshot = config.read_bytes() if config.is_file() else None
            snapshot_mode = (
                config.stat().st_mode & 0o777 if config.is_file() else 0o600
            )
            existing = self.runner.run(
                ["claude", "mcp", "get", SERVER_NAME], timeout=30
            )
            try:
                if existing.returncode == 0:
                    self.runner.run(
                        [
                            "claude",
                            "mcp",
                            "remove",
                            "--scope",
                            cli_scope,
                            SERVER_NAME,
                        ],
                        timeout=30,
                        check=True,
                    )
                self.runner.run(
                    [
                        "claude",
                        "mcp",
                        "add",
                        "--transport",
                        "stdio",
                        "--scope",
                        cli_scope,
                        SERVER_NAME,
                        "--",
                        "hercules",
                    ],
                    cwd=self.project_dir,
                    timeout=30,
                    check=True,
                )
                verification = self.runner.run(
                    ["claude", "mcp", "get", SERVER_NAME],
                    timeout=30,
                )
                if (
                    not self.args.dry_run
                    and (
                        verification.returncode != 0
                        or "hercules" not in verification.stdout.lower()
                    )
                ):
                    raise InstallerError(
                        "Claude MCP registration could not be verified."
                    )
            except Exception:
                if not self.args.dry_run:
                    if snapshot is None:
                        config.unlink(missing_ok=True)
                    else:
                        atomic_write_private_bytes(config, snapshot)
                        if os.name != "nt":
                            config.chmod(snapshot_mode)
                raise
        else:
            write_json_mcp(config, dry_run=self.args.dry_run)
        return config

    def _configure_cursor(self, scope: str) -> Path:
        config = (
            self.project_dir / ".cursor" / "mcp.json"
            if scope == "project"
            else _home() / ".cursor" / "mcp.json"
        )
        write_json_mcp(config, dry_run=self.args.dry_run)
        return config

    def _configure_portable(self, scope: str) -> Path:
        config = (
            self.project_dir / "hercules-mcp.json"
            if scope == "project"
            else self.config_dir / "hercules-mcp.json"
        )
        write_json_mcp(config, dry_run=self.args.dry_run)
        return config

    def _configure_clients(
        self, source: Path, clients: list[str], scope: str
    ) -> tuple[dict[str, str], dict[str, str]]:
        skill_paths: dict[str, str] = {}
        config_paths: dict[str, str] = {}
        adapters = {
            "codex": self._configure_codex,
            "claude": self._configure_claude,
            "cursor": self._configure_cursor,
            "portable": self._configure_portable,
        }
        for client in clients:
            skill_paths[client] = str(self._install_skill(source, client, scope))
            config_paths[client] = str(adapters[client](scope))
        return skill_paths, config_paths

    def _runtime_ready(
        self,
        source: Path,
        capabilities: frozenset[str],
    ) -> tuple[bool, str, dict[str, Any]]:
        try:
            components = RuntimeProvisioner(self.runner, source).status(capabilities)
        except Exception as exc:
            return False, clean_detail(str(exc)), {}
        detail = clean_detail(str(components.get("detail", "ready")))
        if not components.get("wordlists", {}).get("ready", False):
            detail = "required wordlists are missing or invalid"
        return bool(components.get("ready")), detail, components

    def _mcp_probe(self, source: Path) -> dict[str, Any]:
        executable = shutil.which("hercules")
        if not executable:
            return {
                "available": False,
                "started": False,
                "ok": False,
                "error": "The hercules executable is not on PATH.",
            }
        result = self.runner.run(
            [executable, "--validate-install-json"],
            cwd=source,
            timeout=30,
        )
        if result.returncode != 0:
            return {
                "available": True,
                "started": False,
                "ok": False,
                "error": clean_detail(
                    result.stderr.strip()
                    or result.stdout.strip()
                    or f"Registration probe exited with status {result.returncode}."
                ),
            }
        try:
            payload = json.loads(result.stdout)
            tools = int(payload["tools"])
            resources = int(payload["resources"])
            metasploit_enabled = bool(payload["metasploit_enabled"])
            installed = payload.get("installed_capabilities")
            if not isinstance(installed, list) or not all(
                isinstance(key, str) for key in installed
            ):
                installed = list(ALL_CAPABILITIES)
            disabled = payload.get("operator_disabled_tools", [])
            if not isinstance(disabled, list) or not all(
                isinstance(name, str) for name in disabled
            ):
                raise TypeError("operator_disabled_tools must be a string list")
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            return {
                "available": True,
                "started": False,
                "ok": False,
                "error": f"Registration probe returned invalid JSON: {exc}",
            }
        try:
            installed_set = normalize_capabilities(installed)
        except ValueError:
            installed_set = ALL_CAPABILITIES
        expected_names = set(tools_for_capabilities(installed_set))
        if not metasploit_enabled:
            expected_names -= METASPLOIT_TOOLS
        expected_names -= set(disabled)
        expected_tools = len(expected_names)
        ok = tools == expected_tools and resources == EXPECTED_RESOURCES
        return {
            "available": True,
            "started": True,
            "ok": ok,
            "tools": tools,
            "expected_tools": expected_tools,
            "resources": resources,
            "expected_resources": EXPECTED_RESOURCES,
            "metasploit_enabled": metasploit_enabled,
            "installed_capabilities": sorted(installed_set),
            "operator_disabled_tools": sorted(set(disabled)),
            "error": (
                ""
                if ok
                else (
                    f"Expected {expected_tools} tools and {EXPECTED_RESOURCES} resources; "
                    f"found {tools} tools and {resources} resources."
                )
            ),
        }

    def collect_status(self, source: Path | None = None) -> dict[str, Any]:
        checkout_value = source or Path(
            self.state.get("checkout", data_root() / "source")
        )
        checkout = Path(checkout_value).expanduser().resolve()
        explicit_capabilities = str(getattr(self.args, "capabilities", "") or "").strip()
        process_capabilities = os.getenv("HERCULES_INSTALLED_CAPABILITIES", "").strip()
        dotenv_capabilities = read_env_value(
            checkout / ".env",
            "HERCULES_INSTALLED_CAPABILITIES",
        )
        saved_capabilities = self.state.get("installed_capabilities")
        try:
            if explicit_capabilities:
                installed_capabilities = parse_capabilities(
                    explicit_capabilities,
                    legacy_all=False,
                )
            elif process_capabilities:
                installed_capabilities = parse_capabilities(process_capabilities)
            elif dotenv_capabilities:
                installed_capabilities = parse_capabilities(dotenv_capabilities)
            elif isinstance(saved_capabilities, list):
                installed_capabilities = normalize_capabilities(saved_capabilities)
            else:
                installed_capabilities = ALL_CAPABILITIES
        except ValueError as exc:
            if explicit_capabilities or process_capabilities or dotenv_capabilities:
                raise InstallerError(
                    "The active Hercules capability selection contains an unknown key. "
                    "Run hercules-install catalog --json and correct the selection."
                ) from exc
            installed_capabilities = ALL_CAPABILITIES
        commands = {name: bool(shutil.which(name)) for name in ("git", "uv", "docker")}
        daemon = False
        if commands["docker"]:
            daemon = self.runner.run(["docker", "info"], timeout=15).returncode == 0
        setup_ready, setup_detail, setup_components = (
            self._runtime_ready(checkout, installed_capabilities)
            if checkout.is_dir() and commands["docker"] and daemon
            else (False, "Checkout or Docker is unavailable.", {})
        )
        mcp_probe = (
            self._mcp_probe(checkout)
            if checkout.is_dir()
            else {
                "available": bool(shutil.which("hercules")),
                "started": False,
                "ok": False,
                "error": "Checkout is unavailable.",
            }
        )
        surface = capture_surface()
        saved_skill_paths = self.state.get("skill_paths", {})
        skills = {
            client: Path(path).joinpath("SKILL.md").is_file()
            for client, path in saved_skill_paths.items()
            if isinstance(path, str)
        }
        saved_configs = self.state.get("config_paths", {})
        configs = {
            client: mcp_config_is_valid(Path(path), client)
            for client, path in saved_configs.items()
            if isinstance(path, str)
        }
        manifests: dict[str, bool] = {}
        for adapter in ("codex", "claude", "cursor"):
            manifest = checkout / f".{adapter}-plugin" / "plugin.json"
            try:
                parsed = json.loads(manifest.read_text(encoding="utf-8"))
                manifests[adapter] = parsed.get("name") == PLUGIN_NAME
            except (OSError, ValueError, AttributeError):
                manifests[adapter] = False
        surface_ok = (
            surface["full_tools"] == EXPECTED_FULL_TOOLS
            and surface["light_tools"] == EXPECTED_LIGHT_TOOLS
            and surface["resources"] == EXPECTED_RESOURCES
            and surface["catalog_matches"]
            and not surface["errors"]
        )
        skill_routing = validate_skill_routing(checkout, surface)
        configured_workspace = read_env_value(
            checkout / ".env",
            "HERCULES_WORKSPACE_ROOT",
        )
        workspace = Path(
            configured_workspace or checkout / "workspace"
        ).expanduser().resolve()
        workspace_bytes = 0
        workspace_sessions = 0
        if workspace.is_dir():
            for root, directories, files in os.walk(workspace, followlinks=False):
                root_path = Path(root)
                directories[:] = [
                    name
                    for name in directories
                    if not (root_path / name).is_symlink()
                ]
                for name in files:
                    candidate = root_path / name
                    try:
                        if not candidate.is_symlink():
                            workspace_bytes += candidate.stat().st_size
                    except OSError:
                        continue
            workspace_sessions = sum(
                1
                for item in workspace.iterdir()
                if item.is_dir() and re.fullmatch(r"[0-9a-f]{8}", item.name)
            )
        platform_status = self._platform_status()
        return {
            "ready": bool(
                self.state
                and all(commands.values())
                and daemon
                and setup_ready
                and mcp_probe["ok"]
                and surface_ok
                and skill_routing["ok"]
                and skills
                and all(skills.values())
                and configs
                and all(configs.values())
                and all(manifests.values())
            ),
            "installed_state": bool(self.state),
            "checkout": str(checkout),
            "platform": platform_status,
            "paths": {
                "data_root": str(data_root().resolve()),
                "config_root": str(self.config_dir.resolve()),
                "state": str(self.state_path.resolve()),
                "checkout": str(checkout),
                "environment": str((checkout / ".env").resolve()),
                "workspace": str(workspace),
            },
            "workspace": {
                "path": str(workspace),
                "exists": workspace.is_dir(),
                "sessions": workspace_sessions,
                "bytes": workspace_bytes,
            },
            "commands": commands,
            "docker_daemon": daemon,
            "setup_ready": setup_ready,
            "setup_detail": setup_detail,
            "setup_components": setup_components,
            "runtime": setup_components,
            "installed_capabilities": sorted(installed_capabilities),
            "omitted_capabilities": sorted(ALL_CAPABILITIES - installed_capabilities),
            "required_wordlists": list(required_wordlists(installed_capabilities)),
            "mcp_probe": mcp_probe,
            "skills": skills,
            "mcp_configs": configs,
            "plugin_manifests": manifests,
            "surface": surface,
            "skill_routing": skill_routing,
        }

    @staticmethod
    def doctor_issues(status: dict[str, Any]) -> list[dict[str, str]]:
        issues: list[dict[str, str]] = []
        if not status.get("installed_state"):
            issues.append(
                {
                    "code": "installer_state_missing",
                    "message": "Run hercules-install install to register a skill and MCP client.",
                }
            )
        for name, present in status["commands"].items():
            if not present:
                issues.append(
                    {
                        "code": f"missing_{name}",
                        "message": prerequisite_guidance(
                            status.get("platform", {}),
                            name,
                        ),
                    }
                )
        if status["commands"].get("docker") and not status["docker_daemon"]:
            issues.append(
                {
                    "code": "docker_daemon_unavailable",
                    "message": prerequisite_guidance(
                        status.get("platform", {}),
                        "docker_daemon",
                    ),
                }
            )
        probe = status.get("mcp_probe")
        if isinstance(probe, dict) and not probe.get("ok"):
            if not probe.get("available"):
                code = "mcp_executable_missing"
                message = (
                    "Install Hercules and ensure the uv tool bin directory is on PATH."
                )
            elif probe.get("started"):
                code = "mcp_count_mismatch"
                message = str(
                    probe.get("error") or "The registered MCP surface is incorrect."
                )
            else:
                code = "mcp_startup_failure"
                message = str(
                    probe.get("error") or "The MCP registration probe failed."
                )
            issues.append({"code": code, "message": clean_detail(message)})
        if status["docker_daemon"] and not status["setup_ready"]:
            components = status.get("setup_components", {})
            image_exists = bool(
                components.get("exists", components.get("image_exists", False))
            )
            runtime_ready = bool(
                components.get(
                    "runtime_ready",
                    components.get("image_runtime_ready", False),
                )
            )
            wordlists_ready = bool(
                components.get("wordlists", {}).get(
                    "ready",
                    components.get("wordlists_ready", False),
                )
            )
            if components and not image_exists:
                issues.append(
                    {
                        "code": "docker_image_missing",
                        "message": "Build the Hercules image with hercules-install install.",
                    }
                )
            elif components and not runtime_ready:
                issues.append(
                    {
                        "code": "docker_image_invalid",
                        "message": "Rebuild the selected image with hercules-install install --rebuild.",
                    }
                )
            elif (
                components
                and components.get("browser_ready") is False
                and (
                    "browser" in status.get("installed_capabilities", [])
                    or "browser_ready" in components
                )
            ):
                issues.append(
                    {
                        "code": "browser_stack_missing",
                        "message": "Rebuild the image to restore the browser capability.",
                    }
                )
            elif components and not wordlists_ready:
                issues.append(
                    {
                        "code": "wordlists_not_ready",
                        "message": "Run hercules-install install to verify the pinned wordlists.",
                    }
                )
            else:
                issues.append(
                    {
                        "code": "setup_incomplete",
                        "message": "Run hercules-install install --rebuild.",
                    }
                )
        for client, valid in status["skills"].items():
            if not valid:
                issues.append(
                    {
                        "code": f"missing_skill_{client}",
                        "message": f"Reinstall the {client} skill adapter.",
                    }
                )
        for client, valid in status["mcp_configs"].items():
            if not valid:
                issues.append(
                    {
                        "code": f"missing_mcp_{client}",
                        "message": f"Re-register Hercules for {client}.",
                    }
                )
        for client, valid in status["plugin_manifests"].items():
            if not valid:
                issues.append(
                    {
                        "code": f"invalid_plugin_{client}",
                        "message": f"The {client} plugin manifest is missing or invalid.",
                    }
                )
        surface = status["surface"]
        if (
            surface["full_tools"] != EXPECTED_FULL_TOOLS
            or surface["light_tools"] != EXPECTED_LIGHT_TOOLS
            or surface["resources"] != EXPECTED_RESOURCES
            or not surface["catalog_matches"]
        ):
            issues.append(
                {
                    "code": "surface_mismatch",
                    "message": (
                        f"Expected {EXPECTED_FULL_TOOLS}/{EXPECTED_LIGHT_TOOLS} tools and "
                        f"{EXPECTED_RESOURCES} resources; found "
                        f"{surface['full_tools']}/{surface['light_tools']} and {surface['resources']}."
                    ),
                }
            )
        for error in surface["errors"]:
            issues.append({"code": "surface_import_error", "message": redact(error)})
        routing = status.get("skill_routing", {})
        if isinstance(routing, dict) and not routing.get("ok"):
            issues.append(
                {
                    "code": "skill_routing_mismatch",
                    "message": (
                        "Canonical skill routing is missing tool/selector coverage: "
                        f"tools={routing.get('missing_tools', [])}; "
                        f"parameters={routing.get('missing_parameters', [])}; "
                        f"selectors={routing.get('missing_selectors', [])}; "
                        f"resources={routing.get('missing_resources', [])}"
                    ),
                }
            )
        return issues

    def _print(self, payload: dict[str, Any]) -> None:
        if self.args.json:
            rendered = dict(payload)
            if self.runner.dry_run:
                rendered["dry_run"] = True
                rendered["planned_commands"] = self.runner.commands
            print(json.dumps(rendered, indent=2, sort_keys=True))
            return
        status = payload.get("status", payload)
        if "ready" in status:
            print(
                f"Hercules installer status: {'ready' if status['ready'] else 'needs attention'}"
            )
            print(f"  checkout: {status['checkout']}")
            print(
                "  surface: "
                f"{status['surface']['full_tools']} full / "
                f"{status['surface']['light_tools']} lightweight tools, "
                f"{status['surface']['resources']} resources"
            )
        for issue in payload.get("issues", []):
            print(f"  [{issue['code']}] {issue['message']}")
        for client, adapter in payload.get("adapters", {}).items():
            print(f"  {client} skill: {adapter['skill']}")
            print(f"  {client} MCP config: {adapter['mcp_config']}")
        if payload.get("portable_manual_configuration"):
            print(
                "  Portable host: register the displayed STDIO config and skill path "
                "in the client's supported settings."
            )
        if self.runner.dry_run:
            print("Dry-run commands:")
            for command in self.runner.commands:
                print("  " + " ".join(command))

    def execute(self) -> int:
        action = self.args.action
        if action == "catalog":
            payload = catalog_payload()
            if self.args.json:
                print(json.dumps(payload, indent=2, sort_keys=True))
            else:
                print("Hercules capability bundles (core is always included):")
                for row in payload["capabilities"]:
                    suffix = " [mandatory]" if row["mandatory"] else ""
                    tools = ", ".join(row["mcp_tools"])
                    print(f"  {row['key']}{suffix}: {row['description']} — {tools}")
            return 0
        if action in {"check", "doctor"}:
            source = (
                Path(self.args.source).expanduser().resolve()
                if self.args.source
                else None
            )
            status = self.collect_status(source)
            payload: dict[str, Any] = {"status": status}
            if action == "doctor":
                payload["issues"] = self.doctor_issues(status)
            self._print(payload)
            if self.args.runtime_only:
                return 0 if status.get("runtime", {}).get("ready") else 1
            return 0 if status["ready"] else 1

        explicit_source = Path(self.args.source) if self.args.source else None
        selected_clients = resolve_clients(
            self.args.client, non_interactive=self.args.non_interactive
        )
        previous_clients = self.state.get("clients", [])
        clients = list(
            dict.fromkeys(
                [
                    *(
                        client
                        for client in previous_clients
                        if isinstance(client, str) and client in CLIENTS
                    ),
                    *selected_clients,
                ]
            )
        )
        checkout = data_root() / "source"
        managed_checkout_preexisting = checkout.exists()
        preference_source = (
            explicit_source.expanduser().resolve() if explicit_source else checkout
        )
        preference_env = preference_source / ".env"
        scope = self._scope()
        capabilities = self._capabilities(preference_env)
        self._prerequisites(
            require_git=explicit_source is None or (explicit_source / ".git").exists()
        )
        metasploit = "metasploit" in capabilities
        proxy_configured, proxy_value = self._proxy(
            preference_env,
            browser_selected="browser" in capabilities,
        )
        source, commit = prepare_checkout(
            self.runner,
            checkout,
            explicit_source=explicit_source,
            update=action in {"install", "upgrade"},
        )
        self._install_runtime(source)
        runtime_result = self._provision_runtime(source, capabilities)
        env_path = source / ".env"
        previous_env = env_path.read_bytes() if env_path.is_file() else None
        try:
            self._configure_environment(
                source,
                capabilities=capabilities,
                proxy_value=proxy_value,
                workspace_root=(
                    data_root() / "workspaces"
                    if (
                        not self.state
                        and explicit_source is None
                        and not managed_checkout_preexisting
                    )
                    else None
                ),
            )
            skill_paths, config_paths = self._configure_clients(source, clients, scope)
        except Exception:
            if not self.args.dry_run:
                if previous_env is None:
                    env_path.unlink(missing_ok=True)
                else:
                    atomic_write_private_bytes(env_path, previous_env)
            raise
        skill_paths = {
            **(
                self.state.get("skill_paths", {})
                if isinstance(self.state.get("skill_paths"), dict)
                else {}
            ),
            **skill_paths,
        }
        config_paths = {
            **(
                self.state.get("config_paths", {})
                if isinstance(self.state.get("config_paths"), dict)
                else {}
            ),
            **config_paths,
        }
        state = {
            **self.state,
            "schema_version": STATE_SCHEMA_VERSION,
            "checkout": str(source),
            "commit": commit,
            "version": project_version(source),
            "scope": scope,
            "clients": clients,
            "metasploit_enabled": metasploit,
            "installed_capabilities": sorted(capabilities),
            "image": runtime_result["image"].get("image", ""),
            "image_fingerprint": runtime_result["image"].get("fingerprint", ""),
            "expected_tool_count": len(
                set(tools_for_capabilities(capabilities))
                - (METASPLOIT_TOOLS if not metasploit else set())
                - set(parse_disabled(read_env_value(source / ".env", "HERCULES_DISABLED_TOOLS") or ""))
            ),
            "browser_proxy_configured": proxy_configured,
            "workspace_root": (
                read_env_value(source / ".env", "HERCULES_WORKSPACE_ROOT") or ""
            ),
            "skill_paths": skill_paths,
            "config_paths": config_paths,
        }
        try:
            save_state(self.state_path, state, dry_run=self.args.dry_run)
        except Exception:
            # The environment is part of the same installation transaction as
            # the non-secret state. Restore it if the final state commit fails.
            if not self.args.dry_run:
                if previous_env is None:
                    env_path.unlink(missing_ok=True)
                else:
                    atomic_write_private_bytes(env_path, previous_env)
            raise
        self.state = state
        status = self.collect_status(source)
        payload = {
            "installed": not self.args.dry_run,
            "status": status,
            "manual_restart_required": clients,
            "adapters": {
                client: {
                    "skill": skill_paths[client],
                    "mcp_config": config_paths[client],
                }
                for client in clients
            },
            "portable_manual_configuration": "portable" in clients,
        }
        self._print(payload)
        if self.args.dry_run:
            return 0
        return 0 if status["ready"] else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hercules-install",
        description="Install, upgrade, verify, or diagnose Hercules MCP and its Agent Skill.",
    )
    parser.add_argument(
        "action",
        nargs="?",
        choices=("install", "upgrade", "check", "doctor", "catalog"),
        default="install",
    )
    parser.add_argument(
        "--client",
        choices=("auto", "codex", "claude", "cursor", "portable", "all"),
        default="auto",
    )
    parser.add_argument("--scope", choices=("user", "project"))
    parser.add_argument("--project-dir", default="")
    parser.add_argument(
        "--source",
        default="",
        help="Use an existing checkout instead of the managed source.",
    )
    parser.add_argument(
        "--metasploit",
        choices=("keep", "enabled", "disabled"),
        default="keep",
    )
    parser.add_argument(
        "--capabilities",
        default="",
        help="Install all, core, or a comma-separated set from `catalog`.",
    )
    parser.add_argument(
        "--exclude-capabilities",
        default="",
        help="Comma-separated optional bundles to omit from the selected base.",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Rebuild the selected immutable Docker image without cache.",
    )
    parser.add_argument(
        "--runtime-only",
        action="store_true",
        help="For check, gate only Docker image/asset readiness.",
    )
    parser.add_argument(
        "--browser-proxy",
        choices=("keep", "ask", "direct"),
        default="keep",
    )
    parser.add_argument("--non-interactive", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    try:
        exit_code = HerculesInstaller(args).execute()
    except (InstallerError, OSError) as exc:
        if args.json:
            print(json.dumps({"status": "error", "error": redact(str(exc))}, indent=2))
        else:
            print(f"Hercules installation failed: {redact(str(exc))}", file=sys.stderr)
        raise SystemExit(1)
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
