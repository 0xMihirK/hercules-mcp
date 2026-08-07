"""
Docker container lifecycle manager for Hercules.

Manages the creation, command execution, file I/O, and teardown of the
Hercules Kali container. Uses an agent-prepared, capability-specific Docker
image for instant startup. Missing images are diagnosed without mutating setup.

All blocking Docker SDK calls are wrapped with asyncio.to_thread() to
keep the event loop free for parallel tool execution.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import platform
import shlex
import socket
import subprocess
import sys
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, BinaryIO, cast

from docker.errors import APIError, DockerException, ImageNotFound, NotFound

import docker
from hercules.core.build_info import (
    IMAGE_APT_SUITE_LABEL,
    IMAGE_BASE_DIGEST_LABEL,
    IMAGE_BASE_REPOSITORY_LABEL,
    IMAGE_BUILD_CA_LABEL,
    IMAGE_CAPABILITIES_LABEL,
    IMAGE_CAPABILITY_MANIFEST_LABEL,
    IMAGE_CLOAKBROWSER_SHA256_LABEL,
    IMAGE_CLOAKBROWSER_VERSION_LABEL,
    IMAGE_FINGERPRINT_LABEL,
    IMAGE_PLATFORM_LABEL,
    KALI_APT_SUITE,
    KALI_BASE_DIGEST,
    KALI_BASE_REPOSITORY,
    capability_manifest_sha256,
    image_build_fingerprint,
    image_identity,
    legacy_raw_image_identity,
)
from hercules.core.instance_lock import HerculesPortAllocationLock
from hercules.core.security import redact_secrets, reject_control_chars, safe_filename
from hercules.core.tool_catalog import (
    ALL_CAPABILITIES,
    format_capabilities,
    required_backends,
)
from hercules.core.wordlists import provision_wordlists
from hercules.core.workspace import WorkspaceManager, utc_now
from hercules.output.banners import strip_known_banners
from hercules.output.filters import apply_tool_filter
from hercules.output.sanitizer import escape_display_controls, sanitize
from hercules.output.truncator import truncate_output

if TYPE_CHECKING:
    from docker.models.containers import Container

    from hercules.core.config import HerculesConfig

logger = logging.getLogger("hercules.docker")
# Container-internal services bind all interfaces only where Docker host
# publication is separately constrained (or for explicit listener ports).
_CONTAINER_ALL_INTERFACES = "0.0.0.0"  # nosec B104
_DEFAULT_MSF_RPC_PORT = 15_553
_SERVICE_FALLBACK_MIN = 10_000
_SERVICE_FALLBACK_MAX = 32_767
_SERVICE_FALLBACK_STRIDE = 131
_RPC_FALLBACK_SEED = 15_553
_STREAM_FALLBACK_SEED = 17_553


class ContainerUnavailable(RuntimeError):
    """Raised when Docker reports the active container is gone or stopped."""


class RuntimeInitializing(RuntimeError):
    """Raised when a tool reaches its bounded wait while bootstrap continues."""


class RuntimeUnavailable(RuntimeError):
    """Raised when background runtime bootstrap failed deterministically."""


def _project_hash(project_root) -> str:
    normalized = os.path.normcase(str(project_root.resolve()))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def _is_process_running(pid: str | int | None) -> bool:
    try:
        pid_int = int(pid)
    except (TypeError, ValueError):
        return False
    if pid_int <= 0:
        return False

    if platform.system() == "Windows":
        try:
            import ctypes

            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            handle = ctypes.windll.kernel32.OpenProcess(
                PROCESS_QUERY_LIMITED_INFORMATION, False, pid_int
            )
            if handle:
                exit_code = ctypes.c_ulong()
                try:
                    if not ctypes.windll.kernel32.GetExitCodeProcess(
                        handle,
                        ctypes.byref(exit_code),
                    ):
                        return False
                    return exit_code.value == 259  # STILL_ACTIVE
                finally:
                    ctypes.windll.kernel32.CloseHandle(handle)
            return False
        except Exception:
            return False

    try:
        os.kill(pid_int, 0)
        return True
    except OSError:
        return False


def _process_start_token(pid: str | int | None) -> str:
    """Return a stable process-creation token so PID reuse is never trusted."""
    try:
        pid_int = int(pid)
    except (TypeError, ValueError):
        return ""
    if pid_int <= 0:
        return ""

    if platform.system() == "Windows":
        try:
            import ctypes

            class _FileTime(ctypes.Structure):
                _fields_ = [
                    ("low", ctypes.c_uint32),
                    ("high", ctypes.c_uint32),
                ]

            query_limited_information = 0x1000
            handle = ctypes.windll.kernel32.OpenProcess(
                query_limited_information,
                False,
                pid_int,
            )
            if not handle:
                return ""
            creation = _FileTime()
            exit_time = _FileTime()
            kernel = _FileTime()
            user = _FileTime()
            try:
                ok = ctypes.windll.kernel32.GetProcessTimes(
                    handle,
                    ctypes.byref(creation),
                    ctypes.byref(exit_time),
                    ctypes.byref(kernel),
                    ctypes.byref(user),
                )
                if not ok:
                    return ""
                value = (int(creation.high) << 32) | int(creation.low)
                return f"win-{value:x}"
            finally:
                ctypes.windll.kernel32.CloseHandle(handle)
        except Exception:
            return ""

    if platform.system() == "Linux":
        try:
            stat_text = Path(f"/proc/{pid_int}/stat").read_text(encoding="ascii")
            fields = stat_text.rsplit(")", 1)[1].strip().split()
            # Fields after the command start at process-stat field 3. Linux's
            # process start time is field 22, hence zero-based index 19 here.
            return f"linux-{fields[19]}"
        except (OSError, IndexError):
            return ""

    try:
        started = subprocess.check_output(
            ["ps", "-o", "lstart=", "-p", str(pid_int)],
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=2,
        ).strip()
    except Exception:
        return ""
    if not started:
        return ""
    digest = hashlib.sha256(started.encode("utf-8")).hexdigest()[:16]
    return f"posix-{digest}"


def _owner_process_is_live(labels: dict[str, str]) -> bool:
    """Validate the exact labeled owner process, failing closed for legacy labels."""
    owner_pid = labels.get("hercules.owner_pid")
    if not _is_process_running(owner_pid):
        return False
    expected = labels.get("hercules.owner_start_token", "")
    if not expected:
        # Legacy containers lack a creation token. Preserve them while their
        # PID exists rather than risking deletion after an ambiguous lookup.
        return True
    return _process_start_token(owner_pid) == expected


def _recoverable_docker_error(exc: Exception) -> bool:
    if isinstance(exc, NotFound):
        return True
    if isinstance(exc, ContainerUnavailable):
        return True
    if isinstance(exc, APIError):
        text = str(exc).lower()
        return "not found" in text or "not running" in text or "409" in text or "404" in text
    return False


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
    raw_artifact: str = ""
    raw_artifacts: dict[str, str] | None = None
    stdout_artifact: str = ""
    stderr_artifact: str = ""
    filter_notes: list[str] | None = None
    output_transform: list[dict] | None = None
    output_filtered: bool = False
    output_complete: bool = True
    evidence_complete: bool = True
    stdout_truncated: bool = False
    stderr_truncated: bool = False
    stdout_chars: int = 0
    stderr_chars: int = 0
    stdout_bytes: int = 0
    stderr_bytes: int = 0
    stdout_chars_exact: bool = True
    stderr_chars_exact: bool = True
    inline_stdout_chars: int = 0
    inline_stderr_chars: int = 0
    estimated_inline_tokens: int = 0
    status: str = ""
    timed_out: bool = False
    timeout_seconds: int | float | None = None
    terminated: bool = False
    partial_output: bool = False
    container_recovered: bool = False
    old_session_id: str = ""
    session_id: str = ""
    recovery_reason: str = ""
    recovery_mode: str = ""
    workspace_preserved: bool = False
    note: str = ""

    def to_dict(self) -> dict:
        d = {
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "duration_seconds": self.duration_seconds,
            "command": self.command,
            "output_filtered": self.output_filtered,
            "output_complete": self.output_complete,
            "evidence_complete": self.evidence_complete,
            "stdout_truncated": self.stdout_truncated,
            "stderr_truncated": self.stderr_truncated,
            "stdout_chars": self.stdout_chars,
            "stderr_chars": self.stderr_chars,
            "stdout_bytes": self.stdout_bytes,
            "stderr_bytes": self.stderr_bytes,
            "stdout_chars_exact": self.stdout_chars_exact,
            "stderr_chars_exact": self.stderr_chars_exact,
            "inline_stdout_chars": self.inline_stdout_chars,
            "inline_stderr_chars": self.inline_stderr_chars,
            "estimated_inline_tokens": self.estimated_inline_tokens,
        }
        if self.status:
            d["status"] = self.status
        if self.timed_out:
            d["timed_out"] = True
            d["timeout_seconds"] = self.timeout_seconds
            d["terminated"] = self.terminated
            d["partial_output"] = self.partial_output
        if self.truncated:
            d["truncated"] = True
            d["artifact"] = self.artifact
        if self.summary:
            d["summary"] = self.summary
        if self.raw_artifact:
            d["raw_artifact"] = self.raw_artifact
        if self.raw_artifacts:
            d["raw_artifacts"] = self.raw_artifacts
        if self.stdout_artifact:
            d["stdout_artifact"] = self.stdout_artifact
        if self.stderr_artifact:
            d["stderr_artifact"] = self.stderr_artifact
        if self.filter_notes:
            d["filter_notes"] = self.filter_notes
        if self.output_transform:
            d["output_transform"] = self.output_transform
        if self.container_recovered:
            d["container_recovered"] = True
            d["old_session_id"] = self.old_session_id
            d["session_id"] = self.session_id
            d["recovery_reason"] = self.recovery_reason
            if self.recovery_mode:
                d["recovery_mode"] = self.recovery_mode
            d["workspace_preserved"] = self.workspace_preserved
            if self.note:
                d["note"] = self.note
        return d


class _StreamCapture:
    """Keep bounded head/tail bytes and lazily spool overflow to an artifact."""

    def __init__(
        self,
        limit: int,
        *,
        artifact_opener: Callable[[], BinaryIO],
        artifact_container: str,
    ) -> None:
        self.limit = max(64 * 1024, int(limit))
        self._artifact_opener = artifact_opener
        self.artifact_container = artifact_container
        self.total_bytes = 0
        self._buffer = bytearray()
        self._head = bytearray()
        self._tail = bytearray()
        self._overflow = False
        self._artifact = None
        self.artifact_error = ""

    @property
    def overflowed(self) -> bool:
        return self._overflow

    @property
    def artifact_path(self) -> str:
        return (
            self.artifact_container
            if self._overflow and self._artifact is not None and not self.artifact_error
            else ""
        )

    def append(self, chunk: bytes) -> None:
        if not chunk:
            return
        self.total_bytes += len(chunk)
        if not self._overflow and len(self._buffer) + len(chunk) <= self.limit:
            self._buffer.extend(chunk)
            return

        if not self._overflow:
            combined = bytes(self._buffer) + chunk
            self._overflow = True
            head_limit = self.limit // 2
            tail_limit = self.limit - head_limit
            self._head.extend(combined[:head_limit])
            self._tail.extend(combined[-tail_limit:])
            self._buffer.clear()
            try:
                self._artifact = self._artifact_opener()
                self._artifact.write(combined)
            except OSError as exc:
                self.artifact_error = str(exc)
                self._artifact = None
            return

        tail_limit = self.limit - len(self._head)
        self._tail.extend(chunk)
        if len(self._tail) > tail_limit:
            del self._tail[: len(self._tail) - tail_limit]
        if self._artifact is not None:
            try:
                self._artifact.write(chunk)
            except OSError as exc:
                self.artifact_error = str(exc)
                self._artifact.close()
                self._artifact = None

    def finish(self) -> None:
        if self._artifact is not None:
            try:
                self._artifact.flush()
                os.fsync(self._artifact.fileno())
            except OSError as exc:
                self.artifact_error = str(exc)
            finally:
                self._artifact.close()

    def value(self) -> bytes:
        if not self._overflow:
            return bytes(self._buffer)
        omitted = max(0, self.total_bytes - len(self._head) - len(self._tail))
        marker = (
            f"\n\n[STREAM OUTPUT TRUNCATED IN MEMORY: {omitted} bytes omitted; "
            f"full stream artifact: {self.artifact_path or 'unavailable'}]\n\n"
        ).encode()
        return bytes(self._head) + marker + bytes(self._tail)


# ---------------------------------------------------------------------------
# DockerManager
# ---------------------------------------------------------------------------

class DockerManager:
    """
    Manages the lifecycle of the Hercules Kali Docker container.

    Startup flow:
      1. Check Docker is installed and the daemon is running.
      2. Verify the immutable selected-capability image.
      3. Prepare only wordlists required by the selected capabilities.
      4. Create the container with workspace + wordlists mounted.
      5. Poll readiness in the background while MCP clients initialize.

    All public methods are async-safe.
    """

    IMAGE = "hercules-kali"

    def __init__(
        self,
        config: HerculesConfig,
        *,
        instance_id: str | None = None,
        owns_instance_lock: bool = False,
    ) -> None:
        self._config = config
        installed = config.installed_capabilities or ALL_CAPABILITIES
        self.IMAGE, _fingerprint = image_identity(
            config.project_root,
            installed,
            build_ca_sha256=config.build_ca_sha256,
            target_platform=config.image_platform,
            cloakbrowser_version=config.cloakbrowser_version,
            cloakbrowser_sha256=config.cloakbrowser_sha256,
        )
        self._legacy_image, self._legacy_image_fingerprint = legacy_raw_image_identity(
            config.project_root,
            installed,
            build_ca_sha256=config.build_ca_sha256,
            target_platform=config.image_platform,
            cloakbrowser_version=config.cloakbrowser_version,
            cloakbrowser_sha256=config.cloakbrowser_sha256,
        )
        self._client: docker.DockerClient | None = None
        self._container: Container | None = None
        self._workspace = WorkspaceManager(
            config.resolved_workspace_root,
            max_inline_bytes=config.max_inline_file_bytes,
        )
        self._session_id: str = self._workspace.allocate_session()
        self._container_name: str = f"hercules-{self._session_id}"
        self._generation: int = 0
        self._operator_stopped: bool = False
        self._configured_listener_ports: tuple[int, ...] = tuple(
            config.listener_ports
        )
        self._listener_ports: tuple[int, ...] = self._configured_listener_ports
        self._configured_msf_rpc_port = int(config.msf_rpc_port)
        self._msf_rpc_port = self._configured_msf_rpc_port
        self._configured_browser_stream_port = int(config.browser_stream_port or 0)
        self._browser_stream_host_port = self._configured_browser_stream_port
        self._port_allocation_slot = 0
        self._ports_reallocated = False
        if (
            not config.skip_metasploit
            and config.msf_rpc_port in self._listener_ports
        ):
            raise ValueError(
                "MSF_RPC_PORT must not overlap HERCULES_LISTENER_PORTS; "
                "the RPC service is loopback-only."
            )
        if config.browser_stream_port and (
            config.browser_stream_port in self._listener_ports
            or (
                not config.skip_metasploit
                and config.browser_stream_port == config.msf_rpc_port
            )
        ):
            raise ValueError(
                "BROWSER_STREAM_PORT must not overlap MSF_RPC_PORT or "
                "HERCULES_LISTENER_PORTS."
            )
        self._listener_port_range: tuple[int, int] = (
            (min(self._listener_ports), max(self._listener_ports))
            if self._listener_ports
            else (0, 0)
        )
        self._project_root_hash: str = _project_hash(config.project_root)
        self._workspace_root_hash: str = _project_hash(
            config.resolved_workspace_root
        )
        self._instance_id: str = instance_id or uuid.uuid4().hex
        self._owns_instance_lock: bool = bool(owns_instance_lock)
        self._bootstrapped: bool = False
        self._ready: bool = False
        self._ready_task: asyncio.Task | None = None
        self._startup_task: asyncio.Task | None = None
        self._startup_error: str = ""
        self._startup_wait_seconds: float = 120.0
        self._reclaimed_containers: list[str] = []
        self._host_port_bindings: dict[str, object] = {}
        # Serializes container recovery so concurrent tool calls can't spawn
        # duplicate containers (thundering herd). Created lazily because some
        # tests construct DockerManager via __new__ and skip __init__.
        self._recovery_lock: asyncio.Lock | None = None
        # Serializes in-container msfrpcd restarts on this instance's RPC port.
        self._msf_restart_lock: asyncio.Lock | None = None
        self._job_lock: asyncio.Lock | None = None
        self._browser_stream_lock: asyncio.Lock | None = None
        self._browser_stream_relay_state: dict[str, object] = {}
        self._orphan_guardian: subprocess.Popen | None = None
        configured_stream_port = int(
            getattr(config, "browser_stream_port", 0) or 0
        )
        self._browser_stream_relay_port = (
            self._select_browser_relay_port(configured_stream_port)
            if configured_stream_port and platform.system() != "Linux"
            else configured_stream_port
        )
        self._generation_callbacks: list = []
        # Set while stop_container() is tearing down, so the watchdog and
        # recovery paths never resurrect a container we are deliberately killing.
        self._shutting_down: bool = False

    @property
    def session_id(self) -> str:
        """Unique ID for the current session. Changes on restart."""
        return self._session_id

    @property
    def generation(self) -> int:
        """Monotonic container generation used to invalidate process-local caches."""
        return self._generation

    @property
    def listener_port_range(self) -> tuple[int, int]:
        return self._listener_port_range

    @property
    def listener_ports(self) -> tuple[int, ...]:
        return self._listener_ports

    @property
    def msf_rpc_port(self) -> int:
        return int(getattr(self, "_msf_rpc_port", _DEFAULT_MSF_RPC_PORT))

    @property
    def browser_stream_port(self) -> int:
        """Effective host loopback port for the optional browser stream."""
        return int(getattr(self, "_browser_stream_host_port", 0) or 0)

    @property
    def port_allocation(self) -> dict[str, object]:
        """Return configured and effective non-secret port-selection facts."""
        return {
            "automatic": bool(
                getattr(self._config, "auto_allocate_ports", True)
            ),
            "strategy": (
                "configured_then_low_service_pool"
                if getattr(self._config, "auto_allocate_ports", True)
                else "configured_only"
            ),
            "slot": int(getattr(self, "_port_allocation_slot", 0)),
            "attempts": int(getattr(self, "_port_allocation_slot", 0)) + 1,
            "reallocated": bool(getattr(self, "_ports_reallocated", False)),
            "reallocation_reason": (
                "configured_ports_unavailable"
                if getattr(self, "_ports_reallocated", False)
                else ""
            ),
            "automatic_service_fallback_range": [
                _SERVICE_FALLBACK_MIN,
                _SERVICE_FALLBACK_MAX,
            ],
            "configured_rpc_in_windows_default_dynamic_range": (
                49_152
                <= int(
                    getattr(
                        self,
                        "_configured_msf_rpc_port",
                        self.msf_rpc_port,
                    )
                )
                <= 65_535
            ),
            "configured": {
                "metasploit_rpc": int(
                    getattr(self, "_configured_msf_rpc_port", self.msf_rpc_port)
                ),
                "listeners": list(
                    getattr(self, "_configured_listener_ports", self.listener_ports)
                ),
                "browser_stream": int(
                    getattr(
                        self,
                        "_configured_browser_stream_port",
                        self.browser_stream_port,
                    )
                ),
            },
            "effective": {
                "metasploit_rpc": self.msf_rpc_port,
                "listeners": list(self.listener_ports),
                "browser_stream": self.browser_stream_port,
            },
        }

    @property
    def workspace_manager(self) -> WorkspaceManager:
        return self._workspace

    @property
    def workspace_path(self) -> Path:
        return self._workspace.session_path(self._session_id)

    @property
    def browser_stream_relay_port(self) -> int:
        """Container-side relay port; the configured port remains host-facing."""
        return int(getattr(self, "_browser_stream_relay_port", 0) or 0)

    @property
    def network_mode(self) -> str:
        configured = str(getattr(self._config, "docker_network", "") or "")
        if configured:
            return configured
        return "host" if platform.system() == "Linux" else "bridge"

    @property
    def container_running(self) -> bool:
        """Whether this manager currently has an attached container object."""
        return self._container is not None

    def _get_recovery_lock(self) -> asyncio.Lock:
        """Lazily create the recovery lock (safe for __new__-constructed mocks)."""
        lock = getattr(self, "_recovery_lock", None)
        if lock is None:
            lock = asyncio.Lock()
            self._recovery_lock = lock
        return lock

    def _get_msf_restart_lock(self) -> asyncio.Lock:
        """Lazily create the msfrpcd-restart lock."""
        lock = getattr(self, "_msf_restart_lock", None)
        if lock is None:
            lock = asyncio.Lock()
            self._msf_restart_lock = lock
        return lock

    def _get_job_lock(self) -> asyncio.Lock:
        """Serialize job-id allocation and concurrency accounting."""
        lock = getattr(self, "_job_lock", None)
        if lock is None:
            lock = asyncio.Lock()
            self._job_lock = lock
        return lock

    def _get_browser_stream_lock(self) -> asyncio.Lock:
        """Serialize live-view relay replacement across browser sessions."""
        lock = getattr(self, "_browser_stream_lock", None)
        if lock is None:
            lock = asyncio.Lock()
            self._browser_stream_lock = lock
        return lock

    def _select_browser_relay_port(self, host_port: int) -> int:
        """Choose a private high container port distinct from exposed services."""
        excluded = {
            int(host_port),
            self.msf_rpc_port,
            *(int(port) for port in getattr(self, "_listener_ports", ())),
        }
        # Stay above Linux's usual 32768-60999 ephemeral range so the
        # agent-browser backend cannot accidentally receive the relay port.
        lower = 61_000
        span = 65_535 - lower
        first = lower + (int(uuid.uuid4().hex[:4], 16) % span)
        for offset in range(span):
            candidate = lower + ((first - lower + offset) % span)
            if candidate not in excluded:
                return candidate
        raise RuntimeError("could not allocate a private browser stream relay port")

    def mark_operator_stopped(self) -> None:
        """Prevent implicit recovery until an explicit session rotation."""
        self._operator_stopped = True

    def begin_shutdown(self) -> None:
        """Disable watchdog/recovery while an intentional teardown is in progress."""
        self._shutting_down = True

    def attach_startup_task(self, task: asyncio.Task) -> None:
        """Attach the single lifespan-owned background bootstrap task."""
        current = getattr(self, "_startup_task", None)
        if current is not None and not current.done() and current is not task:
            raise RuntimeError("a Hercules runtime bootstrap task is already active")
        self._startup_task = task
        self._startup_error = ""

    def mark_startup_unavailable(self, message: str) -> None:
        """Record a sanitized deterministic bootstrap failure for later calls."""
        self._startup_error = str(message).strip()[:2000]

    def clear_startup_state(self) -> None:
        """Allow an explicit session start after a failed initial bootstrap."""
        task = getattr(self, "_startup_task", None)
        if task is not None and not task.done():
            raise RuntimeError("runtime bootstrap is still active")
        self._startup_task = None
        self._startup_error = ""

    async def cancel_startup(self) -> None:
        """Cancel and settle bootstrap before intentional container teardown."""
        task = getattr(self, "_startup_task", None)
        if task is None or task.done() or task is asyncio.current_task():
            return
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    async def _wait_for_startup(self) -> None:
        """Wait once for lifespan bootstrap without letting callers cancel it."""
        task = getattr(self, "_startup_task", None)
        if task is not None and task is not asyncio.current_task():
            if not task.done():
                try:
                    await asyncio.wait_for(
                        asyncio.shield(task),
                        timeout=float(
                            getattr(self, "_startup_wait_seconds", 120.0)
                        ),
                    )
                except TimeoutError as exc:
                    raise RuntimeInitializing(
                        "The Kali runtime is still initializing after 120 seconds."
                    ) from exc
            # Consume a task exception defensively if a compatibility caller
            # supplied its own bootstrap task instead of the lifespan wrapper.
            if task.done() and not task.cancelled():
                error = task.exception()
                if error is not None:
                    raise RuntimeUnavailable(str(error)) from error
        startup_error = str(getattr(self, "_startup_error", "") or "")
        if startup_error:
            raise RuntimeUnavailable(
                f"The Hercules runtime is unavailable: {startup_error}"
            )

    def register_generation_callback(self, callback) -> None:
        """Register a process-local cache reset callback."""
        self._generation_callbacks.append(callback)

    def _record_reclaimed_container(self, name: str) -> None:
        reclaimed = getattr(self, "_reclaimed_containers", None)
        if reclaimed is None:
            reclaimed = []
            self._reclaimed_containers = reclaimed
        reclaimed.append(name)

    def _notify_generation_changed(self) -> None:
        self._browser_stream_relay_state = {}
        for callback in getattr(self, "_generation_callbacks", []):
            try:
                callback(self._generation)
            except Exception as exc:
                logger.warning("Generation reset callback failed: %s", exc)

    @staticmethod
    def _preflight_host_ports(ports: dict[str, object]) -> None:
        """Fail early when a Docker-published TCP host port is unavailable."""
        checked: set[tuple[str, int]] = set()
        for binding in ports.values():
            if isinstance(binding, tuple):
                host = str(binding[0])
                port = int(binding[1])
            else:
                # Configured reverse-listener ports intentionally accept callbacks.
                host = _CONTAINER_ALL_INTERFACES
                port = int(binding)
            probe_hosts = [host]
            # This compares a configured value; it does not open a listener.
            if host == _CONTAINER_ALL_INTERFACES:
                # Docker Desktop may keep a separate loopback forwarding proxy
                # alive briefly after its wildcard publication disappears.
                probe_hosts.append("127.0.0.1")
            elif host == "::":
                probe_hosts.append("::1")
            for probe_host in probe_hosts:
                key = (probe_host, port)
                if key in checked:
                    continue
                checked.add(key)
                family = socket.AF_INET6 if ":" in probe_host else socket.AF_INET
                with socket.socket(family, socket.SOCK_STREAM) as probe:
                    try:
                        probe.bind((probe_host, port))
                    except OSError as exc:
                        raise RuntimeError(
                            "Required Hercules host TCP port "
                            f"{probe_host}:{port} is unavailable."
                        ) from exc

    @staticmethod
    def _fallback_service_port(
        configured: int,
        *,
        seed: int,
        ordinal: int,
    ) -> int:
        """Return a dispersed low service port, excluding the configured value."""
        span = _SERVICE_FALLBACK_MAX - _SERVICE_FALLBACK_MIN + 1
        wanted = int(ordinal)
        seen = 0
        for index in range(span):
            candidate = _SERVICE_FALLBACK_MIN + (
                (seed - _SERVICE_FALLBACK_MIN + index * _SERVICE_FALLBACK_STRIDE)
                % span
            )
            if candidate == int(configured):
                continue
            if seen == wanted:
                return candidate
            seen += 1
        raise RuntimeError("could not allocate a low loopback service port")

    def _candidate_runtime_ports(
        self,
        slot: int,
    ) -> tuple[int, tuple[int, ...], int] | None:
        """Translate configured ports into one deterministic allocation slot."""
        configured_listeners = getattr(self, "_configured_listener_ports", ())
        if configured_listeners:
            stride = max(configured_listeners) - min(configured_listeners) + 1
        else:
            stride = 1
        listeners = tuple(
            int(port) + (int(slot) * stride) for port in configured_listeners
        )
        configured_rpc = int(
            getattr(self, "_configured_msf_rpc_port", _DEFAULT_MSF_RPC_PORT)
        )
        configured_stream = int(
            getattr(self, "_configured_browser_stream_port", 0) or 0
        )
        if int(slot) == 0:
            rpc_port = configured_rpc
            stream_port = configured_stream
        else:
            ordinal = int(slot) - 1
            rpc_port = self._fallback_service_port(
                configured_rpc,
                seed=_RPC_FALLBACK_SEED,
                ordinal=ordinal,
            )
            stream_port = (
                self._fallback_service_port(
                    configured_stream,
                    seed=_STREAM_FALLBACK_SEED,
                    ordinal=ordinal,
                )
                if configured_stream
                else 0
            )
        selected = [*listeners]
        if not self._config.skip_metasploit:
            selected.append(rpc_port)
        if stream_port:
            selected.append(stream_port)
        if any(port < 1 or port > 65_535 for port in selected):
            return None
        if len(selected) != len(set(selected)):
            return None
        return rpc_port, listeners, stream_port

    def _candidate_host_bindings(
        self,
        rpc_port: int,
        listeners: tuple[int, ...],
        stream_port: int,
    ) -> dict[str, object]:
        """Build a preflight-only map for every host-facing selected port."""
        bindings: dict[str, object] = {}
        if not self._config.skip_metasploit:
            bindings["metasploit-rpc"] = ("127.0.0.1", rpc_port)
        for index, port in enumerate(listeners):
            bindings[f"listener-{index}"] = (
                self._config.listener_bind_host,
                port,
            )
        if stream_port:
            bindings["browser-stream"] = ("127.0.0.1", stream_port)
        return bindings

    async def _allocate_runtime_ports(self) -> None:
        """Select the first collision-free port slot for this IDE instance."""
        automatic = bool(getattr(self._config, "auto_allocate_ports", True))
        slots = range(128) if automatic else range(1)
        last_error: RuntimeError | None = None
        for slot in slots:
            candidate = self._candidate_runtime_ports(slot)
            if candidate is None:
                continue
            rpc_port, listeners, stream_port = candidate
            bindings = self._candidate_host_bindings(
                rpc_port,
                listeners,
                stream_port,
            )
            try:
                await asyncio.to_thread(self._preflight_host_ports, bindings)
            except RuntimeError as exc:
                last_error = exc
                continue

            self._msf_rpc_port = rpc_port
            self._listener_ports = listeners
            self._listener_port_range = (
                (min(listeners), max(listeners)) if listeners else (0, 0)
            )
            self._browser_stream_host_port = stream_port
            if platform.system() == "Linux":
                self._browser_stream_relay_port = stream_port
            self._port_allocation_slot = slot
            self._ports_reallocated = slot != 0
            if slot:
                logger.warning(
                    "Configured Hercules ports are busy; IDE instance %s is using "
                    "allocation slot %d (RPC %d, listeners %s, stream %d).",
                    self._instance_id,
                    slot,
                    rpc_port,
                    listeners,
                    stream_port,
                )
            return

        if last_error is not None and not automatic:
            raise last_error
        raise RuntimeError(
            "Hercules could not find a collision-free runtime port allocation. "
            "The configured surface and 127 dispersed low service-port fallbacks "
            "were unavailable. Close unused Hercules clients, inspect OS-reserved "
            "ports, or set explicit non-conflicting ports."
        ) from last_error

    @staticmethod
    def _container_host_bindings(container: Container) -> dict[str, object]:
        """Return concrete host TCP bindings from inspected Docker metadata."""
        published = (
            getattr(container, "attrs", {})
            .get("NetworkSettings", {})
            .get("Ports", {})
            or {}
        )
        bindings: dict[str, object] = {}
        for container_port, entries in published.items():
            if not str(container_port).endswith("/tcp") or not entries:
                continue
            for index, entry in enumerate(entries):
                if not isinstance(entry, dict):
                    continue
                # An omitted HostIp means wildcard in Docker inspection metadata.
                host = str(entry.get("HostIp") or _CONTAINER_ALL_INTERFACES)
                raw_port = entry.get("HostPort")
                if not isinstance(raw_port, (str, int)):
                    continue
                try:
                    port = int(raw_port)
                except (TypeError, ValueError):
                    continue
                bindings[f"{container_port}:{index}"] = (host, port)
        return bindings

    async def _wait_for_host_ports_available(
        self,
        bindings: dict[str, object],
        *,
        timeout: float = 15.0,
    ) -> None:
        """Wait for prior owners or Docker forwarding proxies to release ports."""
        if not bindings:
            return
        deadline = time.monotonic() + timeout
        while True:
            try:
                await asyncio.to_thread(self._preflight_host_ports, bindings)
                return
            except RuntimeError as exc:
                if time.monotonic() >= deadline:
                    ports = sorted(
                        {
                            int(value[1])
                            for value in bindings.values()
                            if isinstance(value, tuple) and len(value) == 2
                        }
                    )
                    raise RuntimeError(
                        "Hercules host TCP ports remained unavailable after "
                        f"{timeout:g} seconds: {ports}"
                    ) from exc
                await asyncio.sleep(0.25)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start_container(self) -> None:
        """Serialize cross-client port selection through Docker publication."""
        allocation_lock = HerculesPortAllocationLock()
        acquire_task = asyncio.create_task(asyncio.to_thread(allocation_lock.acquire))
        try:
            await asyncio.shield(acquire_task)
        except asyncio.CancelledError:
            # A blocked native file-lock acquisition cannot be interrupted.
            # Settle it and release if it completes after caller cancellation.
            await acquire_task
            await asyncio.to_thread(allocation_lock.release)
            raise
        try:
            await self._start_container_locked()
        finally:
            await asyncio.to_thread(allocation_lock.release)

    def _start_orphan_guardian(self) -> None:
        """Launch independent exact-owner cleanup for abrupt client exits."""
        if self._config.preserve_container or self._container is None:
            return
        owner_token = _process_start_token(os.getpid())
        if not owner_token:
            logger.warning(
                "Could not establish exact process identity; orphan guardian disabled."
            )
            return
        argv = [
            sys.executable,
            "-m",
            "hercules.core.orphan_guardian",
            "--container-id",
            str(self._container.id),
            "--owner-pid",
            str(os.getpid()),
            "--owner-start-token",
            owner_token,
            "--project-hash",
            self._project_root_hash,
            "--workspace-hash",
            self._workspace_root_hash,
            "--instance-id",
            self._instance_id,
        ]
        kwargs: dict[str, object] = {
            "stdin": subprocess.DEVNULL,
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
            "close_fds": True,
        }
        if os.name == "nt":
            kwargs["creationflags"] = (
                subprocess.CREATE_NEW_PROCESS_GROUP
                | subprocess.DETACHED_PROCESS
                | subprocess.CREATE_NO_WINDOW
                | subprocess.CREATE_BREAKAWAY_FROM_JOB
            )
        else:
            kwargs["start_new_session"] = True
        try:
            self._orphan_guardian = subprocess.Popen(argv, **kwargs)
            logger.info(
                "Started exact-owner orphan guardian (pid=%s).",
                self._orphan_guardian.pid,
            )
        except OSError as exc:
            logger.warning("Could not start the Hercules orphan guardian: %s", exc)

    async def _settle_orphan_guardian(self) -> None:
        """Confirm the guardian exits after ordinary container cleanup."""
        process = getattr(self, "_orphan_guardian", None)
        self._orphan_guardian = None
        if process is None:
            return
        if process.poll() is None:
            process.terminate()
        try:
            await asyncio.wait_for(asyncio.to_thread(process.wait), timeout=3)
        except TimeoutError:
            process.kill()
            try:
                await asyncio.wait_for(asyncio.to_thread(process.wait), timeout=3)
            except TimeoutError:
                logger.warning(
                    "Orphan guardian PID %s did not terminate promptly.",
                    process.pid,
                )

    async def _start_container_locked(self) -> None:
        """Full startup: verify setup → create container → wait for ready."""
        # Step 1: Verify Docker and the selected immutable image.
        await self._verify_setup()

        # Step 2: Prepare only required checksum-validated assets.
        extracted_wordlists = await self._ensure_wordlists()

        # Step 3: Prepare host directories (session-isolated workspace)
        workspace_path = self._workspace.session_path(self._session_id)
        if await asyncio.to_thread(
            self._workspace.read_manifest,
            self._session_id,
        ) is None:
            raise RuntimeError(
                f"Active workspace session '{self._session_id}' is missing its "
                "valid Hercules ownership manifest."
            )

        wordlists_path = (
            self._config.wordlist_root or self._config.project_root / "wordlists"
        )
        wordlists_path.mkdir(parents=True, exist_ok=True)

        self._cleanup_empty_workspaces()
        if self._config.workspace_auto_prune:
            result = await asyncio.to_thread(
                self._workspace.prune,
                older_than_days=self._config.workspace_retention_days,
                max_sessions=self._config.workspace_max_sessions,
                max_bytes=self._config.workspace_max_bytes,
                apply=True,
                active_session=self._session_id,
            )
            if result["removed"]:
                logger.info(
                    "Workspace retention removed %d inactive session(s).",
                    len(result["removed"]),
                )

        # Cleanup orphaned containers without touching live sessions.
        await self._cleanup_orphaned_containers()
        await self._allocate_runtime_ports()

        # Step 4: Build container creation kwargs
        env_vars = {
            "MSF_PASSWORD": self._config.msf_password,
            "MSF_RPC_PORT": str(self.msf_rpc_port),
            "SKIP_METASPLOIT": "true" if self._config.skip_metasploit else "false",
            "HERCULES_INSTALLED_CAPABILITIES": format_capabilities(
                self._config.installed_capabilities or ALL_CAPABILITIES
            ),
            # Docker Desktop port forwarding cannot reach a service bound to
            # container loopback, so publish it on host loopback there. Linux
            # host networking shares the host namespace and can bind directly.
            # Docker Desktop needs an internal all-interface bind; the host
            # publication remains constrained to host loopback.
            "MSF_BIND_HOST": (
                "127.0.0.1"
                if platform.system() == "Linux"
                else _CONTAINER_ALL_INTERFACES
            ),
        }

        kwargs: dict = {
            "image": self.IMAGE,
            "name": self._container_name,
            "tty": True,
            "stdin_open": True,
            "detach": True,
            "environment": env_vars,
            "labels": {
                "hercules.managed": "true",
                "hercules.project_root_hash": self._project_root_hash,
                "hercules.project_root": str(self._config.project_root.resolve()),
                "hercules.workspace_root_hash": self._workspace_root_hash,
                "hercules.session_id": self._session_id,
                "hercules.owner_pid": str(os.getpid()),
                "hercules.owner_start_token": _process_start_token(os.getpid()),
                "hercules.instance_id": self._instance_id,
                "hercules.port_allocation_slot": str(self._port_allocation_slot),
                "hercules.msf_rpc_port": str(self.msf_rpc_port),
                "hercules.listener_ports": ",".join(
                    str(port) for port in self._listener_ports
                ),
                "hercules.browser_stream_port": str(self.browser_stream_port),
            },
            "volumes": {
                str(workspace_path): {"bind": "/opt/workspace", "mode": "rw"},
                str(wordlists_path): {"bind": "/opt/wordlists_host", "mode": "ro"},
            },
            "shm_size": "256m",
            # The MCP process owns this container's lifetime. A Docker restart
            # must not resurrect it after an IDE force-terminates the owner;
            # the live-process watchdog recreates/restarts it when appropriate.
            "restart_policy": {"Name": "no"},
        }
        if "seclists" in extracted_wordlists:
            kwargs["volumes"][str(extracted_wordlists["seclists"])] = {
                "bind": "/usr/share/wordlists/seclists",
                "mode": "ro",
            }
        if "rockyou" in extracted_wordlists:
            kwargs["volumes"][str(extracted_wordlists["rockyou"])] = {
                "bind": "/usr/share/wordlists/rockyou.txt",
                "mode": "ro",
            }

        # Linux normally uses host mode for VPNs. A named network override is
        # used by isolated labs and other operator-managed Docker topologies.
        configured_network = str(
            getattr(self._config, "docker_network", "") or ""
        )
        if platform.system() == "Linux" and not configured_network:
            kwargs["network_mode"] = "host"
        else:
            # Docker Desktop provides this name automatically. The explicit
            # mapping also makes it portable to native Linux/custom bridge
            # networks supported by modern Docker Engine. It names the Docker
            # engine host, which may be remote from the MCP client process.
            kwargs["extra_hosts"] = {
                "host.docker.internal": "host-gateway",
            }
            # Map RPC only when enabled; reverse-listener ports remain explicit.
            ports: dict[str, object] = {}
            if not self._config.skip_metasploit:
                ports[f"{self.msf_rpc_port}/tcp"] = (
                    "127.0.0.1",
                    self.msf_rpc_port,
                )
            for p in self._listener_ports:
                ports[f"{p}/tcp"] = (
                    self._config.listener_bind_host,
                    p,
                )
            # Optional headless browser live-view stream port (0 = disabled). The
            # cloakserve CDP port (9222) is deliberately NEVER mapped — it stays
            # loopback-only inside the container.
            stream_port = self.browser_stream_port
            if stream_port:
                ports[f"{self.browser_stream_relay_port}/tcp"] = (
                    "127.0.0.1",
                    int(stream_port),
                )
            kwargs["ports"] = ports
            if configured_network:
                kwargs["network"] = configured_network

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

        # Defensive: remove any pre-existing container holding our exact name
        # (for example, a legacy image with an old restart policy) to avoid a
        # 409 name clash.
        # We only reach here when we intend to OWN this name; the reattach path
        # adopts a still-running same-named container before calling us.
        try:
            clash = await asyncio.to_thread(
                self._client.containers.get, self._container_name
            )
            await asyncio.to_thread(clash.reload)
            labels = (
                getattr(clash, "attrs", {})
                .get("Config", {})
                .get("Labels", {})
                or {}
            )
            workspace_hash = labels.get("hercules.workspace_root_hash", "")
            instance_id = labels.get("hercules.instance_id", "")
            other_instance = bool(
                getattr(self, "_instance_id", "")
                and instance_id
                and instance_id != self._instance_id
            )
            owner_live = _owner_process_is_live(labels)
            legacy_live_owner = bool(
                not workspace_hash
                and instance_id != getattr(self, "_instance_id", "")
                and owner_live
            )
            if (
                labels.get("hercules.managed") != "true"
                or labels.get("hercules.project_root_hash") != self._project_root_hash
                or labels.get("hercules.session_id") != self._session_id
                or (workspace_hash and workspace_hash != self._workspace_root_hash)
                or (other_instance and owner_live)
                or legacy_live_owner
            ):
                raise RuntimeError(
                    f"Container name '{self._container_name}' is already in use by "
                    "a container Hercules cannot prove it owns."
                )
            released_bindings = self._container_host_bindings(clash)
            await asyncio.to_thread(clash.remove, force=True)
            await self._wait_for_host_ports_available(released_bindings)
            self._record_reclaimed_container(self._container_name)
            logger.info(
                "Removed owned pre-existing container '%s' before create.",
                self._container_name,
            )
        except NotFound:
            pass
        except RuntimeError:
            raise
        except Exception as exc:
            logger.warning("Failed to clear pre-existing container '%s': %s", self._container_name, exc)

        if "ports" in kwargs:
            await self._wait_for_host_ports_available(kwargs["ports"])
            self._host_port_bindings = dict(kwargs["ports"])
        elif kwargs.get("network_mode") == "host":
            host_ports: dict[str, object] = {
                f"{self.msf_rpc_port}/tcp": (
                    "127.0.0.1",
                    self.msf_rpc_port,
                ),
                **{
                    # Reverse-listener ports are the deliberate external surface.
                    f"{port}/tcp": (
                        self._config.listener_bind_host,
                        port,
                    )
                    for port in self._listener_ports
                },
            }
            stream_port = self.browser_stream_port
            if stream_port:
                host_ports[f"{int(stream_port)}/tcp"] = (
                    "127.0.0.1",
                    int(stream_port),
                )
            await self._wait_for_host_ports_available(host_ports)
            self._host_port_bindings = dict(host_ports)
        else:
            self._host_port_bindings = {}

        client = self._client
        if client is None:  # defensive invariant after _verify_setup
            raise RuntimeError("Docker client became unavailable before create.")

        async def create_owned_container() -> Container:
            created = await asyncio.to_thread(client.containers.run, **kwargs)
            return cast("Container", created)

        create_task = asyncio.create_task(create_owned_container())
        try:
            self._container = await asyncio.shield(create_task)
        except asyncio.CancelledError:
            # ``to_thread`` cannot be interrupted after Docker accepted the
            # create request. Settle it and remove any late-created container
            # before propagating cancellation, otherwise a client timeout can
            # leave fixed host ports reserved.
            try:
                created = await create_task
            except Exception as exc:
                logger.warning(
                    "Container creation ended during shutdown: %s", exc
                )
            else:
                self._container = created
                try:
                    released_bindings = {
                        **getattr(self, "_host_port_bindings", {}),
                        **self._container_host_bindings(created),
                    }
                    await asyncio.to_thread(created.remove, force=True)
                    await self._wait_for_host_ports_available(released_bindings)
                except NotFound:
                    pass
                except Exception as cleanup_error:
                    logger.warning(
                        "Late-created container cleanup was incomplete: %s",
                        cleanup_error,
                    )
                finally:
                    self._container = None
                    self._host_port_bindings = {}
            raise
        except Exception as exc:
            if isinstance(exc, APIError) and "port is already allocated" in str(exc).lower():
                raise RuntimeError(
                    "A required Hercules host port is already allocated. Free TCP "
                    f"{self.msf_rpc_port}, the configured browser stream port, "
                    "or one of the "
                    f"configured listener ports {self._listener_ports}, then retry."
                ) from exc
            raise

        self._start_orphan_guardian()
        logger.info(
            "Container '%s' started (id=%s).",
            self._container_name,
            self._container.short_id,
        )

        self._generation += 1
        await asyncio.to_thread(
            self._workspace.mark_active,
            self._session_id,
            self._generation,
        )
        self._bootstrapped = True
        self._ready = False
        self._ready_task = asyncio.create_task(self._mark_ready())
        self._notify_generation_changed()

    async def _mark_ready(self) -> None:
        await self._wait_for_ready()
        self._ready = True

    async def ensure_ready(self) -> None:
        """Wait until the container entrypoint has finished runtime setup."""
        await self._wait_for_startup()
        await self._ensure_container_running()
        if getattr(self, "_ready", True):
            return
        task = getattr(self, "_ready_task", None)
        if task is None:
            await self._mark_ready()
            return
        await task

    async def stop_container(self) -> None:
        """Stop and remove the container. Workspace files on host are preserved."""
        if self._container is None:
            self._host_port_bindings = {}
            workspace = getattr(self, "_workspace", None)
            if workspace is not None:
                try:
                    await asyncio.to_thread(
                        workspace.mark_inactive,
                        self._session_id,
                        self._generation,
                    )
                except ValueError:
                    pass
            await self._settle_orphan_guardian()
            return

        task = getattr(self, "_ready_task", None)
        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        stop_error: Exception | None = None
        if not self._config.preserve_container:
            try:
                logger.info("Force-removing container '%s'...", self._container_name)
                released_bindings = {
                    **getattr(self, "_host_port_bindings", {}),
                    **self._container_host_bindings(self._container),
                }
                await asyncio.to_thread(self._container.remove, force=True)
                await self._wait_for_host_ports_available(released_bindings)
            except NotFound:
                pass
            except Exception as exc:
                logger.warning("Error removing container: %s", exc)
                stop_error = exc
        else:
            try:
                logger.info("Stopping container '%s'...", self._container_name)
                await asyncio.to_thread(self._container.stop, timeout=15)
            except Exception as exc:
                logger.warning("Error stopping container: %s", exc)
                stop_error = exc
            logger.info("Container '%s' preserved for debugging.", self._container_name)

        if stop_error is not None:
            raise RuntimeError(
                f"Could not stop Hercules container '{self._container_name}': {stop_error}"
            ) from stop_error

        self._container = None
        self._bootstrapped = False
        self._ready = False
        self._ready_task = None
        self._host_port_bindings = {}
        await self._settle_orphan_guardian()
        workspace = getattr(self, "_workspace", None)
        if workspace is not None:
            try:
                await asyncio.to_thread(
                    workspace.mark_inactive,
                    self._session_id,
                    self._generation,
                )
            except ValueError:
                pass

    async def operator_stop(self) -> None:
        """Terminal operator-requested stop serialized against every recovery path."""
        async with self._get_recovery_lock():
            self._operator_stopped = True
            self._shutting_down = True
            try:
                await self.cancel_startup()
                await self.stop_container()
            finally:
                # The durable operator flag continues to suppress recovery. The
                # transient flag is reserved for an in-progress teardown.
                self._shutting_down = False

    async def restart_container(self, rotate_workspace: bool = True) -> str:
        """
        Recreate the container.

        rotate_workspace=True (default): mint a NEW session ID and a fresh empty
        workspace, then start clean. Used by ``new_session`` /
        ``system_start_new_session`` when the agent deliberately wants a clean
        slate.

        rotate_workspace=False: PRESERVE the current session ID, container name,
        and host workspace dir, recreating the container with the SAME
        /opt/workspace mount. Used by recovery so a container crash is
        transparent and previously written files / job logs survive.

        Ensures the workspace subfolder exists BEFORE tearing down the old
        container, so a failure in start_container() never leaves the manager
        pointing at an ID that corresponds to nothing.

        Returns the (possibly unchanged) session_id.
        """
        old_session_id = self._session_id
        old_name = self._container_name
        if rotate_workspace:
            new_session_id = await asyncio.to_thread(
                self._workspace.allocate_session,
                generation=self._generation,
            )
            new_name = f"hercules-{new_session_id}"
        else:
            new_session_id = old_session_id
            new_name = old_name

        await self.stop_container()
        self._session_id = new_session_id
        self._container_name = new_name
        try:
            await self.start_container()
            await self.ensure_ready()
        except Exception as start_error:
            if rotate_workspace:
                try:
                    await self.stop_container()
                except Exception as cleanup_error:
                    logger.warning(
                        "Failed to stop incomplete new-session container: %s",
                        cleanup_error,
                    )
                self._session_id = old_session_id
                self._container_name = old_name
                try:
                    await self.start_container()
                    await self.ensure_ready()
                except Exception as rollback_error:
                    raise RuntimeError(
                        "New session startup failed and the previous session could "
                        f"not be restored: startup={start_error}; rollback={rollback_error}"
                    ) from start_error
                self._cleanup_empty_workspaces()
                raise RuntimeError(
                    "New session startup failed; the previous session was restored: "
                    f"{start_error}"
                ) from start_error
            raise
        return self._session_id

    async def new_session(self) -> str:
        """
        Deliberately rotate to a fresh, empty session (clean slate).

        Holds the recovery lock so a concurrent watchdog/tool recovery cannot
        race the rotation. This is the public entry point for
        system_start_new_session.
        """
        async with self._get_recovery_lock():
            previously_stopped = bool(getattr(self, "_operator_stopped", False))
            self._operator_stopped = False
            self._shutting_down = False
            try:
                self.clear_startup_state()
                return await self.restart_container(rotate_workspace=True)
            except Exception:
                self._operator_stopped = previously_stopped
                raise

    async def reattach_container(self) -> str:
        """
        Revive the CURRENT session without losing its workspace.

        Strategy (most-preserving first):
          1. If the same-named container still exists, adopt it (running /
             paused → unpause) or ``docker start`` it (exited/created). This
             preserves /opt/workspace AND any in-container writes outside the
             mount.
          2. Otherwise recreate a container with the SAME name and SAME
             workspace mount via restart_container(rotate_workspace=False).
             This preserves /opt/workspace through the host bind mount.

        The caller MUST hold the recovery lock. Returns the recovery mode
        string ("restart" or "recreate"); session_id is unchanged.
        """
        # Cancel any stale readiness task tied to the dead container.
        task = getattr(self, "_ready_task", None)
        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._ready_task = None
        self._ready = False

        existing = None
        try:
            existing = await asyncio.to_thread(
                self._client.containers.get, self._container_name
            )
        except NotFound:
            existing = None
        except Exception as exc:
            logger.warning(
                "reattach: lookup of container %s failed: %s",
                self._container_name, exc,
            )
            existing = None

        mode = ""
        if existing is not None:
            try:
                await asyncio.to_thread(existing.reload)
                labels = (
                    getattr(existing, "attrs", {})
                    .get("Config", {})
                    .get("Labels", {})
                    or {}
                )
                if (
                    labels.get("hercules.managed") != "true"
                    or labels.get("hercules.project_root_hash")
                    != self._project_root_hash
                    or labels.get("hercules.session_id") != self._session_id
                    or (
                        getattr(self, "_instance_id", "")
                        and labels.get("hercules.instance_id") != self._instance_id
                    )
                ):
                    raise RuntimeError(
                        f"Container '{self._container_name}' is not owned by this "
                        "Hercules checkout/session."
                    )
                state = (
                    getattr(existing, "attrs", {}).get("State", {}).get("Status")
                    or getattr(existing, "status", "")
                )
                if state == "paused":
                    await asyncio.to_thread(existing.unpause)
                elif state != "running":
                    # exited / created → start the SAME container (preserves FS).
                    await asyncio.to_thread(existing.start)
                # A running legacy/current container can be adopted directly.
                self._container = existing
                self._generation = getattr(self, "_generation", 0) + 1
                self._notify_generation_changed()
                mode = "restart"
            except RuntimeError:
                raise
            except Exception as exc:
                logger.warning(
                    "reattach: could not revive existing container %s (%s); recreating.",
                    self._container_name, exc,
                )
                existing = None

        if mode != "restart":
            # Remove any stale same-named container to avoid a 409 name clash.
            try:
                stale = await asyncio.to_thread(
                    self._client.containers.get, self._container_name
                )
                await asyncio.to_thread(stale.reload)
                labels = (
                    getattr(stale, "attrs", {})
                    .get("Config", {})
                    .get("Labels", {})
                    or {}
                )
                if (
                    labels.get("hercules.managed") != "true"
                    or labels.get("hercules.project_root_hash")
                    != self._project_root_hash
                    or labels.get("hercules.session_id") != self._session_id
                    or (
                        getattr(self, "_instance_id", "")
                        and labels.get("hercules.instance_id") != self._instance_id
                    )
                ):
                    raise RuntimeError(
                        f"Refusing to remove unowned container '{self._container_name}'."
                    )
                released_bindings = self._container_host_bindings(stale)
                await asyncio.to_thread(stale.remove, force=True)
                await self._wait_for_host_ports_available(released_bindings)
            except NotFound:
                pass
            except RuntimeError:
                raise
            except Exception as exc:
                logger.warning("reattach: failed to remove stale container: %s", exc)
            await self.restart_container(rotate_workspace=False)
            mode = "recreate"
        else:
            # docker-start path: start_container was not called, so spawn the
            # readiness poller ourselves.
            self._bootstrapped = True
            self._ready = False
            self._ready_task = asyncio.create_task(self._mark_ready())

        await asyncio.to_thread(
            self._workspace.mark_active,
            self._session_id,
            self._generation,
        )

        logger.info(
            "reattach: session %s recovered via %s.", self._session_id, mode
        )
        return mode

    async def _cleanup_orphaned_containers(self) -> None:
        """Remove only containers that are safe for this checkout to own."""
        try:
            containers = await asyncio.to_thread(
                self._client.containers.list,
                all=True,
                filters={"name": "hercules-"},
            )
        except Exception as exc:
            logger.warning("Failed to list Hercules containers for cleanup: %s", exc)
            return

        for container in containers:
            name = getattr(container, "name", "")
            if name == self._container_name or not name.startswith("hercules-"):
                continue

            try:
                await asyncio.to_thread(container.reload)
            except NotFound:
                continue
            except Exception as exc:
                logger.warning("Failed to inspect container %s: %s", name, exc)
                continue

            labels = (
                getattr(container, "attrs", {})
                .get("Config", {})
                .get("Labels", {})
                or {}
            )
            state = (
                getattr(container, "attrs", {})
                .get("State", {})
                .get("Status")
                or getattr(container, "status", "")
            )
            is_running = state == "running"
            managed = labels.get("hercules.managed") == "true"

            if not managed:
                logger.warning(
                    "Ignoring unowned container with Hercules-like name: %s", name
                )
                continue

            if labels.get("hercules.project_root_hash") != self._project_root_hash:
                continue

            workspace_hash = labels.get("hercules.workspace_root_hash", "")
            if (
                workspace_hash
                and workspace_hash != getattr(self, "_workspace_root_hash", "")
            ):
                # Acceptance and isolated operator instances may intentionally
                # use the same source checkout with a different workspace.
                continue

            instance_id = labels.get("hercules.instance_id", "")
            other_instance = bool(
                getattr(self, "_instance_id", "")
                and instance_id
                and instance_id != self._instance_id
            )
            owner_pid = labels.get("hercules.owner_pid")
            owner_live = _owner_process_is_live(labels)
            if other_instance and owner_live:
                logger.warning(
                    "Preserving container from live Hercules instance %s: %s",
                    instance_id or "legacy",
                    name,
                )
                continue

            if (
                not workspace_hash
                and instance_id != getattr(self, "_instance_id", "")
                and owner_live
            ):
                # A legacy container has no workspace identity. A live PID may
                # belong to a deliberately isolated instance or may have been
                # reused, so fail closed instead of deleting it.
                logger.warning(
                    "Preserving legacy Hercules container with a live owner: %s",
                    name,
                )
                continue
            if is_running and owner_live and not other_instance:
                raise RuntimeError(
                    f"Another live Hercules container for this checkout is already running: "
                    f"{name} (owner PID {owner_pid}). Close that MCP session first."
                )

            logger.info("Cleaning up orphaned Hercules container: %s", name)
            released_bindings = self._container_host_bindings(container)
            await asyncio.to_thread(container.remove, force=True)
            await self._wait_for_host_ports_available(released_bindings)
            self._record_reclaimed_container(name)

    def _cleanup_empty_workspaces(self) -> None:
        """Remove only empty, inactive workspaces with valid ownership manifests."""
        try:
            removed = self._workspace.cleanup_empty_owned(
                active_session=self._session_id
            )
        except OSError as exc:
            logger.warning("Failed to inspect empty workspace sessions: %s", exc)
            return
        for session_id in removed:
            logger.info("Cleaned up empty owned session workspace: %s", session_id)

    def list_sessions(self) -> list[dict]:
        """List all session workspace folders on disk with metadata."""
        return self._workspace.list_sessions(
            active_session=self._session_id,
            active_running=self._container is not None,
        )

    async def _ensure_container_running(
        self,
        *,
        wait_for_startup: bool = True,
    ) -> None:
        """Refresh Docker state and fail if the active container is stale."""
        if wait_for_startup:
            await self._wait_for_startup()
        if getattr(self, "_operator_stopped", False):
            raise RuntimeError(
                "The Hercules container was explicitly stopped. "
                "Call system_start_new_session to start a fresh environment."
            )
        if self._container is None:
            raise ContainerUnavailable("Container is not running.")
        try:
            reload_fn = getattr(self._container, "reload", None)
            if callable(reload_fn):
                await asyncio.to_thread(reload_fn)
        except NotFound as exc:
            raise ContainerUnavailable("Docker container no longer exists.") from exc

        state = (
            getattr(self._container, "attrs", {})
            .get("State", {})
            .get("Status")
            or getattr(self._container, "status", "")
        )
        if state and state != "running":
            raise ContainerUnavailable(f"Docker container is {state}, not running.")

    async def _recover_container(self, reason: str) -> dict:
        """
        Recover the active session after Docker reports it stale, PRESERVING the
        workspace so the agent's files / job logs survive.

        Serialized by the recovery lock so concurrent in-flight tool calls
        cannot each spawn a duplicate container (thundering herd). After
        acquiring the lock we re-check health: if another waiter already
        recovered, this call no-ops.
        """
        lock = self._get_recovery_lock()
        async with lock:
            if getattr(self, "_operator_stopped", False) or getattr(
                self, "_shutting_down", False
            ):
                raise RuntimeError(
                    "Container recovery is disabled during an operator stop or shutdown."
                )
            old_session = self._session_id

            # Double-check: someone may have already recovered while we waited.
            try:
                await self._ensure_container_running()
                return {
                    "container_recovered": True,
                    "old_session_id": old_session,
                    "session_id": self._session_id,
                    "recovery_reason": reason,
                    "recovery_mode": "noop-already-recovered",
                    "workspace_preserved": True,
                }
            except Exception:
                if getattr(self, "_operator_stopped", False) or getattr(
                    self, "_shutting_down", False
                ):
                    raise RuntimeError(
                        "Container recovery is disabled during an operator stop or shutdown."
                    )
                # Still broken: this waiter now owns recovery.

            logger.warning(
                "Recovering Hercules container for session %s after Docker error: %s",
                old_session,
                reason,
            )
            mode = await self.reattach_container()
            return {
                "container_recovered": True,
                "old_session_id": old_session,
                "session_id": self._session_id,
                "recovery_reason": reason,
                "recovery_mode": mode,
                "workspace_preserved": True,
                "note": "background jobs were interrupted; re-launch if needed (their prior logs are preserved).",
            }

    async def health_ok(self) -> bool:
        """
        Cheap liveness check used by the proactive watchdog: the active
        container exists and is running. Does NOT spawn a process in the
        container (just a Docker state reload).

        Returns True (healthy / not-our-concern) during deliberate teardown or
        before the container is bootstrapped, so the watchdog never resurrects a
        container we are intentionally killing or one that is still starting.
        """
        if getattr(self, "_shutting_down", False):
            return True
        if getattr(self, "_operator_stopped", False):
            return True
        if not getattr(self, "_bootstrapped", False):
            return True
        try:
            await self._ensure_container_running()
            return True
        except Exception:
            return False

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
        compact_output: bool = True,
        preserve_raw: bool = False,
        require_ready: bool = True,
        sensitive_values: tuple[str, ...] | list[str] = (),
    ) -> ExecResult:
        """
        Execute a command inside the running Kali container.

        Uses Docker's low-level exec API so the exec ID, separate streams, and
        in-container PID remain available. On timeout Hercules terminates the
        process group, confirms Docker no longer reports it running, and keeps
        partial output.

        When clean_output=True:
          1. Terminal control sequences are stripped.
          2. Known tool banners are removed (if tool_name is provided).
          3. Tool-specific compacting runs only for registered high-noise tools
             unless compact_output=False.
          4. stdout and stderr are truncated independently with head+tail.
          5. Raw output is saved when filtering or truncation changes the payload.
        """
        recovery_meta: dict = {}
        try:
            await self._ensure_container_running(wait_for_startup=require_ready)
            if require_ready:
                await self.ensure_ready()
        except Exception as exc:
            if require_ready and _recoverable_docker_error(exc):
                recovery_meta = await self._recover_container(str(exc))
                await self._ensure_container_running()
                await self.ensure_ready()
            else:
                raise

        requested_timeout = timeout or self._config.default_timeout
        # Hard ceiling: no single exec can exceed max_exec_timeout, so a wedged
        # container can never pin a tool (or the bg-job plumbing) indefinitely.
        ceiling = getattr(self._config, "max_exec_timeout", 0) or requested_timeout
        effective_timeout = min(requested_timeout, ceiling)
        start = time.monotonic()

        secret_values = list(sensitive_values)
        secret_values.append(getattr(self._config, "msf_password", ""))
        for key, value in (env or {}).items():
            if any(marker in key.lower() for marker in ("password", "token", "secret", "proxy", "cookie", "auth")):
                secret_values.append(str(value))
        safe_cmd = escape_display_controls(redact_secrets(cmd, secret_values))

        async def _run_once():
            api = getattr(getattr(self, "_client", None), "api", None)
            container_id = getattr(self._container, "id", None)
            if api is None or not container_id:
                # Compatibility path for simple fake containers in local tests.
                def _legacy_run():
                    return self._container.exec_run(
                        cmd=["bash", "-c", cmd],
                        stdout=True,
                        stderr=True,
                        demux=True,
                        workdir=workdir,
                        environment=env,
                    )

                legacy = await asyncio.wait_for(
                    asyncio.to_thread(_legacy_run), timeout=effective_timeout
                )
                legacy_stdout, legacy_stderr = legacy.output
                return (
                    legacy.exit_code,
                    legacy_stdout or b"",
                    legacy_stderr or b"",
                    False,
                    False,
                    {
                        "stdout_total_bytes": len(legacy_stdout or b""),
                        "stderr_total_bytes": len(legacy_stderr or b""),
                        "stdout_stream_truncated": False,
                        "stderr_stream_truncated": False,
                        "stdout_stream_artifact": "",
                        "stderr_stream_artifact": "",
                    },
                )

            exec_token = uuid.uuid4().hex
            control_dir = "/run/hercules/exec"
            pid_path = f"{control_dir}/{exec_token}.pgid"
            marker = f"hercules-exec-{exec_token}"
            managed_command = (
                f"umask 077; mkdir -p {shlex.quote(control_dir)}; "
                f"setsid bash -c {shlex.quote(cmd)} {shlex.quote(marker)} & "
                f"child=$!; printf '%s\\n' \"$child\" > {shlex.quote(pid_path)}; "
                'wait "$child"'
            )
            exec_data = await asyncio.to_thread(
                api.exec_create,
                container_id,
                ["bash", "-c", managed_command],
                stdout=True,
                stderr=True,
                environment=env,
                workdir=workdir,
            )
            exec_id = exec_data["Id"]
            await asyncio.to_thread(
                self._workspace.ensure_directory,
                self._session_id,
                "/opt/workspace/logs",
            )
            capture_limit = self._config.max_captured_output_bytes
            stdout_artifact = (
                f"/opt/workspace/logs/exec_{exec_token}_stdout.bin"
            )
            stderr_artifact = (
                f"/opt/workspace/logs/exec_{exec_token}_stderr.bin"
            )
            capture_session_id = self._session_id
            stdout_capture = _StreamCapture(
                capture_limit,
                artifact_opener=lambda session_id=capture_session_id: (
                    self._workspace.open_exclusive_writer(
                        session_id,
                        stdout_artifact,
                    )
                ),
                artifact_container=stdout_artifact,
            )
            stderr_capture = _StreamCapture(
                capture_limit,
                artifact_opener=lambda session_id=capture_session_id: (
                    self._workspace.open_exclusive_writer(
                        session_id,
                        stderr_artifact,
                    )
                ),
                artifact_container=stderr_artifact,
            )
            stream_holder: dict[str, object] = {}

            def _consume_stream() -> None:
                stream = api.exec_start(exec_id, stream=True, demux=True)
                stream_holder["stream"] = stream
                try:
                    for chunk in stream:
                        if isinstance(chunk, tuple):
                            stdout_chunk, stderr_chunk = chunk
                        else:
                            stdout_chunk, stderr_chunk = chunk, None
                        if stdout_chunk:
                            stdout_capture.append(stdout_chunk)
                        if stderr_chunk:
                            stderr_capture.append(stderr_chunk)
                finally:
                    stdout_capture.finish()
                    stderr_capture.finish()

            stream_task = asyncio.create_task(asyncio.to_thread(_consume_stream))
            done, _ = await asyncio.wait({stream_task}, timeout=effective_timeout)
            timed_out = not done
            terminated = False
            if timed_out:
                pid = 0
                try:
                    pid_result = await asyncio.to_thread(
                        self._container.exec_run,
                        ["cat", pid_path],
                        stdout=True,
                        stderr=False,
                    )
                    pid_output = pid_result.output
                    if isinstance(pid_output, tuple):
                        pid_output = pid_output[0]
                    pid = int((pid_output or b"").decode("ascii", errors="ignore").strip())
                except (AttributeError, TypeError, ValueError):
                    logger.error(
                        "Timed-out Docker exec %s did not publish its in-container process group.",
                        exec_id,
                    )
                if pid > 0:
                    # Freeze the group before killing it. A bash that is waiting
                    # on a child may otherwise handle TERM, resume, and execute
                    # the next command during a grace-period sleep.
                    kill_cmd = (
                        f"kill -STOP -- -{pid} 2>/dev/null || kill -STOP {pid} 2>/dev/null || true; "
                        f"kill -KILL -- -{pid} 2>/dev/null || kill -KILL {pid} 2>/dev/null || true"
                    )
                    await asyncio.to_thread(
                        self._container.exec_run,
                        ["bash", "-c", kill_cmd],
                        stdout=False,
                        stderr=False,
                    )
                    await asyncio.wait({stream_task}, timeout=5)
                    final_info = await asyncio.to_thread(api.exec_inspect, exec_id)
                    terminated = not bool(final_info.get("Running", False))
                else:
                    await asyncio.to_thread(
                        self._container.exec_run,
                        [
                            "bash",
                            "-c",
                            (
                                f"pkill -KILL -f "
                                f"{shlex.quote('[h]' + marker[1:])} "
                                "2>/dev/null || true"
                            ),
                        ],
                        stdout=False,
                        stderr=False,
                    )
                    await asyncio.wait({stream_task}, timeout=5)
                    final_info = await asyncio.to_thread(api.exec_inspect, exec_id)
                    terminated = not bool(final_info.get("Running", False))
                if not stream_task.done():
                    stream = stream_holder.get("stream")
                    close = getattr(stream, "close", None)
                    if callable(close):
                        try:
                            close()
                        except Exception:
                            pass
                    logger.error("Timed-out Docker exec %s did not close after termination.", exec_id)
            if stream_task.done():
                stream_task.result()
            info = await asyncio.to_thread(api.exec_inspect, exec_id)
            await asyncio.to_thread(
                self._container.exec_run,
                ["rm", "-f", pid_path],
                stdout=False,
                stderr=False,
            )
            exit_code = -1 if timed_out else int(info.get("ExitCode") or 0)
            return (
                exit_code,
                stdout_capture.value(),
                stderr_capture.value(),
                timed_out,
                terminated,
                {
                    "stdout_total_bytes": stdout_capture.total_bytes,
                    "stderr_total_bytes": stderr_capture.total_bytes,
                    "stdout_stream_truncated": stdout_capture.overflowed,
                    "stderr_stream_truncated": stderr_capture.overflowed,
                    "stdout_stream_artifact": stdout_capture.artifact_path,
                    "stderr_stream_artifact": stderr_capture.artifact_path,
                    "stdout_artifact_error": stdout_capture.artifact_error,
                    "stderr_artifact_error": stderr_capture.artifact_error,
                },
            )

        logger.debug("exec_command: %s (timeout=%ds)", safe_cmd[:120], effective_timeout)

        try:
            (
                exit_code,
                stdout_raw,
                stderr_raw,
                timed_out,
                terminated,
                stream_meta,
            ) = await _run_once()
        except TimeoutError:
            # Only the fake-container compatibility path reaches this branch.
            exit_code, stdout_raw, stderr_raw = -1, b"", b""
            timed_out, terminated = True, False
            stream_meta = {
                "stdout_total_bytes": 0,
                "stderr_total_bytes": 0,
                "stdout_stream_truncated": False,
                "stderr_stream_truncated": False,
                "stdout_stream_artifact": "",
                "stderr_stream_artifact": "",
            }
        except Exception as exc:
            if require_ready and _recoverable_docker_error(exc):
                recovery_meta = await self._recover_container(str(exc))
                await self._ensure_container_running()
                await self.ensure_ready()
                start = time.monotonic()
                (
                    exit_code,
                    stdout_raw,
                    stderr_raw,
                    timed_out,
                    terminated,
                    stream_meta,
                ) = await _run_once()
            else:
                raise

        stdout_bytes = int(stream_meta.get("stdout_total_bytes", len(stdout_raw or b"")))
        stderr_bytes = int(stream_meta.get("stderr_total_bytes", len(stderr_raw or b"")))
        duration = round(time.monotonic() - start, 2)
        if exit_code != 0:
            logger.debug("Command exited %d: %s", exit_code, safe_cmd[:120])

        stdout_stream_truncated = bool(stream_meta["stdout_stream_truncated"])
        stderr_stream_truncated = bool(stream_meta["stderr_stream_truncated"])
        stdout_artifact = str(stream_meta["stdout_stream_artifact"])
        stderr_artifact = str(stream_meta["stderr_stream_artifact"])
        raw_artifacts: dict[str, str] = {}
        filter_notes: list[str] = []
        transforms: list[dict] = []
        capture_failed = False
        if stdout_stream_truncated:
            filter_notes.append("stdout streamed to a bounded-memory artifact")
            if stdout_artifact:
                raw_artifacts["stdout"] = stdout_artifact
        if stderr_stream_truncated:
            filter_notes.append("stderr streamed to a bounded-memory artifact")
            if stderr_artifact:
                raw_artifacts["stderr"] = stderr_artifact
        for key in ("stdout_artifact_error", "stderr_artifact_error"):
            if stream_meta.get(key):
                capture_failed = True
                filter_notes.append(f"{key}: {stream_meta[key]}")

        async def _save_artifact(
            kind: str,
            content: str | bytes,
            *,
            binary: bool = False,
        ) -> str:
            if not content:
                return ""
            ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S_%f")
            log_name = tool_name or "exec"
            safe_name = "".join(
                c if c.isalnum() or c in "-_" else "_"
                for c in log_name
            )[:48] or "exec"
            extension = "bin" if binary else "txt"
            path = f"/opt/workspace/logs/{safe_name}_{kind}_{ts}.{extension}"
            try:
                await self._write_file_internal(path, content)
                return path
            except Exception as exc:
                logger.warning("Failed to write %s artifact log: %s", kind, exc)
                return ""

        def _decode_stream(payload: bytes) -> tuple[str, bool]:
            if not payload:
                return "", False
            try:
                decoded = payload.decode("utf-8")
            except UnicodeDecodeError:
                return "", True
            suspicious = sum(
                1
                for value in payload
                if value == 0
                or value < 0x09
                or 0x0E <= value <= 0x1A
                or 0x1C <= value < 0x20
            )
            return decoded, bool(b"\x00" in payload or suspicious > max(8, len(payload) // 20))

        raw_stdout, stdout_binary = _decode_stream(stdout_raw or b"")
        raw_stderr, stderr_binary = _decode_stream(stderr_raw or b"")
        stdout = raw_stdout
        stderr = raw_stderr

        for stream_name, payload, is_binary, existing_artifact in (
            ("stdout", stdout_raw or b"", stdout_binary, stdout_artifact),
            ("stderr", stderr_raw or b"", stderr_binary, stderr_artifact),
        ):
            if not is_binary:
                continue
            binary_artifact = existing_artifact or await _save_artifact(
                f"{stream_name}_raw",
                payload,
                binary=True,
            )
            if binary_artifact:
                raw_artifacts[stream_name] = binary_artifact
            else:
                capture_failed = True
            notice = (
                f"[{stream_name} contained binary or invalid UTF-8 data; "
                f"artifact: {binary_artifact or 'unavailable'}]"
            )
            if stream_name == "stdout":
                stdout = notice
            else:
                stderr = notice
            transforms.append(
                {
                    "stream": stream_name,
                    "type": "binary_artifact",
                    "semantic": False,
                    "removed_lines": 0,
                    "removed_chars": 0,
                    "filter_version": 1,
                }
            )
            filter_notes.append(f"{stream_name} returned as a binary artifact notice")

        if timed_out:
            timeout_message = f"Command timed out after {effective_timeout}s"
            stderr = f"{stderr.rstrip()}\n{timeout_message}".lstrip()
            logger.warning("%s: %s", timeout_message, safe_cmd[:120])

        def _record_transform(
            stream_name: str,
            transform_type: str,
            before: str,
            after: str,
            *,
            semantic: bool,
            removed_lines: int | None = None,
            removed_chars: int | None = None,
            version: int = 1,
        ) -> None:
            if before == after:
                return
            transforms.append(
                {
                    "stream": stream_name,
                    "type": transform_type,
                    "semantic": semantic,
                    "removed_lines": (
                        max(0, len(before.splitlines()) - len(after.splitlines()))
                        if removed_lines is None
                        else removed_lines
                    ),
                    "removed_chars": (
                        max(0, len(before) - len(after))
                        if removed_chars is None
                        else removed_chars
                    ),
                    "filter_version": version,
                }
            )

        if clean_output:
            # Terminal rendering is safety sanitation, not semantic deletion.
            before_stdout, before_stderr = stdout, stderr
            if not stdout_binary:
                stdout = sanitize(stdout)
            if not stderr_binary:
                stderr = sanitize(stderr)
            _record_transform(
                "stdout", "terminal_render", before_stdout, stdout, semantic=False
            )
            _record_transform(
                "stderr", "terminal_render", before_stderr, stderr, semantic=False
            )

            if tool_name:
                before_stdout = stdout
                stdout = strip_known_banners(stdout, tool_name)
                _record_transform(
                    "stdout", "exact_banner", before_stdout, stdout, semantic=False
                )

                before_stderr = stderr
                stderr = strip_known_banners(stderr, tool_name)
                _record_transform(
                    "stderr", "exact_banner", before_stderr, stderr, semantic=False
                )

                # Semantic scanner compaction is stdout-only. Warnings,
                # tracebacks, and capability/completeness diagnostics on stderr
                # are always retained after terminal safety cleanup.
                if compact_output and not stdout_binary:
                    stdout_filter = apply_tool_filter(stdout, tool_name)
                    stdout = stdout_filter.text
                    if stdout_filter.changed:
                        transforms.append(
                            {
                                "stream": "stdout",
                                "type": f"{tool_name}_semantic_compaction",
                                "semantic": True,
                                "removed_lines": stdout_filter.removed_lines,
                                "removed_chars": stdout_filter.removed_chars,
                                "filter_version": stdout_filter.version,
                            }
                        )
                        filter_notes.append(f"{stdout_filter.note} on stdout")

        semantic_filtered = any(item["semantic"] for item in transforms)
        output_filtered = any(
            item["type"] != "terminal_render" for item in transforms
        )
        if transforms and not filter_notes:
            filter_notes.append("output transformed; see output_transform statistics")

        stdout_chars_exact = not stdout_stream_truncated and not stdout_binary
        stderr_chars_exact = not stderr_stream_truncated and not stderr_binary
        stdout_chars = len(raw_stdout) if stdout_chars_exact else stdout_bytes
        stderr_chars = len(raw_stderr) if stderr_chars_exact else stderr_bytes

        response_budget = max(
            0,
            int(getattr(self._config, "max_inline_response_chars", 12_000)),
        )
        per_stream_limit = max(0, int(max_output_chars))
        total_budget = min(response_budget, per_stream_limit * 2)
        if len(stdout) + len(stderr) <= total_budget:
            stdout_limit = min(per_stream_limit, max(len(stdout), 0))
            stderr_limit = min(per_stream_limit, max(len(stderr), 0))
        else:
            # Reserve at least one third for diagnostics, then give unused
            # capacity back to the other stream.
            stderr_reserve = min(
                per_stream_limit,
                len(stderr),
                max(0, total_budget // 3),
            )
            stdout_limit = min(per_stream_limit, len(stdout), total_budget - stderr_reserve)
            stderr_limit = min(per_stream_limit, len(stderr), total_budget - stdout_limit)
            unused = total_budget - stdout_limit - stderr_limit
            if unused > 0:
                stderr_extra = min(unused, per_stream_limit - stderr_limit, len(stderr) - stderr_limit)
                stderr_limit += stderr_extra
                unused -= stderr_extra
                stdout_limit += min(unused, per_stream_limit - stdout_limit, len(stdout) - stdout_limit)

        stdout_will_truncate = stdout_stream_truncated or len(stdout) > stdout_limit
        stderr_will_truncate = stderr_stream_truncated or len(stderr) > stderr_limit
        changed_from_raw = bool(transforms) or timed_out

        raw_artifact = ""
        if (
            preserve_raw
            or timed_out
            or changed_from_raw
            or stdout_will_truncate
            or stderr_will_truncate
        ):
            if not stdout_stream_truncated and not stderr_stream_truncated and not stdout_binary and not stderr_binary:
                raw_payload = (
                    f"$ {safe_cmd}\n\n"
                    f"[stdout]\n{raw_stdout}\n\n"
                    f"[stderr]\n{raw_stderr}"
                )
                raw_artifact = await _save_artifact("raw", raw_payload)
                if raw_artifact:
                    raw_artifacts["combined"] = raw_artifact
            else:
                for stream_name, content, stream_truncated, is_binary in (
                    ("stdout", raw_stdout, stdout_stream_truncated, stdout_binary),
                    ("stderr", raw_stderr, stderr_stream_truncated, stderr_binary),
                ):
                    if stream_truncated or is_binary or not content:
                        continue
                    saved = await _save_artifact(f"{stream_name}_raw", content)
                    if saved:
                        raw_artifacts[stream_name] = saved
                raw_artifact = (
                    raw_artifacts.get("combined")
                    or raw_artifacts.get("stdout")
                    or raw_artifacts.get("stderr")
                    or ""
                )
            if raw_artifact:
                filter_notes.append("raw output preserved in artifact")
            elif changed_from_raw or stdout_will_truncate or stderr_will_truncate:
                capture_failed = True

        # Save complete processed streams before applying inline bounds. A raw
        # stream artifact can serve both roles when no transform changed it.
        if stdout_will_truncate and not stdout_artifact:
            stdout_artifact = await _save_artifact("stdout", stdout)
        if stderr_will_truncate and not stderr_artifact:
            stderr_artifact = await _save_artifact("stderr", stderr)
        if stdout_will_truncate and not stdout_artifact:
            capture_failed = True
        if stderr_will_truncate and not stderr_artifact:
            capture_failed = True

        stdout, stdout_truncated = truncate_output(
            stdout, max_chars=stdout_limit, artifact_path=stdout_artifact
        )
        stderr, stderr_truncated = truncate_output(
            stderr, max_chars=stderr_limit, artifact_path=stderr_artifact
        )
        stdout_truncated = stdout_truncated or stdout_stream_truncated
        stderr_truncated = stderr_truncated or stderr_stream_truncated
        truncated = stdout_truncated or stderr_truncated
        artifact_path = stdout_artifact or stderr_artifact
        if stdout_truncated:
            filter_notes.append("stdout truncated with head/tail preservation")
        if stderr_truncated:
            filter_notes.append("stderr truncated with head/tail preservation")

        evidence_complete = not timed_out and not capture_failed
        if changed_from_raw and not raw_artifacts:
            evidence_complete = False
        if stdout_truncated and not (stdout_artifact or raw_artifacts.get("stdout") or raw_artifact):
            evidence_complete = False
        if stderr_truncated and not (stderr_artifact or raw_artifacts.get("stderr") or raw_artifact):
            evidence_complete = False

        inline_chars = len(stdout) + len(stderr)
        return ExecResult(
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            duration_seconds=duration,
            command=safe_cmd,
            truncated=truncated,
            artifact=artifact_path,
            raw_artifact=raw_artifact,
            raw_artifacts=raw_artifacts,
            stdout_artifact=stdout_artifact,
            stderr_artifact=stderr_artifact,
            filter_notes=filter_notes,
            output_transform=transforms,
            output_filtered=output_filtered,
            output_complete=not semantic_filtered and not truncated and not timed_out and not capture_failed,
            evidence_complete=evidence_complete,
            stdout_truncated=stdout_truncated,
            stderr_truncated=stderr_truncated,
            stdout_chars=stdout_chars,
            stderr_chars=stderr_chars,
            stdout_bytes=stdout_bytes,
            stderr_bytes=stderr_bytes,
            stdout_chars_exact=stdout_chars_exact,
            stderr_chars_exact=stderr_chars_exact,
            inline_stdout_chars=len(stdout),
            inline_stderr_chars=len(stderr),
            estimated_inline_tokens=(inline_chars + 3) // 4,
            status="timeout" if timed_out else "",
            timed_out=timed_out,
            timeout_seconds=effective_timeout if timed_out else None,
            terminated=terminated,
            partial_output=bool(timed_out and (stdout_raw or stderr_raw)),
            **recovery_meta,
        )

    async def exec_argv(
        self,
        argv: list[str],
        **kwargs,
    ) -> ExecResult:
        """Execute structured argv through the managed executor.

        This is the internal path for commands composed entirely from named
        parameters. Each argument is single-line validated and quoted. Public
        raw shell and documented raw-argument surfaces continue to use
        ``exec_command`` explicitly.
        """
        if not argv:
            raise ValueError("argv must contain at least one argument")
        quoted = [
            shlex.quote(
                reject_control_chars(str(argument), label=f"argv[{index}]")
            )
            for index, argument in enumerate(argv)
        ]
        return await self.exec_command(" ".join(quoted), **kwargs)

    async def _browser_relay_is_running(self, state: dict[str, object]) -> bool:
        try:
            pid = int(state["pid"])
            pgid = int(state["pgid"])
            ticks = shlex.quote(str(state["start_ticks"]))
        except (KeyError, TypeError, ValueError):
            return False
        command = (
            f"test -r /proc/{pid}/stat || exit 3; "
            f"test \"$(awk '{{print $22}}' /proc/{pid}/stat)\" = {ticks} || exit 4; "
            f"test \"$(ps -o pgid= -p {pid} 2>/dev/null | tr -d ' ')\" = {pgid} "
            "|| exit 5; "
            f"state=$(ps -o stat= -p {pid} 2>/dev/null | tr -d ' '); "
            "case \"$state\" in Z*) exit 6;; esac; "
            f"kill -0 {pid} 2>/dev/null"
        )
        result = await self.exec_command(
            command,
            timeout=10,
            clean_output=False,
            preserve_raw=True,
        )
        return result.exit_code == 0

    async def _stop_browser_stream_relay(
        self,
        state: dict[str, object],
    ) -> bool:
        """Stop only a relay whose PID, start time, and process group still match."""
        try:
            pid = int(state["pid"])
            pgid = int(state["pgid"])
            ticks = shlex.quote(str(state["start_ticks"]))
        except (KeyError, TypeError, ValueError):
            return False
        command = (
            "verify_relay() { "
            f"test -r /proc/{pid}/stat || return 3; "
            f"test \"$(awk '{{print $22}}' /proc/{pid}/stat)\" = {ticks} || return 4; "
            f"test \"$(ps -o pgid= -p {pid} 2>/dev/null | tr -d ' ')\" = {pgid} "
            "|| return 5; "
            "}; "
            "verify_relay || exit $?; "
            f"kill -TERM -- -{pgid} 2>/dev/null || exit 6; "
            "for _ in $(seq 1 20); do "
            f"kill -0 {pid} 2>/dev/null || exit 0; "
            f"state=$(ps -o stat= -p {pid} 2>/dev/null | tr -d ' '); "
            "case \"$state\" in Z*) exit 0;; esac; sleep 0.1; done; "
            "verify_relay || exit $?; "
            f"kill -KILL -- -{pgid} 2>/dev/null || exit 7; "
            "for _ in $(seq 1 20); do "
            f"kill -0 {pid} 2>/dev/null || exit 0; "
            f"state=$(ps -o stat= -p {pid} 2>/dev/null | tr -d ' '); "
            "case \"$state\" in Z*) exit 0;; esac; sleep 0.1; done; exit 8"
        )
        result = await self.exec_command(
            command,
            timeout=15,
            clean_output=False,
            preserve_raw=True,
        )
        return result.exit_code == 0

    async def ensure_browser_stream_relay(
        self,
        *,
        session: str,
        backend_port: int,
    ) -> dict[str, object]:
        """Expose one agent-browser loopback stream through a generation-bound relay."""
        host_port = self.browser_stream_port
        backend_port = int(backend_port)
        relay_port = self.browser_stream_relay_port
        if not 1 <= host_port <= 65_535 or not 1 <= relay_port <= 65_535:
            raise RuntimeError("browser streaming is not configured")
        if not 1 <= backend_port <= 65_535:
            raise ValueError("agent-browser returned an invalid stream port")

        async with self._get_browser_stream_lock():
            state = dict(getattr(self, "_browser_stream_relay_state", {}))
            expected = (
                state.get("session") == session
                and state.get("backend_port") == backend_port
                and state.get("generation") == self._generation
            )
            if expected and await self._browser_relay_is_running(state):
                return {
                    "relay_status": "already_running",
                    "stream_active": True,
                    "relay_replaced": False,
                    "relay_port": relay_port,
                    "backend_port": backend_port,
                    "generation": self._generation,
                }

            replaced = False
            if (
                state
                and state.get("generation") == self._generation
                and await self._browser_relay_is_running(state)
            ):
                if not await self._stop_browser_stream_relay(state):
                    return {
                        "relay_status": "replacement_failed",
                        "stream_active": False,
                        "relay_replaced": False,
                        "relay_port": relay_port,
                        "backend_port": backend_port,
                        "generation": self._generation,
                        "error": (
                            "The existing browser relay could not be verified "
                            "as terminated; no replacement was started."
                        ),
                    }
                replaced = True
            self._browser_stream_relay_state = {}

            bind_host = (
                "127.0.0.1"
                if platform.system() == "Linux"
                else _CONTAINER_ALL_INTERFACES
            )
            relay_target = f"ncat -4 127.0.0.1 {backend_port}"
            log_path = "/opt/workspace/logs/browser-stream-relay.log"
            command = (
                "mkdir -p /opt/workspace/logs; "
                f"nohup setsid ncat -4 -l {bind_host} {relay_port} --keep-open "
                f"--sh-exec {shlex.quote(relay_target)} "
                f">>{shlex.quote(log_path)} 2>&1 < /dev/null & "
                "pid=$!; sleep 0.25; kill -0 \"$pid\" 2>/dev/null || exit 9; "
                "ticks=$(awk '{print $22}' /proc/\"$pid\"/stat) || exit 10; "
                "pgid=$(ps -o pgid= -p \"$pid\" | tr -d ' ') || exit 11; "
                "printf '%s %s %s\\n' \"$pid\" \"$pgid\" \"$ticks\""
            )
            result = await self.exec_command(
                command,
                timeout=15,
                clean_output=False,
                preserve_raw=True,
            )
            if result.exit_code != 0:
                return {
                    "relay_status": "start_failed",
                    "stream_active": False,
                    "relay_replaced": replaced,
                    "relay_port": relay_port,
                    "backend_port": backend_port,
                    "generation": self._generation,
                    "error": result.stderr or "browser stream relay failed to start",
                }
            fields = result.stdout.strip().split()
            if len(fields) < 3 or not all(field.isdigit() for field in fields[-3:]):
                return {
                    "relay_status": "start_unconfirmed",
                    "stream_active": False,
                    "relay_replaced": replaced,
                    "relay_port": relay_port,
                    "backend_port": backend_port,
                    "generation": self._generation,
                    "error": "browser stream relay returned incomplete process metadata",
                }
            pid, pgid, start_ticks = fields[-3:]
            state = {
                "session": session,
                "backend_port": backend_port,
                "relay_port": relay_port,
                "generation": self._generation,
                "pid": int(pid),
                "pgid": int(pgid),
                "start_ticks": start_ticks,
            }
            if not await self._browser_relay_is_running(state):
                return {
                    "relay_status": "start_unconfirmed",
                    "stream_active": False,
                    "relay_replaced": replaced,
                    "relay_port": relay_port,
                    "backend_port": backend_port,
                    "generation": self._generation,
                    "error": "browser stream relay exited before verification",
                }
            self._browser_stream_relay_state = state
            return {
                "relay_status": "started",
                "stream_active": True,
                "relay_replaced": replaced,
                "relay_port": relay_port,
                "backend_port": backend_port,
                "generation": self._generation,
            }

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
        """Execute a managed background process group with durable metadata."""
        async with self._get_job_lock():
            return await self._exec_background_locked(cmd, job_id, workdir, env)

    async def _exec_background_locked(
        self,
        cmd: str,
        job_id: str,
        workdir: str | None,
        env: dict[str, str] | None,
    ) -> str:
        if self._container is None:
            raise RuntimeError("Container is not running.")
        job_id = safe_filename(job_id, label="job_id", maximum=64)
        existing = await asyncio.to_thread(self._load_job_metadata, job_id)
        if existing and existing.get("state") in {
            "starting",
            "running",
            "terminating",
        }:
            status = await self._job_process_status(existing)
            if status["running"]:
                raise RuntimeError(f"background job_id '{job_id}' is already active")

        active_jobs = 0
        active_candidates: list[tuple[str, dict]] = []
        jobs_path = self.workspace_path / "jobs"
        if jobs_path.is_dir():
            for metadata_path in jobs_path.glob("*.json"):
                candidate_id = metadata_path.stem
                try:
                    candidate_id = safe_filename(
                        candidate_id,
                        label="job_id",
                        maximum=64,
                    )
                except ValueError:
                    continue
                payload = await asyncio.to_thread(
                    self._load_job_metadata,
                    candidate_id,
                )
                if payload is None:
                    continue
                if payload.get("generation") != self._generation:
                    continue
                if payload.get("state") not in {"starting", "running", "terminating"}:
                    continue
                active_candidates.append((candidate_id, payload))

        statuses = await asyncio.gather(
            *(
                self._job_process_status(payload)
                for _, payload in active_candidates
            )
        )
        for (candidate_id, payload), status in zip(
            active_candidates,
            statuses,
            strict=True,
        ):
            if status["running"]:
                active_jobs += 1
            else:
                payload["state"] = (
                    "stale"
                    if status["stale"] or status["pid_reused"]
                    else "unknown"
                )
                candidate_id = str(payload.get("job_id", candidate_id))
                try:
                    candidate_id = safe_filename(
                        candidate_id,
                        label="job_id",
                        maximum=64,
                    )
                except ValueError:
                    continue
                await asyncio.to_thread(
                    self._save_job_metadata,
                    candidate_id,
                    payload,
                )
        if active_jobs >= self._config.max_background_jobs:
            raise RuntimeError(
                "maximum managed background jobs reached "
                f"({self._config.max_background_jobs})"
            )

        base = f"/opt/workspace/jobs/{job_id}"
        command_path = f"{base}.command.sh"
        wrapper_path = f"{base}.wrapper.sh"
        log_file = f"{base}.log"
        pid_file = f"{base}.pid"
        pgid_file = f"{base}.pgid"
        ticks_file = f"{base}.start_ticks"
        exit_file = f"{base}.exit"
        finished_file = f"{base}.finished"
        await self.write_file(command_path, cmd, mode=0o700)
        wrapper = (
            "#!/usr/bin/env bash\n"
            "set +e\n"
            "child=0\n"
            "terminate_group() {\n"
            "  trap '' TERM INT\n"
            "  if [ \"$child\" -gt 0 ] 2>/dev/null; then\n"
            "    for member in $(pgrep -g \"$$\" 2>/dev/null); do\n"
            "      [ \"$member\" = \"$$\" ] || kill -TERM \"$member\" 2>/dev/null || true\n"
            "    done\n"
            "    for _ in $(seq 1 20); do\n"
            "      kill -0 \"$child\" 2>/dev/null || break\n"
            "      sleep 0.1\n"
            "    done\n"
            "    if kill -0 \"$child\" 2>/dev/null; then\n"
            "      for member in $(pgrep -g \"$$\" 2>/dev/null); do\n"
            "        [ \"$member\" = \"$$\" ] || kill -KILL \"$member\" 2>/dev/null || true\n"
            "      done\n"
            "    fi\n"
            "    wait \"$child\" 2>/dev/null || true\n"
            "  fi\n"
            "  exit 143\n"
            "}\n"
            "trap terminate_group TERM INT\n"
            f"bash {shlex.quote(command_path)} &\n"
            "child=$!\n"
            "wait \"$child\"\n"
            "rc=$?\n"
            f"printf '%s\\n' \"$rc\" > {shlex.quote(exit_file)}.tmp\n"
            f"mv -f {shlex.quote(exit_file)}.tmp {shlex.quote(exit_file)}\n"
            f"date -u +%Y-%m-%dT%H:%M:%SZ > {shlex.quote(finished_file)}\n"
            f"rm -f -- {shlex.quote(command_path)} {shlex.quote(wrapper_path)}\n"
            'exit "$rc"\n'
        )
        await self.write_file(wrapper_path, wrapper, mode=0o700)
        metadata = {
            "schema_version": 1,
            "job_id": job_id,
            "generation": self._generation,
            "container_id": str(getattr(self._container, "id", "")),
            "state": "starting",
            "created_at": utc_now(),
            "updated_at": utc_now(),
            "command_sha256": hashlib.sha256(cmd.encode("utf-8")).hexdigest(),
            "pid": 0,
            "pgid": 0,
            "start_ticks": "",
            "exit_code": None,
            "log_path": log_file,
        }
        await asyncio.to_thread(self._save_job_metadata, job_id, metadata)

        launch = (
            f"rm -f -- {shlex.quote(exit_file)} {shlex.quote(finished_file)}; "
            f"nohup setsid bash {shlex.quote(wrapper_path)} "
            f"> {shlex.quote(log_file)} 2>&1 < /dev/null & "
            "pid=$!; "
            f"printf '%s\\n' \"$pid\" > {shlex.quote(pid_file)}; "
            f"ps -o pgid= -p \"$pid\" | tr -d ' ' > {shlex.quote(pgid_file)}; "
            f"awk '{{print $22}}' /proc/\"$pid\"/stat > {shlex.quote(ticks_file)}; "
            "printf '%s\\n' \"$pid\""
        )
        result = await self.exec_command(
            launch,
            workdir=workdir,
            env=env,
            clean_output=False,
            timeout=15,
            preserve_raw=True,
        )
        if result.exit_code != 0:
            metadata.update(
                {
                    "state": "start_failed",
                    "updated_at": utc_now(),
                    "error": result.stderr or "background launch failed",
                }
            )
            await asyncio.to_thread(self._save_job_metadata, job_id, metadata)
            raise RuntimeError(metadata["error"])
        try:
            pid = int((await self.read_file(pid_file, max_bytes=64)).strip())
            pgid = int((await self.read_file(pgid_file, max_bytes=64)).strip())
            start_ticks = (await self.read_file(ticks_file, max_bytes=128)).strip()
        except (OSError, ValueError) as exc:
            metadata.update(
                {
                    "state": "start_failed",
                    "updated_at": utc_now(),
                    "error": f"background process metadata was incomplete: {exc}",
                }
            )
            launch_pid = next(
                (
                    int(line)
                    for line in reversed(result.stdout.splitlines())
                    if line.strip().isdigit() and int(line) > 0
                ),
                0,
            )
            if launch_pid:
                await self.exec_command(
                    f"kill -TERM -- -{launch_pid} 2>/dev/null || "
                    f"kill -TERM {launch_pid} 2>/dev/null || true",
                    clean_output=False,
                    timeout=15,
                )
            await self._cleanup_job_control_files(job_id)
            await asyncio.to_thread(self._save_job_metadata, job_id, metadata)
            raise RuntimeError(metadata["error"]) from exc
        metadata.update(
            {
                "state": "running",
                "updated_at": utc_now(),
                "pid": pid,
                "pgid": pgid,
                "start_ticks": start_ticks,
            }
        )
        await asyncio.to_thread(self._save_job_metadata, job_id, metadata)
        return job_id

    def _job_metadata_path(self, job_id: str) -> str:
        return f"/opt/workspace/jobs/{job_id}.json"

    def _load_job_metadata(self, job_id: str) -> dict | None:
        try:
            result = self._workspace.read_chunk(
                self._session_id,
                self._job_metadata_path(job_id),
                max_bytes=1024 * 1024,
            )
            if result.truncated:
                return None
            payload = json.loads(result.data.decode("utf-8"))
        except (OSError, UnicodeError, ValueError, TypeError):
            return None
        return payload if isinstance(payload, dict) else None

    def _save_job_metadata(self, job_id: str, payload: dict) -> None:
        payload["updated_at"] = utc_now()
        self._workspace.atomic_write(
            self._session_id,
            self._job_metadata_path(job_id),
            (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8"),
            mode=0o600,
        )

    async def _cleanup_job_control_files(self, job_id: str) -> None:
        """Remove private launch controls while preserving logs and job evidence."""
        job_id = safe_filename(job_id, label="job_id", maximum=64)
        suffixes = (
            ".command.sh",
            ".wrapper.sh",
            ".pid",
            ".pgid",
            ".start_ticks",
        )

        def _unlink() -> None:
            for suffix in suffixes:
                try:
                    self._workspace.unlink(
                        self._session_id,
                        f"/opt/workspace/jobs/{job_id}{suffix}",
                        missing_ok=True,
                    )
                except (OSError, ValueError):
                    logger.warning(
                        "Could not clean background-job control file for %s%s.",
                        job_id,
                        suffix,
                    )

        await asyncio.to_thread(_unlink)

    async def _job_process_status(self, metadata: dict) -> dict:
        if metadata.get("generation") != self._generation:
            return {"running": False, "stale": True, "pid_reused": False}
        try:
            pid = int(metadata.get("pid", 0))
        except (TypeError, ValueError):
            return {"running": False, "stale": False, "pid_reused": False}
        expected_ticks = str(metadata.get("start_ticks", ""))
        if pid <= 0 or not expected_ticks:
            return {"running": False, "stale": False, "pid_reused": False}
        command = (
            f"test -r /proc/{pid}/stat || exit 3; "
            f"ticks=$(awk '{{print $22}}' /proc/{pid}/stat); "
            f"test \"$ticks\" = {shlex.quote(expected_ticks)} || exit 4; "
            f"kill -0 {pid} 2>/dev/null || exit 5; "
            f"state=$(ps -o stat= -p {pid} 2>/dev/null | tr -d ' '); "
            'case "$state" in *Z*) exit 6;; esac; echo running'
        )
        result = await self.exec_command(
            command,
            clean_output=False,
            timeout=15,
        )
        return {
            "running": result.exit_code == 0,
            "stale": False,
            "pid_reused": result.exit_code == 4,
        }

    async def check_job(self, job_id: str, tail_lines: int = 50) -> dict:
        """Check managed job state and return a bounded log tail."""
        job_id = safe_filename(job_id, label="job_id", maximum=64)
        tail_lines = max(1, min(int(tail_lines), 10_000))
        metadata = await asyncio.to_thread(self._load_job_metadata, job_id)
        if metadata is None:
            return {
                "job_id": job_id,
                "state": "missing",
                "is_running": False,
                "stale": False,
                "output": "",
                "log_path": f"/opt/workspace/jobs/{job_id}.log",
            }
        process = await self._job_process_status(metadata)
        is_running = process["running"]
        if process["stale"]:
            metadata["state"] = "stale"
        elif process["pid_reused"]:
            metadata["state"] = "stale_pid"
        elif is_running:
            metadata["state"] = "running"
        else:
            exit_path = f"/opt/workspace/jobs/{job_id}.exit"
            try:
                exit_code = int((await self.read_file(exit_path, max_bytes=64)).strip())
            except (OSError, ValueError):
                exit_code = None
            metadata["exit_code"] = exit_code
            metadata["state"] = (
                "completed"
                if exit_code == 0
                else "failed" if exit_code is not None else "unknown"
            )
            if not metadata.get("finished_at"):
                finished_path = f"/opt/workspace/jobs/{job_id}.finished"
                try:
                    metadata["finished_at"] = (
                        await self.read_file(finished_path, max_bytes=128)
                    ).strip()
                except OSError:
                    metadata["finished_at"] = utc_now()
        await asyncio.to_thread(self._save_job_metadata, job_id, metadata)

        log_path = str(metadata.get("log_path") or f"/opt/workspace/jobs/{job_id}.log")
        out_res = await self.exec_command(
            f"tail -n {tail_lines} -- {shlex.quote(log_path)} 2>/dev/null",
            clean_output=True,
            timeout=15,
        )
        wc_res = await self.exec_command(
            f"wc -l < {shlex.quote(log_path)} 2>/dev/null",
            clean_output=False,
            timeout=15,
        )
        return {
            "job_id": job_id,
            "pid": str(metadata.get("pid", "")),
            "pgid": str(metadata.get("pgid", "")),
            "is_running": is_running,
            "state": metadata.get("state", "unknown"),
            "generation": metadata.get("generation", 0),
            "stale": bool(process["stale"] or process["pid_reused"]),
            "created_at": metadata.get("created_at", ""),
            "updated_at": metadata.get("updated_at", ""),
            "finished_at": metadata.get("finished_at", ""),
            "exit_code": metadata.get("exit_code"),
            "total_lines": wc_res.stdout.strip(),
            "showing_last": tail_lines,
            "output": out_res.stdout,
            "log_path": log_path,
        }

    async def terminate_job(self, job_id: str) -> dict:
        """Terminate one verified current-generation process group."""
        job_id = safe_filename(job_id, label="job_id", maximum=64)
        metadata = await asyncio.to_thread(self._load_job_metadata, job_id)
        if metadata is None:
            return {
                "killed": False,
                "terminated": False,
                "confirmed": False,
                "state": "missing",
            }
        process = await self._job_process_status(metadata)
        if process["stale"] or process["pid_reused"]:
            metadata["state"] = "stale"
            await asyncio.to_thread(self._save_job_metadata, job_id, metadata)
            return {
                "killed": False,
                "terminated": False,
                "confirmed": False,
                "state": "stale",
                "stale": True,
            }
        if not process["running"]:
            status = await self.check_job(job_id, tail_lines=1)
            return {
                "killed": False,
                "terminated": True,
                "confirmed": True,
                "state": status["state"],
            }
        pid = int(metadata["pid"])
        pgid = int(metadata.get("pgid") or pid)
        expected_ticks = shlex.quote(str(metadata.get("start_ticks", "")))
        metadata["state"] = "terminating"
        await asyncio.to_thread(self._save_job_metadata, job_id, metadata)
        command = (
            "verify_job() { "
            f"test -r /proc/{pid}/stat || return 3; "
            f"ticks=$(awk '{{print $22}}' /proc/{pid}/stat) || return 3; "
            f"test \"$ticks\" = {expected_ticks} || return 4; "
            f"current_pgid=$(ps -o pgid= -p {pid} 2>/dev/null | tr -d ' ') || return 3; "
            f"test \"$current_pgid\" = {pgid} || return 5; "
            "}; "
            "verify_job || exit $?; "
            f"kill -TERM {pid} 2>/dev/null || exit 6; "
            "for _ in $(seq 1 20); do "
            f"kill -0 {pid} 2>/dev/null || exit 0; sleep 0.1; done; "
            "verify_job || exit $?; "
            f"kill -KILL -- -{pgid} 2>/dev/null || exit 7; "
            "for _ in $(seq 1 20); do "
            f"kill -0 {pid} 2>/dev/null || exit 0; sleep 0.1; done; exit 1"
        )
        termination_result = await self.exec_command(
            command,
            clean_output=False,
            timeout=15,
        )
        final = await self._job_process_status(metadata)
        confirmed = termination_result.exit_code == 0 and not final["running"]
        metadata.update(
            {
                "state": "terminated" if confirmed else "termination_failed",
                "finished_at": utc_now() if confirmed else "",
            }
        )
        if confirmed:
            await self._cleanup_job_control_files(job_id)
        await asyncio.to_thread(self._save_job_metadata, job_id, metadata)
        return {
            # The shell poll can observe a short-lived zombie and exit nonzero;
            # the verified PID/start-tick status below is authoritative.
            "killed": confirmed,
            "terminated": confirmed,
            "confirmed": confirmed,
            "state": metadata["state"],
        }

    async def kill_job(self, job_id: str) -> bool:
        """Compatibility wrapper returning the historical boolean."""
        result = await self.terminate_job(job_id)
        return bool(result["killed"])


    # ------------------------------------------------------------------
    # File I/O through the owned host bind mount
    # ------------------------------------------------------------------

    async def write_file(
        self,
        container_path: str,
        content: str | bytes,
        mode: int = 0o755,
        require_ready: bool = True,
    ) -> None:
        """Atomically write a file under the active owned workspace."""
        try:
            await self._ensure_container_running()
            if require_ready:
                await self.ensure_ready()
        except Exception as exc:
            if require_ready and _recoverable_docker_error(exc):
                await self._recover_container(str(exc))
                await self._ensure_container_running()
                await self.ensure_ready()
            else:
                raise

        data = content.encode("utf-8") if isinstance(content, str) else content
        try:
            await asyncio.to_thread(
                self._workspace.atomic_write,
                self._session_id,
                container_path,
                data,
                mode=mode,
            )
        except Exception as exc:
            if require_ready and _recoverable_docker_error(exc):
                await self._recover_container(str(exc))
                await self._ensure_container_running()
                await self.ensure_ready()
                await asyncio.to_thread(
                    self._workspace.atomic_write,
                    self._session_id,
                    container_path,
                    data,
                    mode=mode,
                )
            else:
                raise
        logger.debug("Wrote file: %s (%d bytes)", container_path, len(data))

    async def ensure_workspace_directory(
        self,
        container_path: str,
        *,
        mode: int = 0o700,
    ) -> None:
        """Create and revalidate an owned host directory under the workspace."""
        await self._ensure_container_running()
        await self.ensure_ready()
        await asyncio.to_thread(
            self._workspace.ensure_directory,
            self._session_id,
            container_path,
            mode=mode,
        )

    async def validate_workspace_file(self, container_path: str) -> None:
        """Reject non-files and link/reparse escapes before a tool uses a path."""
        await asyncio.to_thread(
            self._workspace.validate_file,
            self._session_id,
            container_path,
        )

    async def validate_workspace_entry(self, container_path: str) -> None:
        """Reject missing entries and link/reparse escapes."""
        await asyncio.to_thread(
            self._workspace.validate_existing,
            self._session_id,
            container_path,
        )

    def normalize_workspace_path(self, container_path: str) -> str:
        """Return the canonical container path for an owned workspace entry."""
        return self._workspace.normalize_container_path(container_path)

    async def _write_file_internal(
        self,
        container_path: str,
        content: str | bytes,
    ) -> None:
        """Internal helper for writing artifact logs. Ensures parent dirs exist."""
        await self.write_file(container_path, content, require_ready=False)

    async def read_file_chunk(
        self,
        container_path: str,
        *,
        offset: int = 0,
        max_bytes: int = 0,
        require_ready: bool = True,
    ):
        """Read a bounded chunk from the active owned workspace."""
        try:
            await self._ensure_container_running()
            if require_ready:
                await self.ensure_ready()
        except Exception as exc:
            if require_ready and _recoverable_docker_error(exc):
                await self._recover_container(str(exc))
                await self._ensure_container_running()
                await self.ensure_ready()
            else:
                raise
        try:
            result = await asyncio.to_thread(
                self._workspace.read_chunk,
                self._session_id,
                container_path,
                offset=offset,
                max_bytes=max_bytes,
            )
        except Exception as exc:
            if require_ready and _recoverable_docker_error(exc):
                await self._recover_container(str(exc))
                await self._ensure_container_running()
                await self.ensure_ready()
                result = await asyncio.to_thread(
                    self._workspace.read_chunk,
                    self._session_id,
                    container_path,
                    offset=offset,
                    max_bytes=max_bytes,
                )
            else:
                raise
        logger.debug("Read file: %s (%d bytes)", container_path, len(result.data))
        return result

    async def read_file_bytes(
        self,
        container_path: str,
        require_ready: bool = True,
        *,
        offset: int = 0,
        max_bytes: int = 0,
    ) -> bytes:
        """Read raw bytes, bounded by the configured inline-file ceiling."""
        result = await self.read_file_chunk(
            container_path,
            offset=offset,
            max_bytes=max_bytes,
            require_ready=require_ready,
        )
        if result.truncated and max_bytes == 0:
            raise ValueError(
                f"workspace file is {result.total_bytes} bytes, above the "
                f"{self._config.max_inline_file_bytes}-byte inline limit"
            )
        return result.data

    async def read_file(
        self,
        container_path: str,
        require_ready: bool = True,
        *,
        offset: int = 0,
        max_bytes: int = 0,
    ) -> str:
        """Read bounded UTF-8 text from the active workspace."""
        content = await self.read_file_bytes(
            container_path,
            require_ready=require_ready,
            offset=offset,
            max_bytes=max_bytes,
        )
        return content.decode("utf-8", errors="replace")

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
                    port=self.msf_rpc_port,
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

    async def restart_msfrpcd(self) -> None:
        """
        Restart msfrpcd INSIDE the already-running container (no recreate).

        msfrpcd is a background child of PID1 (`sleep infinity`), so it can die
        while the container stays alive. Reconnecting an RPC client is useless if
        the process is gone — this revives the process. Serialized so two
        concurrent reconnects don't double-start on the configured RPC port. All internal
        exec calls use require_ready=False so they never re-enter the recovery
        path (deadlock guard).
        """
        if self._config.skip_metasploit:
            return
        lock = self._get_msf_restart_lock()
        async with lock:
            # Kill any stale / half-dead msfrpcd.
            await self.exec_command(
                "pkill -f msfrpcd || true",
                timeout=15, require_ready=False, clean_output=False,
            )
            # Ensure PostgreSQL is up (msfrpcd wants the DB but tolerates none).
            await self.exec_command(
                "pg_ctlcluster $(pg_lsclusters -h 2>/dev/null | awk '{print $1}' | head -1) "
                "$(pg_lsclusters -h 2>/dev/null | awk '{print $2}' | head -1) start "
                "2>/dev/null || /etc/init.d/postgresql start 2>/dev/null || true",
                timeout=60, require_ready=False, clean_output=False,
            )
            # Relaunch detached; log to the workspace for durable diagnostics.
            await self.exec_command(
                "mkdir -p /opt/workspace/logs && "
                'nohup msfrpcd -P "$MSF_PASSWORD" -S -a "$MSF_BIND_HOST" '
                '-p "$MSF_RPC_PORT" '
                "> /opt/workspace/logs/msfrpcd.log 2>&1 & echo started",
                timeout=20, require_ready=False, clean_output=False,
                env={
                    "MSF_PASSWORD": self._config.msf_password,
                    "MSF_RPC_PORT": str(self.msf_rpc_port),
                    "MSF_BIND_HOST": (
                        "127.0.0.1"
                        if platform.system() == "Linux"
                        # Internal container bind; Docker publishes RPC on host loopback.
                        else _CONTAINER_ALL_INTERFACES
                    ),
                },
            )
        logger.info(
            "restart_msfrpcd: msfrpcd relaunched in container %s.",
            self._container_name,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _verify_setup(self) -> None:
        """
        Verify that the agent prepared the selected runtime described by install.md:
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
            else:
                docker_hint = (
                    "Consult the host's supported Docker installation guidance and "
                    "https://docs.docker.com/llms-full.txt. Hercules does not make "
                    "privileged host changes."
                )

            error_msg = (
                "\n" + "=" * 60 + "\n"
                "  HERCULES ERROR: Docker is not available.\n"
                + "=" * 60 + "\n\n"
                "  The Docker daemon is not running or Docker is not installed.\n\n"
                f"  Platform: {os_name}\n"
                f"  Fix: {docker_hint}\n\n"
                "  After Docker is working, complete the outcomes in install.md.\n\n"
                + "=" * 60 + "\n"
            )
            logger.critical(error_msg)
            raise SystemExit(error_msg) from exc

        # Check the canonical image first. For one compatibility release, an
        # otherwise identical pre-canonicalization image may be reused from the
        # same checkout after every security/capability label is revalidated.
        try:
            capabilities = self._config.installed_capabilities or ALL_CAPABILITIES
            expected_fingerprint = image_build_fingerprint(
                self._config.project_root,
                capabilities,
                build_ca_sha256=self._config.build_ca_sha256,
                target_platform=self._config.image_platform,
                cloakbrowser_version=self._config.cloakbrowser_version,
                cloakbrowser_sha256=self._config.cloakbrowser_sha256,
            )
            expected_capabilities = format_capabilities(capabilities)
            expected_manifest = capability_manifest_sha256(capabilities)
            candidates = [(self.IMAGE, expected_fingerprint, False)]
            legacy_image = str(getattr(self, "_legacy_image", "") or "")
            legacy_fingerprint = str(
                getattr(self, "_legacy_image_fingerprint", "") or ""
            )
            if legacy_image and legacy_image != self.IMAGE:
                candidates.append((legacy_image, legacy_fingerprint, True))

            selected = False
            for candidate_tag, candidate_fingerprint, is_legacy in candidates:
                try:
                    image = await asyncio.to_thread(
                        self._client.images.get,
                        candidate_tag,
                    )
                except ImageNotFound:
                    continue
                labels = (
                    getattr(image, "attrs", {})
                    .get("Config", {})
                    .get("Labels", {})
                    or {}
                )
                if (
                    labels.get(IMAGE_FINGERPRINT_LABEL) != candidate_fingerprint
                    or labels.get(IMAGE_CAPABILITIES_LABEL) != expected_capabilities
                    or labels.get(IMAGE_BUILD_CA_LABEL, "")
                    != self._config.build_ca_sha256
                    or labels.get(IMAGE_BASE_REPOSITORY_LABEL) != KALI_BASE_REPOSITORY
                    or labels.get(IMAGE_BASE_DIGEST_LABEL) != KALI_BASE_DIGEST
                    or labels.get(IMAGE_APT_SUITE_LABEL) != KALI_APT_SUITE
                    or labels.get(IMAGE_PLATFORM_LABEL) != self._config.image_platform
                    or labels.get(IMAGE_CAPABILITY_MANIFEST_LABEL) != expected_manifest
                    or (
                        "browser" in capabilities
                        and (
                            labels.get(IMAGE_CLOAKBROWSER_VERSION_LABEL)
                            != self._config.cloakbrowser_version
                            or labels.get(IMAGE_CLOAKBROWSER_SHA256_LABEL)
                            != self._config.cloakbrowser_sha256
                        )
                    )
                ):
                    continue
                self.IMAGE = candidate_tag
                selected = True
                if is_legacy:
                    logger.warning(
                        "Reusing verified legacy image '%s'; rebuild the canonical "
                        "line-ending-independent image during the next planned upgrade.",
                        candidate_tag,
                    )
                break
            if not selected:
                raise ImageNotFound(
                    "no local Hercules image matches the selected runtime inputs"
                )
            logger.info("Image '%s' found locally. Ready for instant startup.", self.IMAGE)
            await self._verify_image_runtime_ready()
        except ImageNotFound:
            error_msg = (
                "\n" + "=" * 60 + "\n"
                "  HERCULES ERROR: Setup not complete.\n"
                + "=" * 60 + "\n\n"
                f"  The '{self.IMAGE}' Docker image is missing or stale.\n"
                "  Build the confirmed capability profile described by install.md.\n"
                "  Hercules can expose the required non-secret build metadata through\n"
                "  its read-only setup-information mode.\n\n"
                + "=" * 60 + "\n"
            )
            logger.critical(error_msg)
            raise SystemExit(error_msg)

    async def _verify_image_runtime_ready(self) -> None:
        """Fail early if a stale local image is missing required runtime files."""
        capabilities = self._config.installed_capabilities or ALL_CAPABILITIES
        checks = [
            "test -x /entrypoint.sh",
            "! head -n 1 /entrypoint.sh | od -An -tx1 | grep -qi '0d'",
            "test -s /opt/hercules-capabilities.txt",
            "test -s /opt/hercules-capability-manifest.spec",
            (
                f"printf '%s  %s\\n' '{capability_manifest_sha256(capabilities)}' "
                "'/opt/hercules-capability-manifest.spec' | sha256sum -c -"
            ),
            (
                "grep -qx 'apt_suite=" + KALI_APT_SUITE
                + "' /opt/hercules-capabilities.txt"
            ),
            (
                "grep -qx 'platform=" + self._config.image_platform
                + "' /opt/hercules-capabilities.txt"
            ),
        ]
        checks.extend(
            f"command -v {shlex.quote(binary)} >/dev/null"
            for binary in required_backends(capabilities)
        )
        if "browser" in capabilities:
            checks.extend((
                "python3 -c 'import cloakbrowser'",
                (
                    "python3 -c \"import importlib.metadata as m; "
                    f"assert m.version('cloakbrowser') == "
                    f"'{self._config.cloakbrowser_version}'\""
                ),
                "python3 -m cloakbrowser info 2>/dev/null | grep -qi 'Installed: *True'",
                (
                    "cloak_binary=$(python3 -m cloakbrowser info 2>/dev/null | "
                    "sed -n 's/^[Bb]inary:[[:space:]]*//p' | head -n 1); "
                    "test -n \"$cloak_binary\" && test -x \"$cloak_binary\""
                ),
                (
                    "cloak_binary=$(python3 -m cloakbrowser info 2>/dev/null | "
                    "sed -n 's/^[Bb]inary:[[:space:]]*//p' | head -n 1); "
                    "AGENT_BROWSER_EXECUTABLE_PATH=\"$cloak_binary\" "
                    "agent-browser --help >/dev/null"
                ),
                "command -v agent-browser >/dev/null",
            ))
        check_cmd = " && ".join(checks)
        try:
            await asyncio.to_thread(
                self._client.containers.run,
                self.IMAGE,
                ["-c", check_cmd],
                entrypoint="/bin/sh",
                remove=True,
            )
        except Exception as exc:
            error_msg = (
                "\n" + "=" * 60 + "\n"
                "  HERCULES ERROR: Docker image is stale or incomplete.\n"
                + "=" * 60 + "\n\n"
                f"  The '{self.IMAGE}' image exists but failed runtime checks.\n"
                "  Rebuild it from the current Dockerfile using the declarative\n"
                "  metadata exposed by Hercules and the outcomes in install.md.\n\n"
                + "=" * 60 + "\n"
            )
            logger.critical(error_msg)
            raise SystemExit(error_msg) from exc

    async def _ensure_wordlists(self) -> dict[str, Path]:
        """Prepare only wordlists required by the installed capability profile."""
        result = await asyncio.to_thread(
            provision_wordlists,
            self._config.wordlist_root or self._config.project_root / "wordlists",
            self._config.installed_capabilities or ALL_CAPABILITIES,
            dry_run=False,
        )
        return {
            key: Path(value)
            for key, value in result.get("paths", {}).items()
        }

    async def _wait_for_ready(self, timeout: int = 300) -> None:
        """Wait for the entrypoint script to finish initial setup."""
        logger.info("Waiting for container entrypoint to complete...")

        for _ in range(timeout):
            result = await self.exec_command(
                "test -f /tmp/hercules-ready && echo ready",
                timeout=5,
                require_ready=False,
            )
            if result.exit_code == 0:
                logger.info("Container is ready.")
                return
            await asyncio.sleep(1)

        logs = ""
        try:
            raw_logs = await asyncio.to_thread(self._container.logs, tail=100)
            logs = (raw_logs or b"").decode("utf-8", errors="replace")
        except Exception as exc:
            logs = f"<container logs unavailable: {exc}>"
        raise TimeoutError(
            f"Container readiness check timed out after {timeout}s. "
            f"Recent entrypoint logs:\n{logs[-8000:]}"
        )

    @property
    def container(self) -> Container | None:
        return self._container

    @property
    def is_ready(self) -> bool:
        return self._container is not None and self._bootstrapped and self._ready
