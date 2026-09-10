from __future__ import annotations

import asyncio
import hashlib
import json
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

from hercules.core.docker_manager import DockerManager, RuntimeNotStarted
from hercules.core.firewall import classify_exception
from hercules.core.workspace import WorkspaceManager

# Captured from origin/main at 2a016e6. Descriptions may evolve, but every
# pre-existing public tool name and input schema stays backward compatible.
_EXISTING_SCHEMA_SHA256 = {
    "browser_act": "ef208aeae7666b992a5d5997919f65e2b0587e2630ad80a585e55c42bc7896f3",
    "browser_cmd": "5ed148e6316e3c2526c9556b5e01272dd78d16e80043c2641125ee0a04b76fb5",
    "browser_eval": "f08cd40e57984e46d0a9b8d865288f51dfebe8d1ecab5e50cdaebeaf52909768",
    "browser_open": "085d28f97242b973d445591e3cb2d5ba68325e0916dc9cf86375e0af5239e327",
    "browser_read": "a0e96d887881a1c939f4738ec4855351433ee10d0df06239f9da6ae94a6a3ccd",
    "browser_screenshot": "fcf81452d9b8c1a44c3a9f438bed617b46fd5da3bbe5aa245d4f18e6b72354dc",
    "browser_session": "a0455ccb26f38527ba5a0ceedc4501e5bcef80d8603449628c48b8d7e4739c97",
    "browser_skill": "b0f6b0be1cf9216985d22bc316d9702ba054e7bf98b2e410e8e765a0d0355d53",
    "browser_snapshot": "b336c5ef5425ccbbb7aa2fdf173a6592d5af471494690ad8bf11b8bb61d86b01",
    "browser_wait": "a31ead9d840156375f8ebe893cae1bb449e2cc0a5575ad3a818f101fbc43b5d0",
    "bruteforce_hydra": "0ed056c3a04c345e663b72afed89ec329ddb2145830b625125e790dac2ab8966",
    "crack_john": "4ee805c4f6895d34a7e81adc1594e7d506b912835fa7031175f20289b6a6e240",
    "ctf_binwalk": "88d45ba5401510497ef3b4d9039d0ffddd1acf9aa19b190f0e25987ce8690e37",
    "ctf_steghide": "ecd93dfa4e7e11475ab0019e30da4a072d7592793c15efc75caed5f93c0fa034",
    "fuzz_dirs": "582896ff4f0b942463fd9eeb80602dfbfa30e8b8cfe9c1560fbac7fc23376e7d",
    "metasploit_generate_payload": "51ff55913b31a4cecf337fafe32bc20a3de292a08b6300eb80a2667f972d79b2",
    "metasploit_manage": "93ebc37b450f6e66d9897a2ac5a24bfc64eda9797a68302f7fab08d79f43eefa",
    "metasploit_run_module": "91203a45aba486ec47d8272aa7612406423782bede4d8f681f86b0f14c587752",
    "metasploit_search": "10798ac8d2df2a3150d204e10be2e4fb12cc89650fb68e3a6d3b4b38e1914e26",
    "metasploit_start_listener": "d5fbf0be6c9f58ea9256eefb5eda2dec0a67c2ea0ef1ab2ca2e379c5c5514b49",
    "ncat": "02e25048ccebf5ec76a57768ec22cd8dd2f0c9afbdd48178eaee244ddcf4d70a",
    "network_curl": "64db90836e2cc3e776e7aca78245bb90facfb345d5e41c0c60c4cd56674757ee",
    "network_hping3": "be94fa6f22a10e35c6b9515f513ccea15d262d89038fe86057dc6188cc11bf29",
    "nmap_run_nse_script": "458b5089f5e418dd67cbc751b2238314319ee72b8edf8c9ee9a0fbc7aca7384e",
    "nmap_scan": "41fa1345d6595817d49316a5b28b7ba6a05aff5db2b7067312e8ffef23bc9b99",
    "nmap_write_nse_script": "e261c05768c9441e57b2c0cc8abe8dcce6bee01b2044aa9993c397bc66e3bad7",
    "nuclei_run": "6aa72a2c5f4e374511597d2638240ca732bbbc1c64624a6d16242dad6ae748a6",
    "nuclei_write_template": "0863ca49d0670920e458e08df8a8547017f99b2f09b02375d0bdf10f53e24a7b",
    "recon_amass": "345219669c6f9e26488a35d257506a619269cff72844223b0f7ff17cc7f34f2f",
    "recon_dns": "5debb24feb3e86a11c456d77c4e1e0ebf92573b69f7c400cd4fef746adf5faba",
    "recon_whois": "7f8c6c0db0bc1c1ff14f78c20f97fb65e32467e95a01cf6f641682f7a454ee43",
    "searchsploit": "98755342ac72aeba88cb6be611dedbcd88947d8f6d4b471066fa31d912592f92",
    "shell_check_job": "1bd65c635a267fcc408f804027fef8bd601d3028cbc09dfbb2402dc0551b13f3",
    "shell_exec": "767bf4f90024f6099b3ca9c1493093b9f6272a0698a7ae52e0ce21785e70df88",
    "shell_exec_background": "e105148c70a772f0de5dd0124cdfa91f715e066688fa2f44ab6b4178c5ceef9b",
    "shell_kill_job": "4d4a2ddb4001b2f0910705808d05833701160435c552cc28ef5d6315b59e998d",
    "sqlmap_run": "e2fedd55a1c09241ae806197f76e2272b8f5eef1655c4a7039dbc80534df007e",
    "system_list_sessions": "99334726611ccf58a148b0814696bfa6fe08c1b2d027e946beccf5a74331c9aa",
    "system_network_info": "99334726611ccf58a148b0814696bfa6fe08c1b2d027e946beccf5a74331c9aa",
    "system_start_new_session": "99334726611ccf58a148b0814696bfa6fe08c1b2d027e946beccf5a74331c9aa",
    "system_stop_container": "99334726611ccf58a148b0814696bfa6fe08c1b2d027e946beccf5a74331c9aa",
    "web_scan": "6765a1bd39b121038a7ed1e966ac94a8a13fb3667338ae7bb20d13e00a37a939",
    "web_vuln_scan": "137b5698816f8fb9f3adce94470558e346497dbe3c9b72c1d1404f30dabe1694",
    "workspace_read_file": "025278b96c3096a9e9dfd024b36c997af8f6af095d885f5c4951cfd9c8b22384",
    "workspace_write_file": "337991700aa9955f972eeede78627d7316400909f609fb0e3954a8514e71b85e",
}


