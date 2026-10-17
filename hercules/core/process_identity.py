"""Fail-closed host owner checks for workspace maintenance."""

import os


def owner_state(manifest: dict) -> str:
    """Return live, dead or unknown; absence of a successful probe is not death."""
    from hercules.core.docker_manager import _process_start_token

    pid = manifest.get("owner_pid")
    if pid is None:
        return "unknown" if manifest.get("state") == "active" else "dead"
    try:
        pid = int(pid)
    except (ValueError, TypeError):
        return "unknown"
    if pid <= 0:
        return "unknown"
    if os.name == "nt":
        if pid > 0xFFFFFFFF:
            return "unknown"
        import ctypes
        from ctypes import wintypes

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.GetExitCodeProcess.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(wintypes.DWORD),
        ]
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = kernel.OpenProcess(0x1000, False, pid)
        if not handle:
            return "dead" if ctypes.get_last_error() == 87 else "unknown"
        try:
            code = wintypes.DWORD()
            if not kernel.GetExitCodeProcess(handle, ctypes.byref(code)):
                return "unknown"
            if code.value != 259:
                return "dead"
        finally:
            kernel.CloseHandle(handle)
    else:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return "dead"
        except (OSError, OverflowError):
            return "unknown"
    expected = manifest.get("owner_start_token")
    actual = _process_start_token(pid)
    if not expected or not actual:
        return "unknown"
    return "live" if expected == actual else "dead"
