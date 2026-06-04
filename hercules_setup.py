#!/usr/bin/env python3
"""
Hercules MCP Server — First-Time Setup (interactive)

Run this once before using the Hercules MCP server. It will:
  1. Verify Docker is installed and the daemon is running.
  2. (Interactive) Let you opt out of individual MCP tools — watching the
     context-token cost shrink live — then save the selection to .env.
  3. Build the hercules-kali Docker image (bakes ALL tools, regardless of which
     ones you register).
  4. Download SecLists and rockyou.txt wordlists locally.

Opting out of a tool only stops it from being *registered* as an MCP tool, which
removes its name/description/schema from the model's context (that is the token
saving). The binary stays in the image, so the agent can still run it via
shell_exec — you only opt out of the structured tool, never the capability.

Usage:
    python hercules_setup.py            # Interactive TUI (falls back to classic if no TTY)
    python hercules_setup.py --classic  # Skip the TUI; build non-interactively
    python hercules_setup.py --yes      # Non-interactive, accept defaults, build
    python hercules_setup.py --check    # Check if setup is complete
    python hercules_setup.py --tokens   # Print the per-tool token report and exit
    python hercules_setup.py --rebuild  # Force rebuild of the Docker image

Works on Windows and Linux. The interactive UI uses Textual
(https://textual.textualize.io/) and is installed on demand.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import tarfile
import time
import urllib.request
import zipfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent
# Make the `hercules` package importable when run as a loose script.
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DOCKERFILE = PROJECT_ROOT / "Dockerfile"
ENTRYPOINT = PROJECT_ROOT / "docker" / "entrypoint.sh"
WORDLISTS_DIR = PROJECT_ROOT / "wordlists"
ENV_PATH = PROJECT_ROOT / ".env"
IMAGE_NAME = "hercules-kali"

WORDLIST_URLS = {
    "SecLists.zip": "https://github.com/danielmiessler/SecLists/archive/refs/heads/master.zip",
    "rockyou.txt.tar.gz": "https://github.com/danielmiessler/SecLists/raw/master/Passwords/Leaked-Databases/rockyou.txt.tar.gz",
}

# Token-model tuning. These are deliberately conservative estimates of the MCP
# framing each tool adds on top of its name/description/schema text.
_PER_TOOL_FRAMING = 6     # braces/keys for {"name","description","inputSchema"}
_SCHEMA_FLAT = 40         # fallback per-tool schema cost when signatures can't be read
_BASE_PROTOCOL = 8        # misc. protocol overhead added to the server instructions

# ---------------------------------------------------------------------------
# Colors (cross-platform)
# ---------------------------------------------------------------------------

if platform.system() == "Windows":
    os.system("")  # Enable ANSI escape codes on Windows 10+

# Emoji / box-drawing chars in the banners and token report would crash on the
# legacy cp1252 console. Force UTF-8 with replacement so output never aborts.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

class C:
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    RED    = "\033[91m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    BLUE   = "\033[94m"
    CYAN   = "\033[96m"
    DIM    = "\033[2m"


def banner():
    print(f"""
{C.CYAN}{C.BOLD}+============================================================+
|               HERCULES MCP SERVER SETUP                    |
|          AI-Orchestrated Offensive Security                 |
+============================================================+{C.RESET}
""")


def step(num: int, total: int, msg: str):
    print(f"\n{C.BLUE}{C.BOLD}[{num}/{total}]{C.RESET} {C.BOLD}{msg}{C.RESET}")
    print(f"{C.DIM}{'-' * 58}{C.RESET}")


def ok(msg: str):
    print(f"  {C.GREEN}[OK]{C.RESET} {msg}")


def warn(msg: str):
    print(f"  {C.YELLOW}[!!]{C.RESET} {msg}")


def fail(msg: str):
    print(f"  {C.RED}[FAIL]{C.RESET} {msg}")


def info(msg: str):
    print(f"  {C.DIM}> {msg}{C.RESET}")


# ---------------------------------------------------------------------------
# Step 1: Check Docker
# ---------------------------------------------------------------------------

def check_docker() -> bool:
    """Verify Docker CLI exists and daemon is running."""
    docker_path = shutil.which("docker")
    if not docker_path:
        fail("Docker CLI not found on PATH.")
        print()
        if platform.system() == "Windows":
            print(f"  {C.YELLOW}Install Docker Desktop:{C.RESET}")
            print(f"  https://docs.docker.com/desktop/install/windows-install/")
        else:
            print(f"  {C.YELLOW}Install Docker:{C.RESET}")
            print(f"  curl -fsSL https://get.docker.com | sh")
            print(f"  sudo systemctl start docker")
            print(f"  sudo usermod -aG docker $USER")
        return False

    ok(f"Docker CLI found: {docker_path}")

    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            fail("Docker daemon is not running.")
            if platform.system() == "Windows":
                print(f"\n  {C.YELLOW}Start Docker Desktop from the Start Menu or system tray.{C.RESET}")
            else:
                print(f"\n  {C.YELLOW}Start the Docker daemon:{C.RESET}")
                print(f"  sudo systemctl start docker")
            return False
    except FileNotFoundError:
        fail("Docker command failed.")
        return False
    except subprocess.TimeoutExpired:
        fail("Docker daemon is not responding (timeout).")
        return False

    ok("Docker daemon is running.")
    return True


# ---------------------------------------------------------------------------
# Step 2: Build Docker Image
# ---------------------------------------------------------------------------

def check_image_exists() -> bool:
    """Check if the hercules-kali image exists locally."""
    result = subprocess.run(
        ["docker", "images", "-q", IMAGE_NAME],
        capture_output=True, text=True,
    )
    return bool(result.stdout.strip())


def check_image_runtime_ready() -> bool:
    """Verify the existing image contains the runtime files Hercules requires."""
    result = subprocess.run(
        [
            "docker", "run", "--rm",
            "--entrypoint", "/bin/sh",
            IMAGE_NAME,
            "-c",
            "test -x /entrypoint.sh "
            "&& ! head -n 1 /entrypoint.sh | od -An -tx1 | grep -qi '0d' "
            "&& command -v nmap >/dev/null "
            "&& command -v nuclei >/dev/null "
            "&& command -v ffuf >/dev/null "
            "&& command -v amass >/dev/null",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    return result.returncode == 0


def check_browser_ready() -> bool:
    """Verify the stealth browser stack is baked into the image.

    Checks Node + agent-browser (control) + cloakbrowser (stealth Chromium
    binary installed). Non-fatal: the browser_* tools degrade gracefully if
    absent.
    """
    try:
        result = subprocess.run(
            [
                "docker", "run", "--rm",
                "--entrypoint", "/bin/sh",
                IMAGE_NAME,
                "-c",
                "command -v node >/dev/null "
                "&& command -v agent-browser >/dev/null "
                "&& python3 -c 'import cloakbrowser' "
                "&& python3 -m cloakbrowser info 2>/dev/null | grep -qi 'Installed: *True'",
            ],
            capture_output=True, text=True, timeout=60,
        )
        return result.returncode == 0
    except Exception:
        return False


def build_image(force_rebuild: bool = False) -> bool:
    """Build the hercules-kali Docker image from the Dockerfile."""
    if not force_rebuild and check_image_exists():
        if check_image_runtime_ready():
            ok(f"Image '{IMAGE_NAME}' already exists. Skipping build.")
            return True
        warn(f"Image '{IMAGE_NAME}' exists but is missing required runtime files. Rebuilding.")

    if not DOCKERFILE.exists():
        fail(f"Dockerfile not found at: {DOCKERFILE}")
        return False

    if not ENTRYPOINT.exists():
        fail(f"entrypoint.sh not found at: {ENTRYPOINT}")
        return False

    info(f"Building '{IMAGE_NAME}' from Dockerfile...")
    info("This is a one-time operation. It may take 10-15 minutes.")
    info("All offensive security tools are being baked into the image.")
    print()

    build_attempts = [
        ["docker", "build", "--pull", "-t", IMAGE_NAME, "."],
    ]
    if force_rebuild:
        build_attempts[0].insert(3, "--no-cache")
    else:
        build_attempts.append(["docker", "build", "--pull", "--no-cache", "-t", IMAGE_NAME, "."])

    start = time.time()
    last_returncode = 1

    for attempt_num, cmd in enumerate(build_attempts, start=1):
        if attempt_num > 1:
            warn("Docker build failed. Retrying once with --pull --no-cache to refresh Kali package indexes.")
            print()

        process = subprocess.Popen(
            cmd,
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        for line in process.stdout:
            line = line.strip()
            if not line:
                continue

            lower = line.lower()
            interesting_error = any(
                marker in lower
                for marker in (
                    "error",
                    "failed",
                    "e:",
                    "unable to",
                    "temporary failure",
                    "hash sum mismatch",
                )
            )

            if line.startswith("#") and ("[" in line or "RUN" in line or "COPY" in line or "FROM" in line):
                print(f"  {C.CYAN}>{C.RESET} {line[:110]}")
            elif interesting_error:
                print(f"  {C.RED}>{C.RESET} {line[:180]}")

        process.wait()
        last_returncode = process.returncode
        if process.returncode == 0:
            elapsed = time.time() - start
            ok(f"Image '{IMAGE_NAME}' built successfully in {elapsed:.0f}s.")
            return True

    fail(f"Docker build failed (exit code {last_returncode}).")
    return False


# ---------------------------------------------------------------------------
# Step 3: Download Wordlists
# ---------------------------------------------------------------------------

def download_with_progress(url: str, dest: Path, label: str) -> bool:
    """Download a file with a simple progress indicator."""
    try:
        def _reporthook(block_num, block_size, total_size):
            downloaded = block_num * block_size
            if total_size > 0:
                pct = min(100, downloaded * 100 // total_size)
                mb_done = downloaded / (1024 * 1024)
                mb_total = total_size / (1024 * 1024)
                bar_len = 30
                filled = int(bar_len * pct / 100)
                bar = "#" * filled + "." * (bar_len - filled)
                print(f"\r  {C.DIM}[{bar}] {pct}% ({mb_done:.1f}/{mb_total:.1f} MB){C.RESET}", end="", flush=True)
            else:
                mb_done = downloaded / (1024 * 1024)
                print(f"\r  {C.DIM}Downloaded {mb_done:.1f} MB...{C.RESET}", end="", flush=True)

        urllib.request.urlretrieve(url, str(dest), reporthook=_reporthook)
        print()
        ok(f"{label} downloaded.")
        return True
    except Exception as exc:
        print()
        fail(f"Failed to download {label}: {exc}")
        return False


def is_valid_wordlist_archive(filename: str, path: Path) -> bool:
    """Return True when a downloaded wordlist archive is readable."""
    if not path.exists() or path.stat().st_size == 0:
        return False
    if filename.endswith(".zip"):
        return zipfile.is_zipfile(path)
    if filename.endswith(".tar.gz"):
        return tarfile.is_tarfile(path)
    return True


def ensure_wordlists() -> bool:
    """Download SecLists and rockyou.txt if not already present."""
    WORDLISTS_DIR.mkdir(parents=True, exist_ok=True)
    all_ok = True

    for filename, url in WORDLIST_URLS.items():
        dest = WORDLISTS_DIR / filename
        if is_valid_wordlist_archive(filename, dest):
            size_mb = dest.stat().st_size / (1024 * 1024)
            ok(f"{filename} already present ({size_mb:.1f} MB).")
            continue
        if dest.exists():
            warn(f"{filename} is present but invalid. Re-downloading.")
            dest.unlink()

        info(f"Downloading {filename}...")
        if not download_with_progress(url, dest, filename) or not is_valid_wordlist_archive(filename, dest):
            warn(f"{filename} could not be downloaded. It will not be available inside the container.")
            if dest.exists() and not is_valid_wordlist_archive(filename, dest):
                dest.unlink()
            all_ok = False

    return all_ok


# ---------------------------------------------------------------------------
# Status check (used by MCP server)
# ---------------------------------------------------------------------------

def is_setup_complete() -> dict:
    """
    Quick check returning setup status.
    Used by the MCP server to decide whether to start or show an error.
    """
    status = {
        "docker_available": False,
        "image_exists": False,
        "image_runtime_ready": False,
        "browser_ready": False,
        "wordlists_ready": False,
        "ready": False,
        "errors": [],
    }

    docker_path = shutil.which("docker")
    if not docker_path:
        status["errors"].append("Docker is not installed. Install Docker and run: python hercules_setup.py")
        return status

    try:
        result = subprocess.run(["docker", "info"], capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            status["errors"].append("Docker daemon is not running. Start Docker and retry.")
            return status
    except Exception:
        status["errors"].append("Docker daemon is not responding.")
        return status

    status["docker_available"] = True

    if check_image_exists():
        status["image_exists"] = True
        if check_image_runtime_ready():
            status["image_runtime_ready"] = True
            status["browser_ready"] = check_browser_ready()
        else:
            status["errors"].append(
                f"The '{IMAGE_NAME}' Docker image exists but is not runtime-ready. "
                f"Run: python hercules_setup.py --rebuild"
            )
    else:
        status["errors"].append(
            f"The '{IMAGE_NAME}' Docker image has not been built yet. "
            f"Run: python hercules_setup.py"
        )

    wl_dir = PROJECT_ROOT / "wordlists"
    if (
        is_valid_wordlist_archive("SecLists.zip", wl_dir / "SecLists.zip")
        and is_valid_wordlist_archive("rockyou.txt.tar.gz", wl_dir / "rockyou.txt.tar.gz")
    ):
        status["wordlists_ready"] = True

    status["ready"] = (
        status["docker_available"]
        and status["image_exists"]
        and status["image_runtime_ready"]
    )
    return status


# ---------------------------------------------------------------------------
# Token model — estimate the context cost of the registered tool surface
# ---------------------------------------------------------------------------

_ENC = None
_ENC_TRIED = False


def _estimate_tokens(text: str) -> int:
    """Estimate token count. Uses tiktoken when available, else a ~4 chars/token
    heuristic. Only relative deltas matter for the live meter, so either is fine."""
    global _ENC, _ENC_TRIED
    if not text:
        return 0
    if not _ENC_TRIED:
        _ENC_TRIED = True
        try:
            import tiktoken
            _ENC = tiktoken.get_encoding("cl100k_base")
        except Exception:
            _ENC = None
    if _ENC is not None:
        try:
            return len(_ENC.encode(text))
        except Exception:
            pass
    return max(len(text) // 4, len(text.split()))


def _json_type(ann):
    """Map a Python annotation to a (json_type, enum_or_None) pair."""
    import typing
    try:
        if typing.get_origin(ann) is typing.Literal:
            return "string", [str(a) for a in typing.get_args(ann)]
    except Exception:
        pass
    mapping = {str: "string", int: "integer", float: "number", bool: "boolean"}
    return mapping.get(ann, "string"), None


def _approx_schema_json(fn) -> str:
    """Build an approximate JSON-Schema string for a tool function's parameters
    (excluding ctx), close to what FastMCP serializes into inputSchema."""
    import inspect
    import json
    import typing
    try:
        hints = typing.get_type_hints(fn)
    except Exception:
        hints = {}
    try:
        sig = inspect.signature(fn)
    except Exception:
        return ""
    props, required = {}, []
    for pname, p in sig.parameters.items():
        if pname in ("ctx", "self", "return"):
            continue
        ann = hints.get(pname, p.annotation)
        jtype, enum = _json_type(ann)
        entry = {"type": jtype, "title": pname.replace("_", " ").title()}
        if enum:
            entry["enum"] = enum
        if p.default is inspect.Parameter.empty:
            required.append(pname)
        elif p.default is not None:
            entry["default"] = p.default
        props[pname] = entry
    schema = {"type": "object", "properties": props}
    if required:
        schema["required"] = required
    try:
        return json.dumps(schema)
    except Exception:
        return ""


def _capture_tool_surface():
    """Register every tool on a throwaway MCP to capture (description, fn) per
    tool — without importing FastMCP's server runtime or touching Docker.
    Returns (descriptions, fns) or (None, None) if the tool modules can't import."""
    import importlib
    from hercules.core.tool_catalog import REGISTRARS

    descriptions: dict = {}
    fns: dict = {}

    class _Capture:
        def tool(self, *a, description=None, **k):
            if a and callable(a[0]) and description is None and len(a) == 1 and not k:
                fn = a[0]
                descriptions[fn.__name__] = None
                fns[fn.__name__] = fn
                return fn

            def deco(fn):
                descriptions[fn.__name__] = description
                fns[fn.__name__] = fn
                return fn

            return deco

        def __getattr__(self, _name):
            def _flex(*a, **k):
                if a and callable(a[0]) and len(a) == 1 and not k:
                    return a[0]
                return lambda fn: fn
            return _flex

    cap = _Capture()
    for path in REGISTRARS:
        mod_name, fn_name = path.split(":")
        try:
            module = importlib.import_module(mod_name)
            getattr(module, fn_name)(cap)
        except Exception:
            return None, None
    return descriptions, fns