def _manager() -> DockerManager:
    manager = object.__new__(DockerManager)
    manager._recovery_lock = None
    manager._operator_stopped = True
    manager._shutting_down = False
    manager._container = None
    manager._client = None
    manager._session_id = "aaaaaaaa"
    manager._container_name = "hercules-aaaaaaaa"
    manager._instance_id = "instance"
    manager._generation = 0
    manager._generation_callbacks = []
    manager._browser_stream_relay_state = {}
    manager._workspace_was_started = False
    return manager


def test_stopped_runtime_returns_agent_guidance() -> None:
    manager = _manager()

    with pytest.raises(RuntimeNotStarted) as raised:
        asyncio.run(manager._ensure_container_running())

    result = classify_exception(raised.value, "shell_exec")
    assert result["error_type"] == "runtime_not_started"
    assert result["recoverable"] is True
    assert result["next_steps"][0] == "Call system_start_container."


def test_explicit_start_is_concurrent_and_idempotent() -> None:
    manager = _manager()

    async def start() -> None:
        await asyncio.sleep(0)
        manager._container = object()

    manager.start_container = AsyncMock(side_effect=start)
    manager.ensure_ready = AsyncMock()
    manager.stop_container = AsyncMock()
    manager._ensure_container_running = AsyncMock()

    async def scenario() -> tuple[str, str]:
        first, second = await asyncio.gather(
            manager.operator_start(), manager.operator_start()
        )
        return first, second

    assert asyncio.run(scenario()) == ("created", "already_running")
    manager.start_container.assert_awaited_once()
    manager.stop_container.assert_not_awaited()


