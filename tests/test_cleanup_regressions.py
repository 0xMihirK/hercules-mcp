from __future__ import annotations

import asyncio
import importlib
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastmcp import Client, FastMCP
from fastmcp.client.transports import StdioTransport

from hercules.core.concurrency import ConcurrencyManager
from hercules.core.config import HerculesConfig
from hercules.core.docker_manager import DockerManager, ExecResult, RuntimeNotStarted
from hercules.core.firewall import classify_exception
from hercules.core.tool_catalog import CORE_TOOLS, METASPLOIT_TOOLS, TOOL_REGISTRARS
from hercules.core.workspace import WorkspaceManager, WorkspaceRead
from hercules.tools.ctf.ctf_tool import register_ctf_tools
from hercules.tools.exploitation import metasploit_tool as msf_tools
from hercules.tools.exploitation.searchsploit_tool import register_searchsploit_tools
from hercules.tools.system.file_tool import register_file_tools
from hercules.tools.system.shell_tool import register_shell_tools

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("kind", ["heavy", "light"])
def test_concurrency_limits_release_and_reuse(kind):
    async def scenario():
        manager = ConcurrencyManager(1, 1, heavy_timeout=0.02, light_timeout=0.02)
        acquire = getattr(manager, f"acquire_{kind}")
        other = "light" if kind == "heavy" else "heavy"
        async with acquire("holder") as job_id:
            assert job_id.startswith("holder-") and len(job_id) == 13
            assert manager._active[kind] == 1
            async with getattr(manager, f"acquire_{other}")("independent"):
                assert manager._active == {"heavy": 1, "light": 1}
            with pytest.raises(RuntimeError) as raised:
                async with acquire("queued"):
                    pytest.fail("pool admitted a second job")
            assert str(raised.value) == (
                f"Concurrency limit reached: cannot schedule 'queued' ({kind}). "
                f"Currently active: 1 {kind} jobs."
            )
            assert (
                classify_exception(raised.value, "queued")["error_type"]
                == "server_busy"
            )
        assert manager._active == {"heavy": 0, "light": 0}
        with pytest.raises(ValueError, match="body failed"):
            async with acquire("failing"):
                raise ValueError("body failed")
        async with acquire("reused"):
            assert manager._active[kind] == 1
        assert manager._active == {"heavy": 0, "light": 0}

    asyncio.run(scenario())