def build_token_model(disabled: "set[str] | frozenset[str] | None" = None):
    """Return (base_tokens, cost_by_tool, precise) where cost_by_tool maps every
    tool name to its estimated context-token cost. `precise` is True when the
    function signatures were readable (schema-accurate)."""
    from hercules.core.guidance import SERVER_INSTRUCTIONS, TOOL_DESCRIPTIONS
    from hercules.core.tool_catalog import all_tool_names

    descriptions, fns = _capture_tool_surface()
    precise = descriptions is not None
    cost: dict[str, int] = {}
    for name in all_tool_names():
        desc = (descriptions.get(name) if descriptions else None) or TOOL_DESCRIPTIONS.get(name, "")
        if fns and name in fns:
            schema_tokens = _estimate_tokens(_approx_schema_json(fns[name]))
        else:
            schema_tokens = _SCHEMA_FLAT
        cost[name] = (
            _estimate_tokens(name)
            + _estimate_tokens(desc)
            + schema_tokens
            + _PER_TOOL_FRAMING
        )
    base = _estimate_tokens(SERVER_INSTRUCTIONS) + _BASE_PROTOCOL
    return base, cost, precise


# ---------------------------------------------------------------------------
# .env helpers (persist the tool selection the server reads)
# ---------------------------------------------------------------------------

