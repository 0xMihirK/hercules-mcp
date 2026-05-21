"""
Docker container lifecycle manager for Hercules.

Manages the creation, command execution, file I/O, and teardown of the
Hercules Kali container. Uses a pre-built Docker image (hercules-kali)
for instant startup. Falls back to building the image from the Dockerfile
if it doesn't exist locally.

All blocking Docker SDK calls are wrapped with asyncio.to_thread() to
keep the event loop free for parallel tool execution.
"""

from __future__ import annotations

import asyncio
import io
import logging
import os
import platform
import shutil
import tarfile
import time
import urllib.request
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from hercules.output.sanitizer import sanitize
from hercules.output.truncator import truncate_output
from hercules.output.banners import strip_known_banners

import docker
from docker.errors import DockerException, ImageNotFound, NotFound

if TYPE_CHECKING:
    from docker.models.containers import Container

    from hercules.core.config import HerculesConfig

logger = logging.getLogger("hercules.docker")


# ---------------------------------------------------------------------------
# Wordlist download URLs
# ---------------------------------------------------------------------------

_WORDLIST_URLS = {
    "SecLists.zip": "https://github.com/danielmiessler/SecLists/archive/refs/heads/master.zip",
    "rockyou.txt.tar.gz": "https://github.com/danielmiessler/SecLists/raw/master/Passwords/Leaked-Databases/rockyou.txt.tar.gz",
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ExecResult:
    """Structured result from a command executed inside the Kali container."""
    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    command: str
    truncated: bool = False
    artifact: str = ""
    summary: str = ""

    def to_dict(self) -> dict:
        d = {
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "duration_seconds": self.duration_seconds,
            "command": self.command,
        }
        if self.truncated:
            d["truncated"] = True
            d["artifact"] = self.artifact
        if self.summary:
            d["summary"] = self.summary
        return d


# ---------------------------------------------------------------------------
# DockerManager
# ---------------------------------------------------------------------------

class DockerManager:
    """
    Manages the lifecycle of the Hercules Kali Docker container.

    Startup flow:
      1. Check Docker is installed and the daemon is running.
      2. Look for the pre-built 'hercules-kali' image locally.
         If missing → build it from the Dockerfile in the project root.
      3. Ensure wordlists (SecLists, rockyou.txt) are downloaded locally.
      4. Create the container with workspace + wordlists mounted.
      5. Wait for the entrypoint to finish (MSF, wordlists extraction).

    All public methods are async-safe.
    """

    IMAGE = "hercules-kali"

    def __init__(self, config: HerculesConfig) -> None:
        self._config = config
        self._client: docker.DockerClient | None = None
        self._container: Container | None = None
        self._session_id: str = uuid.uuid4().hex[:8]
        self._container_name: str = f"hercules-{self._session_id}"
        self._bootstrapped: bool = False

    @property
    def session_id(self) -> str:
        """Unique ID for the current session. Changes on restart."""
        return self._session_id

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start_container(self) -> None:
        """Full startup: verify setup → create container → wait for ready."""

        # Step 1: Verify setup is complete (Docker + image + wordlists)
        await self._verify_setup()

        # Step 2: Ensure wordlists are present (non-blocking, warn only)
        await self._ensure_wordlists()

        # Step 4: Prepare host directories (session-isolated workspace)
        workspace_path = self._config.project_root / "workspace" / self._session_id
        workspace_path.mkdir(parents=True, exist_ok=True)

        wordlists_path = self._config.project_root / "wordlists"
        wordlists_path.mkdir(parents=True, exist_ok=True)
        
        self._cleanup_empty_workspaces()

        # Cleanup orphaned containers from previous abrupt shutdowns
        try:
            for c in self._client.containers.list(all=True, filters={"name": "hercules-"}):
                if c.name != self._container_name and c.name.startswith("hercules-"):
                    logger.info("Cleaning up orphaned container: %s", c.name)
                    c.remove(force=True)
        except Exception as exc:
            logger.warning("Failed to cleanup orphaned containers: %s", exc)

        # Step 5: Build container creation kwargs
        env_vars = {
            "MSF_PASSWORD": self._config.msf_password,
            "SKIP_METASPLOIT": "true" if self._config.skip_metasploit else "false",
        }

        kwargs: dict = {
            "image": self.IMAGE,
            "name": self._container_name,
            "tty": True,
            "stdin_open": True,
            "detach": True,
            "environment": env_vars,
            "volumes": {
                str(workspace_path): {"bind": "/opt/workspace", "mode": "rw"},
                str(wordlists_path): {"bind": "/opt/wordlists_host", "mode": "ro"},
            },
            "shm_size": "256m",
        }

        # Handle networking: Linux uses host mode for VPNs. Windows/Mac use port mapping.
        if platform.system() == "Linux":
            kwargs["network_mode"] = "host"
        else:
            # Map msfrpcd + reverse shell listener ports (4444-4464)
            ports = {"55553/tcp": 55553}
            for p in range(4444, 4465):
                ports[f"{p}/tcp"] = p
            kwargs["ports"] = ports

        # Capabilities
        if self._config.use_privileged:
            kwargs["privileged"] = True
        else:
            kwargs["cap_add"] = ["NET_ADMIN", "NET_RAW"]

        # Resource limits
        if self._config.container_cpu_limit > 0:
            kwargs["nano_cpus"] = int(self._config.container_cpu_limit * 1e9)
        if self._config.container_mem_limit and self._config.container_mem_limit != "0":
            kwargs["mem_limit"] = self._config.container_mem_limit

        logger.info("Creating container '%s'...", self._container_name)
        
        try:
            self._container = await asyncio.to_thread(
                self._client.containers.run, **kwargs
            )
        except Exception as exc:
            import docker
            if isinstance(exc, docker.errors.APIError) and "port is already allocated" in str(exc).lower():
                logger.warning("Port conflict detected. Attempting to shift reverse shell port range to 4470-4490...")
                if platform.system() != "Linux":
                    # Keep msfrpcd port but shift reverse shell ports
                    new_ports = {"55553/tcp": 55553}
                    for p in range(4470, 4491):
                        new_ports[f"{p}/tcp"] = p
                    kwargs["ports"] = new_ports
                    self._container = await asyncio.to_thread(
                        self._client.containers.run, **kwargs
                    )
                else:
                    raise
            else:
                raise

        logger.info(
            "Container '%s' started (id=%s).",
            self._container_name,
            self._container.short_id,
        )

        # Step 6: Wait for entrypoint to signal readiness
        await self._wait_for_ready()
        self._bootstrapped = True

    async def stop_container(self) -> None:
        """Stop and remove the container. Workspace files on host are preserved."""
        if self._container is None:
            return

        try:
            logger.info("Stopping container '%s'...", self._container_name)
            await asyncio.to_thread(self._container.stop, timeout=15)
        except Exception as exc:
            logger.warning("Error stopping container: %s", exc)

        if not self._config.preserve_container:
            try:
                logger.info("Removing container '%s'...", self._container_name)
                await asyncio.to_thread(self._container.remove, force=True)
            except NotFound:
                pass
            except Exception as exc:
                logger.warning("Error removing container: %s", exc)
        else:
            logger.info("Container '%s' preserved for debugging.", self._container_name)

        self._container = None
        self._bootstrapped = False

    async def restart_container(self) -> str:
        """
        Atomically restart the container with a new session ID and workspace.

        Creates the new workspace subfolder BEFORE tearing down the old
        container, so a failure in start_container() never leaves the
        manager pointing at an ID that corresponds to nothing.

        Returns the new session_id.
        """
        new_session_id = uuid.uuid4().hex[:8]
        new_name = f"hercules-{new_session_id}"

        # Create the workspace subfolder FIRST — if this fails, old container is still alive
        new_workspace = self._config.project_root / "workspace" / new_session_id
        new_workspace.mkdir(parents=True, exist_ok=True)

        # Now it's safe to tear down the old one
        await self.stop_container()

        self._session_id = new_session_id
        self._container_name = new_name
        await self.start_container()
        return self._session_id

    def _cleanup_empty_workspaces(self) -> None:
        """Remove any legacy workspace session folders that are completely empty."""
        workspace_root = self._config.project_root / "workspace"
        if not workspace_root.exists():
            return

        for entry in workspace_root.iterdir():
            if entry.is_dir() and len(entry.name) == 8 and entry.name != self._session_id:
                # Count files, ignoring empty directories
                file_count = sum(1 for _ in entry.rglob("*") if _.is_file())
                if file_count == 0:
                    try:
                        shutil.rmtree(entry)
                        logger.info("Cleaned up empty session workspace: %s", entry.name)
                    except Exception as exc:
                        logger.warning("Failed to remove empty workspace %s: %s", entry.name, exc)

    def list_sessions(self) -> list[dict]:
        """List all session workspace folders on disk with metadata."""
        workspace_root = self._config.project_root / "workspace"
        sessions = []
        if not workspace_root.exists():
            return sessions

        for entry in sorted(workspace_root.iterdir()):
            if entry.is_dir() and len(entry.name) == 8:
                # Count files and total size
                file_count = sum(1 for _ in entry.rglob("*") if _.is_file())
                total_bytes = sum(f.stat().st_size for f in entry.rglob("*") if f.is_file())
                sessions.append({
                    "session_id": entry.name,
                    "is_active": entry.name == self._session_id and self._container is not None,
                    "file_count": file_count,
                    "total_size_mb": round(total_bytes / (1024 * 1024), 2),
                    "path": str(entry),
                })
        return sessions

    # ------------------------------------------------------------------
    # Command execution
    # ------------------------------------------------------------------

    async def exec_command(
        self,
        cmd: str,
        timeout: int | None = None,
        workdir: str | None = None,
        env: dict[str, str] | None = None,
        clean_output: bool = True,
        max_output_chars: int = 8000,
        tool_name: str = "",
    ) -> ExecResult:
        """
        Execute a command inside the running Kali container.

        Uses asyncio.to_thread to avoid blocking the event loop.
        Enforces a timeout via asyncio.wait_for.

        When clean_output=True:
          1. ANSI escape codes are stripped.
          2. Known tool banners are removed (if tool_name is provided).
          3. Consecutive blank lines are compressed.
          4. Output is truncated with head+tail if over max_output_chars.
          5. Full raw output is always saved to /opt/workspace/logs/.
        """
        if self._container is None:
            raise RuntimeError("Container is not running.")

        effective_timeout = timeout or self._config.default_timeout
        start = time.monotonic()

        def _run():
            return self._container.exec_run(
                cmd=["bash", "-c", cmd],
                stdout=True,
                stderr=True,
                demux=True,
                workdir=workdir,
                environment=env,
            )

        logger.debug("exec_command: %s (timeout=%ds)", cmd[:120], effective_timeout)

        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(_run),
                timeout=effective_timeout,
            )
        except asyncio.TimeoutError:
            logger.warning("Command timed out after %ds: %s", effective_timeout, cmd[:120])
            return ExecResult(
                exit_code=-1,
                stdout="",
                stderr=f"Command timed out after {effective_timeout}s",
                duration_seconds=float(effective_timeout),
                command=cmd,
            )

        exit_code = result.exit_code
        stdout_raw, stderr_raw = result.output
        stdout = (stdout_raw or b"").decode("utf-8", errors="replace")
        stderr = (stderr_raw or b"").decode("utf-8", errors="replace")
        duration = round(time.monotonic() - start, 2)

        if exit_code != 0:
            logger.debug("Command exited %d: %s", exit_code, cmd[:120])

        truncated = False
        artifact_path = ""

        if clean_output:
            # Step 1: ANSI stripping + whitespace compression
            stdout = sanitize(stdout)
            stderr = sanitize(stderr)

            # Step 2: Known banner removal
            if tool_name:
                stdout = strip_known_banners(stdout, tool_name)

            # Step 3: Save full output to artifact log before truncation
            if len(stdout) > max_output_chars:
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                log_name = tool_name or "exec"
                artifact_path = f"/opt/workspace/logs/{log_name}_{ts}.txt"
                try:
                    await self._write_file_internal(artifact_path, stdout)
                except Exception as exc:
                    logger.warning("Failed to write artifact log: %s", exc)

            # Step 4: Truncate with head+tail
            stdout, truncated = truncate_output(
                stdout, max_chars=max_output_chars, artifact_path=artifact_path
            )

        return ExecResult(
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            duration_seconds=duration,
            command=cmd,
            truncated=truncated,
            artifact=artifact_path,
        )

    # ------------------------------------------------------------------
    # Background Job Management
    # ------------------------------------------------------------------

    async def exec_background(
        self,
        cmd: str,
        job_id: str,
        workdir: str | None = None,
        env: dict[str, str] | None = None,
    ) -> str:
        """
        Execute a command in the background.
        Output is written to /opt/workspace/jobs/<job_id>.log
        PID is written to /opt/workspace/jobs/<job_id>.pid
        """
        if self._container is None:
            raise RuntimeError("Container is not running.")

        # Ensure jobs dir exists
        await self.exec_command("mkdir -p /opt/workspace/jobs")
        
        script_path = f"/opt/workspace/jobs/{job_id}.sh"
        log_file = f"/opt/workspace/jobs/{job_id}.log"
        pid_file = f"/opt/workspace/jobs/{job_id}.pid"
        
        # Write command to a temporary script to avoid quoting issues
        await self.write_file(script_path, cmd, mode=0o755)
        
        # Run it in background and detach completely
        bg_cmd = f"nohup bash {script_path} > {log_file} 2>&1 & echo $! > {pid_file}"
        await self.exec_command(bg_cmd, workdir=workdir, env=env)
        
        return job_id
        
    async def check_job(self, job_id: str, tail_lines: int = 50) -> dict:
        """Check if job is running and get the last N lines of output."""
        try:
            pid_content = await self.read_file(f"/opt/workspace/jobs/{job_id}.pid")
            pid = pid_content.strip()
        except Exception:
            pid = ""
            
        # Check if running
        is_running = False
        if pid:
            res = await self.exec_command(f"kill -0 {pid}", clean_output=False)
            is_running = (res.exit_code == 0)
            
        # Get only the last N lines (not the entire accumulated buffer)
        out_res = await self.exec_command(
            f"tail -n {tail_lines} /opt/workspace/jobs/{job_id}.log",
            clean_output=True,
        )

        # Get total line count for context
        wc_res = await self.exec_command(
            f"wc -l < /opt/workspace/jobs/{job_id}.log",
            clean_output=False,
        )
        total_lines = wc_res.stdout.strip()
        
        return {
            "job_id": job_id,
            "pid": pid,
            "is_running": is_running,
            "total_lines": total_lines,
            "showing_last": tail_lines,
            "output": out_res.stdout,
            "log_path": f"/opt/workspace/jobs/{job_id}.log",
        }
        
    async def kill_job(self, job_id: str) -> bool:
        """Kill a running background job."""
        try:
            pid_content = await self.read_file(f"/opt/workspace/jobs/{job_id}.pid")
            pid = pid_content.strip()
        except Exception:
            return False
            
        if pid:
            res = await self.exec_command(f"kill -9 {pid}")
            return res.exit_code == 0
        return False


    # ------------------------------------------------------------------
    # File I/O via tar archives
    # ------------------------------------------------------------------

    async def write_file(
        self, container_path: str, content: str | bytes, mode: int = 0o755
    ) -> None:
        """Write a file into the running container using put_archive."""
        if self._container is None:
            raise RuntimeError("Container is not running.")

        data = content.encode("utf-8") if isinstance(content, str) else content

        def _put():
            tarstream = io.BytesIO()
            with tarfile.open(fileobj=tarstream, mode="w") as tar:
                info = tarfile.TarInfo(name=os.path.basename(container_path))
                info.size = len(data)
                info.mode = mode
                tar.addfile(info, io.BytesIO(data))
            tarstream.seek(0)
            dir_path = os.path.dirname(container_path) or "/"
            # Ensure parent directory exists
            self._container.exec_run(["mkdir", "-p", dir_path])
            self._container.put_archive(dir_path, tarstream)

        await asyncio.to_thread(_put)
        logger.debug("Wrote file: %s (%d bytes)", container_path, len(data))

    async def _write_file_internal(self, container_path: str, content: str) -> None:
        """Internal helper for writing artifact logs. Ensures parent dirs exist."""
        await self.write_file(container_path, content)

    async def read_file(self, container_path: str) -> str:
        """Read a file from the running container using get_archive."""
        if self._container is None:
            raise RuntimeError("Container is not running.")

        def _read():
            bits, _ = self._container.get_archive(container_path)
            stream = io.BytesIO()
            for chunk in bits:
                stream.write(chunk)
            stream.seek(0)
            with tarfile.open(fileobj=stream, mode="r") as tar:
                member = tar.getmembers()[0]
                f = tar.extractfile(member)
                return f.read().decode("utf-8", errors="replace") if f else ""

        content = await asyncio.to_thread(_read)
        logger.debug("Read file: %s (%d bytes)", container_path, len(content))
        return content

    # ------------------------------------------------------------------
    # Metasploit readiness
    # ------------------------------------------------------------------

    async def wait_for_msfrpcd(
        self, max_retries: int = 90, interval: float = 2.0
    ):
        """
        Poll msfrpcd until it accepts RPC connections.

        Returns a connected MsfRpcClient instance.
        Raises TimeoutError if msfrpcd doesn't become ready.
        """
        from pymetasploit3.msfrpc import MsfRpcClient

        logger.info(
            "Waiting for msfrpcd to become ready (max %ds)...",
            max_retries * interval,
        )

        for attempt in range(1, max_retries + 1):
            try:
                client = await asyncio.to_thread(
                    MsfRpcClient,
                    self._config.msf_password,
                    server="127.0.0.1",
                    port=55553,
                    ssl=False,
                )
                logger.info("msfrpcd ready after %d attempts.", attempt)
                return client
            except Exception:
                if attempt < max_retries:
                    await asyncio.sleep(interval)

        raise TimeoutError(
            f"msfrpcd did not become ready after {max_retries * interval}s"
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _verify_setup(self) -> None:
        """
        Verify that hercules_setup.py has been run:
          1. Docker is installed and daemon is running.
          2. The pre-built hercules-kali image exists.

        Raises SystemExit with a clear, actionable message if not.
        """
        # Check Docker availability
        logger.info("Checking Docker availability...")
        try:
            self._client = await asyncio.to_thread(docker.from_env)
            await asyncio.to_thread(self._client.ping)
            logger.info("Docker daemon is running.")
        except DockerException as exc:
            os_name = platform.system()
            if os_name == "Windows":
                docker_hint = "Install Docker Desktop: https://docs.docker.com/desktop/install/windows-install/"
            elif os_name == "Linux":
                docker_hint = "Install: curl -fsSL https://get.docker.com | sh && sudo systemctl start docker"
            else:
                docker_hint = "Install Docker Desktop: https://docs.docker.com/desktop/install/mac-install/"

            error_msg = (
                "\n" + "=" * 60 + "\n"
                "  HERCULES ERROR: Docker is not available.\n"
                + "=" * 60 + "\n\n"
                "  The Docker daemon is not running or Docker is not installed.\n\n"
                f"  Platform: {os_name}\n"
                f"  Fix: {docker_hint}\n\n"
                "  After installing Docker, run setup:\n"
                "    python hercules_setup.py\n\n"
                + "=" * 60 + "\n"
            )
            logger.critical(error_msg)
            raise SystemExit(error_msg) from exc

        # Check image exists
        try:
            await asyncio.to_thread(self._client.images.get, self.IMAGE)
            logger.info("Image '%s' found locally. Ready for instant startup.", self.IMAGE)
        except ImageNotFound:
            error_msg = (
                "\n" + "=" * 60 + "\n"
                "  HERCULES ERROR: Setup not complete.\n"
                + "=" * 60 + "\n\n"
                f"  The '{self.IMAGE}' Docker image was not found.\n"
                "  You must run the setup script first:\n\n"
                "    python hercules_setup.py\n\n"
                "  This is a one-time operation that builds the image\n"
                "  with all offensive security tools pre-installed.\n\n"
                + "=" * 60 + "\n"
            )
            logger.critical(error_msg)
            raise SystemExit(error_msg)

    async def _ensure_wordlists(self) -> None:
        """Download SecLists and rockyou.txt to the local wordlists folder if not present."""
        wordlists_dir = self._config.project_root / "wordlists"
        wordlists_dir.mkdir(parents=True, exist_ok=True)

        for filename, url in _WORDLIST_URLS.items():
            dest = wordlists_dir / filename
            if dest.exists():
                logger.info("Wordlist '%s' already present.", filename)
                continue

            logger.info(
                "Downloading '%s' (one-time download)...", filename
            )

            def _download(url=url, dest=dest):
                urllib.request.urlretrieve(url, str(dest))

            try:
                await asyncio.to_thread(_download)
                logger.info("Downloaded '%s' successfully.", filename)
            except Exception as exc:
                logger.warning(
                    "Failed to download '%s': %s. "
                    "Wordlists will not be available inside the container. "
                    "You can manually place them in: %s",
                    filename,
                    exc,
                    wordlists_dir,
                )

    async def _wait_for_ready(self, timeout: int = 30) -> None:
        """Wait for the entrypoint script to finish initial setup."""
        logger.info("Waiting for container entrypoint to complete...")

        for _ in range(timeout):
            result = await self.exec_command("echo ready", timeout=5)
            if result.exit_code == 0:
                logger.info("Container is ready.")
                return
            await asyncio.sleep(1)

        logger.warning("Container readiness check timed out after %ds.", timeout)

    @property
    def container(self) -> Container | None:
        return self._container

    @property
    def is_ready(self) -> bool:
        return self._container is not None and self._bootstrapped