def test_explicit_start_reattaches_the_same_session() -> None:
    manager = _manager()
    manager._client = object()
    manager.reattach_container = AsyncMock(return_value="restart")
    manager.ensure_ready = AsyncMock()
    manager.stop_container = AsyncMock()

    assert asyncio.run(manager.operator_start()) == "restart"
    assert manager.session_id == "aaaaaaaa"
    manager.reattach_container.assert_awaited_once()


def test_reattach_restarts_an_exact_owned_preserved_container() -> None:
    manager = _manager()
    manager._project_root_hash = "project"
    manager._instance_id = "instance"
    manager._ready_task = None
    manager._ready = False
    manager._workspace = Mock()
    manager._mark_ready = AsyncMock()

    container = Mock()
    container.attrs = {
        "Config": {
            "Labels": {
                "hercules.managed": "true",
                "hercules.project_root_hash": "project",
                "hercules.session_id": "aaaaaaaa",
                "hercules.instance_id": "instance",
            }
        },
        "State": {"Status": "exited"},
    }
    manager._client = Mock()
    manager._client.containers.get.return_value = container

    async def scenario() -> str:
        mode = await manager.reattach_container()
        await manager._ready_task
        return mode

    assert asyncio.run(scenario()) == "restart"
    container.start.assert_called_once_with()
    claim = manager._workspace.update_manifest.call_args
    assert claim.args == ("aaaaaaaa",)
    assert claim.kwargs["state"] == "active"
    assert claim.kwargs["generation"] == 1
    assert claim.kwargs["container_started"] is True


def test_new_session_rotates_workspace_without_starting() -> None:
    manager = _manager()
    workspace = Mock()
    workspace.allocate_session.return_value = "bbbbbbbb"
    workspace.cleanup_empty_owned.return_value = []
    manager._workspace = workspace
    manager.stop_container = AsyncMock()
    manager.start_container = AsyncMock()
    generation_changed = Mock()
    manager._generation_callbacks = [generation_changed]

    assert asyncio.run(manager.new_session()) == "bbbbbbbb"
    assert manager.session_id == "bbbbbbbb"
    assert manager.container_running is False
    assert manager._operator_stopped is True
    manager.start_container.assert_not_awaited()
    manager.stop_container.assert_awaited_once_with(release_workspace=True)
    claim = workspace.update_manifest.call_args
    assert claim.args == ("bbbbbbbb",)
    assert claim.kwargs["generation"] == 1
    assert claim.kwargs["container_started"] is False
    generation_changed.assert_called_once_with(1)


def test_new_session_stop_failure_preserves_the_old_session() -> None:
    manager = _manager()
    workspace = Mock()
    workspace.allocate_session.return_value = "bbbbbbbb"
    workspace.cleanup_empty_owned.return_value = ["bbbbbbbb"]
    manager._workspace = workspace
    manager.stop_container = AsyncMock(side_effect=RuntimeError("cannot stop"))

    with pytest.raises(RuntimeError, match="cannot stop"):
        asyncio.run(manager.new_session())

    assert manager.session_id == "aaaaaaaa"
    assert manager._operator_stopped is True
    workspace.mark_inactive.assert_called_once_with("bbbbbbbb", 1)
    workspace.cleanup_empty_owned.assert_called_once_with(
        active_session="aaaaaaaa",
        only_session="bbbbbbbb",
    )


def test_failed_start_cleans_up_and_returns_to_stopped() -> None:
    manager = _manager()
    manager.start_container = AsyncMock(side_effect=RuntimeError("boom"))
    manager.stop_container = AsyncMock()

    with pytest.raises(RuntimeError, match="boom"):
        asyncio.run(manager.operator_start())

    assert manager._operator_stopped is True
    manager.stop_container.assert_awaited_once_with(force_remove=True)


