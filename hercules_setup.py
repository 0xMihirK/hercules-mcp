#!/usr/bin/env python3
"""
Hercules MCP Server — First-Time Setup

Run this script once before using the Hercules MCP server.
It will:
  1. Verify Docker is installed and the daemon is running.
  2. Build the hercules-kali Docker image (bakes all tools).
  3. Download SecLists and rockyou.txt wordlists locally.

Usage:
    python hercules_setup.py          # Full setup
    python hercules_setup.py --check  # Check if setup is complete
    python hercules_setup.py --rebuild # Force rebuild of Docker image

Works on Windows and Linux.
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
DOCKERFILE = PROJECT_ROOT / "Dockerfile"
ENTRYPOINT = PROJECT_ROOT / "docker" / "entrypoint.sh"
WORDLISTS_DIR = PROJECT_ROOT / "wordlists"
IMAGE_NAME = "hercules-kali"

WORDLIST_URLS = {
    "SecLists.zip": "https://github.com/danielmiessler/SecLists/archive/refs/heads/master.zip",
    "rockyou.txt.tar.gz": "https://github.com/danielmiessler/SecLists/raw/master/Passwords/Leaked-Databases/rockyou.txt.tar.gz",
}

# ---------------------------------------------------------------------------
# Colors (cross-platform)
# ---------------------------------------------------------------------------

if platform.system() == "Windows":
    os.system("")  # Enable ANSI escape codes on Windows 10+

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
    # Check if docker CLI is available
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

    # Check if daemon is running
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

        # Stream docker build output in real time
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

            # Show step headers clearly, compress verbose output
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
        print()  # newline after progress bar
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
        "wordlists_ready": False,
        "ready": False,
        "errors": [],
    }

    # Docker
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

    # Image
    if check_image_exists():
        status["image_exists"] = True
        if check_image_runtime_ready():
            status["image_runtime_ready"] = True
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

    # Wordlists (optional — warn but don't block)
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
# Main
# ---------------------------------------------------------------------------

def main():
    banner()

    # --check flag: quick status report
    if "--check" in sys.argv:
        status = is_setup_complete()
        if status["ready"]:
            ok("Hercules setup is complete. The MCP server is ready to run.")
            if not status["wordlists_ready"]:
                warn("Wordlists not downloaded. Run setup again to download them.")
        else:
            fail("Hercules setup is incomplete:")
            for err in status["errors"]:
                print(f"    {C.RED}>{C.RESET} {err}")
        sys.exit(0 if status["ready"] else 1)

    total_steps = 3

    force_rebuild = "--rebuild" in sys.argv

    # Step 1: Docker
    step(1, total_steps, "Checking Docker installation")
    if not check_docker():
        print(f"\n{C.RED}{C.BOLD}Setup cannot continue without Docker.{C.RESET}")
        sys.exit(1)

    # Step 2: Build image
    step(2, total_steps, "Building hercules-kali Docker image")
    if not build_image(force_rebuild=force_rebuild):
        print(f"\n{C.RED}{C.BOLD}Image build failed. Check the errors above.{C.RESET}")
        sys.exit(1)

    # Step 3: Wordlists
    step(3, total_steps, "Downloading wordlists (SecLists + rockyou.txt)")
    ensure_wordlists()

    # Done
    print(f"""
{C.GREEN}{C.BOLD}+============================================================+
|                  SETUP COMPLETE                            |
+============================================================+{C.RESET}

  The Hercules MCP server is ready to use.

  {C.BOLD}Next steps:{C.RESET}
    1. Add the server to your MCP client config (e.g. Claude Desktop).
    2. Set any environment variables in {C.CYAN}.env{C.RESET} (optional).
    3. Start using Hercules tools!

  {C.DIM}Subsequent startups will be instant (~5 seconds).{C.RESET}
""")


if __name__ == "__main__":
    main()
