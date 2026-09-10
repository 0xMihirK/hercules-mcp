from __future__ import annotations

import asyncio
import sys
import threading
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import anyio
import pytest
from docker.errors import NotFound
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

from hercules.core import docker_manager as docker_module
from hercules.core.config import HerculesConfig
from hercules.core.docker_manager import DockerManager


@pytest.fixture
def runtime(monkeypatch, tmp_path):
    """Run the real lifecycle against a fake Docker SDK and allocation lock."""
    manager = DockerManager(HerculesConfig(
        workspace_root=tmp_path / "workspace",
        wordlist_root=tmp_path / "wordlists",
        watchdog_interval=0,
    ))
    container = Mock(id="owned-container", short_id="owned", attrs={})
    container.exec_run.return_value = SimpleNamespace(
        exit_code=0, output=(b"local-ok", b""),
    )
    containers = {}

    def get(name):
        if name not in containers:
            raise NotFound(name)
        return containers[name]

    def create(**kwargs):
        container.attrs = {
            "Config": {"Labels": kwargs["labels"]},
            "State": {"Status": "running"},
        }
        containers[kwargs["name"]] = container
        return container

    def remove(**_kwargs):
        containers.pop(manager._container_name, None)

    container.remove.side_effect = remove
    container.start.side_effect = lambda: container.attrs["State"].update(
        Status="running"
    )
    container.stop.side_effect = lambda **kwargs: container.attrs["State"].update(
        Status="exited"
    )
    api = Mock()
    api.exec_create.return_value = {"Id": "test-exec"}
    api.exec_start.side_effect = lambda *args, **kwargs: iter([(b"local-ok", b"")])
    api.exec_inspect.return_value = {"Running": False, "ExitCode": 0}
    client = SimpleNamespace(api=api, containers=Mock())
    client.containers.get.side_effect = get
    client.containers.run.side_effect = create
    lock = Mock(wraps=threading.Lock())
    monkeypatch.setattr(docker_module, "HerculesPortAllocationLock", lambda: lock)

    async def verify():
        manager._client = client

    manager._verify_setup = verify
    manager._ensure_wordlists = AsyncMock(return_value={})
    manager._cleanup_orphaned_containers = AsyncMock()
    manager._allocate_runtime_ports = AsyncMock()
    manager._wait_for_host_ports_available = AsyncMock()
    manager._wait_for_ready = AsyncMock()
    manager._start_orphan_guardian = Mock()
    manager._settle_orphan_guardian = AsyncMock()
    return SimpleNamespace(
        manager=manager, container=container, client=client,
        containers=containers, lock=lock,
    )


async def _cancel_when_blocked(action, entered, release, cancellation):
    async def interrupt(cancel):
        await asyncio.wait_for(entered.wait(), timeout=5)
        cancel()
        # Allow cancellation to reach the caller while its native operation
        # still runs; only then let the worker finish and publish its result.
        asyncio.get_running_loop().call_later(0.02, release.set)

    try:
        if cancellation == "request":
            with anyio.CancelScope() as scope:
                interrupter = asyncio.create_task(interrupt(scope.cancel))
                await action()
            assert scope.cancel_called
        else:
            operation = asyncio.create_task(action())
            interrupter = asyncio.create_task(interrupt(operation.cancel))
            with pytest.raises(asyncio.CancelledError):
                await operation
        await interrupter
    finally:
        release.set()


@pytest.mark.parametrize("cancellation", ["request", "task"])
@pytest.mark.parametrize("phase", ["lock", "create", "ready", "reattach"])
def test_cancelled_start_settles_workers_and_releases_resources(
    runtime, phase, cancellation,
):
    manager = runtime.manager

    async def scenario():
        entered = asyncio.Event()
        release = threading.Event()
        loop = asyncio.get_running_loop()

        def blocked(function):
            def run(*args, **kwargs):
                loop.call_soon_threadsafe(entered.set)
                assert release.wait(timeout=5)
                return function(*args, **kwargs)
            return run

        if phase == "lock":
            runtime.lock.acquire.side_effect = blocked(runtime.lock._mock_wraps.acquire)
        elif phase == "create":
            runtime.client.containers.run.side_effect = blocked(
                runtime.client.containers.run.side_effect
            )
        elif phase == "reattach":
            manager._config = replace(manager._config, preserve_container=True)
            await manager.operator_start()
            await manager.operator_stop()
            runtime.container.start.side_effect = blocked(
                runtime.container.start.side_effect
            )
        else:
            async def pending_readiness():
                entered.set()
                await asyncio.Future()
            manager._wait_for_ready.side_effect = pending_readiness

        session = manager.session_id
        await _cancel_when_blocked(
            manager.operator_start, entered, release, cancellation,
        )

        assert runtime.containers == {}
        assert manager.container_running is False
        assert manager._operator_stopped is True
        assert manager._shutting_down is False
        assert manager._host_port_bindings == {}
        assert manager.session_id == session
        assert manager._workspace.read_manifest(session) is not None
        assert not runtime.lock._mock_wraps.locked()
        assert runtime.container.remove.call_count == (0 if phase == "lock" else 1)
        manager._settle_orphan_guardian.assert_awaited()

        # Cancellation must leave both the manager and allocation lock reusable.
        manager._wait_for_ready.side_effect = None
        await manager.operator_start()
        await manager.operator_stop()
        if phase == "reattach":
            # Successful preserve-mode stop intentionally retains the container.
            manager._container = runtime.container
            await manager.stop_container(force_remove=True)
        assert runtime.containers == {}
        assert not runtime.lock._mock_wraps.locked()

    anyio.run(scenario)