def test_cancelled_start_cleans_up_and_returns_to_stopped() -> None:
    manager = _manager()
    manager.start_container = AsyncMock(side_effect=asyncio.CancelledError)
    manager.stop_container = AsyncMock()

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(manager.operator_start())

    assert manager._operator_stopped is True
    manager.stop_container.assert_awaited_once_with(force_remove=True)


def test_forced_start_cleanup_ignores_preserve_container() -> None:
    manager = _manager()
    manager._config = Mock(preserve_container=True)
    container = Mock()
    manager._container = container
    manager._ready_task = None
    manager._bootstrapped = True
    manager._ready = True
    manager._host_port_bindings = {"4444/tcp": ("127.0.0.1", 4444)}
    manager._container_host_bindings = Mock(return_value={})
    manager._wait_for_host_ports_available = AsyncMock()
    manager._settle_orphan_guardian = AsyncMock()
    manager._workspace = Mock()

    asyncio.run(manager.stop_container(force_remove=True))

    container.remove.assert_called_once_with(force=True)
    container.stop.assert_not_called()
    manager._container_host_bindings.assert_called_once()
    manager._wait_for_host_ports_available.assert_awaited_once_with(
        {"4444/tcp": ("127.0.0.1", 4444)}
    )
    manager._workspace.mark_inactive.assert_not_called()


@pytest.mark.skipif(os.name != "nt", reason="Windows process flags")
def test_orphan_guardian_starts_without_a_console_window(monkeypatch) -> None:
    from hercules.core import docker_manager as docker_module

    manager = _manager()
    manager._config = Mock(preserve_container=False)
    manager._container = Mock(id="container-id")
    manager._project_root_hash = "project"
    manager._workspace_root_hash = "workspace"
    process = Mock(pid=1234)
    popen = Mock(return_value=process)
    monkeypatch.setattr(docker_module, "_process_start_token", lambda _pid: "token")
    monkeypatch.setattr(docker_module.subprocess, "Popen", popen)

    manager._start_orphan_guardian()

    argv = popen.call_args.args[0]
    kwargs = popen.call_args.kwargs
    flags = kwargs["creationflags"]
    assert isinstance(argv, list)
    assert argv[:3] == [sys.executable, "-m", "hercules.core.orphan_guardian"]
    assert flags == (
        docker_module.subprocess.CREATE_NO_WINDOW
        | docker_module.subprocess.CREATE_BREAKAWAY_FROM_JOB
    )
    assert not flags & docker_module.subprocess.DETACHED_PROCESS
    assert not flags & docker_module.subprocess.CREATE_NEW_PROCESS_GROUP
    assert kwargs["shell"] is False
    assert kwargs["stdin"] == docker_module.subprocess.DEVNULL
    assert kwargs["stdout"] == docker_module.subprocess.DEVNULL
    assert kwargs["stderr"] == docker_module.subprocess.DEVNULL


def test_cold_cleanup_removes_only_its_exact_workspace(tmp_path) -> None:
    workspace = WorkspaceManager(tmp_path)
    first = workspace.allocate_session()
    second = workspace.allocate_session()
    workspace.update_manifest(first, state="active", generation=0)
    workspace.update_manifest(second, state="active", generation=0)
    manager = _manager()
    manager._workspace = workspace
    manager._session_id = first

    manager.cleanup_unused_workspace()

    assert not workspace.session_path(first).exists()
    assert workspace.session_path(second).exists()


def test_abandoned_cold_cleanup_preserves_started_workspaces(tmp_path) -> None:
    workspace = WorkspaceManager(tmp_path)
    current = workspace.allocate_session()
    abandoned = workspace.allocate_session()
    started = workspace.allocate_session()
    workspace.update_manifest(current, state="active", container_started=False)
    workspace.update_manifest(
        abandoned,
        state="active",
        container_started=False,
        owner_pid=-1,
        owner_start_token="dead",
    )
    workspace.update_manifest(
        started,
        state="active",
        container_started=True,
        owner_pid=-1,
        owner_start_token="dead",
    )
    manager = _manager()
    manager._workspace = workspace
    manager._session_id = current

    manager._cleanup_abandoned_cold_workspaces()

    assert workspace.session_path(current).exists()
    assert not workspace.session_path(abandoned).exists()
    assert workspace.session_path(started).exists()