def read_disabled_from_env() -> set[str]:
    """Read the currently-disabled tool set from .env (empty if unset/missing)."""
    from hercules.core.tool_catalog import parse_disabled
    if not ENV_PATH.exists():
        return set()
    try:
        for line in ENV_PATH.read_text(encoding="utf-8", errors="replace").splitlines():
            s = line.strip()
            if s.startswith("HERCULES_DISABLED_TOOLS") and "=" in s:
                return set(parse_disabled(s.split("=", 1)[1]))
    except Exception:
        return set()
    return set()


def _upsert_env(key: str, value: str) -> None:
    """Set KEY=value in .env, preserving all other lines. Creates .env if absent."""
    lines: list[str] = []
    if ENV_PATH.exists():
        lines = ENV_PATH.read_text(encoding="utf-8", errors="replace").splitlines()
    out, found = [], False
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith(f"{key}=") or stripped.startswith(f"{key} ="):
            out.append(f"{key}={value}")
            found = True
        else:
            out.append(line)
    if not found:
        if out and out[-1].strip() != "":
            out.append("")
        out.append("# Tools opted out via hercules_setup.py (still reachable via shell_exec)")
        out.append(f"{key}={value}")
    ENV_PATH.write_text("\n".join(out).rstrip("\n") + "\n", encoding="utf-8")