@pytest.mark.parametrize("cancellation", ["request", "task"])
@pytest.mark.parametrize("phase", ["allocate", "claim", "stop"])
def test_cancelled_rotation_rolls_back_candidate_and_allows_restart(
    runtime, phase, cancellation,
):
    manager = runtime.manager

    async def scenario():
        await manager.operator_start()
        session = manager.session_id
        manager._workspace.atomic_write(session, "evidence.txt", b"keep me", mode=0o600)
        entered = asyncio.Event()
        release = threading.Event()
        loop = asyncio.get_running_loop()

        def blocked(function):
            def run(*args, **kwargs):
                loop.call_soon_threadsafe(entered.set)
                assert release.wait(timeout=5)
                return function(*args, **kwargs)
            return run

        if phase == "allocate":
            manager._workspace.allocate_session = blocked(manager._workspace.allocate_session)
        elif phase == "claim":
            manager._claim_workspace = blocked(manager._claim_workspace)
        else:
            runtime.container.remove.side_effect = blocked(runtime.container.remove.side_effect)

        await _cancel_when_blocked(
            manager.new_session, entered, release, cancellation,
        )

        assert manager.session_id == session
        assert manager._shutting_down is False
        assert [entry.name for entry in manager._workspace.root.iterdir()] == [session]
        assert (manager.workspace_path / "evidence.txt").read_bytes() == b"keep me"
        assert runtime.containers == {}
        await manager.operator_start()
        assert manager.container_running
        await manager.operator_stop()

    anyio.run(scenario)


def test_mcp_tool_recovers_an_active_container_without_watchdog(runtime, monkeypatch):
    monkeypatch.setenv("WATCHDOG_INTERVAL", "0")
    from hercules import main

    monkeypatch.setattr(main, "DockerManager", lambda *args, **kwargs: runtime.manager)

    async def scenario():
        async with Client(main.mcp) as client:
            await client.call_tool("system_start_container")
            session = runtime.manager.session_id
            runtime.container.attrs["State"]["Status"] = "exited"
            result = (await client.call_tool(
                "shell_exec", {"command": "printf local-ok"},
            )).structured_content
            assert result["exit_code"] == 0
            assert result["stdout"] == "local-ok"
            runtime.container.start.assert_called_once()
            assert runtime.manager.session_id == session
            await client.call_tool("system_stop_container")
            stopped = (await client.call_tool(
                "shell_exec", {"command": "true"}, raise_on_error=False,
            )).structured_content
            assert stopped["error_type"] == "runtime_not_started"
            runtime.container.start.assert_called_once()

    asyncio.run(scenario())


def test_core_profile_stdio_matches_setup_facts(monkeypatch, tmp_path):
    from hercules.core.setup_info import setup_information

    monkeypatch.setenv("HERCULES_INSTALLED_CAPABILITIES", "core")
    monkeypatch.setenv("HERCULES_DISABLED_TOOLS", "")
    facts = setup_information(Path(__file__).resolve().parents[1])
    transport = StdioTransport(
        command=sys.executable,
        args=["-m", "hercules.main"],
        cwd=str(Path(__file__).resolve().parents[1]),
        env={
            "HERCULES_INSTALLED_CAPABILITIES": "core",
            "HERCULES_DISABLED_TOOLS": "",
            "HERCULES_WORKSPACE_ROOT": str(tmp_path),
            "WATCHDOG_INTERVAL": "0",
        },
    )

    async def scenario():
        async with Client(transport) as client:
            tools = await client.list_tools()
            resources = await client.list_resources()
            assert {tool.name for tool in tools} == set(facts["mcp_surface"]["tool_names"])
            assert len(tools) == facts["mcp_surface"]["tools"] == 11
            assert len(resources) == facts["mcp_surface"]["resources"] == 7

    asyncio.run(scenario())