@pytest.mark.parametrize("kind", ["heavy", "light"])
@pytest.mark.parametrize("phase", ["waiting", "acquired"])
def test_concurrency_cancellation_does_not_leak_slots(kind, phase):
    async def scenario():
        manager = ConcurrencyManager(1, 1, heavy_timeout=5, light_timeout=5)
        acquire = getattr(manager, f"acquire_{kind}")
        entered = asyncio.Event()

        async def work():
            entered.set()
            async with acquire("cancelled"):
                entered.set()
                await asyncio.Future()

        if phase == "waiting":
            async with acquire("holder"):
                task = asyncio.create_task(work())
                await entered.wait()
                task.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await task
                assert manager._active[kind] == 1
        else:

            async def acquired_work():
                async with acquire("cancelled"):
                    entered.set()
                    await asyncio.Future()

            task = asyncio.create_task(acquired_work())
            await entered.wait()
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        assert manager._active == {"heavy": 0, "light": 0}
        async with acquire("reused"):
            assert manager._active[kind] == 1

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "profile,skip,disabled,count",
    [
        ("all", "false", "", 46),
        ("all", "true", "", 41),
        ("core", "false", "", 11),
        ("all", "false", "nmap_scan,metasploit_search,shell_exec", 44),
        ("all", "false", "removed_tool,nmap_scan,shell_exec", 45),
    ],
)
def test_native_visibility_matches_stdio_and_setup(
    profile, skip, disabled, count, tmp_path
):
    env = {
        **os.environ,
        "HERCULES_INSTALLED_CAPABILITIES": profile,
        "HERCULES_DISABLED_TOOLS": disabled,
        "SKIP_METASPLOIT": skip,
        "HERCULES_WORKSPACE_ROOT": str(tmp_path),
        "WATCHDOG_INTERVAL": "0",
    }
    launcher = [sys.executable, "-m", "hercules.main"]

    def facts(flag):
        completed = subprocess.run(
            [*launcher, flag],
            env=env,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        return json.loads(completed.stdout)

    setup = facts("--setup-info-json")
    validation = facts("--validate-mcp-json")
    assert setup["mcp_surface"]["catalog_matches"] is True
    assert setup["mcp_surface"]["errors"] == []
    expected_names = set(setup["mcp_surface"]["tool_names"])
    assert validation["operator_disabled_tools"] == sorted(
        set(filter(None, disabled.split(","))) - CORE_TOOLS
    )

    async def scenario():
        reference = FastMCP("Unfiltered schema reference")
        for item in TOOL_REGISTRARS:
            module, function = item.path.split(":")
            getattr(importlib.import_module(module), function)(reference)
        baseline = {
            tool.name: tool.to_mcp_tool().model_dump()
            for tool in await reference.list_tools()
        }
        transport = StdioTransport(launcher[0], launcher[1:], cwd=PROJECT_ROOT, env=env)
        async with Client(transport) as client:
            tools = await client.list_tools()
            assert {tool.name for tool in tools} == expected_names
            assert len(tools) == validation["tools"] == count
            assert len(await client.list_resources()) == validation["resources"] == 7
            assert CORE_TOOLS <= expected_names
            assert {tool.name: tool.model_dump() for tool in tools} == {
                name: baseline[name] for name in expected_names
            }
            absent = set(baseline) - expected_names
            reported = absent - (
                METASPLOIT_TOOLS if not validation["metasploit_enabled"] else set()
            )
            assert validation["unavailable_or_hidden_tools"] == sorted(reported)
            for name in absent:
                result = await client.call_tool(name, {}, raise_on_error=False)
                assert (
                    result.is_error
                    or result.structured_content["error_type"] == "tool_not_found"
                )
            cold = await client.call_tool(
                "shell_exec", {"command": "true"}, raise_on_error=False
            )
            assert cold.structured_content["error_type"] == "runtime_not_started"

    try:
        asyncio.run(scenario())
    finally:
        # STDIO transport shutdown can terminate the process before its final
        # manifest write. Only clean these disposable, evidence-free sessions.
        workspace = WorkspaceManager(tmp_path)
        for session in workspace.list_sessions():
            session_id = session["session_id"]
            workspace.mark_inactive(session_id)
            assert workspace.cleanup_empty_owned(only_session=session_id) == [
                session_id
            ]


async def _call(registrar, name, manager, **arguments):
    server = FastMCP("Tool regression")
    registrar(server)
    tool = await server.get_tool(name)
    ctx = SimpleNamespace(
        lifespan_context={
            "docker": manager,
            "concurrency": ConcurrencyManager(),
            "config": HerculesConfig(),
            "msf_state": {"client": None},
        }
    )
    return await tool.fn(ctx=ctx, **arguments)


@pytest.mark.parametrize("encoding", ["text", "base64"])
def test_paged_file_response_preserves_metadata(encoding):
    manager = Mock(spec=DockerManager)
    manager.read_file_chunk.return_value = WorkspaceRead(b"abc", 12, 2, True, 5)
    result = asyncio.run(
        _call(
            register_file_tools,
            "workspace_read_file",
            manager,
            path="evidence.bin",
            encoding=encoding,
            offset=2,
            max_bytes=3,
        )
    )
    content = {"content": "abc"} if encoding == "text" else {"content_base64": "YWJj"}
    assert result == {
        "tool": "workspace_read_file",
        "path": "/opt/workspace/evidence.bin",
        "encoding": encoding,
        "bytes": 3,
        "total_bytes": 12,
        "offset": 2,
        "truncated": True,
        "next_offset": 5,
        **content,
    }
    manager.read_file_chunk.assert_awaited_once_with(
        "/opt/workspace/evidence.bin",
        offset=2,
        max_bytes=3,
    )
    manager.read_file_bytes.assert_not_awaited()


def test_job_termination_keeps_every_response_field():
    manager = Mock(spec=DockerManager)
    termination = {
        "killed": True,
        "terminated": True,
        "confirmed": True,
        "state": "terminated",
    }
    manager.terminate_job.return_value = termination
    result = asyncio.run(
        _call(register_shell_tools, "shell_kill_job", manager, job_id="fixture")
    )
    assert result == {"tool": "shell_kill_job", "job_id": "fixture", **termination}
    manager.terminate_job.assert_awaited_once_with("fixture")


def test_searchsploit_uses_owned_directory_and_bounded_read():
    manager = Mock(spec=DockerManager)
    manager.exec_command.side_effect = [
        ExecResult(0, "mirrored", "", 0, "mirror"),
        ExecResult(0, "fixture.py\n", "", 0, "find"),
    ]
    manager.read_file_chunk.return_value = WorkspaceRead(
        b"a" * 9000, 10000, 0, True, 9000
    )
    result = asyncio.run(
        _call(
            register_searchsploit_tools,
            "searchsploit",
            manager,
            action="get",
            query_or_id="123",
        )
    )
    directory = manager.ensure_workspace_directory.await_args.args[0]
    assert directory.startswith("/opt/workspace/exploits/")
    assert result["exploit_path"] == f"{directory}/fixture.py"
    assert result["exploit_content"] == "a" * 8000
    assert result["exploit_size"] == result["exploit_bytes"] == 10000
    assert result["truncated"] is result["exploit_content_truncated"] is True
    assert result["next_offset"] == 8000
    manager.read_file_chunk.assert_awaited_once_with(
        result["exploit_path"], max_bytes=32768
    )


@pytest.mark.parametrize(
    "name,arguments",
    [
        ("ctf_binwalk", {"extract": True}),
        ("ctf_steghide", {"action": "extract"}),
    ],
)
def test_ctf_preserves_workspace_validation(name, arguments):
    manager = Mock(spec=DockerManager)
    manager.normalize_workspace_path.return_value = "/opt/workspace/fixture.bin"
    manager.exec_command.return_value = ExecResult(0, "ok", "", 0, "fixture")
    result = asyncio.run(
        _call(register_ctf_tools, name, manager, filepath="fixture.bin", **arguments)
    )
    assert result["exit_code"] == 0
    manager.validate_workspace_file.assert_awaited_once_with(
        "/opt/workspace/fixture.bin"
    )
    if name == "ctf_steghide":
        directory = manager.ensure_workspace_directory.await_args.args[0]
        assert result["extracted_path"] == f"{directory}/extracted.bin"
    manager.exec_command.reset_mock()
    manager.validate_workspace_file.side_effect = ValueError("outside workspace")
    result = asyncio.run(
        _call(register_ctf_tools, name, manager, filepath="fixture.bin", **arguments)
    )
    assert result["status"] == "error"
    manager.exec_command.assert_not_awaited()


def test_metasploit_lazy_connection_reconnect_and_errors(monkeypatch):
    async def scenario():
        manager = Mock(spec=DockerManager)
        first, second = Mock(), Mock()
        manager.wait_for_msfrpcd.side_effect = [first, second]
        rpc = AsyncMock()
        monkeypatch.setattr(msf_tools, "_rpc", rpc)
        state = {"client": None}
        ctx = SimpleNamespace(
            lifespan_context={
                "docker": manager,
                "config": HerculesConfig(),
                "msf_state": state,
            }
        )
        assert await msf_tools._get_msf(ctx) is first
        assert await msf_tools._get_msf(ctx) is first
        manager.wait_for_msfrpcd.assert_awaited_once_with(max_retries=20, interval=2.0)
        rpc.side_effect = ConnectionError("stale RPC")
        assert await msf_tools._get_msf(ctx) is second
        manager.restart_msfrpcd.assert_awaited_once()
        assert state == {"client": second}
        manager.wait_for_msfrpcd.side_effect = ConnectionError("still offline")
        with pytest.raises(msf_tools.MetasploitUnavailable, match="reconnect failed"):
            await msf_tools._get_msf(ctx)
        assert state == {"client": second}
        state["client"] = None
        manager.wait_for_msfrpcd.side_effect = ConnectionError("not listening")
        with pytest.raises(msf_tools.MetasploitUnavailable) as raised:
            await msf_tools._get_msf(ctx)
        assert "failed to initialize" in str(raised.value)
        assert state == {"client": None}
        assert (
            msf_tools._not_available("metasploit_search", raised.value)["error_type"]
            == "backend_unavailable"
        )
        assert (
            classify_exception(raised.value, "metasploit_search")["recoverable"]
            is False
        )
        manager.wait_for_msfrpcd.reset_mock()
        manager.ensure_ready.side_effect = RuntimeNotStarted("stopped")
        with pytest.raises(RuntimeNotStarted):
            await msf_tools._get_msf(ctx)
        manager.wait_for_msfrpcd.assert_not_awaited()
        manager.ensure_ready.reset_mock()
        ctx.lifespan_context["config"] = HerculesConfig(skip_metasploit=True)
        with pytest.raises(msf_tools.MetasploitUnavailable, match="disabled"):
            await msf_tools._get_msf(ctx)
        manager.ensure_ready.assert_not_awaited()

    asyncio.run(scenario())


def test_payload_cli_fallback_prepares_owned_directory(monkeypatch):
    monkeypatch.setattr(
        msf_tools,
        "_get_msf",
        AsyncMock(side_effect=msf_tools.MetasploitUnavailable("offline")),
    )
    manager = Mock(spec=DockerManager)
    manager.exec_command.return_value = ExecResult(
        0, "generated", "", 0, "mocked msfvenom"
    )
    manager.read_file_bytes.return_value = b"local-fixture"
    result = asyncio.run(
        _call(
            msf_tools.register_metasploit_tools,
            "metasploit_generate_payload",
            manager,
            payload="generic/custom",
            options={},
            format="raw",
        )
    )
    manager.ensure_workspace_directory.assert_awaited_once_with(
        "/opt/workspace/payloads"
    )
    assert result["status"] == "success"
    assert result["payload_size"] == len(b"local-fixture")
    assert result["save_path"].startswith("/opt/workspace/payloads/")