def write_disabled_to_env(disabled: "set[str] | list[str]") -> None:
    """Persist the disabled-tool selection to .env."""
    from hercules.core.tool_catalog import format_disabled
    _upsert_env("HERCULES_DISABLED_TOOLS", format_disabled(set(disabled)))


# ---------------------------------------------------------------------------
# Advanced settings (server runtime knobs persisted to .env)
# ---------------------------------------------------------------------------

# Mirrors the relevant HerculesConfig.from_env() defaults; the Advanced tab of
# the setup UI edits these and writes them back to .env.
_SETTING_DEFAULTS: dict[str, str] = {
    "TOOL_INSTALL_MODE": "minimal",
    "MAX_CONCURRENT_HEAVY": "3",
    "MAX_CONCURRENT_LIGHT": "10",
    "CONTAINER_CPU_LIMIT": "0",
    "CONTAINER_MEM_LIMIT": "0",
    "DEFAULT_TIMEOUT": "300",
    "BROWSER_HEADLESS": "true",
    "ALLOWED_TARGETS": "",
    "BLOCKED_TARGETS": "",
}


def read_env_settings() -> dict[str, str]:
    """Read the advanced settings from .env, falling back to defaults."""
    vals = dict(_SETTING_DEFAULTS)
    if ENV_PATH.exists():
        try:
            for line in ENV_PATH.read_text(encoding="utf-8", errors="replace").splitlines():
                s = line.strip()
                if not s or s.startswith("#") or "=" not in s:
                    continue
                k, v = s.split("=", 1)
                k = k.strip()
                if k in vals:
                    vals[k] = v.strip()
        except Exception:
            pass
    return vals


def write_settings_to_env(settings: dict) -> None:
    """Persist advanced settings to .env (only known keys)."""
    for key in _SETTING_DEFAULTS:
        if key in settings:
            _upsert_env(key, str(settings[key]))


