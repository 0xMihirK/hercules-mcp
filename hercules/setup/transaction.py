"""Crash-recoverable host writes with fingerprint-checked rollback."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

from hercules.core.config_io import atomic_write_private_bytes


class SetupError(RuntimeError):
    def __init__(
        self,
        code: str,
        message: str,
        next_action: str = "Run hercules-setup status --client <client>.",
    ):
        super().__init__(message)
        self.code = code
        self.next_action = next_action


def digest(content: bytes | None) -> str:
    return hashlib.sha256(content).hexdigest() if content is not None else "missing"


def read(path: Path) -> bytes | None:
    if path.is_symlink():
        raise SetupError("unsafe_path", f"Refusing a symbolic link: {path}")
    return path.read_bytes() if path.exists() else None


class InstallLock:
    def __init__(self, path: Path):
        self.path = path
        self.file = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.file = self.path.open("a+b")
        try:
            self.file.seek(0)
            if not self.file.read(1):
                self.file.write(b"0")
                self.file.flush()
            self.file.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(self.file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            self.file.close()
            raise SetupError(
                "setup_busy",
                "Another setup operation holds this installation lock",
                "Wait for that operation, then resume.",
            ) from exc
        return self

    def __exit__(self, *_args):
        self.file.close()


class Transaction:
    def __init__(self, directory: Path, *, operation: dict | None = None):
        self.directory = directory.resolve()
        self.path = self.directory / "transaction.json"
        if self.path.exists():
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
            if self.data.get("schema_version") != 1:
                raise SetupError("journal_invalid", "Unsupported transaction journal")
            for item in self.data.get("writes", []):
                if not Path(item["path"]).is_absolute():
                    raise SetupError("journal_invalid", "Write target must be absolute")
                for key in ("backup", "replacement"):
                    if Path(item[key]).resolve().parent != self.directory:
                        raise SetupError(
                            "journal_invalid",
                            "Backup path escapes the transaction directory",
                        )
        else:
            self.data = {
                "schema_version": 1,
                "id": uuid.uuid4().hex,
                "operation": operation or {},
                "phase": "preparing",
                "writes": [],
                "processes": [],
                "retained": [],
                "cleanup": [],
            }
            self.save()

    def save(self):
        atomic_write_private_bytes(self.path, json.dumps(self.data, indent=2).encode())

    def phase(self, name: str):
        self.data["phase"] = name
        self.save()

    def write(
        self,
        path: Path,
        content: bytes,
        *,
        expected: bytes | None,
        entry: dict | None = None,
        durable: bool = False,
    ):
        path = path.absolute()
        if digest(read(path)) != digest(expected):
            raise SetupError(
                "configuration_changed",
                f"Configuration changed during setup: {path}",
                "Review the changes, then run resume.",
            )
        if content == expected:
            return
        index = len(self.data["writes"])
        backup = self.directory / f"{index}.before"
        after = self.directory / f"{index}.after"
        if expected is not None:
            atomic_write_private_bytes(backup, expected)
        atomic_write_private_bytes(after, content)
        record = {
            "path": str(path),
            "before": digest(expected),
            "after": digest(content),
            "backup": str(backup),
            "replacement": str(after),
            "entry": entry,
            "durable": durable,
        }
        # Persist undo information before any live write (including a failed one).
        self.data["writes"].append(record)
        if durable:
            self.data["retained"].append(str(path))
        self.save()
        if digest(read(path)) != record["before"]:
            raise SetupError(
                "configuration_changed", f"Concurrent edit detected: {path}"
            )
        atomic_write_private_bytes(path, content)

    def rollback(self) -> list[str]:
        leftovers = []
        for item in reversed(self.data["writes"]):
            if item.get("durable"):
                # Generated secrets are safe resumable progress, not disposable config.
                continue
            path = Path(item["path"])
            try:
                actual = read(path)
                if digest(actual) == item["before"]:
                    continue
                original = (
                    Path(item["backup"]).read_bytes()
                    if item["before"] != "missing"
                    else None
                )
                if digest(original) != item["before"]:
                    raise SetupError("journal_invalid", "Backup fingerprint changed")
                if digest(actual) != item["after"]:
                    # An unrelated client setting may have changed since our write.
                    if not item["entry"] or actual is None:
                        leftovers.append(str(path))
                        continue
                    from hercules.setup.documents import edit, lookup, parse

                    meta = item["entry"]
                    keys = tuple(meta["keys"])
                    current_text = actual.decode("utf-8-sig")
                    applied = Path(item["replacement"]).read_text(encoding="utf-8-sig")
                    if digest(Path(item["replacement"]).read_bytes()) != item["after"]:
                        raise SetupError(
                            "journal_invalid", "Replacement fingerprint changed"
                        )
                    if lookup(parse(current_text, meta["format"]), keys) != lookup(
                        parse(applied, meta["format"]), keys
                    ):
                        leftovers.append(str(path))
                        continue
                    old = lookup(
                        parse((original or b"").decode("utf-8-sig"), meta["format"]),
                        keys,
                    )
                    restored = edit(current_text, meta["format"], keys, old).encode(
                        "utf-8"
                    )
                else:
                    restored = original
                if read(path) != actual:
                    leftovers.append(str(path))
                    continue
                if restored is None:
                    path.unlink(missing_ok=True)
                else:
                    atomic_write_private_bytes(path, restored)
            except (OSError, ValueError, RuntimeError):
                leftovers.append(str(path))
        self.data["cleanup"] = leftovers
        self.phase("rollback_blocked" if leftovers else "rolled_back")
        if not leftovers:
            self.clear_backups()
        return leftovers

    def clear_backups(self):
        for item in self.data["writes"]:
            for key in ("backup", "replacement"):
                path = Path(item[key]).resolve()
                if path.parent != self.directory:
                    raise SetupError(
                        "journal_invalid",
                        "Backup path escapes the transaction directory",
                    )
                path.unlink(missing_ok=True)
        self.data["writes"] = []
        self.save()

    def commit(self):
        # Recovery treats this durable marker as committed even if backup removal
        # is interrupted. Success is reported only after removal completes.
        self.phase("committed")
        self.clear_backups()

    def cleanup_temporaries(self):
        import shutil

        staging = self.data.get("workspace_staging")
        if staging:
            from hercules.core.workspace import WorkspaceManager, _is_reparse_or_symlink
            from hercules.core.instance_lock import workspace_lock

            path = Path(staging["path"])
            destination = Path(self.data["operation"]["destination"])
            if path.parent != destination.parent or not path.name.startswith(f".{destination.name}.hercules-migrate-"):
                raise SetupError("unsafe_cleanup", "Migration staging path escaped its destination")
            with workspace_lock(destination):
                if path.exists() or path.is_symlink():
                    details = path.stat(follow_symlinks=False)
                    if _is_reparse_or_symlink(path) or (details.st_dev, details.st_ino) != (staging["device"], staging["inode"]):
                        raise SetupError("unsafe_cleanup", "Migration staging identity changed; retained for review")
                    anchor, name = WorkspaceManager._external_parent(path)
                    try:
                        WorkspaceManager._remove_tree_at(anchor, name)
                    finally:
                        WorkspaceManager._close_anchor(anchor)

        for name in ("facts.json", "native-client"):
            path = self.directory / name
            if path.resolve() != path:
                raise SetupError("unsafe_cleanup", "Temporary path changed identity")
            if path.is_dir() and name == "native-client":
                shutil.rmtree(path)
            else:
                path.unlink(missing_ok=True)

    def run(
        self,
        argv: list[str],
        *,
        cwd: Path | None = None,
        env: dict | None = None,
        timeout: int = 120,
        capture: bool = True,
    ) -> str:
        from hercules.core.docker_manager import _process_start_token

        output = subprocess.PIPE if capture else None
        process = subprocess.Popen(
            argv,
            cwd=cwd,
            env=env,
            shell=False,
            stdin=subprocess.DEVNULL,
            stdout=output,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        item = {
            "pid": process.pid,
            "start": _process_start_token(process.pid),
            "executable": str(argv[0]),
            "done": False,
        }
        self.data["processes"].append(item)
        try:
            self.save()
            started = time.monotonic()
            while True:
                remaining = timeout - (time.monotonic() - started)
                if remaining <= 0:
                    raise subprocess.TimeoutExpired(argv, timeout)
                try:
                    stdout, stderr = process.communicate(timeout=min(20, remaining))
                    break
                except subprocess.TimeoutExpired:
                    if time.monotonic() - started >= timeout:
                        raise
                    print(
                        f"{Path(argv[0]).name} is still running ({int(time.monotonic() - started)}s); waiting for its result.",
                        file=sys.stderr,
                        flush=True,
                    )
            if process.returncode:
                # Diagnostics may contain secrets; only expose the private path.
                diagnostic = self.directory / f"process-{process.pid}.log"
                atomic_write_private_bytes(
                    diagnostic, (stderr or "No stderr was returned.").encode()
                )
                self.data["retained"].append(str(diagnostic))
                raise SetupError(
                    "command_failed",
                    f"{Path(argv[0]).name} exited with code {process.returncode}",
                    f"Review the private diagnostic at {diagnostic}; correct the cause, then resume. Do not bypass a harness denial.",
                )
            return (stdout or "").strip()
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)
            item["done"] = True
            self.save()

    def check_processes(self):
        from hercules.core.docker_manager import (
            _is_process_running,
            _process_start_token,
        )

        for item in self.data["processes"]:
            if item["done"] or not _is_process_running(item["pid"]):
                continue
            current = _process_start_token(item["pid"])
            if not current or current == item["start"]:
                raise SetupError(
                    "operation_still_running",
                    f"A transaction-owned process may still be running (PID {item['pid']})",
                    "Wait for or stop that exact setup process, then resume. Live MCP sessions must not be stopped.",
                )


def recover(root: Path):
    for path in sorted((root / "transactions").glob("*/transaction.json")):
        transaction = Transaction(path.parent)
        transaction.check_processes()
        transaction.cleanup_temporaries()
        if transaction.data.get("verification"):
            from hercules.setup.runtime import cleanup_verification

            cleanup_verification(
                transaction.directory, transaction.data["verification"]
            )
            transaction.save()
        if transaction.data["phase"] == "committed":
            transaction.clear_backups()
        elif transaction.data["writes"]:
            if transaction.rollback():
                raise SetupError(
                    "rollback_conflict",
                    "Recovery found concurrent edits; original private backups were retained",
                    f"Review {path.parent} before resuming.",
                )


def new_transaction(root: Path, operation: dict) -> Transaction:
    return Transaction(
        root / "transactions" / f"{int(time.time())}-{uuid.uuid4().hex[:12]}",
        operation=operation,
    )
