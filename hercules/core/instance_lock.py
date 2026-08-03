"""Interprocess coordination locks used by Hercules runtime processes."""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import BinaryIO, Self

_HELD_LOCKS: set[str] = set()
_PORT_ALLOCATION_THREAD_LOCK = threading.Lock()


class InstanceLockError(RuntimeError):
    """Raised when another Hercules server already owns the checkout lock."""


class HerculesInstanceLock:
    """Small stdlib-only exclusive file lock scoped to one project checkout."""

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root.resolve()
        self.lock_path = self.project_root / ".hercules.lock"
        self.instance_id = uuid.uuid4().hex
        self._file = None
        self._key = os.path.normcase(str(self.lock_path))

    def acquire(self) -> None:
        if self._key in _HELD_LOCKS:
            raise InstanceLockError(self._busy_message(self._read_owner()))

        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self._file = self.lock_path.open("a+", encoding="utf-8")
        try:
            self._lock_file()
        except OSError as exc:
            owner = self._read_owner()
            self._file.close()
            self._file = None
            raise InstanceLockError(self._busy_message(owner)) from exc

        _HELD_LOCKS.add(self._key)
        self._write_owner()

    def release(self) -> None:
        if self._file is None:
            return
        try:
            self._unlock_file()
        finally:
            try:
                self._file.close()
            finally:
                self._file = None
                _HELD_LOCKS.discard(self._key)
                try:
                    self.lock_path.unlink()
                except OSError:
                    pass

    def _lock_file(self) -> None:
        if platform.system() == "Windows":
            import msvcrt

            self._file.seek(0)
            if not self._file.read(1):
                self._file.write("\0")
                self._file.flush()
            self._file.seek(0)
            msvcrt.locking(self._file.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(self._file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    def _unlock_file(self) -> None:
        if platform.system() == "Windows":
            import msvcrt

            self._file.seek(0)
            msvcrt.locking(self._file.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(self._file.fileno(), fcntl.LOCK_UN)

    def _write_owner(self) -> None:
        payload = {
            "pid": os.getpid(),
            "instance_id": self.instance_id,
            "project_root": str(self.project_root),
            "command": " ".join(sys.argv),
            "created_at": datetime.now(UTC).isoformat(),
        }
        self._file.seek(0)
        self._file.truncate()
        json.dump(payload, self._file, indent=2)
        self._file.write("\n")
        self._file.flush()

    def _read_owner(self) -> dict:
        try:
            text = self.lock_path.read_text(encoding="utf-8").strip()
            return json.loads(text) if text else {}
        except Exception:
            return {}

    def _busy_message(self, owner: dict) -> str:
        pid = owner.get("pid", "unknown")
        command = owner.get("command") or _process_command(pid) or "unknown"
        return (
            "Another Hercules MCP server is already running for this checkout.\n"
            f"Project: {self.project_root}\n"
            f"Owner PID: {pid}\n"
            f"Owner command: {command}\n"
            "Close that Codex/MCP session, or stop the owning process, then start Hercules again."
        )


def _runtime_state_root() -> Path:
    """Return a per-user, non-synced directory shared by all checkouts."""
    system = platform.system()
    if system == "Windows":
        base = Path(os.getenv("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    elif system == "Darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        runtime = os.getenv("XDG_RUNTIME_DIR", "").strip()
        state = os.getenv("XDG_STATE_HOME", "").strip()
        base = (
            Path(runtime)
            if runtime
            else Path(state) if state else Path.home() / ".local" / "state"
        )
    return base / "hercules-mcp" / "runtime"


class HerculesPortAllocationLock:
    """Serialize host-port selection and Docker publication across IDE clients.

    The coordination file is non-secret durable runtime state. It is retained
    between launches so waiters never race an unlink/recreate boundary.
    """

    def __init__(self) -> None:
        self.lock_path = _runtime_state_root() / "port-allocation.lock"
        self._file: BinaryIO | None = None
        self._thread_locked = False

    def acquire(self) -> None:
        _PORT_ALLOCATION_THREAD_LOCK.acquire()
        self._thread_locked = True
        try:
            self.lock_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            if os.name != "nt":
                os.chmod(self.lock_path.parent, 0o700)
            self._file = self.lock_path.open("a+b")
            if os.name != "nt":
                os.chmod(self.lock_path, 0o600)
            self._lock_file()
        except BaseException:
            if self._file is not None:
                self._file.close()
                self._file = None
            self._release_thread_lock()
            raise

    def release(self) -> None:
        try:
            if self._file is not None:
                try:
                    self._unlock_file()
                finally:
                    self._file.close()
                    self._file = None
        finally:
            self._release_thread_lock()

    def _release_thread_lock(self) -> None:
        if self._thread_locked:
            self._thread_locked = False
            _PORT_ALLOCATION_THREAD_LOCK.release()

    def _lock_file(self) -> None:
        if self._file is None:
            raise RuntimeError("port-allocation lock file is not open")
        self._file.seek(0)
        if not self._file.read(1):
            self._file.write(b"\0")
            self._file.flush()
        self._file.seek(0)
        if platform.system() == "Windows":
            import msvcrt

            msvcrt.locking(self._file.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl

            fcntl.flock(self._file.fileno(), fcntl.LOCK_EX)

    def _unlock_file(self) -> None:
        if self._file is None:
            return
        self._file.seek(0)
        if platform.system() == "Windows":
            import msvcrt

            msvcrt.locking(self._file.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(self._file.fileno(), fcntl.LOCK_UN)

    def __enter__(self) -> Self:
        self.acquire()
        return self

    def __exit__(self, *_args: object) -> None:
        self.release()


def _process_command(pid) -> str:
    try:
        pid_int = int(pid)
    except (TypeError, ValueError):
        return ""

    if platform.system() == "Windows":
        try:
            out = subprocess.check_output(
                [
                    "wmic",
                    "process",
                    "where",
                    f"processid={pid_int}",
                    "get",
                    "CommandLine",
                    "/value",
                ],
                text=True,
                stderr=subprocess.DEVNULL,
                timeout=2,
            )
            for line in out.splitlines():
                if line.startswith("CommandLine="):
                    return line.split("=", 1)[1].strip()
        except Exception:
            return ""
    else:
        try:
            data = Path(f"/proc/{pid_int}/cmdline").read_bytes()
            return data.replace(b"\0", b" ").decode("utf-8", errors="replace").strip()
        except Exception:
            return ""
    return ""