def _to_int(value, default: int) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _to_float(value, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _mem_to_gb(value) -> int:
    """Parse a Docker memory-limit string (e.g. '4g', '2048m', '0') to whole GB."""
    v = str(value or "0").strip().lower()
    if v in ("", "0"):
        return 0
    try:
        if v.endswith("g"):
            return int(float(v[:-1]))
        if v.endswith("m"):
            return max(0, int(float(v[:-1]) / 1024))
        return int(float(v))
    except ValueError:
        return 0


# ---------------------------------------------------------------------------
# Headless token report (`--tokens`)
# ---------------------------------------------------------------------------

def print_token_report(disabled: "set[str] | None" = None) -> None:
    """Print a per-capability token table and the totals for a given selection."""
    from hercules.core.tool_catalog import CATEGORIES, CORE_TOOLS, all_tool_names

    disabled = set(disabled or set()) - CORE_TOOLS
    base, cost, precise = build_token_model(disabled)

    banner()
    method = "tiktoken (cl100k_base)" if precise and _ENC is not None else "~ estimate (chars/4)"
    print(f"  {C.BOLD}Context-token cost of the MCP tool surface{C.RESET}  {C.DIM}[{method}]{C.RESET}")
    print(f"  {C.DIM}Opt-out is per tool/capability; a disabled tool's subtools are NOT injected "
          f"into the agent's context.{C.RESET}\n")

    def is_on(name: str) -> bool:
        return name in CORE_TOOLS or name not in disabled

    for cat in CATEGORIES:
        cat_tokens = sum(cost.get(t, 0) for cap in cat.capabilities for t in cap.tools)
        lock = f" {C.DIM}(core — always on){C.RESET}" if cat.core else ""
        print(f"  {C.CYAN}{C.BOLD}{cat.emoji}  {cat.title}{C.RESET}  {C.DIM}~{cat_tokens:,} tok{C.RESET}{lock}")
        for cap in cat.capabilities:
            cap_tokens = sum(cost.get(t, 0) for t in cap.tools)
            on = any(is_on(t) for t in cap.tools)
            mark = f"{C.GREEN}[x]{C.RESET}" if on else f"{C.RED}[ ]{C.RESET}"
            sub = f"{len(cap.tools)} subtool{'s' if len(cap.tools) != 1 else ''}"
            print(f"      {mark} {cap.label:<28} {C.DIM}{cap_tokens:>5,} tok · {sub}{C.RESET}")
        print()

    baseline = base + sum(cost.values())
    total = base + sum(cost[t] for t in all_tool_names() if is_on(t))
    saved = baseline - total
    pct = (saved / baseline * 100) if baseline else 0.0
    reg = sum(1 for t in all_tool_names() if is_on(t))

    print(f"  {C.DIM}{'-' * 58}{C.RESET}")
    print(f"  server instructions (fixed) : {C.DIM}{base:>7,} tok{C.RESET}")
    print(f"  baseline (all tools on)     : {baseline:>7,} tok")
    print(f"  {C.BOLD}current selection           : {C.CYAN}{total:>7,} tok{C.RESET}  "
          f"{C.GREEN}(saved {saved:,}, {pct:.0f}%){C.RESET}")
    print(f"  registered subtools         : {reg}/{len(all_tool_names())}")
    if disabled:
        print(f"\n  {C.DIM}opted out (still reachable via shell_exec): {', '.join(sorted(disabled))}{C.RESET}")
    print()


# ---------------------------------------------------------------------------
# Textual interactive UI
# ---------------------------------------------------------------------------

_APP_CLASS = None


def _build_app_class():
    """Lazily import Textual and build the setup App class (cached)."""
    global _APP_CLASS
    if _APP_CLASS is not None:
        return _APP_CLASS

    from rich.text import Text
    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.containers import Horizontal, Vertical, VerticalScroll
    from textual.reactive import reactive
    from textual.widget import Widget
    from textual.widgets import (
        Button, Footer, Header, Input, RadioButton, Select, Static,
        TabbedContent, TabPane,
    )

    from hercules.core.tool_catalog import (
        CATEGORIES,
        CORE_TOOLS,
        all_tool_names,
        disabled_capabilities,
        tools_for_capabilities,
    )

    class Slider(Widget, can_focus=True):
        """Minimal keyboard/mouse slider — a focusable track with a value.

        Arrow keys (or h/l) nudge by one step, Home/End jump to the ends, and a
        click jumps to the clicked position. Read the result from ``.value``.
        """

        DEFAULT_CSS = """
        Slider { height: 1; width: 1fr; padding: 0 1; }
        Slider:focus { background: $boost; }
        """

        value = reactive(0.0)

        def __init__(self, minimum: float, maximum: float, step: float = 1.0,
                     value: float = 0.0, *, as_float: bool = False, id=None):
            super().__init__(id=id)
            self._min = float(minimum)
            self._max = float(maximum)
            self._step = float(step)
            self._as_float = as_float
            self.value = float(value)

        def validate_value(self, v):
            return max(self._min, min(self._max, float(v)))

        def watch_value(self) -> None:
            self.refresh()

        def _fmt(self, v) -> str:
            return f"{v:g}" if self._as_float else f"{int(round(v))}"

        def _track(self, valstr: str) -> int:
            return max(8, self.size.width - len(valstr) - 4)

        def render(self):
            valstr = self._fmt(self.value)
            track = self._track(valstr)
            span = (self.value - self._min) / (self._max - self._min) if self._max != self._min else 0.0
            pos = int(round(span * (track - 1)))
            return Text.from_markup(
                f"[#2f9bff]{'━' * pos}●[/][#30363d]{'━' * (track - 1 - pos)}[/]  [b]{valstr}[/]"
            )

        def on_key(self, event) -> None:
            if event.key in ("left", "down", "h"):
                self.value -= self._step
                event.stop()
            elif event.key in ("right", "up", "l"):
                self.value += self._step
                event.stop()
            elif event.key == "home":
                self.value = self._min
                event.stop()
            elif event.key == "end":
                self.value = self._max
                event.stop()

        def on_click(self, event) -> None:
            track = self._track(self._fmt(self.value))
            x = max(0, min(track - 1, getattr(event, "x", 1) - 1))
            steps = round((x / max(1, track - 1)) * (self._max - self._min) / self._step)
            self.value = self._min + steps * self._step
            self.focus()
            event.stop()

    class HerculesSetupApp(App):
        CSS = """
        Screen { background: $surface; align-horizontal: center; }
        Header { background: $surface; }
        HeaderIcon { display: none; }
        Footer { background: $surface; }

        /* Centered, fixed-width card so wide terminals stay balanced. */
        #frame { width: 62; max-width: 100%; height: 1fr; }

        #meter {
            height: auto; padding: 1 2; margin: 1 0 0 0;
            border: round $panel-lighten-2; background: $surface;
        }
        #list {
            height: 1fr; padding: 0;
            scrollbar-size-vertical: 1;
            scrollbar-background: $surface;
            scrollbar-background-hover: $surface;
            scrollbar-background-active: $surface;
            scrollbar-color: $primary-darken-1;
            scrollbar-color-hover: $primary;
            scrollbar-color-active: $primary;
        }
        #core-note { color: $text-muted; padding: 1 1 0 1; }
        .section { color: $text-muted; text-style: bold; padding: 1 1 0 1; }

        RadioButton {
            border: none; height: 1; padding: 0 1; width: 1fr;
            background: transparent;
        }
        /* off = muted hollow + dim label; on = accent dot + bright label */
        RadioButton > .toggle--button { color: $text-muted; background: $surface; }
        RadioButton > .toggle--label { color: $text-muted; }
        RadioButton.-on > .toggle--button { color: $primary; }
        RadioButton.-on > .toggle--label { color: $text; }
        RadioButton:focus { background: $boost; }
        RadioButton:focus > .toggle--label { text-style: bold; }

        #actions { height: auto; padding: 1 0 0 0; align-horizontal: right; }
        #actions Button { margin: 0 0 0 2; min-width: 12; }

        /* Tabs + advanced settings */
        TabbedContent { height: 1fr; }
        Tabs { background: $surface; }
        TabPane { padding: 0; }
        #adv {
            height: 1fr; padding: 0 0 1 0;
            scrollbar-size-vertical: 1;
            scrollbar-background: $surface;
            scrollbar-color: $primary-darken-1;
            scrollbar-color-hover: $primary;
        }
        .adv-label { color: $text-muted; padding: 1 1 0 1; }
        #adv Select, #adv Input { margin: 0 1; width: 1fr; }
        #adv Input { border: tall $panel-lighten-1; }
        #adv Input:focus { border: tall $primary; }
        """

        BINDINGS = [
            Binding("a", "all", "All on"),
            Binding("n", "none", "All off"),
            Binding("s", "save", "Save & build"),
            Binding("ctrl+s", "save", "Save", show=False),
            Binding("q", "cancel", "Quit"),
            Binding("escape", "cancel", "Quit", show=False),
        ]

        TITLE = "Hercules MCP"
        SUB_TITLE = "tool selection"

        def __init__(self, *, base, cost, precise, initial_disabled,
                     image_ready=True, force_rebuild=False, initial_settings=None):
            super().__init__()
            self.base = base
            self.cost = cost
            self.precise = precise
            self.image_ready = image_ready
            # Opt-out is per capability; expand the initial disabled tool set to
            # the capabilities that are fully disabled.
            self._initial_off = set(disabled_capabilities(set(initial_disabled)))
            self.baseline = base + sum(cost.values())
            self._cap_cb: dict = {}      # capability key -> Checkbox
            self._cap_tools: dict = {}   # capability key -> tuple of MCP tool names
            self._opt_rebuild = bool(force_rebuild or not image_ready)
            self._opt_wordlists = True

            # Advanced settings — parsed + clamped to each control's range.
            st = dict(initial_settings or _SETTING_DEFAULTS)
            self._install = st.get("TOOL_INSTALL_MODE", "minimal")
            if self._install not in ("minimal", "headless", "large"):
                self._install = "minimal"
            self._heavy = min(16, max(1, _to_int(st.get("MAX_CONCURRENT_HEAVY"), 3)))
            self._light = min(32, max(1, _to_int(st.get("MAX_CONCURRENT_LIGHT"), 10)))
            self._cpu = min(16.0, max(0.0, _to_float(st.get("CONTAINER_CPU_LIMIT"), 0.0)))
            self._mem = min(32, max(0, _mem_to_gb(st.get("CONTAINER_MEM_LIMIT"))))
            self._timeout = min(1800, max(30, _to_int(st.get("DEFAULT_TIMEOUT"), 300)))
            self._browser = str(st.get("BROWSER_HEADLESS", "true")).strip().lower()
            if self._browser not in ("true", "false"):
                self._browser = "true"
            self._allowed = st.get("ALLOWED_TARGETS", "") or ""
            self._blocked = st.get("BLOCKED_TARGETS", "") or ""

        # ----- layout -----
        def compose(self) -> ComposeResult:
            yield Header(show_clock=False)
            with Vertical(id="frame"):
                yield Static(id="meter")
                with TabbedContent(initial="tab-tools", id="tabs"):
                    with TabPane("Tools", id="tab-tools"):
                        with VerticalScroll(id="list"):
                            yield from self._compose_tools()
                    with TabPane("Advanced", id="tab-advanced"):
                        with VerticalScroll(id="adv"):
                            yield from self._compose_advanced()
                with Horizontal(id="actions"):
                    yield Button("Cancel", id="cancel")
                    yield Button("Save & build", id="save", variant="primary")
            yield Footer()

        def _compose_tools(self):
            core_tok = sum(
                self.cost.get(t, 0)
                for cat in CATEGORIES if cat.core
                for cap in cat.capabilities for t in cap.tools
            )
            yield Static(
                f"[dim]Core tools always registered · {core_tok:,} tok[/]",
                id="core-note",
            )
            for cat in CATEGORIES:
                if cat.core:
                    continue
                yield Static(cat.title.upper(), classes="section")
                for cap in cat.capabilities:
                    self._cap_tools[cap.key] = cap.tools
                    rb = RadioButton(
                        self._cap_label(cap),
                        value=(cap.key not in self._initial_off),
                        id=f"cap-{cap.key}",
                    )
                    self._cap_cb[cap.key] = rb
                    yield rb
            yield Static("OPTIONS", classes="section")
            yield RadioButton("Rebuild Docker image", value=self._opt_rebuild, id="opt-rebuild")
            yield RadioButton("Download / verify wordlists", value=True, id="opt-wordlists")

        def _compose_advanced(self):
            yield Static("CONTAINER RUNTIME", classes="section")

            yield Static("Tool install mode", classes="adv-label")
            yield Select(
                [("minimal", "minimal"), ("headless", "headless"), ("large", "large")],
                value=self._install, allow_blank=False, id="set-install",
            )

            yield Static("Max concurrent · heavy ops", classes="adv-label")
            yield Slider(1, 16, 1, self._heavy, id="set-heavy")
            yield Static("Max concurrent · light ops", classes="adv-label")
            yield Slider(1, 32, 1, self._light, id="set-light")

            yield Static("CPU limit · cores (0 = unlimited)", classes="adv-label")
            yield Slider(0, 16, 0.5, self._cpu, as_float=True, id="set-cpu")
            yield Static("Memory limit · GB (0 = unlimited)", classes="adv-label")
            yield Slider(0, 32, 1, self._mem, id="set-mem")

            yield Static("Default command timeout · seconds", classes="adv-label")
            yield Slider(30, 1800, 30, self._timeout, id="set-timeout")

            yield Static("BROWSER", classes="section")
            yield Static("Browser mode", classes="adv-label")
            yield Select(
                [("headless", "true"), ("headed (Xvfb)", "false")],
                value=self._browser, allow_blank=False, id="set-browser",
            )

            yield Static("SAFETY · TARGET SCOPE", classes="section")
            yield Static("Allowed targets · comma-separated (blank = allow all)", classes="adv-label")
            yield Input(value=self._allowed, placeholder="example.com, 10.0.0.0/24", id="set-allowed")
            yield Static("Blocked targets · comma-separated (block wins)", classes="adv-label")
            yield Input(value=self._blocked, placeholder="*.gov, 169.254.169.254", id="set-blocked")

        def on_mount(self) -> None:
            self.theme = "textual-dark"
            self._refresh_meter()

        # ----- helpers -----
        def _cap_label(self, cap):
            """Row label: name on the left, dim token count aligned on the right."""
            from rich.text import Text
            tok = sum(self.cost.get(t, 0) for t in cap.tools)
            n = len(cap.tools)
            name = cap.label + (f"  ({n})" if n > 1 else "")
            num = f"{tok:,}"
            col_right = 52  # right edge of the value column within the label area
            pad = max(2, col_right - len(name) - len(num))
            label = Text(name, no_wrap=True, overflow="ellipsis")
            label.append(" " * pad)
            label.append(num, style="dim")
            return label

        def _enabled_tools(self) -> set:
            """All registered tool names: core + tools of capabilities left on."""
            on = set(CORE_TOOLS)
            for key, cb in self._cap_cb.items():
                if cb.value:
                    on.update(self._cap_tools[key])
            return on

        def _total(self) -> int:
            return self.base + sum(self.cost.get(t, 0) for t in self._enabled_tools())

        def _render_meter(self) -> str:
            total = self._total()
            saved = self.baseline - total
            pct = (saved / self.baseline * 100) if self.baseline else 0.0
            reg = len(self._enabled_tools())
            tot = len(all_tool_names())
            width = 52
            filled = max(0, min(width, round(width * total / self.baseline))) if self.baseline else width
            bar = "[#2f9bff]" + "━" * filled + "[/][#30363d]" + "━" * (width - filled) + "[/]"
            sep = "[dim]  ·  [/]"
            return (
                f"[b]Context budget[/]\n"
                f"[b #2f9bff]{total:,}[/][dim] tokens[/]{sep}"
                f"{reg}/{tot} tools{sep}"
                f"[#3fb950]{pct:.0f}% saved[/]\n"
                f"{bar}"
            )

        def _refresh_meter(self) -> None:
            self.query_one("#meter", Static).update(self._render_meter())

        def _set_all(self, value: bool) -> None:
            for cb in self._cap_cb.values():
                cb.value = value
            self._refresh_meter()

        # ----- events -----
        def on_radio_button_changed(self, event) -> None:
            cb = getattr(event, "radio_button", None) or event.control
            cid = cb.id or ""
            if cid == "opt-rebuild":
                self._opt_rebuild = bool(event.value)
            elif cid == "opt-wordlists":
                self._opt_wordlists = bool(event.value)
            elif cid.startswith("cap-"):
                self._refresh_meter()

        def on_button_pressed(self, event) -> None:
            bid = event.button.id or ""
            if bid == "save":
                self.action_save()
            elif bid == "cancel":
                self.action_cancel()

        # ----- actions -----
        def action_all(self) -> None:
            self._set_all(True)

        def action_none(self) -> None:
            self._set_all(False)

        def _gather_settings(self) -> dict:
            """Read the Advanced tab controls into an env-ready settings dict."""
            cpu = self.query_one("#set-cpu", Slider).value
            mem = int(round(self.query_one("#set-mem", Slider).value))
            return {
                "TOOL_INSTALL_MODE": str(self.query_one("#set-install", Select).value),
                "MAX_CONCURRENT_HEAVY": str(int(round(self.query_one("#set-heavy", Slider).value))),
                "MAX_CONCURRENT_LIGHT": str(int(round(self.query_one("#set-light", Slider).value))),
                "CONTAINER_CPU_LIMIT": f"{cpu:g}",
                "CONTAINER_MEM_LIMIT": "0" if mem == 0 else f"{mem}g",
                "DEFAULT_TIMEOUT": str(int(round(self.query_one("#set-timeout", Slider).value))),
                "BROWSER_HEADLESS": str(self.query_one("#set-browser", Select).value),
                "ALLOWED_TARGETS": self.query_one("#set-allowed", Input).value.strip(),
                "BLOCKED_TARGETS": self.query_one("#set-blocked", Input).value.strip(),
            }

        def action_save(self) -> None:
            off = {key for key, cb in self._cap_cb.items() if not cb.value}
            disabled = sorted(tools_for_capabilities(off))
            self.exit({
                "disabled": disabled,
                "capabilities_off": sorted(off),
                "settings": self._gather_settings(),
                "rebuild": self._opt_rebuild,
                "wordlists": self._opt_wordlists,
                "proceed": True,
            })

        def action_cancel(self) -> None:
            self.exit(None)

    _APP_CLASS = HerculesSetupApp
    return _APP_CLASS


def build_app(initial_disabled=None, force_rebuild: bool = False,
              image_ready: bool = True, model=None, initial_settings=None):
    """Construct the setup TUI app. `model` may be a precomputed
    (base, cost, precise) tuple (used by tests); otherwise it is computed."""
    app_cls = _build_app_class()
    if model is None:
        base, cost, precise = build_token_model(set(initial_disabled or set()))
    else:
        base, cost, precise = model
    return app_cls(
        base=base, cost=cost, precise=precise,
        initial_disabled=set(initial_disabled or set()),
        image_ready=image_ready, force_rebuild=force_rebuild,
        initial_settings=initial_settings or dict(_SETTING_DEFAULTS),
    )


def _textual_available() -> bool:
    import importlib.util
    return importlib.util.find_spec("textual") is not None


def ensure_textual_pkg() -> bool:
    """Ensure Textual is importable, offering to pip-install it if missing."""
    if _textual_available():
        return True
    print()
    warn("The interactive setup needs the 'textual' package, which isn't installed.")
    try:
        answer = input("  Install it now with pip? [Y/n] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False
    if answer not in ("", "y", "yes"):
        return False
    info("Installing textual ...")
    # Try pip first; fall back to `uv pip` for pip-less uv-managed venvs.
    attempts = [[sys.executable, "-m", "pip", "install", "textual>=0.60"]]
    if shutil.which("uv"):
        attempts.append(["uv", "pip", "install", "--python", sys.executable, "textual>=0.60"])
    for cmd in attempts:
        try:
            if subprocess.run(cmd).returncode == 0 and _textual_available():
                return True
        except Exception:
            continue
    fail("Failed to install textual. Falling back to the classic setup.")
    return False


def run_tui(force_rebuild: bool = False):
    """Run the interactive selection UI. Returns a selection dict, or None if the
    user cancelled."""
    initial_disabled = read_disabled_from_env()
    initial_settings = read_env_settings()
    image_ready = check_image_exists()
    app = build_app(
        initial_disabled=initial_disabled,
        force_rebuild=force_rebuild,
        image_ready=image_ready,
        initial_settings=initial_settings,
    )
    return app.run()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _do_check() -> None:
    status = is_setup_complete()
    if status["ready"]:
        ok("Hercules setup is complete. The MCP server is ready to run.")
        if not status["wordlists_ready"]:
            warn("Wordlists not downloaded. Run setup again to download them.")
        if status["browser_ready"]:
            ok("Stealth browser ready (cloakbrowser + agent-browser).")
        else:
            warn("Stealth browser not detected. Rebuild the image to enable browser_* tools.")
        disabled = read_disabled_from_env()
        if disabled:
            info(f"{len(disabled)} tool(s) opted out via .env: {', '.join(sorted(disabled))}")
    else:
        fail("Hercules setup is incomplete:")
        for err in status["errors"]:
            print(f"    {C.RED}>{C.RESET} {err}")
    sys.exit(0 if status["ready"] else 1)


def _final_summary(disabled: "set[str] | None") -> None:
    """Print the completion banner, including the token total for the selection."""
    try:
        from hercules.core.tool_catalog import CORE_TOOLS, all_tool_names
        base, cost, _ = build_token_model(set(disabled or set()))
        disabled = set(disabled or set()) - CORE_TOOLS
        baseline = base + sum(cost.values())
        total = base + sum(
            cost[t] for t in all_tool_names() if t in CORE_TOOLS or t not in disabled
        )
        saved = baseline - total
        token_line = (
            f"  {C.BOLD}Tool surface:{C.RESET} {len(all_tool_names()) - len(disabled)}"
            f"/{len(all_tool_names())} tools  ·  ~{total:,} ctx tokens"
        )
        if saved > 0:
            token_line += f"  {C.GREEN}(saved ~{saved:,}){C.RESET}"
    except Exception:
        token_line = ""

    print(f"""
{C.GREEN}{C.BOLD}+============================================================+
|                  SETUP COMPLETE                            |
+============================================================+{C.RESET}

  The Hercules MCP server is ready to use.
""")
    if token_line:
        print(token_line)
        if disabled:
            print(f"  {C.DIM}opted out (still reachable via shell_exec): {', '.join(sorted(disabled))}{C.RESET}")
        print()
    print(f"""  {C.BOLD}Next steps:{C.RESET}
    1. (Re)start your MCP client so it re-reads the tool selection.
    2. Tweak {C.CYAN}.env{C.RESET} any time, or re-run {C.CYAN}python hercules_setup.py{C.RESET}.

  {C.DIM}Subsequent startups will be instant (~5 seconds).{C.RESET}
""")


def main():
    args = set(sys.argv[1:])

    if "--check" in args:
        banner()
        _do_check()
        return

    if "--tokens" in args:
        print_token_report(read_disabled_from_env())
        return

    force_rebuild = "--rebuild" in args
    classic = bool(args & {"--classic", "--no-tui", "--yes", "-y"})
    interactive = sys.stdin.isatty() and sys.stdout.isatty()
    want_tui = (not classic) and interactive

    selection = None
    if want_tui:
        if ensure_textual_pkg():
            try:
                selection = run_tui(force_rebuild=force_rebuild)
            except Exception as exc:
                warn(f"Interactive UI failed to start ({exc}). Using the classic setup.")
                selection = None
            else:
                if selection is None:
                    print(f"\n{C.YELLOW}Setup cancelled — no changes made.{C.RESET}")
                    return
        else:
            warn("Continuing with the classic (non-interactive) setup.")

    banner()

    if selection is not None:
        write_disabled_to_env(selection["disabled"])
        if selection.get("settings"):
            write_settings_to_env(selection["settings"])
        force_rebuild = force_rebuild or selection["rebuild"]
        do_wordlists = selection["wordlists"]
        n = len(selection["disabled"])
        ok(f"Saved tool selection to .env ({n} tool(s) opted out; still reachable via shell_exec).")
        if selection.get("settings"):
            ok("Saved advanced settings to .env (install mode, concurrency, limits, targets, browser mode).")
    else:
        do_wordlists = True

    total_steps = 3 if do_wordlists else 2

    step(1, total_steps, "Checking Docker installation")
    if not check_docker():
        print(f"\n{C.RED}{C.BOLD}Setup cannot continue without Docker.{C.RESET}")
        sys.exit(1)

    step(2, total_steps, "Building hercules-kali Docker image")
    if not build_image(force_rebuild=force_rebuild):
        print(f"\n{C.RED}{C.BOLD}Image build failed. Check the errors above.{C.RESET}")
        sys.exit(1)

    if do_wordlists:
        step(3, total_steps, "Downloading wordlists (SecLists + rockyou.txt)")
        ensure_wordlists()

    if check_browser_ready():
        ok("Stealth browser ready (cloakbrowser + agent-browser).")
    else:
        warn("Stealth browser stack not detected in the image (browser_* tools will be unavailable).")

    _final_summary(read_disabled_from_env())


if __name__ == "__main__":
    main()
