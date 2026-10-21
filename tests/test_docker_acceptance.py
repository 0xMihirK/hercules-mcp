from __future__ import annotations

import asyncio
import os
import signal
import socket
import subprocess
import sys
import threading
from pathlib import Path

import pytest
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

import docker
from hercules.core.tool_catalog import ALL_CAPABILITIES, format_capabilities
from hercules.core.workspace import WorkspaceManager

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUN_ACCEPTANCE = os.getenv("HERCULES_RUN_DOCKER_ACCEPTANCE") == "1"


@pytest.fixture
def cached_runtime():
    from hercules.core.setup_info import setup_information
    from hercules.setup.runtime import assets_ready, image_status

    state = image_status(setup_information(PROJECT_ROOT, capabilities="all"))
    if state != "ready":
        pytest.fail(f"Docker/Windows release acceptance blocked: matching image is {state}")
    if not assets_ready(PROJECT_ROOT / "wordlists", list(ALL_CAPABILITIES)):
        pytest.fail("Docker release acceptance blocked: verified assets unavailable")


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
    workspace_root.mkdir(parents=True, exist_ok=True)
    (workspace_root / "local-verification.env").touch(exist_ok=True)
    return StdioTransport(
        sys.executable,
        ["-m", "hercules.main"],
        cwd=str(PROJECT_ROOT),
        env={
            **os.environ,
            "HERCULES_ENV_FILE": str(workspace_root / "local-verification.env"),
            "MSF_PASSWORD": "hercules-local-verification-only",
            "BROWSER_PROXY_URL": "",
            "BROWSER_PROXY": "",
            "BROWSER_LOCALE": "",
            "BROWSER_TIMEZONE": "",
            "HERCULES_DOCKER_NETWORK": "host",
            "HERCULES_LISTENER_BIND_HOST": "127.0.0.1",
            "USE_PRIVILEGED": "false",
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
            # The guardian may remove a listed container before SDK inspection.
            ignore_removed=True,
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
def test_real_stdio_explicit_container_lifecycle(tmp_path: Path, cached_runtime, console_windows) -> None:
    """Exercise cold, running, stopped, resumed, and fresh-session states."""
    initial_containers = _project_containers()
    test_sessions: set[str] = set()

    async def scenario() -> None:
        async with Client(_transport(tmp_path)) as client:
            tools = await client.list_tools()
            resources = await client.list_resources()
            assert (len(tools), len(resources)) == (47, 7)
            assert _project_containers() == initial_containers

            inventory = (await client.call_tool("system_list_sessions")).structured_content
            cold_session = inventory["session_id"]
            manager = WorkspaceManager(tmp_path)
            source = tmp_path / "local-handout.bin"
            source.write_bytes(b"\x00\xfflocal-evidence")
            manager.transfer(cold_session, "challenge/handout.bin", source, direction="import")
            offline = (await client.call_tool("workspace_inspect", {
                "action": "read", "path": "challenge/handout.bin", "encoding": "base64",
            })).structured_content
            assert offline["status"] == "success" and not offline["container_accessible"]
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

            custom = (await client.call_tool("shell_exec", {"command": (
                "trap 'find /opt/workspace/challenge/.venv -type l -delete' EXIT; "
                "python3 -m venv --copies /opt/workspace/challenge/.venv && "
                "/opt/workspace/challenge/.venv/bin/python -m pip --version && "
                "printf '%s\\n' 'from pathlib import Path' "
                "'assert Path(\"/opt/workspace/challenge/handout.bin\").read_bytes() == bytes([0,255])+b\"local-evidence\"' "
                "'Path(\"/opt/workspace/challenge/result.txt\").write_text(\"custom-tool-ok\")' "
                "> /opt/workspace/challenge/custom.py && "
                "/opt/workspace/challenge/.venv/bin/python /opt/workspace/challenge/custom.py"
            ), "timeout": 300})).structured_content
            assert custom["exit_code"] == 0
            exported = tmp_path / "local-result.txt"
            manager.transfer(session_id, "challenge/result.txt", exported, direction="export")
            assert exported.read_text() == "custom-tool-ok"

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
            assert opened.get("exit_code") == 0, opened
            title = (
                await client.call_tool(
                    "browser_read",
                    {"what": "title", "session": "acceptance"},
                )
            ).structured_content
            assert title.get("exit_code") == 0, title

            network_info = (
                await client.call_tool("system_network_info")
            ).structured_content
            assert network_info["network_mode"] == "host"
            assert network_info["container_ips"]

            # A second cold MCP process gets schemas and a workspace but must
            # neither create a container nor disturb this live exact-owned one.
            before_second = _project_containers()
            async with Client(_transport(tmp_path)) as second:
                assert len(await second.list_tools()) == 47
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
            assert stopped["cleanup"]["confirmed"] is True
            assert container_id not in _project_containers()
            _assert_ports_released(network_info)
            retained = (await client.call_tool("workspace_inspect", {
                "action": "read", "path": "challenge/result.txt",
            })).structured_content
            assert retained["content"] == "custom-tool-ok" and not retained["container_accessible"]
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
            reused_venv = (await client.call_tool("shell_exec", {
                "command": "/opt/workspace/challenge/.venv/bin/python /opt/workspace/challenge/custom.py && cat /opt/workspace/challenge/result.txt",
            })).structured_content
            assert reused_venv["exit_code"] == 0 and "custom-tool-ok" in reused_venv["stdout"]
            # Linux venv lib64 links become inaccessible reparse points on a
            # Windows bind mount. Remove only this disposable fixture's links
            # after verifying reuse, so host pytest cleanup can settle.
            links = (await client.call_tool("shell_exec", {
                "command": "find /opt/workspace/challenge/.venv -type l -delete",
            })).structured_content
            assert links["exit_code"] == 0
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


@pytest.mark.skipif(not RUN_ACCEPTANCE, reason="Opt-in concurrent owner/preserved runtime checks")
def test_live_owners_concurrent_start_and_preserved_reattachment(tmp_path, cached_runtime, console_windows):
    sessions = set()
    initial = _project_containers()

    async def scenario():
        first_transport, second_transport = _transport(tmp_path), _transport(tmp_path)
        for transport in (first_transport, second_transport):
            transport.env.update(SKIP_METASPLOIT="true", HERCULES_INSTALLED_CAPABILITIES="shell,session,workspace,browser")
        second_transport.env["PRESERVE_CONTAINER"] = "true"
        async with Client(first_transport, timeout=180) as first, Client(second_transport, timeout=180) as other:
            async def open_browser(selected, suffix):
                job = (await selected.call_tool("shell_exec_background", {"command": "python3 -m http.server 18080 --bind 127.0.0.1 --directory /tmp", "job_id": "browser-fixture-"+suffix})).structured_content
                assert job.get("status") != "error", job
                ready = (await selected.call_tool("shell_exec", {"command": "for i in $(seq 1 20); do curl -fsS http://127.0.0.1:18080/ >/dev/null && exit 0; sleep 1; done; exit 1", "timeout": 30})).structured_content
                assert ready["exit_code"] == 0, ready
                opened = (await selected.call_tool("browser_open", {"url": "http://127.0.0.1:18080/", "session": "recovery-browser"})).structured_content
                assert opened.get("exit_code") == 0, opened
            second_started = (await other.call_tool("system_start_container")).structured_content
            assert second_started["status"] == "success", second_started
            sessions.add(second_started["session_id"])
            other_id, _ = _exact_container(second_started["session_id"])
            try:
                results = await asyncio.gather(*[first.call_tool("system_start_container") for _ in range(3)])
                starts = [result.structured_content for result in results]
                assert all(result["status"] == "success" for result in starts), starts
                session = starts[0]["session_id"]
                sessions.add(session)
                assert {result["session_id"] for result in starts} == {session}
                assert sorted(result["start_mode"] for result in starts) == ["already_running", "already_running", "created"]
                assert _exact_container(second_started["session_id"]) == (other_id, "running")
                first_id, _ = _exact_container(session)
                await open_browser(first, "crash-before")

                def crash_exact():
                    docker_client = docker.from_env(timeout=20)
                    try:
                        owned = docker_client.containers.get(first_id)
                        labels = owned.attrs.get("Config", {}).get("Labels") or {}
                        assert labels.get("hercules.managed") == "true"
                        assert labels.get("hercules.session_id") == session
                        assert labels.get("hercules.project_root") == str(PROJECT_ROOT)
                        owned.kill()
                    finally:
                        docker_client.close()

                await asyncio.to_thread(crash_exact)
                recovered = (await first.call_tool("shell_exec", {"command": "printf recovered-locally"})).structured_content
                # shell_exec's workspace-script write can recover before the
                # command runs; its result need not carry exec recovery metadata.
                assert recovered["exit_code"] == 0 and recovered["stdout"] == "recovered-locally", recovered
                assert _exact_container(session) == (first_id, "running")
                await open_browser(first, "crash-after")
                assert _exact_container(second_started["session_id"]) == (other_id, "running")
                assert (await first.call_tool("system_stop_container")).structured_content["cleanup"]["confirmed"]
                assert _exact_container(second_started["session_id"]) == (other_id, "running")
                await open_browser(other, "preserve-before")
                preserved = (await other.call_tool("system_stop_container")).structured_content
                assert preserved["cleanup"]["confirmed"], preserved
                assert _exact_container(second_started["session_id"]) == (other_id, "exited")
                resumed = (await other.call_tool("system_start_container")).structured_content
                assert resumed["status"] == "success", resumed
                assert _exact_container(second_started["session_id"]) == (other_id, "running")
                await open_browser(other, "preserve-after")
                assert (await first.call_tool("system_start_container")).structured_content["status"] == "success"
                assert (await other.call_tool("shell_exec", {"command": "printf live-owner-ok"})).structured_content["stdout"] == "live-owner-ok"
            finally:
                await first.call_tool("system_stop_container")
                await other.call_tool("system_stop_container")
    try:
        asyncio.run(scenario())
    finally:
        # The preserve fixture is intentionally stopped, then explicitly removed
        # by its exact test-owned identity; never leave a verification container.
        _remove_exact_test_containers(sessions)
    assert _project_containers() == initial


def _guardian_pids(container_id: str) -> list[int]:
    if os.name == "nt":
        result = subprocess.run([
            "powershell", "-NoProfile", "-Command",
            ("Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -like '*hercules.core.orphan_guardian*' "
             f"-and $_.CommandLine -like '*{container_id}*' }} | Select-Object -ExpandProperty ProcessId"),
        ], capture_output=True, text=True, check=True, timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW)
        return [int(value) for value in result.stdout.split()]
    result = subprocess.run(["ps", "-eo", "pid,args"], capture_output=True, text=True, check=True)
    return [int(line.split()[0]) for line in result.stdout.splitlines()
            if "hercules.core.orphan_guardian" in line and container_id in line]


@pytest.mark.skipif(not RUN_ACCEPTANCE, reason="Opt-in real partial-start cancellation cleanup")
def test_cancelled_real_start_releases_exact_owned_resources(tmp_path, cached_runtime, console_windows, monkeypatch):
    from hercules.core.config import HerculesConfig
    from hercules.core.docker_manager import DockerManager

    initial = _project_containers()
    sessions = set()
    async def scenario():
        manager = DockerManager(HerculesConfig(project_root=PROJECT_ROOT, workspace_root=tmp_path,
            installed_capabilities=frozenset({"shell", "session", "workspace"}),
            skip_metasploit=True, listener_ports=(), docker_network="host", watchdog_interval=0))
        sessions.add(manager.session_id)
        manager._workspace.atomic_write(manager.session_id, "retained.txt", b"cancelled-start-evidence", mode=0o600)
        entered = asyncio.Event()
        async def delayed_readiness():
            entered.set()
            await asyncio.Event().wait()
        monkeypatch.setattr(manager, "_mark_ready", delayed_readiness)
        task = asyncio.create_task(manager.operator_start())
        try:
            await asyncio.wait_for(entered.wait(), 90)
            container_id = manager._container.id
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert _project_containers() == initial
            assert manager._last_cleanup["confirmed"] is True
            assert not await asyncio.to_thread(_guardian_pids, container_id)
            assert (manager.workspace_path / "retained.txt").read_bytes() == b"cancelled-start-evidence"
        finally:
            if not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
            await manager.stop_container(force_remove=True, release_workspace=True)
            manager.cleanup_unused_workspace()
            if manager._client is not None:
                manager._client.close()
    try:
        asyncio.run(scenario())
    finally:
        _remove_exact_test_containers(sessions)


@pytest.mark.skipif(not RUN_ACCEPTANCE, reason="set HERCULES_RUN_DOCKER_ACCEPTANCE=1 for exact-owned Docker tests")
def test_force_terminated_stdio_owner_is_cleaned_by_guardian(tmp_path, cached_runtime, console_windows):
    from hercules.core.docker_manager import _process_start_token, _project_hash

    initial = _project_containers()
    sessions = set()

    async def scenario():
        async with Client(_transport(tmp_path)) as client:
            started = (await client.call_tool("system_start_container")).structured_content
            assert started["status"] == "success"
            session = started["session_id"]
            sessions.add(session)
            container_id, _ = _exact_container(session)
            # Keep the boundary/engine active when the owner is forcibly lost.
            fixture = (await client.call_tool("shell_exec_background", {
                "command": "python3 -m http.server 18080 --bind 127.0.0.1 --directory /tmp",
                "job_id": "forced-owner-browser-fixture",
            })).structured_content
            assert fixture.get("status") != "error", fixture
            ready = (await client.call_tool("shell_exec", {"command": "for i in $(seq 1 20); do curl -fsS http://127.0.0.1:18080/ >/dev/null && exit 0; sleep 1; done; exit 1", "timeout": 30})).structured_content
            assert ready["exit_code"] == 0, ready
            opened = (await client.call_tool("browser_open", {"url": "http://127.0.0.1:18080/", "session": "forced-owner"})).structured_content
            assert opened.get("exit_code") == 0, opened
            network = (await client.call_tool("system_network_info")).structured_content
            assert await asyncio.to_thread(_guardian_pids, container_id), "exact test guardian did not start"
            docker_client = docker.from_env()
            try:
                labels = docker_client.containers.get(container_id).attrs["Config"]["Labels"]
                assert labels["hercules.workspace_root_hash"] == _project_hash(tmp_path)
                pid = int(labels["hercules.owner_pid"])
                assert _process_start_token(pid) == labels["hercules.owner_start_token"]
                os.kill(pid, signal.SIGTERM if os.name == "nt" else signal.SIGKILL)
            finally:
                docker_client.close()
            for _ in range(150):
                if container_id not in _project_containers():
                    break
                await asyncio.sleep(0.2)
            assert _project_containers() == initial
            _assert_ports_released(network)
            for _ in range(30):
                if not await asyncio.to_thread(_guardian_pids, container_id):
                    break
                await asyncio.sleep(0.2)
            assert not await asyncio.to_thread(_guardian_pids, container_id)

    try:
        asyncio.run(scenario())
    finally:
        _remove_exact_test_containers(sessions)
