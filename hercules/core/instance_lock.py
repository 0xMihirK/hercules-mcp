"""Interprocess coordination locks used by Hercules runtime processes."""

from __future__ import annotations

import os
import platform
import threading
from pathlib import Path
from typing import BinaryIO, Self

_PORT_ALLOCATION_THREAD_LOCK = threading.Lock()


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
