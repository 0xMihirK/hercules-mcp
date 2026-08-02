"""Owned Hercules workspace sessions and safe host-path operations.

The Docker container always sees the active session at ``/opt/workspace``.
This module owns the host-side mapping, records non-secret session metadata,
and refuses to prune or mutate directories that Hercules cannot prove it owns.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import threading
import time
import uuid
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path, PurePosixPath
from typing import Any, BinaryIO

SESSION_ID_RE = re.compile(r"^[0-9a-f]{8}$")
MANIFEST_NAME = ".hercules-session.json"
MANIFEST_SCHEMA_VERSION = 1
CONTAINER_WORKSPACE = PurePosixPath("/opt/workspace")
WINDOWS_RESERVED_NAMES = {
    "aux",
    "com1",
    "com2",
    "com3",
    "com4",
    "com5",
    "com6",
    "com7",
    "com8",
    "com9",
    "con",
    "lpt1",
    "lpt2",
    "lpt3",
    "lpt4",
    "lpt5",
    "lpt6",
    "lpt7",
    "lpt8",
    "lpt9",
    "nul",
    "prn",
}

if os.name == "nt":
    import ctypes
    import msvcrt
    from ctypes import wintypes

    _KERNEL32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _NTDLL = ctypes.WinDLL("ntdll")
    _FILE_LIST_DIRECTORY = 0x0001
    _FILE_READ_ATTRIBUTES = 0x0080
    _DELETE = 0x00010000
    _SYNCHRONIZE = 0x00100000
    _GENERIC_READ = 0x80000000
    _GENERIC_WRITE = 0x40000000
    _FILE_SHARE_ALL = 0x00000007
    _OPEN_EXISTING = 3
    _FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
    _FILE_OPEN_REPARSE_POINT = 0x00200000
    _FILE_DIRECTORY_FILE = 0x00000001
    _FILE_NON_DIRECTORY_FILE = 0x00000040
    _FILE_SYNCHRONOUS_IO_NONALERT = 0x00000020
    _FILE_OPEN = 1
    _FILE_CREATE = 2
    _FILE_OPEN_IF = 3
    _OBJ_CASE_INSENSITIVE = 0x00000040
    _FILE_ATTRIBUTE_REPARSE_POINT = 0x00000400
    _FILE_ATTRIBUTE_TAG_INFO_CLASS = 9
    _FILE_DISPOSITION_INFO_CLASS = 4
    _FILE_RENAME_INFORMATION_CLASS = 10
    _INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

    class _UnicodeString(ctypes.Structure):
        _fields_ = [
            ("Length", wintypes.USHORT),
            ("MaximumLength", wintypes.USHORT),
            ("Buffer", wintypes.LPWSTR),
        ]

    class _ObjectAttributes(ctypes.Structure):
        _fields_ = [
            ("Length", wintypes.ULONG),
            ("RootDirectory", wintypes.HANDLE),
            ("ObjectName", ctypes.POINTER(_UnicodeString)),
            ("Attributes", wintypes.ULONG),
            ("SecurityDescriptor", wintypes.LPVOID),
            ("SecurityQualityOfService", wintypes.LPVOID),
        ]

    class _IoStatusUnion(ctypes.Union):
        _fields_ = [  # noqa: RUF012 - ctypes requires this mutable class layout
            ("Status", wintypes.LONG),
            ("Pointer", wintypes.LPVOID),
        ]

    class _IoStatusBlock(ctypes.Structure):
        _anonymous_ = ("value",)
        _fields_ = [
            ("value", _IoStatusUnion),
            ("Information", ctypes.c_size_t),
        ]

    class _FileAttributeTagInfo(ctypes.Structure):
        _fields_ = [
            ("FileAttributes", wintypes.DWORD),
            ("ReparseTag", wintypes.DWORD),
        ]

    class _FileDispositionInfo(ctypes.Structure):
        _fields_ = [("DeleteFile", wintypes.BOOL)]

    class _FileRenameInfo(ctypes.Structure):
        _fields_ = [
            ("ReplaceIfExists", wintypes.BOOLEAN),
            ("RootDirectory", wintypes.HANDLE),
            ("FileNameLength", wintypes.DWORD),
            ("FileName", wintypes.WCHAR * 1),
        ]

    _KERNEL32.CreateFileW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    _KERNEL32.CreateFileW.restype = wintypes.HANDLE
    _KERNEL32.CloseHandle.argtypes = [wintypes.HANDLE]
    _KERNEL32.CloseHandle.restype = wintypes.BOOL
    _KERNEL32.GetFileInformationByHandleEx.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        wintypes.LPVOID,
        wintypes.DWORD,
    ]
    _KERNEL32.GetFileInformationByHandleEx.restype = wintypes.BOOL
    _KERNEL32.SetFileInformationByHandle.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        wintypes.LPVOID,
        wintypes.DWORD,
    ]
    _KERNEL32.SetFileInformationByHandle.restype = wintypes.BOOL
    _KERNEL32.GetFinalPathNameByHandleW.argtypes = [
        wintypes.HANDLE,
        wintypes.LPWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
    ]
    _KERNEL32.GetFinalPathNameByHandleW.restype = wintypes.DWORD
    _NTDLL.NtCreateFile.argtypes = [
        ctypes.POINTER(wintypes.HANDLE),
        wintypes.DWORD,
        ctypes.POINTER(_ObjectAttributes),
        ctypes.POINTER(_IoStatusBlock),
        wintypes.LPVOID,
        wintypes.ULONG,
        wintypes.ULONG,
        wintypes.ULONG,
        wintypes.ULONG,
        wintypes.LPVOID,
        wintypes.ULONG,
    ]
    _NTDLL.NtCreateFile.restype = wintypes.LONG
    _NTDLL.NtSetInformationFile.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(_IoStatusBlock),
        wintypes.LPVOID,
        wintypes.ULONG,
        ctypes.c_int,
    ]
    _NTDLL.NtSetInformationFile.restype = wintypes.LONG
    _NTDLL.RtlNtStatusToDosError.argtypes = [wintypes.LONG]
    _NTDLL.RtlNtStatusToDosError.restype = wintypes.ULONG


def _windows_error_from_status(status: int, operation: str) -> OSError:
    if os.name != "nt":
        return OSError(operation)
    code = int(_NTDLL.RtlNtStatusToDosError(status))
    return OSError(code, f"{operation}: {ctypes.FormatError(code)}")


def _win_close(handle: int) -> None:
    if os.name == "nt" and handle not in {0, None, _INVALID_HANDLE_VALUE}:
        _KERNEL32.CloseHandle(handle)


def _win_reject_reparse(handle: int, *, label: str) -> None:
    info = _FileAttributeTagInfo()
    if not _KERNEL32.GetFileInformationByHandleEx(
        handle,
        _FILE_ATTRIBUTE_TAG_INFO_CLASS,
        ctypes.byref(info),
        ctypes.sizeof(info),
    ):
        raise ctypes.WinError(ctypes.get_last_error())
    if info.FileAttributes & _FILE_ATTRIBUTE_REPARSE_POINT:
        raise ValueError(f"workspace path traverses a reparse point: {label!r}")


def _win_open_root(path: Path) -> int:
    handle = _KERNEL32.CreateFileW(
        str(path),
        _FILE_LIST_DIRECTORY | _FILE_READ_ATTRIBUTES | _SYNCHRONIZE,
        _FILE_SHARE_ALL,
        None,
        _OPEN_EXISTING,
        _FILE_FLAG_BACKUP_SEMANTICS | _FILE_OPEN_REPARSE_POINT,
        None,
    )
    if handle == _INVALID_HANDLE_VALUE:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        _win_reject_reparse(handle, label=str(path))
    except Exception:
        _win_close(handle)
        raise
    return int(handle)


def _win_open_at(
    parent: int,
    name: str,
    *,
    directory: bool | None,
    create: bool = False,
    exclusive: bool = False,
    write: bool = False,
    delete: bool = False,
) -> int:
    encoded = name.encode("utf-16-le")
    buffer = ctypes.create_unicode_buffer(name)
    unicode_name = _UnicodeString(
        len(encoded),
        len(encoded),
        ctypes.cast(buffer, wintypes.LPWSTR),
    )
    attributes = _ObjectAttributes(
        ctypes.sizeof(_ObjectAttributes),
        parent,
        ctypes.pointer(unicode_name),
        _OBJ_CASE_INSENSITIVE,
        None,
        None,
    )
    status_block = _IoStatusBlock()
    handle = wintypes.HANDLE()
    desired_access = _FILE_READ_ATTRIBUTES | _SYNCHRONIZE
    desired_access |= _FILE_LIST_DIRECTORY if directory else _GENERIC_READ
    if write:
        desired_access |= _GENERIC_WRITE
    if delete:
        desired_access |= _DELETE
    options = _FILE_SYNCHRONOUS_IO_NONALERT | _FILE_OPEN_REPARSE_POINT
    if directory is True:
        options |= _FILE_DIRECTORY_FILE
    elif directory is False:
        options |= _FILE_NON_DIRECTORY_FILE
    disposition = (
        _FILE_CREATE
        if exclusive
        else (_FILE_OPEN_IF if create else _FILE_OPEN)
    )
    status = int(
        _NTDLL.NtCreateFile(
            ctypes.byref(handle),
            desired_access,
            ctypes.byref(attributes),
            ctypes.byref(status_block),
            None,
            0,
            _FILE_SHARE_ALL,
            disposition,
            options,
            None,
            0,
        )
    )
    if status < 0:
        error = _windows_error_from_status(status, f"open {name!r}")
        error_code = getattr(error, "winerror", None) or error.errno
        if error_code in {2, 3}:
            raise FileNotFoundError(name) from error
        if error_code in {80, 183}:
            raise FileExistsError(name) from error
        if error_code in {267}:
            raise NotADirectoryError(name) from error
        raise error
    try:
        _win_reject_reparse(handle.value, label=name)
    except Exception:
        _win_close(handle.value)
        raise
    return int(handle.value)


def _win_handle_to_fd(handle: int, flags: int) -> int:
    try:
        return msvcrt.open_osfhandle(handle, flags | os.O_BINARY)
    except Exception:
        _win_close(handle)
        raise


def _win_rename_at(file_handle: int, parent: int, name: str) -> None:
    encoded = name.encode("utf-16-le")
    size = _FileRenameInfo.FileName.offset + len(encoded)
    raw = ctypes.create_string_buffer(size)
    info = _FileRenameInfo.from_buffer(raw)
    info.ReplaceIfExists = 1
    info.RootDirectory = parent
    info.FileNameLength = len(encoded)
    ctypes.memmove(
        ctypes.addressof(raw) + _FileRenameInfo.FileName.offset,
        encoded,
        len(encoded),
    )
    status_block = _IoStatusBlock()
    status = int(
        _NTDLL.NtSetInformationFile(
            file_handle,
            ctypes.byref(status_block),
            raw,
            size,
            _FILE_RENAME_INFORMATION_CLASS,
        )
    )
    if status < 0:
        raise _windows_error_from_status(status, f"replace {name!r}")


def _win_final_path(handle: int) -> Path:
    required = _KERNEL32.GetFinalPathNameByHandleW(handle, None, 0, 0)
    if not required:
        raise ctypes.WinError(ctypes.get_last_error())
    buffer = ctypes.create_unicode_buffer(required + 1)
    written = _KERNEL32.GetFinalPathNameByHandleW(
        handle,
        buffer,
        len(buffer),
        0,
    )
    if not written or written >= len(buffer):
        raise ctypes.WinError(ctypes.get_last_error())
    value = buffer.value
    if value.startswith("\\\\?\\UNC\\"):
        value = "\\\\" + value[8:]
    elif value.startswith("\\\\?\\"):
        value = value[4:]
    return Path(value)


def _win_delete_at(parent: int, name: str, *, directory: bool | None = None) -> None:
    handle = _win_open_at(
        parent,
        name,
        directory=directory,
        delete=True,
    )
    try:
        disposition = _FileDispositionInfo(True)
        if not _KERNEL32.SetFileInformationByHandle(
            handle,
            _FILE_DISPOSITION_INFO_CLASS,
            ctypes.byref(disposition),
            ctypes.sizeof(disposition),
        ):
            raise ctypes.WinError(ctypes.get_last_error())
    finally:
        _win_close(handle)


def _win_mark_delete(handle: int) -> None:
    disposition = _FileDispositionInfo(True)
    if not _KERNEL32.SetFileInformationByHandle(
        handle,
        _FILE_DISPOSITION_INFO_CLASS,
        ctypes.byref(disposition),
        ctypes.sizeof(disposition),
    ):
        raise ctypes.WinError(ctypes.get_last_error())


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _is_reparse_or_symlink(path: Path) -> bool:
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode):
        return True
    attributes = getattr(info, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(attributes & reparse_flag)


def _validate_session_id(session_id: str) -> str:
    value = str(session_id).strip().lower()
    if not SESSION_ID_RE.fullmatch(value):
        raise ValueError("session_id must be exactly eight lowercase hexadecimal characters")
    return value


@dataclass(frozen=True)
class WorkspaceRead:
    data: bytes
    total_bytes: int
    offset: int
    truncated: bool
    next_offset: int | None


class WorkspaceManager:
    """Manage Hercules-owned session directories under one host root."""

    def __init__(self, root: Path, *, max_inline_bytes: int = 8 * 1024 * 1024) -> None:
        self.root = Path(root).expanduser().resolve()
        self.max_inline_bytes = max(1, int(max_inline_bytes))
        self._manifest_lock = threading.RLock()
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _close_anchor(anchor: int) -> None:
        if os.name == "nt":
            _win_close(anchor)
        else:
            os.close(anchor)

    def _open_root_anchor(self) -> int:
        if os.name == "nt":
            return _win_open_root(self.root)
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
        flags |= getattr(os, "O_NOFOLLOW", 0)
        anchor = os.open(self.root, flags)
        if not stat.S_ISDIR(os.fstat(anchor).st_mode):
            os.close(anchor)
            raise NotADirectoryError(self.root)
        return anchor

    @staticmethod
    def _open_directory_at(
        parent: int,
        name: str,
        *,
        create: bool = False,
        exclusive: bool = False,
        delete: bool = False,
        mode: int = 0o700,
    ) -> int:
        if os.name == "nt":
            return _win_open_at(
                parent,
                name,
                directory=True,
                create=create,
                exclusive=exclusive,
                delete=delete,
            )
        if create:
            try:
                os.mkdir(name, mode=mode, dir_fd=parent)
            except FileExistsError:
                if exclusive:
                    raise
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
        flags |= getattr(os, "O_NOFOLLOW", 0)
        anchor = os.open(name, flags, dir_fd=parent)
        if not stat.S_ISDIR(os.fstat(anchor).st_mode):
            os.close(anchor)
            raise NotADirectoryError(name)
        return anchor

    @staticmethod
    def _open_file_at(
        parent: int,
        name: str,
        *,
        write: bool = False,
        exclusive: bool = False,
        delete: bool = False,
        mode: int = 0o600,
    ) -> int:
        if os.name == "nt":
            return _win_open_at(
                parent,
                name,
                directory=False if write else None,
                create=exclusive,
                exclusive=exclusive,
                write=write,
                delete=delete,
            )
        flags = os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0)
        flags |= os.O_WRONLY | os.O_CREAT | os.O_EXCL if write else os.O_RDONLY
        handle = os.open(name, flags, mode, dir_fd=parent)
        if not stat.S_ISREG(os.fstat(handle).st_mode):
            os.close(handle)
            raise IsADirectoryError(name)
        return handle

    @staticmethod
    def _fd_from_handle(handle: int, flags: int) -> int:
        if os.name == "nt":
            return _win_handle_to_fd(handle, flags)
        return handle

    @staticmethod
    def _read_handle(handle: int, *, offset: int, limit: int) -> tuple[bytes, int]:
        descriptor = WorkspaceManager._fd_from_handle(handle, os.O_RDONLY)
        try:
            details = os.fstat(descriptor)
            if not stat.S_ISREG(details.st_mode):
                raise IsADirectoryError("workspace entry is not a regular file")
            os.lseek(descriptor, offset, os.SEEK_SET)
            chunks: list[bytes] = []
            remaining = limit
            while remaining > 0:
                chunk = os.read(descriptor, min(remaining, 1024 * 1024))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            return b"".join(chunks), int(details.st_size)
        finally:
            os.close(descriptor)

    def _read_manifest_from_anchor(
        self,
        session_anchor: int,
        session_id: str,
    ) -> dict[str, Any] | None:
        try:
            handle = self._open_file_at(session_anchor, MANIFEST_NAME)
            raw, total = self._read_handle(handle, offset=0, limit=64 * 1024)
            if total > 64 * 1024:
                return None
            payload = json.loads(raw.decode("utf-8"))
        except (OSError, UnicodeError, ValueError, TypeError):
            return None
        if (
            not isinstance(payload, dict)
            or payload.get("schema_version") != MANIFEST_SCHEMA_VERSION
            or payload.get("session_id") != session_id
        ):
            return None
        return payload

    def _open_session_anchor(
        self,
        session_id: str,
        *,
        require_owned: bool = True,
    ) -> int:
        session_id = _validate_session_id(session_id)
        root_anchor = self._open_root_anchor()
        try:
            session_anchor = self._open_directory_at(root_anchor, session_id)
        finally:
            self._close_anchor(root_anchor)
        if require_owned and self._read_manifest_from_anchor(
            session_anchor, session_id
        ) is None:
            self._close_anchor(session_anchor)
            raise ValueError(f"workspace session '{session_id}' is not Hercules-owned")
        return session_anchor

    def _relative_parts(self, container_path: str) -> tuple[str, ...]:
        normalized = PurePosixPath(self.normalize_container_path(container_path))
        relative = normalized.relative_to(CONTAINER_WORKSPACE)
        return tuple(relative.parts) if str(relative) != "." else ()

    def _open_parent_anchor(
        self,
        session_id: str,
        container_path: str,
        *,
        create_directories: bool,
    ) -> tuple[int, str]:
        parts = self._relative_parts(container_path)
        if not parts:
            raise IsADirectoryError(container_path)
        current = self._open_session_anchor(session_id)
        try:
            for part in parts[:-1]:
                child = self._open_directory_at(
                    current,
                    part,
                    create=create_directories,
                    mode=0o700,
                )
                self._close_anchor(current)
                current = child
            return current, parts[-1]
        except Exception:
            self._close_anchor(current)
            raise

    @staticmethod
    def _atomic_replace_at(
        parent: int,
        name: str,
        content: bytes,
        *,
        mode: int,
    ) -> None:
        temporary = f".{name}.{uuid.uuid4().hex}.tmp"
        handle = WorkspaceManager._open_file_at(
            parent,
            temporary,
            write=True,
            exclusive=True,
            delete=True,
            mode=mode,
        )
        descriptor = WorkspaceManager._fd_from_handle(handle, os.O_WRONLY)
        renamed = False
        try:
            view = memoryview(content)
            while view:
                written = os.write(descriptor, view)
                view = view[written:]
            os.fsync(descriptor)
            if os.name == "nt":
                native_handle = msvcrt.get_osfhandle(descriptor)
                for attempt in range(6):
                    try:
                        _win_rename_at(native_handle, parent, name)
                        break
                    except OSError as exc:
                        code = getattr(exc, "winerror", None) or exc.errno
                        if code not in {5, 32, 33} or attempt == 5:
                            raise
                        # Docker Desktop bind mounts, indexers, and antivirus can
                        # briefly retain a handle without delete sharing.
                        time.sleep(0.01 * (2**attempt))
            else:
                try:
                    os.fchmod(descriptor, mode)
                except OSError:
                    pass
                os.replace(
                    temporary,
                    name,
                    src_dir_fd=parent,
                    dst_dir_fd=parent,
                )
                os.fsync(parent)
            renamed = True
        finally:
            os.close(descriptor)
            if not renamed:
                with suppress(OSError, ValueError):
                    if os.name == "nt":
                        _win_delete_at(parent, temporary)
                    else:
                        os.unlink(temporary, dir_fd=parent)

    def open_exclusive_writer(
        self,
        session_id: str,
        container_path: str,
        *,
        mode: int = 0o600,
    ) -> BinaryIO:
        """Open one unique evidence file without following workspace links."""
        parent, name = self._open_parent_anchor(
            session_id,
            container_path,
            create_directories=True,
        )
        try:
            handle = self._open_file_at(
                parent,
                name,
                write=True,
                exclusive=True,
                mode=mode,
            )
        finally:
            self._close_anchor(parent)
        descriptor = self._fd_from_handle(handle, os.O_WRONLY)
        return os.fdopen(descriptor, "wb", buffering=0)

    def unlink(self, session_id: str, container_path: str, *, missing_ok: bool = False) -> None:
        """Remove one file relative to a verified, pinned workspace parent."""
        try:
            parent, name = self._open_parent_anchor(
                session_id,
                container_path,
                create_directories=False,
            )
        except FileNotFoundError:
            if missing_ok:
                return
            raise
        try:
            if os.name == "nt":
                _win_delete_at(parent, name)
            else:
                os.unlink(name, dir_fd=parent)
        except FileNotFoundError:
            if not missing_ok:
                raise
        finally:
            self._close_anchor(parent)

    def session_path(self, session_id: str) -> Path:
        return self.root / _validate_session_id(session_id)

    def manifest_path(self, session_id: str) -> Path:
        return self.session_path(session_id) / MANIFEST_NAME

    def allocate_session(self, *, generation: int = 0) -> str:
        """Atomically reserve an unused eight-character session directory."""
        for _ in range(256):
            session_id = uuid.uuid4().hex[:8]
            root_anchor = self._open_root_anchor()
            session_anchor = 0
            try:
                try:
                    session_anchor = self._open_directory_at(
                        root_anchor,
                        session_id,
                        create=True,
                        exclusive=True,
                        delete=os.name == "nt",
                        mode=0o700,
                    )
                except FileExistsError:
                    continue
                payload = {
                    "schema_version": MANIFEST_SCHEMA_VERSION,
                    "session_id": session_id,
                    "created_at": utc_now(),
                    "last_used_at": utc_now(),
                    "generation": int(generation),
                    "state": "inactive",
                    "pinned": False,
                }
                self._atomic_replace_at(
                    session_anchor,
                    MANIFEST_NAME,
                    (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode(
                        "utf-8"
                    ),
                    mode=0o600,
                )
                return session_id
            except Exception:
                if session_anchor:
                    with suppress(OSError, ValueError):
                        self._remove_open_tree(
                            root_anchor,
                            session_id,
                            session_anchor,
                        )
                raise
            finally:
                if session_anchor:
                    self._close_anchor(session_anchor)
                self._close_anchor(root_anchor)
        raise RuntimeError("could not allocate a unique Hercules workspace session")

    def read_manifest(self, session_id: str) -> dict[str, Any] | None:
        try:
            anchor = self._open_session_anchor(session_id, require_owned=False)
        except (OSError, ValueError):
            return None
        try:
            return self._read_manifest_from_anchor(anchor, session_id)
        finally:
            self._close_anchor(anchor)

    def update_manifest(self, session_id: str, **changes: Any) -> dict[str, Any]:
        with self._manifest_lock:
            anchor = self._open_session_anchor(session_id)
            try:
                manifest = self._read_manifest_from_anchor(anchor, session_id)
                if manifest is None:
                    raise ValueError(
                        f"workspace session '{session_id}' is not Hercules-owned"
                    )
                manifest.update(changes)
                manifest["schema_version"] = MANIFEST_SCHEMA_VERSION
                manifest["session_id"] = session_id
                manifest["last_used_at"] = utc_now()
                self._atomic_replace_at(
                    anchor,
                    MANIFEST_NAME,
                    (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode(
                        "utf-8"
                    ),
                    mode=0o600,
                )
                return manifest
            finally:
                self._close_anchor(anchor)

    def mark_active(self, session_id: str, generation: int) -> None:
        self.update_manifest(session_id, state="active", generation=int(generation))

    def mark_inactive(self, session_id: str, generation: int | None = None) -> None:
        changes: dict[str, Any] = {"state": "inactive"}
        if generation is not None:
            changes["generation"] = int(generation)
        self.update_manifest(session_id, **changes)

    def pin(self, session_id: str, pinned: bool) -> dict[str, Any]:
        return self.update_manifest(session_id, pinned=bool(pinned))

    def normalize_container_path(self, value: str) -> str:
        if not isinstance(value, str):
            # Callers translate every unsafe path through one ValueError contract.
            raise ValueError("workspace path must be a string")  # noqa: TRY004
        if any(character in value for character in ("\r", "\n", "\x00")):
            raise ValueError("workspace path contains forbidden control characters")
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("workspace path must not be empty")
        if "\\" in cleaned:
            raise ValueError("workspace paths must use forward slashes")
        if re.match(r"^[a-zA-Z]:", cleaned) or cleaned.startswith("//"):
            raise ValueError("host drive and network paths are not valid workspace paths")

        candidate = (
            PurePosixPath(cleaned)
            if cleaned.startswith("/")
            else CONTAINER_WORKSPACE / cleaned
        )
        parts: list[str] = []
        for part in candidate.parts:
            if part in {"", "/"}:
                continue
            if part == ".":
                continue
            if part == "..":
                raise ValueError("workspace path traversal is not allowed")
            if ":" in part or part.endswith((".", " ")):
                raise ValueError(f"workspace path uses an unsafe component: {part!r}")
            if part.casefold().split(".", 1)[0] in WINDOWS_RESERVED_NAMES:
                raise ValueError(f"workspace path uses reserved device name: {part!r}")
            parts.append(part)
        normalized = PurePosixPath("/", *parts)
        try:
            relative = normalized.relative_to(CONTAINER_WORKSPACE)
        except ValueError as exc:
            raise ValueError("workspace file paths must stay under /opt/workspace") from exc
        if str(relative) == ".":
            return str(CONTAINER_WORKSPACE)
        return str(CONTAINER_WORKSPACE / relative)

    def resolve_host_path(
        self,
        session_id: str,
        container_path: str,
        *,
        for_write: bool = False,
    ) -> Path:
        normalized = self.normalize_container_path(container_path)
        session_root = self.session_path(session_id)
        if self.read_manifest(session_id) is None:
            raise ValueError(f"workspace session '{session_id}' is not Hercules-owned")
        relative = PurePosixPath(normalized).relative_to(CONTAINER_WORKSPACE)
        candidate = session_root.joinpath(*relative.parts)

        current = session_root
        for index, part in enumerate(relative.parts):
            current = current / part
            if not current.exists() and not current.is_symlink():
                if not for_write and index < len(relative.parts):
                    break
                continue
            if _is_reparse_or_symlink(current):
                raise ValueError(f"workspace path traverses a symbolic link: {part!r}")

        resolved_root = session_root.resolve()
        probe = candidate if candidate.exists() else candidate.parent
        try:
            probe.resolve().relative_to(resolved_root)
        except (OSError, ValueError) as exc:
            raise ValueError("workspace path resolves outside the active session") from exc
        return candidate

    def atomic_write(
        self,
        session_id: str,
        container_path: str,
        content: bytes,
        *,
        mode: int,
    ) -> Path:
        normalized = self.normalize_container_path(container_path)
        parent, name = self._open_parent_anchor(
            session_id,
            normalized,
            create_directories=True,
        )
        try:
            self._atomic_replace_at(parent, name, content, mode=mode)
        finally:
            self._close_anchor(parent)
        self.update_manifest(session_id)
        return self.session_path(session_id).joinpath(
            *self._relative_parts(normalized)
        )

    def ensure_directory(
        self,
        session_id: str,
        container_path: str,
        *,
        mode: int = 0o700,
    ) -> Path:
        parts = self._relative_parts(container_path)
        current = self._open_session_anchor(session_id)
        try:
            for part in parts:
                child = self._open_directory_at(
                    current,
                    part,
                    create=True,
                    mode=mode,
                )
                self._close_anchor(current)
                current = child
            if os.name != "nt":
                with suppress(OSError):
                    os.fchmod(current, mode)
        finally:
            self._close_anchor(current)
        self.update_manifest(session_id)
        return self.session_path(session_id).joinpath(*parts)

    def validate_file(self, session_id: str, container_path: str) -> Path:
        parent, name = self._open_parent_anchor(
            session_id,
            container_path,
            create_directories=False,
        )
        try:
            handle = self._open_file_at(parent, name)
        finally:
            self._close_anchor(parent)
        descriptor = self._fd_from_handle(handle, os.O_RDONLY)
        try:
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                raise IsADirectoryError(container_path)
        finally:
            os.close(descriptor)
        return self.session_path(session_id).joinpath(
            *self._relative_parts(container_path)
        )

    def validate_existing(self, session_id: str, container_path: str) -> Path:
        parts = self._relative_parts(container_path)
        if not parts:
            anchor = self._open_session_anchor(session_id)
            self._close_anchor(anchor)
            return self.session_path(session_id)
        parent, name = self._open_parent_anchor(
            session_id,
            container_path,
            create_directories=False,
        )
        handle = 0
        try:
            if os.name == "nt":
                handle = _win_open_at(parent, name, directory=None)
                _win_close(handle)
            else:
                flags = os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0)
                handle = os.open(name, flags, dir_fd=parent)
                os.close(handle)
        finally:
            self._close_anchor(parent)
        return self.session_path(session_id).joinpath(*parts)

    def read_chunk(
        self,
        session_id: str,
        container_path: str,
        *,
        offset: int = 0,
        max_bytes: int = 0,
    ) -> WorkspaceRead:
        if offset < 0:
            raise ValueError("offset must be zero or greater")
        requested = int(max_bytes)
        if requested < 0:
            raise ValueError("max_bytes must be zero or greater")
        limit = self.max_inline_bytes if requested == 0 else min(
            requested, self.max_inline_bytes
        )
        parent, name = self._open_parent_anchor(
            session_id,
            container_path,
            create_directories=False,
        )
        try:
            handle = self._open_file_at(parent, name)
        finally:
            self._close_anchor(parent)
        data, total = self._read_handle(handle, offset=offset, limit=limit)
        consumed = offset + len(data)
        truncated = consumed < total
        self.update_manifest(session_id)
        return WorkspaceRead(
            data=data,
            total_bytes=total,
            offset=offset,
            truncated=truncated,
            next_offset=consumed if truncated else None,
        )

    @staticmethod
    def _list_anchor_names(anchor: int) -> list[str]:
        if os.name == "nt":
            path = _win_final_path(anchor)
            with os.scandir(path) as entries:
                return sorted(entry.name for entry in entries)
        return sorted(os.listdir(anchor))

    @staticmethod
    def _copy_regular_at(
        source_parent: int,
        destination_parent: int,
        name: str,
    ) -> tuple[int, str]:
        source_handle = WorkspaceManager._open_file_at(source_parent, name)
        source_fd = WorkspaceManager._fd_from_handle(source_handle, os.O_RDONLY)
        destination_fd = -1
        try:
            source_stat = os.fstat(source_fd)
            if not stat.S_ISREG(source_stat.st_mode):
                raise ValueError(
                    f"workspace migration refuses non-regular file: {name!r}"
                )
            destination_handle = WorkspaceManager._open_file_at(
                destination_parent,
                name,
                write=True,
                exclusive=True,
                mode=source_stat.st_mode & 0o777,
            )
            destination_fd = WorkspaceManager._fd_from_handle(
                destination_handle,
                os.O_WRONLY,
            )
            digest = hashlib.sha256()
            total = 0
            while True:
                chunk = os.read(source_fd, 1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
                total += len(chunk)
                view = memoryview(chunk)
                while view:
                    written = os.write(destination_fd, view)
                    view = view[written:]
            os.fsync(destination_fd)
            if os.name != "nt":
                with suppress(OSError):
                    os.fchmod(destination_fd, source_stat.st_mode & 0o777)
            return total, digest.hexdigest()
        finally:
            os.close(source_fd)
            if destination_fd >= 0:
                os.close(destination_fd)

    @classmethod
    def _copy_anchor_tree(
        cls,
        source: int,
        destination: int,
        *,
        prefix: str = "",
    ) -> tuple[int, int, dict[str, str]]:
        count = 0
        total = 0
        digests: dict[str, str] = {}
        for name in cls._list_anchor_names(source):
            relative = f"{prefix}/{name}" if prefix else name
            source_child = 0
            try:
                source_child = cls._open_directory_at(source, name)
            except NotADirectoryError:
                size, digest = cls._copy_regular_at(source, destination, name)
                count += 1
                total += size
                digests[relative] = digest
                continue
            destination_child = 0
            try:
                destination_child = cls._open_directory_at(
                    destination,
                    name,
                    create=True,
                    exclusive=True,
                    mode=0o700,
                )
                child_count, child_total, child_digests = cls._copy_anchor_tree(
                    source_child,
                    destination_child,
                    prefix=relative,
                )
                count += child_count
                total += child_total
                digests.update(child_digests)
                if os.name != "nt":
                    os.fsync(destination_child)
            finally:
                if destination_child:
                    cls._close_anchor(destination_child)
                cls._close_anchor(source_child)
        return count, total, digests

    @classmethod
    def _inventory_anchor(
        cls,
        anchor: int,
        *,
        prefix: str = "",
    ) -> tuple[int, int, dict[str, str]]:
        count = 0
        total = 0
        digests: dict[str, str] = {}
        for name in cls._list_anchor_names(anchor):
            relative = f"{prefix}/{name}" if prefix else name
            child = 0
            try:
                child = cls._open_directory_at(anchor, name)
            except NotADirectoryError:
                handle = cls._open_file_at(anchor, name)
                descriptor = cls._fd_from_handle(handle, os.O_RDONLY)
                try:
                    details = os.fstat(descriptor)
                    if not stat.S_ISREG(details.st_mode):
                        raise ValueError(
                            "workspace migration refuses non-regular entry: "
                            f"{relative}"
                        )
                    digest = hashlib.sha256()
                    while True:
                        chunk = os.read(descriptor, 1024 * 1024)
                        if not chunk:
                            break
                        digest.update(chunk)
                finally:
                    os.close(descriptor)
                count += 1
                total += int(details.st_size)
                digests[relative] = digest.hexdigest()
                continue
            try:
                child_count, child_total, child_digests = cls._inventory_anchor(
                    child,
                    prefix=relative,
                )
                count += child_count
                total += child_total
                digests.update(child_digests)
            finally:
                cls._close_anchor(child)
        return count, total, digests

    @classmethod
    def _remove_open_tree(cls, parent: int, name: str, directory: int) -> None:
        expected = os.fstat(directory) if os.name != "nt" else None
        for child_name in cls._list_anchor_names(directory):
            try:
                child = cls._open_directory_at(
                    directory,
                    child_name,
                    delete=os.name == "nt",
                )
            except NotADirectoryError:
                if os.name == "nt":
                    _win_delete_at(directory, child_name, directory=False)
                else:
                    os.unlink(child_name, dir_fd=directory)
            else:
                try:
                    cls._remove_open_tree(directory, child_name, child)
                finally:
                    cls._close_anchor(child)
        if os.name == "nt":
            _win_mark_delete(directory)
            return
        current = os.stat(name, dir_fd=parent, follow_symlinks=False)
        if (
            expected is None
            or not stat.S_ISDIR(current.st_mode)
            or current.st_dev != expected.st_dev
            or current.st_ino != expected.st_ino
        ):
            raise RuntimeError(
                f"workspace directory changed during deletion: {name!r}"
            )
        os.rmdir(name, dir_fd=parent)

    @classmethod
    def _remove_tree_at(cls, parent: int, name: str) -> None:
        directory = cls._open_directory_at(
            parent,
            name,
            delete=os.name == "nt",
        )
        try:
            cls._remove_open_tree(parent, name, directory)
        finally:
            cls._close_anchor(directory)

    def _session_usage(self, path: Path) -> tuple[int, int]:
        count = 0
        total = 0
        for directory, dirnames, filenames in os.walk(path, followlinks=False):
            base = Path(directory)
            dirnames[:] = [
                name
                for name in dirnames
                if not _is_reparse_or_symlink(base / name)
            ]
            for name in filenames:
                candidate = base / name
                try:
                    if _is_reparse_or_symlink(candidate) or not candidate.is_file():
                        continue
                    size = candidate.stat().st_size
                except OSError:
                    continue
                count += 1
                total += size
        return count, total

    def list_sessions(
        self,
        *,
        active_session: str = "",
        active_running: bool = False,
        running_jobs: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        sessions: list[dict[str, Any]] = []
        if not self.root.exists():
            return sessions
        job_sessions = running_jobs or set()
        for entry in sorted(self.root.iterdir(), key=lambda item: item.name):
            if not entry.is_dir() or not SESSION_ID_RE.fullmatch(entry.name):
                continue
            manifest = self.read_manifest(entry.name)
            file_count, total_bytes = self._session_usage(entry)
            owned = manifest is not None
            pinned = bool(manifest and manifest.get("pinned"))
            manifest_active = bool(manifest and manifest.get("state") == "active")
            active = (entry.name == active_session and active_running) or manifest_active
            created = (
                manifest.get("created_at")
                if manifest
                else datetime.fromtimestamp(entry.stat().st_ctime, UTC).isoformat()
            )
            last_used = (
                manifest.get("last_used_at")
                if manifest
                else datetime.fromtimestamp(entry.stat().st_mtime, UTC).isoformat()
            )
            sessions.append(
                {
                    "session_id": entry.name,
                    "is_active": active,
                    "file_count": file_count,
                    "total_size_mb": round(total_bytes / (1024 * 1024), 2),
                    "path": str(entry),
                    "total_bytes": total_bytes,
                    "created_at": created,
                    "last_used_at": last_used,
                    "state": "active" if active else (
                        str(manifest.get("state", "inactive")) if manifest else "legacy"
                    ),
                    "generation": int(manifest.get("generation", 0)) if manifest else 0,
                    "pinned": pinned,
                    "owned": owned,
                    "retention_eligible": bool(
                        owned
                        and not active
                        and not manifest_active
                        and not pinned
                        and entry.name not in job_sessions
                    ),
                }
            )
        return sessions

    def cleanup_empty_owned(self, *, active_session: str = "") -> list[str]:
        removed: list[str] = []
        for session in self.list_sessions(active_session=active_session):
            if (
                session["session_id"] == active_session
                or session["state"] == "active"
                or not session["owned"]
                or session["pinned"]
            ):
                continue
            session_id = session["session_id"]
            root_anchor = self._open_root_anchor()
            directory = 0
            try:
                directory = self._open_directory_at(
                    root_anchor,
                    session_id,
                    delete=os.name == "nt",
                )
                manifest = self._read_manifest_from_anchor(directory, session_id)
                if (
                    manifest is None
                    or manifest.get("state") == "active"
                    or manifest.get("pinned")
                ):
                    continue
                if any(
                    name != MANIFEST_NAME
                    for name in self._list_anchor_names(directory)
                ):
                    continue
                self._remove_open_tree(root_anchor, session_id, directory)
                removed.append(session_id)
            except (FileNotFoundError, OSError, ValueError):
                continue
            finally:
                if directory:
                    self._close_anchor(directory)
                self._close_anchor(root_anchor)
        return removed

    def prune(
        self,
        *,
        older_than_days: int = 0,
        max_sessions: int = 0,
        max_bytes: int = 0,
        apply: bool = False,
        active_session: str = "",
        running_jobs: set[str] | None = None,
    ) -> dict[str, Any]:
        sessions = self.list_sessions(
            active_session=active_session,
            active_running=bool(active_session),
            running_jobs=running_jobs,
        )
        eligible = [item for item in sessions if item["retention_eligible"]]
        eligible.sort(
            key=lambda item: _parse_timestamp(item["last_used_at"])
            or datetime.min.replace(tzinfo=UTC)
        )
        selected: dict[str, str] = {}
        now = datetime.now(UTC)
        if older_than_days > 0:
            cutoff = now - timedelta(days=older_than_days)
            for item in eligible:
                last_used = _parse_timestamp(item["last_used_at"])
                if last_used is not None and last_used < cutoff:
                    selected[item["session_id"]] = "age"

        remaining = [item for item in sessions if item["session_id"] not in selected]
        if max_sessions > 0 and len(remaining) > max_sessions:
            excess = len(remaining) - max_sessions
            for item in eligible:
                if excess <= 0:
                    break
                if item["session_id"] in selected:
                    continue
                selected[item["session_id"]] = "session_limit"
                excess -= 1

        if max_bytes > 0:
            remaining_bytes = sum(
                item["total_bytes"]
                for item in sessions
                if item["session_id"] not in selected
            )
            for item in eligible:
                if remaining_bytes <= max_bytes:
                    break
                if item["session_id"] in selected:
                    continue
                selected[item["session_id"]] = "byte_limit"
                remaining_bytes -= item["total_bytes"]

        removed: list[str] = []
        errors: dict[str, str] = {}
        if apply:
            for session_id in selected:
                root_anchor = self._open_root_anchor()
                directory = 0
                try:
                    directory = self._open_directory_at(
                        root_anchor,
                        session_id,
                        delete=os.name == "nt",
                    )
                    manifest = self._read_manifest_from_anchor(directory, session_id)
                    if manifest is None:
                        errors[session_id] = (
                            "ownership manifest is missing or invalid"
                        )
                        continue
                    if (
                        manifest.get("state") == "active"
                        or manifest.get("pinned")
                        or session_id in (running_jobs or set())
                    ):
                        errors[session_id] = (
                            "session became active, pinned, or job-protected"
                        )
                        continue
                    self._remove_open_tree(root_anchor, session_id, directory)
                    removed.append(session_id)
                except (OSError, ValueError, RuntimeError) as exc:
                    errors[session_id] = str(exc)
                finally:
                    if directory:
                        self._close_anchor(directory)
                    self._close_anchor(root_anchor)
        return {
            "apply": apply,
            "selected": [
                {"session_id": session_id, "reason": reason}
                for session_id, reason in selected.items()
            ],
            "removed": removed,
            "errors": errors,
            "preserved": len(sessions) - len(removed),
        }

    def migrate(self, destination: Path, *, delete_source: bool = False) -> dict[str, Any]:
        requested = Path(destination).expanduser()
        target_parent = requested.absolute().parent.resolve()
        target = target_parent / requested.name
        if target == self.root:
            return {
                "source": str(self.root),
                "destination": str(target),
                "migrated": False,
                "reason": "already_using_destination",
            }
        if target.is_symlink() or (
            target.exists()
            and (
                not target.is_dir()
                or _is_reparse_or_symlink(target)
                or any(target.iterdir())
            )
        ):
            raise ValueError(
                "migration destination must be an absent or empty real directory"
            )
        if self.root == Path(self.root.anchor) or target == Path(target.anchor):
            raise ValueError("workspace migration cannot use a filesystem root")
        try:
            target.relative_to(self.root)
        except ValueError:
            pass
        else:
            raise ValueError("migration destination cannot be inside the source")

        target_parent.mkdir(parents=True, exist_ok=True)
        staging_name = f".{target.name}.hercules-migrate-{uuid.uuid4().hex}"
        parent_anchor = (
            _win_open_root(target_parent)
            if os.name == "nt"
            else os.open(
                target_parent,
                os.O_RDONLY
                | os.O_DIRECTORY
                | os.O_CLOEXEC
                | getattr(os, "O_NOFOLLOW", 0),
            )
        )
        source_anchor = self._open_root_anchor()
        staging_anchor = 0
        migrated = False
        try:
            staging_anchor = self._open_directory_at(
                parent_anchor,
                staging_name,
                create=True,
                exclusive=True,
                delete=os.name == "nt",
                mode=0o700,
            )
            source_inventory = self._copy_anchor_tree(
                source_anchor,
                staging_anchor,
            )
            target_inventory = self._inventory_anchor(staging_anchor)
            if source_inventory != target_inventory:
                raise RuntimeError("workspace migration verification failed")
            if target.exists():
                existing = self._open_directory_at(parent_anchor, target.name)
                try:
                    if self._list_anchor_names(existing):
                        raise ValueError(
                            "migration destination became non-empty during copy"
                        )
                finally:
                    self._close_anchor(existing)
                self._remove_tree_at(parent_anchor, target.name)
            if os.name == "nt":
                _win_rename_at(staging_anchor, parent_anchor, target.name)
            else:
                os.replace(
                    staging_name,
                    target.name,
                    src_dir_fd=parent_anchor,
                    dst_dir_fd=parent_anchor,
                )
                os.fsync(parent_anchor)
            migrated = True
        finally:
            if staging_anchor:
                self._close_anchor(staging_anchor)
            self._close_anchor(source_anchor)
            if not migrated:
                with suppress(OSError, ValueError):
                    self._remove_tree_at(parent_anchor, staging_name)
            self._close_anchor(parent_anchor)

        source_deleted = False
        source_delete_error = ""
        if delete_source:
            source_parent = self.root.parent
            source_parent_anchor = (
                _win_open_root(source_parent)
                if os.name == "nt"
                else os.open(
                    source_parent,
                    os.O_RDONLY
                    | os.O_DIRECTORY
                    | os.O_CLOEXEC
                    | getattr(os, "O_NOFOLLOW", 0),
                )
            )
            try:
                self._remove_tree_at(source_parent_anchor, self.root.name)
                source_deleted = True
            except (OSError, ValueError) as exc:
                source_delete_error = str(exc)
            finally:
                self._close_anchor(source_parent_anchor)
        return {
            "source": str(self.root),
            "destination": str(target),
            "migrated": True,
            "source_deleted": source_deleted,
            "source_delete_error": source_delete_error,
            "files": source_inventory[0],
            "bytes": source_inventory[1],
        }
