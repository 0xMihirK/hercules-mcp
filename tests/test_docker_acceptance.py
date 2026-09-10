from __future__ import annotations

import asyncio
import os
import socket
import sys
import threading
from pathlib import Path

import pytest
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

import docker
from hercules.core.tool_catalog import ALL_CAPABILITIES, format_capabilities

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUN_ACCEPTANCE = os.getenv("HERCULES_RUN_DOCKER_ACCEPTANCE") == "1"


@pytest.fixture
def console_windows():
    """Observe Windows console show events across real start/stop cycles."""
    if os.name != "nt":
        yield
        return

    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    callback_type = ctypes.WINFUNCTYPE(
        None, wintypes.HANDLE, wintypes.DWORD, wintypes.HWND,
        wintypes.LONG, wintypes.LONG, wintypes.DWORD, wintypes.DWORD,
    )
    user32.SetWinEventHook.argtypes = [
        wintypes.DWORD, wintypes.DWORD, wintypes.HMODULE, callback_type,
        wintypes.DWORD, wintypes.DWORD, wintypes.DWORD,
    ]
    user32.SetWinEventHook.restype = wintypes.HANDLE
    user32.UnhookWinEvent.argtypes = [wintypes.HANDLE]
    user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.PeekMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT, wintypes.UINT]
    user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
    user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
    user32.DispatchMessageW.restype = ctypes.c_ssize_t
    ready, stop = threading.Event(), threading.Event()
    shown, errors = [], []

    def watch():
        @callback_type
        def on_show(_hook, _event, window, object_id, child_id, _thread, _time):
            if object_id or child_id:
                return
            name = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(window, name, len(name))
            if name.value in {"ConsoleWindowClass", "CASCADIA_HOSTING_WINDOW_CLASS"}:
                pid = wintypes.DWORD()
                user32.GetWindowThreadProcessId(window, ctypes.byref(pid))
                shown.append((pid.value, name.value))

        # EVENT_OBJECT_SHOW, out-of-context delivery on this thread's queue.
        hook = user32.SetWinEventHook(0x8002, 0x8002, None, on_show, 0, 0, 0)
        if not hook:
            errors.append(str(ctypes.WinError(ctypes.get_last_error())))
        ready.set()
        if not hook:
            return
        try:
            message = wintypes.MSG()
            while not stop.wait(0.01):
                while user32.PeekMessageW(ctypes.byref(message), None, 0, 0, 1):
                    user32.TranslateMessage(ctypes.byref(message))
                    user32.DispatchMessageW(ctypes.byref(message))
        finally:
            user32.UnhookWinEvent(hook)

    watcher = threading.Thread(target=watch, daemon=True)
    watcher.start()
    try:
        assert ready.wait(5) and not errors, errors
        yield
    finally:
        stop.set()
        watcher.join(timeout=5)
    assert not watcher.is_alive()
    assert not shown, f"Console windows appeared during lifecycle smoke test (PID, class): {shown}"


def _transport(workspace_root: Path) -> StdioTransport:
    return StdioTransport(
        sys.executable,
        ["-m", "hercules.main"],
        cwd=str(PROJECT_ROOT),
        env={
            **os.environ,
            "ALLOWED_TARGETS": "127.0.0.1",
            "HERCULES_INSTALLED_CAPABILITIES": format_capabilities(
                ALL_CAPABILITIES
            ),
            "HERCULES_WORKSPACE_ROOT": str(workspace_root),
            "HERCULES_DISABLED_TOOLS": "",
            "SKIP_METASPLOIT": "false",
            "PRESERVE_CONTAINER": "false",
            "WATCHDOG_INTERVAL": "0",
        },
    )


def _project_containers() -> dict[str, str]:
    client = docker.from_env()
    try:
        containers = client.containers.list(
            all=True,
            filters={
                "label": [
                    "hercules.managed=true",
                    f"hercules.project_root={PROJECT_ROOT}",
                ]
            },
        )
        return {container.id: container.status for container in containers}
    finally:
        client.close()