def test_watchdog_never_recovers_a_stopped_runtime() -> None:
    manager = _manager()
    manager._bootstrapped = True
    manager._ensure_container_running = AsyncMock(side_effect=RuntimeError("dead"))

    assert asyncio.run(manager.health_ok()) is True
    manager._ensure_container_running.assert_not_awaited()

    manager._operator_stopped = False
    assert asyncio.run(manager.health_ok()) is False


def test_active_runtime_recovery_preserves_the_session() -> None:
    manager = _manager()
    manager._operator_stopped = False
    manager._bootstrapped = True
    manager._ensure_container_running = AsyncMock(
        side_effect=RuntimeError("container crashed")
    )
    manager.reattach_container = AsyncMock(return_value="recreate")

    result = asyncio.run(manager._recover_container("watchdog test"))

    assert result["container_recovered"] is True
    assert result["old_session_id"] == "aaaaaaaa"
    assert result["session_id"] == "aaaaaaaa"
    assert result["recovery_mode"] == "recreate"
    assert result["workspace_preserved"] is True
    manager.reattach_container.assert_awaited_once()


def test_existing_mcp_input_schemas_match_captured_baseline() -> None:
    from hercules import main

    async def collect() -> dict[str, str]:
        hashes = {}
        for tool in await main.mcp.list_tools():
            if tool.name == "system_start_container":
                continue
            schema = json.dumps(tool.parameters, sort_keys=True, separators=(",", ":"))
            hashes[tool.name] = hashlib.sha256(schema.encode()).hexdigest()
        return hashes

    assert asyncio.run(collect()) == _EXISTING_SCHEMA_SHA256


