"""Interprocess coordination locks used by Hercules runtime processes."""

from __future__ import annotations

import os
import hashlib
import platform
import threading
from pathlib import Path
from contextlib import contextmanager
from typing import BinaryIO, Self

_PORT_ALLOCATION_THREAD_LOCK = threading.Lock()
_WORKSPACE_THREAD_LOCKS: dict[str, threading.RLock] = {}
_WORKSPACE_REGISTRY_LOCK = threading.Lock()
_WORKSPACE_HELD = threading.local()


def _persistent_state_root() -> Path:
    """Return durable per-user state shared by all checkouts."""
    system = platform.system()
    if system == "Windows":
        base = Path(os.getenv("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    elif system == "Darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        state = os.getenv("XDG_STATE_HOME", "").strip()
        base = Path(state) if state else Path.home() / ".local" / "state"
    return base / "hercules-mcp" / "runtime"


def _runtime_state_root() -> Path:
    """Transient port coordination may use the operating system runtime dir."""
    runtime = os.getenv("XDG_RUNTIME_DIR", "").strip()
    if platform.system() not in {"Windows", "Darwin"} and runtime:
        return Path(runtime) / "hercules-mcp" / "runtime"
    return _persistent_state_root()


class HerculesPortAllocationLock:
    """Serialize host-port selection and Docker publication across IDE clients.

    The coordination file is non-secret durable runtime state. It is retained
    between launches so waiters never race an unlink/recreate boundary.
    """

    def __init__(self, *, lock_path: Path | None = None, thread_lock=None) -> None:
        self.lock_path = lock_path or _runtime_state_root() / "port-allocation.lock"
        self._thread_lock = thread_lock or _PORT_ALLOCATION_THREAD_LOCK
        self._file: BinaryIO | None = None
        self._thread_locked = False

    def acquire(self) -> None:
        self._thread_lock.acquire()
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
            self._thread_lock.release()

    def _lock_file(self) -> None:
        if self._file is None:
            raise RuntimeError("port-allocation lock file is not open")
        self._file.seek(0)
        if os.fstat(self._file.fileno()).st_size == 0:
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


def workspace_state_path(root: Path, suffix: str) -> Path:
    key = os.path.normcase(str(Path(root).resolve()))
    # Keep transaction paths below Windows MAX_PATH without changing OS policy.
    return _persistent_state_root() / "workspaces" / (hashlib.sha256(key.encode()).hexdigest()[:32] + suffix)


@contextmanager
def workspace_lock(root: Path):
    """Reentrant in one thread, cross-process across immutable installations."""
    path = workspace_state_path(root, ".lock")
    key = str(path)
    with _WORKSPACE_REGISTRY_LOCK:
        thread_lock = _WORKSPACE_THREAD_LOCKS.setdefault(key, threading.RLock())
    with thread_lock:
        held = getattr(_WORKSPACE_HELD, "keys", set())
        if key in held:
            yield
            return
        with HerculesPortAllocationLock(lock_path=path, thread_lock=thread_lock):
            _WORKSPACE_HELD.keys = held | {key}
            try:
                yield
            finally:
                _WORKSPACE_HELD.keys = held