def _exact_container(session_id: str):
    client = docker.from_env()
    try:
        container = client.containers.get(f"hercules-{session_id}")
        container.reload()
        labels = container.attrs.get("Config", {}).get("Labels", {}) or {}
        assert labels.get("hercules.managed") == "true"
        assert labels.get("hercules.session_id") == session_id
        assert labels.get("hercules.project_root") == str(PROJECT_ROOT)
        return container.id, container.status
    finally:
        client.close()


def _remove_exact_test_containers(session_ids: set[str]) -> None:
    client = docker.from_env()
    try:
        for session_id in session_ids:
            try:
                container = client.containers.get(f"hercules-{session_id}")
            except docker.errors.NotFound:
                continue
            container.reload()
            labels = container.attrs.get("Config", {}).get("Labels", {}) or {}
            if (
                labels.get("hercules.managed") == "true"
                and labels.get("hercules.session_id") == session_id
                and labels.get("hercules.project_root") == str(PROJECT_ROOT)
            ):
                container.remove(force=True)
    finally:
        client.close()


def _assert_ports_released(network_info: dict) -> None:
    effective = network_info["port_allocation"]["effective"]
    ports = [effective["metasploit_rpc"], *effective["listeners"]]
    if effective["browser_stream"]:
        ports.append(effective["browser_stream"])
    for port in ports:
        with socket.socket() as probe:
            if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            probe.bind(("127.0.0.1", int(port)))