def test_cold_mcp_connection_starts_no_container(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("HERCULES_WORKSPACE_ROOT", str(tmp_path))
    from hercules import main

    start = AsyncMock(side_effect=AssertionError("cold connection started Docker"))
    monkeypatch.setattr(DockerManager, "start_container", start)

    async def scenario() -> tuple[set[str], int, dict, dict]:
        async with Client(main.mcp) as client:
            tools = {tool.name for tool in await client.list_tools()}
            resources = await client.list_resources()
            result = await client.call_tool(
                "shell_exec", {"command": "true"}, raise_on_error=False
            )
            rotated = await client.call_tool("system_start_new_session")
            return (
                tools,
                len(resources),
                result.structured_content,
                rotated.structured_content,
            )

    tools, resource_count, result, rotated = asyncio.run(scenario())
    assert len(tools) == 46
    assert resource_count == 7
    assert "system_start_container" in tools
    assert result["error_type"] == "runtime_not_started"
    assert rotated["status"] == "success"
    assert rotated["container_running"] is False
    assert rotated["next_steps"] == [
        "Call system_start_container before using Docker-backed tools."
    ]
    start.assert_not_awaited()


def test_every_docker_backed_tool_uses_the_cold_runtime_guard(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("HERCULES_WORKSPACE_ROOT", str(tmp_path))
    from hercules import main
    from hercules.core.firewall import _DOCKER_BACKED_TOOLS

    start = AsyncMock(side_effect=AssertionError("cold tool call started Docker"))
    monkeypatch.setattr(DockerManager, "start_container", start)

    async def scenario() -> dict[str, dict]:
        async with Client(main.mcp) as client:
            exposed = {tool.name for tool in await client.list_tools()}
            results = {}
            for tool in sorted(_DOCKER_BACKED_TOOLS & exposed):
                called = await client.call_tool(tool, {}, raise_on_error=False)
                results[tool] = called.structured_content
            return results

    results = asyncio.run(scenario())
    assert set(results) == _DOCKER_BACKED_TOOLS
    assert all(item["error_type"] == "runtime_not_started" for item in results.values())
    assert all(item["recoverable"] is True for item in results.values())
    start.assert_not_awaited()


def test_real_stdio_cold_connection_starts_no_container(tmp_path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    transport = StdioTransport(
        sys.executable,
        ["-m", "hercules.main"],
        cwd=str(project_root),
        env={
            **os.environ,
            "HERCULES_WORKSPACE_ROOT": str(tmp_path),
        },
    )

    async def scenario() -> tuple[int, int, dict, set[str]]:
        async with Client(transport) as client:
            tools = await client.list_tools()
            resources = await client.list_resources()
            result = await client.call_tool(
                "shell_exec",
                {"command": "true"},
                raise_on_error=False,
            )
            active_sessions = {
                entry.name for entry in tmp_path.iterdir() if entry.is_dir()
            }
            return (
                len(tools),
                len(resources),
                result.structured_content,
                active_sessions,
            )

    tool_count, resource_count, result, first_sessions = asyncio.run(scenario())
    assert (tool_count, resource_count) == (46, 7)
    assert result["error_type"] == "runtime_not_started"
    assert len(first_sessions) == 1

    _, _, second_result, second_sessions = asyncio.run(scenario())
    assert second_result["error_type"] == "runtime_not_started"
    assert len(second_sessions) == 1
    assert second_sessions.isdisjoint(first_sessions)

    workspace = WorkspaceManager(tmp_path)
    for session in second_sessions:
        manifest = workspace.read_manifest(session)
        assert manifest is not None
        workspace.mark_inactive(session, int(manifest["generation"]))
        assert workspace.cleanup_empty_owned(
            active_session="",
            only_session=session,
        ) == [session]


def test_start_tool_reports_the_public_lifecycle_fields(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("HERCULES_WORKSPACE_ROOT", str(tmp_path))
    from hercules import main

    async def start(manager: DockerManager) -> str:
        manager._container = object()
        return "created"

    async def stop(manager: DockerManager, **_kwargs) -> None:
        manager._container = None

    monkeypatch.setattr(DockerManager, "operator_start", start)
    monkeypatch.setattr(DockerManager, "stop_container", stop)

    async def scenario() -> dict:
        async with Client(main.mcp) as client:
            result = await client.call_tool("system_start_container")
            return result.structured_content

    result = asyncio.run(scenario())
    assert result["tool"] == "system_start_container"
    assert result["status"] == "success"
    assert result["container_running"] is True
    assert result["start_mode"] == "created"
    assert result["session_id"]
    assert result["workspace"].startswith("/opt/workspace (host: ")


def test_start_tool_redacts_failure_details(monkeypatch, tmp_path) -> None:
    secret = "mcp-redaction-secret-7f9e2"
    monkeypatch.setenv("HERCULES_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("MSF_PASSWORD", secret)
    from hercules import main

    async def fail(_manager: DockerManager) -> str:
        raise RuntimeError(f"token={secret}\x1b")

    monkeypatch.setattr(DockerManager, "operator_start", fail)

    async def scenario() -> dict:
        async with Client(main.mcp) as client:
            result = await client.call_tool("system_start_container")
            return result.structured_content

    result = asyncio.run(scenario())
    assert result["status"] == "error"
    assert secret not in result["error"]
    assert result["error"] == "token=***"


def test_install_update_contract_is_documented() -> None:
    project_root = Path(__file__).resolve().parents[1]
    readme = (project_root / "README.md").read_text(encoding="utf-8")
    install = (project_root / "install.md").read_text(encoding="utf-8")
    install_text = " ".join(install.split())

    assert readme.count("Install or update Hercules MCP from") == 1
    for phrase in (
        "Update in place",
        "Reinstall",
        "fast-forward only",
        "dirty or diverged",
        "fresh staged checkout",
        "atomic",
        "Preserve .env",
        "finally-equivalent cleanup",
        "success, failure, cancellation, and interruption",
        "Never perform a broad Docker",
    ):
        assert phrase in install_text
