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
import time
import urllib.request
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


def build_image(force_rebuild: bool = False) -> bool:
    """Build the hercules-kali Docker image from the Dockerfile."""
    if not force_rebuild and check_image_exists():
        ok(f"Image '{IMAGE_NAME}' already exists. Skipping build.")
        return True

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

    start = time.time()

    # Stream docker build output in real time
    process = subprocess.Popen(
        ["docker", "build", "-t", IMAGE_NAME, "."],
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    current_step = ""
    for line in process.stdout:
        line = line.strip()
        if not line:
            continue

        # Show step headers clearly, compress verbose output
        if line.startswith("#") and ("[" in line or "RUN" in line or "COPY" in line or "FROM" in line):
            current_step = line
            print(f"  {C.CYAN}>{C.RESET} {line[:75]}")
        elif "error" in line.lower():
            print(f"  {C.RED}>{C.RESET} {line[:75]}")

    process.wait()
    elapsed = time.time() - start

    if process.returncode != 0:
        fail(f"Docker build failed (exit code {process.returncode}).")
        return False

    ok(f"Image '{IMAGE_NAME}' built successfully in {elapsed:.0f}s.")
    return True


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


def ensure_wordlists() -> bool:
    """Download SecLists and rockyou.txt if not already present."""
    WORDLISTS_DIR.mkdir(parents=True, exist_ok=True)
    all_ok = True

    for filename, url in WORDLIST_URLS.items():
        dest = WORDLISTS_DIR / filename
        if dest.exists():
            size_mb = dest.stat().st_size / (1024 * 1024)
            ok(f"{filename} already present ({size_mb:.1f} MB).")
            continue

        info(f"Downloading {filename}...")
        if not download_with_progress(url, dest, filename):
            warn(f"{filename} could not be downloaded. It will not be available inside the container.")
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
    else:
        status["errors"].append(
            f"The '{IMAGE_NAME}' Docker image has not been built yet. "
            f"Run: python hercules_setup.py"
        )

    # Wordlists (optional — warn but don't block)
    wl_dir = PROJECT_ROOT / "wordlists"
    if (wl_dir / "SecLists.zip").exists() or (wl_dir / "rockyou.txt.tar.gz").exists():
        status["wordlists_ready"] = True

    status["ready"] = status["docker_available"] and status["image_exists"]
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