@pytest.mark.skipif(
    not RUN_ACCEPTANCE,
    reason="set HERCULES_RUN_DOCKER_ACCEPTANCE=1 for the real Docker test",
)
def test_real_stdio_explicit_container_lifecycle(tmp_path: Path, console_windows) -> None:
    """Exercise cold, running, stopped, resumed, and fresh-session states."""
    initial_containers = _project_containers()
    test_sessions: set[str] = set()

    async def scenario() -> None:
        async with Client(_transport(tmp_path)) as client:
            tools = await client.list_tools()
            resources = await client.list_resources()
            assert (len(tools), len(resources)) == (46, 7)
            assert _project_containers() == initial_containers

            cold = await client.call_tool(
                "shell_exec",
                {"command": "true"},
                raise_on_error=False,
            )
            assert cold.structured_content["error_type"] == "runtime_not_started"

            started = (
                await client.call_tool("system_start_container")
            ).structured_content
            assert started["status"] == "success"
            assert started["container_running"] is True
            assert started["start_mode"] == "created"
            session_id = started["session_id"]
            test_sessions.add(session_id)
            container_id, status = _exact_container(session_id)
            assert status == "running"
            assert set(_project_containers()) == {
                *initial_containers,
                container_id,
            }

            repeated = (
                await client.call_tool("system_start_container")
            ).structured_content
            assert repeated["status"] == "success"
            assert repeated["session_id"] == session_id
            assert repeated["start_mode"] == "already_running"
            assert _exact_container(session_id)[0] == container_id

            # Force a crash of only this verification container. With the
            # watchdog disabled, the next MCP call must perform lazy recovery.
            docker_client = docker.from_env()
            try:
                docker_client.containers.get(container_id).kill()
            finally:
                docker_client.close()

            command = (
                await client.call_tool(
                    "shell_exec",
                    {"command": "printf hercules-local-ok"},
                )
            ).structured_content
            assert command["exit_code"] == 0
            assert command["stdout"] == "hercules-local-ok"
            assert _exact_container(session_id) == (container_id, "running")

            fixture = (
                await client.call_tool(
                    "shell_exec",
                    {
                        "command": (
                            "mkdir -p /opt/workspace/browser-fixture && "
                            "printf '%s' '<!doctype html><title>Hercules local "
                            "fixture</title><h1>local-only</h1>' > "
                            "/opt/workspace/browser-fixture/index.html"
                        )
                    },
                )
            ).structured_content
            assert fixture["exit_code"] == 0
            background = (
                await client.call_tool(
                    "shell_exec_background",
                    {
                        "command": (
                            "python3 -m http.server 18080 --bind 127.0.0.1 "
                            "--directory /opt/workspace/browser-fixture"
                        ),
                        "job_id": "local-browser-fixture",
                    },
                )
            ).structured_content
            assert background["job_id"] == "local-browser-fixture"
            ready = (
                await client.call_tool(
                    "shell_exec",
                    {
                        "command": (
                            "for i in $(seq 1 30); do "
                            "curl -fsS http://127.0.0.1:18080 >/dev/null && exit 0; "
                            "sleep 1; done; exit 1"
                        ),
                        "timeout": 40,
                    },
                )
            ).structured_content
            assert ready["exit_code"] == 0
            opened = (
                await client.call_tool(
                    "browser_open",
                    {"url": "http://127.0.0.1:18080", "session": "acceptance"},
                )
            ).structured_content
            assert opened["exit_code"] == 0
            title = (
                await client.call_tool(
                    "browser_read",
                    {"what": "title", "session": "acceptance"},
                )
            ).structured_content
            assert title["exit_code"] == 0
            assert "Hercules local fixture" in str(title)

            network_info = (
                await client.call_tool("system_network_info")
            ).structured_content
            assert network_info["network_mode"] in {"bridge", "host"}
            assert network_info["container_ips"]

            # A second cold MCP process gets schemas and a workspace but must
            # neither create a container nor disturb this live exact-owned one.
            before_second = _project_containers()
            async with Client(_transport(tmp_path)) as second:
                assert len(await second.list_tools()) == 46
                second_cold = await second.call_tool(
                    "shell_exec",
                    {"command": "true"},
                    raise_on_error=False,
                )
                assert (
                    second_cold.structured_content["error_type"]
                    == "runtime_not_started"
                )
                assert _project_containers() == before_second
                assert _exact_container(session_id) == (container_id, "running")

            stopped = (
                await client.call_tool("system_stop_container")
            ).structured_content
            assert stopped["status"] == "success"
            assert container_id not in _project_containers()
            _assert_ports_released(network_info)
            after_stop = await client.call_tool(
                "shell_exec",
                {"command": "true"},
                raise_on_error=False,
            )
            assert after_stop.structured_content["error_type"] == "runtime_not_started"

            resumed = (
                await client.call_tool("system_start_container")
            ).structured_content
            assert resumed["status"] == "success"
            assert resumed["session_id"] == session_id
            resumed_id, resumed_status = _exact_container(session_id)
            assert resumed_status == "running"
            assert resumed_id != container_id
            assert (
                await client.call_tool("system_stop_container")
            ).structured_content["status"] == "success"

            rotated = (
                await client.call_tool("system_start_new_session")
            ).structured_content
            assert rotated["status"] == "success"
            assert rotated["container_running"] is False
            assert rotated["old_session_id"] == session_id
            fresh_session = rotated["new_session_id"]
            test_sessions.add(fresh_session)
            assert fresh_session != session_id
            assert _project_containers() == initial_containers
            fresh_cold = await client.call_tool(
                "shell_exec",
                {"command": "true"},
                raise_on_error=False,
            )
            assert fresh_cold.structured_content["error_type"] == "runtime_not_started"

            fresh_started = (
                await client.call_tool("system_start_container")
            ).structured_content
            assert fresh_started["status"] == "success"
            assert fresh_started["session_id"] == fresh_session
            assert _exact_container(fresh_session)[1] == "running"
            assert (
                await client.call_tool("system_stop_container")
            ).structured_content["status"] == "success"
            assert _project_containers() == initial_containers

    try:
        asyncio.run(scenario())
    finally:
        _remove_exact_test_containers(test_sessions)