def test_sdk_streaming_preserves_bounded_output_and_artifacts(runtime):
    manager = runtime.manager
    manager._config = replace(manager._config, max_captured_output_bytes=64 * 1024)
    stdout = b"a" * (64 * 1024 + 1)
    stderr = b"diagnostic" * 7000
    runtime.client.api.exec_start.side_effect = lambda *args, **kwargs: iter([
        (stdout, stderr), (b"tail", None),
    ])

    async def scenario():
        await manager.operator_start()
        try:
            result = await manager.exec_command("local-fixture", clean_output=False)
            payload = result.to_dict()
            assert payload["exit_code"] == 0
            assert payload["stdout_bytes"] == len(stdout) + 4
            assert payload["stderr_bytes"] == len(stderr)
            assert payload["stdout_truncated"] and payload["stderr_truncated"]
            assert payload["evidence_complete"] is True
            assert await manager.read_file_bytes(payload["stdout_artifact"]) == stdout + b"tail"
            assert await manager.read_file(payload["stderr_artifact"]) == stderr.decode()
            chunk = await manager.read_file_chunk(payload["stdout_artifact"], offset=len(stdout), max_bytes=2)
            assert (chunk.data, chunk.total_bytes, chunk.next_offset) == (b"ta", len(stdout) + 4, len(stdout) + 2)
            runtime.client.api.exec_create.assert_called_once()
            runtime.client.api.exec_start.assert_called_once_with("test-exec", stream=True, demux=True)
            runtime.client.api.exec_inspect.assert_called_once_with("test-exec")
        finally:
            await manager.operator_stop()

    asyncio.run(scenario())


def test_sdk_timeout_terminates_process_group_and_keeps_partial_output(runtime):
    release = threading.Event()

    def stream(*args, **kwargs):
        yield b"partial", None
        assert release.wait(timeout=5)

    def control(command, **kwargs):
        if command[0] == "cat":
            return SimpleNamespace(exit_code=0, output=b"1234\n")
        if command[0] == "bash":
            assert "kill -STOP -- -1234" in command[2]
            assert "kill -KILL -- -1234" in command[2]
            release.set()
        return SimpleNamespace(exit_code=0, output=b"")

    runtime.client.api.exec_start.side_effect = stream
    runtime.container.exec_run.side_effect = control

    async def scenario():
        await runtime.manager.operator_start()
        try:
            result = await runtime.manager.exec_command("local-fixture", timeout=0.1, clean_output=False)
            payload = result.to_dict()
            assert payload["exit_code"] == -1
            assert payload["timed_out"] is payload["terminated"] is payload["partial_output"] is True
            assert payload["stdout"] == "partial"
            assert payload["timeout_seconds"] == 0.1
            assert release.is_set()
        finally:
            release.set()
            await runtime.manager.operator_stop()

    asyncio.run(scenario())


def test_generation_resets_cached_metasploit_client_and_session_state(runtime, monkeypatch):
    from hercules import main
    from hercules.tools.exploitation import metasploit_tool

    monkeypatch.setenv("WATCHDOG_INTERVAL", "0")
    monkeypatch.setattr(main, "DockerManager", lambda *args, **kwargs: runtime.manager)

    async def scenario():
        async with main.docker_lifespan(main.mcp) as context:
            state = context["msf_state"]
            assert state == {"client": None}
            await runtime.manager.operator_start()
            state["client"] = object()
            metasploit_tool._session_modes["1"] = "shell"
            metasploit_tool._session_shell_channels["1"] = "channel"
            metasploit_tool._session_locks["1"] = asyncio.Lock()
            metasploit_tool._module_cache["exploit"] = ["cached-module"]
            metasploit_tool._module_cache_time = 123
            await runtime.manager.new_session()
            assert state == {"client": None}
            assert metasploit_tool._session_modes == {}
            assert metasploit_tool._session_shell_channels == {}
            assert metasploit_tool._session_locks == {}
            assert metasploit_tool._module_cache == {}
            assert metasploit_tool._module_cache_time == 0
            assert runtime.manager.container_running is False

    asyncio.run(scenario())
