from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from typing import Literal
from unittest.mock import AsyncMock

import pytest
from fastmcp import Client, FastMCP
from fastmcp.tools.base import ToolResult
from mcp.types import ImageContent
from pydantic import BaseModel

from hercules.core.concurrency import ConcurrencyManager
from hercules.core.config import HerculesConfig
from hercules.core.docker_manager import DockerManager, ExecResult
from hercules.core.firewall import ParameterFilterMiddleware, ToolExceptionFirewall
from hercules.core.workspace import MANIFEST_NAME, WorkspaceManager
from hercules.tools.network.network_tool import _parse_headers
from hercules.tools.system.file_tool import register_file_tools
from hercules.tools.web.web_scanner_tool import register_web_scanner_tools
from hercules.workspace_cli import build_parser, run


@pytest.fixture
def workspace(tmp_path):
    manager = WorkspaceManager(tmp_path / "owned", max_inline_bytes=3)
    session = manager.allocate_session()
    return manager, session


def test_workspace_metadata_and_read_are_bounded_and_readonly(workspace):
    manager, session = workspace
    manager.atomic_write(session, "challenge/evidence.bin", b"\x00\xffabcd", mode=0o600)
    manifest = manager.session_path(session) / MANIFEST_NAME
    before = manifest.read_bytes()
    assert manager.inspect(session, "challenge", action="stat")["type"] == "directory"
    assert manager.inspect(session, "challenge/evidence.bin", action="stat")["size_bytes"] == 6
    manager.atomic_write(session, "challenge/notes.txt", b"notes", mode=0o600)
    before = manifest.read_bytes()
    page = manager.inspect(session, "challenge", action="list", max_entries=1)
    assert page["truncated"] and page["next_offset"] == 1
    assert len(page["entries"]) == 1
    chunk = manager.read_chunk(session, "challenge/evidence.bin", touch=False)
    assert chunk.data == b"\x00\xffa" and chunk.next_offset == 3
    assert manifest.read_bytes() == before
    with pytest.raises(ValueError):
        manager.inspect(session, "/opt/workspace/../outside", action="list")
    with pytest.raises(ValueError):
        manager.inspect("bad", "", action="list")


def test_offline_tool_can_read_retained_evidence(workspace):
    manager, retained = workspace
    current = manager.allocate_session()
    manager.atomic_write(retained, "evidence.bin", b"\x00\xffabcd", mode=0o600)
    docker = SimpleNamespace(_workspace=manager, session_id=current, container_running=False)
    server = FastMCP("Offline fixture")
    register_file_tools(server)

    async def scenario():
        tool = await server.get_tool("workspace_inspect")
        return await tool.fn(action="read", path="evidence.bin", session_id=retained,
                             encoding="base64", ctx=SimpleNamespace(lifespan_context={"docker": docker}))

    result = asyncio.run(scenario())
    assert base64.b64decode(result["content_base64"]) == b"\x00\xffa"
    assert result["next_offset"] == 3 and result["total_bytes"] == 6
    assert result["container_workspace"] is None and not result["container_accessible"]


def test_transfer_roundtrip_conflicts_and_cli(workspace, tmp_path, monkeypatch):
    manager, session = workspace
    source = tmp_path / "é input file.bin"
    payload = bytes(range(256)) * 5000
    source.write_bytes(payload)
    monkeypatch.setenv("HERCULES_WORKSPACE_ROOT", str(manager.root))
    args = build_parser().parse_args(["import", "--session", session, "--source", str(source),
                                     "--destination", "challenge/evidence.bin", "--json"])
    imported = run(args)
    assert imported["checksum_verified"] and imported["bytes"] == len(payload)
    assert imported["sha256"] == hashlib.sha256(payload).hexdigest()
    with pytest.raises(FileExistsError):
        run(args)
    destination = tmp_path / "é exported file.bin"
    exported = manager.transfer(session, "challenge/evidence.bin", destination, direction="export")
    assert exported["sha256"] == imported["sha256"]
    assert destination.read_bytes() == payload
    with pytest.raises(FileExistsError):
        manager.transfer(session, "challenge/evidence.bin", destination, direction="export")
    source.write_bytes(b"replacement")
    manager.transfer(session, "challenge/evidence.bin", source, direction="import", overwrite=True)
    assert manager.read_chunk(session, "challenge/evidence.bin", max_bytes=3).data == b"rep"
    with pytest.raises(ValueError):
        manager.transfer(session, MANIFEST_NAME, source, direction="import", overwrite=True)


def test_transfer_failure_and_interruption_leave_no_temporary_files(workspace, tmp_path, monkeypatch):
    manager, session = workspace
    source = tmp_path / "input.bin"
    source.write_bytes(b"evidence")
    manager.ensure_directory(session, "challenge")
    for failure in (OSError("disk full"), KeyboardInterrupt()):
        with monkeypatch.context() as patch:
            def fail(*args):
                raise failure
            patch.setattr("hercules.core.workspace.os.write", fail)
            with pytest.raises(type(failure)):
                manager.transfer(session, "challenge/output.bin", source, direction="import")
        assert list((manager.session_path(session) / "challenge").iterdir()) == []
    assert source.read_bytes() == b"evidence"


def test_concurrent_transfers_cannot_overwrite_without_permission(workspace, tmp_path):
    manager, session = workspace
    source = tmp_path / "input.bin"
    source.write_bytes(b"verified" * 100000)
    manager.ensure_directory(session, "challenge")

    def transfer():
        try:
            return manager.transfer(session, "challenge/output.bin", source, direction="import")
        except OSError as exc:
            return exc

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: transfer(), range(2)))
    assert sum(isinstance(result, dict) for result in results) == 1
    assert (manager.session_path(session) / "challenge/output.bin").read_bytes() == source.read_bytes()
    assert [p.name for p in (manager.session_path(session) / "challenge").iterdir()] == ["output.bin"]


@pytest.mark.skipif(os.name != "nt", reason="Windows sharing-lock regression")
def test_locked_windows_destination_keeps_original_and_removes_transfer_temp(workspace, tmp_path):
    from hercules.core import workspace as module

    manager, session = workspace
    manager.atomic_write(session, "input.bin", b"replacement", mode=0o600)
    destination = tmp_path / "locked.bin"
    destination.write_bytes(b"original")
    handle = module._KERNEL32.CreateFileW(str(destination), module._GENERIC_READ, 1, None,
                                         module._OPEN_EXISTING, 0, None)
    assert handle != module._INVALID_HANDLE_VALUE
    try:
        with pytest.raises(OSError):
            manager.transfer(session, "input.bin", destination, direction="export", overwrite=True)
        assert destination.read_bytes() == b"original"
        assert not list(tmp_path.glob(".hercules-transfer-*.tmp"))
    finally:
        module._win_close(handle)


def test_workspace_and_transfer_reject_links(workspace, tmp_path):
    manager, session = workspace
    outside = tmp_path / "outside.bin"
    outside.write_bytes(b"private")
    link = manager.session_path(session) / "link.bin"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("symlink creation unavailable on this Windows host")
    with pytest.raises((OSError, ValueError)):
        manager.inspect(session, "link.bin", action="stat")
    with pytest.raises((OSError, ValueError)):
        manager.transfer(session, "link.bin", outside, direction="import", overwrite=True)
    assert outside.read_bytes() == b"private"


def test_workspace_and_transfer_reject_directory_reparse_points(workspace, tmp_path):
    manager, session = workspace
    outside = tmp_path / "external-directory"
    outside.mkdir()
    (outside / "private.txt").write_bytes(b"private")
    link = manager.session_path(session) / "linked-directory"
    if os.name == "nt":
        result = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(outside)],
                                capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        assert result.returncode == 0, "could not create disposable junction fixture"
    else:
        link.symlink_to(outside, target_is_directory=True)
    for action in ("list", "stat"):
        with pytest.raises((OSError, ValueError)):
            manager.inspect(session, "linked-directory", action=action)
    with pytest.raises((OSError, ValueError)):
        manager.read_chunk(session, "linked-directory/private.txt", touch=False)
    with pytest.raises((OSError, ValueError)):
        manager.transfer(session, "linked-directory/private.txt", outside / "private.txt",
                         direction="import", overwrite=True)
    with pytest.raises((OSError, ValueError)):
        manager.transfer(session, "safe.txt", link / "private.txt", direction="import")
    assert (outside / "private.txt").read_bytes() == b"private"


@pytest.mark.parametrize("value,expected", [
    ('{"User-Agent":"Agent (compatible, test)","X-Test":"a,b"}', ["User-Agent: Agent (compatible, test)", "X-Test: a,b"]),
    ("Accept: text/html,application/json", ["Accept: text/html,application/json"]),
    ("X-A: one, X-B: two", ["X-A: one", "X-B: two"]),
    ("X-A: one\r\nX-B: two", ["X-A: one", "X-B: two"]),
])
def test_headers_preserve_values(value, expected):
    assert _parse_headers(value) == expected


@pytest.mark.parametrize("value", ['{"X":"a\\n"}', '{"X":1}', '{"X":"a","X":"b"}',
                                    "missing colon", "X: a\r", "X: a\x00", "Bad Name: value"])
def test_headers_reject_malformed_controls(value):
    with pytest.raises(ValueError):
        _parse_headers(value)


def test_validation_boundary_and_ignored_options():
    server = FastMCP("Contract fixture")
    server.add_middleware(ParameterFilterMiddleware())
    server.add_middleware(ToolExceptionFirewall())

    class InternalModel(BaseModel):
        number: int

    @server.tool
    async def fixture(mode: Literal["quick", "custom"], internal: bool = False) -> dict:
        if internal:
            InternalModel(number="bad")
        return {"status": "success"}

    async def scenario():
        async with Client(server) as client:
            for arguments in ({}, {"mode": "invalid"}):
                result = (await client.call_tool("fixture", arguments)).structured_content
                assert result["error_type"] == "invalid_parameters" and result["recoverable"]
            result = (await client.call_tool("fixture", {"mode": "quick", "internal": True})).structured_content
            assert result["error_type"] == "internal_error"
            result = (await client.call_tool("fixture", {"mode": "quick", "options": "SECRET", "description": "annotation"})).structured_content
            assert result["ignored_arguments"] == ["options"] and "SECRET" not in json.dumps(result)
            result = (await client.call_tool("fixture", {"mode": "quick", "description": "annotation"})).structured_content
            assert "usage_warnings" not in result

    asyncio.run(scenario())


def test_ignored_option_warning_keeps_native_image_content():
    server = FastMCP("Native image fixture")
    server.add_middleware(ParameterFilterMiddleware())

    @server.tool
    async def fixture() -> ToolResult:
        return ToolResult(content=[ImageContent(type="image", data="AA==", mimeType="image/png")],
                          structured_content={"status": "success"})

    async def scenario():
        async with Client(server) as client:
            result = await client.call_tool("fixture", {"options": "ignored"})
            assert result.structured_content["ignored_arguments"] == ["options"]
            assert any(block.type == "image" for block in result.content)

    asyncio.run(scenario())


@pytest.mark.parametrize("url,expected", [("http://127.0.0.1/api", "/api/FUZZ"),
                                         ("http://127.0.0.1/api/FUZZ", "/api/FUZZ")])
def test_ffuf_uses_exactly_one_placeholder(url, expected):
    server = FastMCP("Fuzz fixture")
    register_web_scanner_tools(server)
    manager = SimpleNamespace(exec_command=AsyncMock(return_value=ExecResult(0, "", "", 0, "fixture")))
    ctx = SimpleNamespace(lifespan_context={"docker": manager, "config": HerculesConfig(),
                                          "concurrency": ConcurrencyManager()})

    async def scenario():
        tool = await server.get_tool("fuzz_dirs")
        await tool.fn(target_url=url, tool="ffuf", wordlist="/fixture.txt", ctx=ctx)
        assert expected in manager.exec_command.await_args.args[0]
        assert manager.exec_command.await_args.args[0].count("FUZZ") == 1
        before = manager.exec_command.await_count
        result = await tool.fn(target_url="http://127.0.0.1/FUZZ/FUZZ", tool="ffuf", ctx=ctx)
        assert result["error_type"] == "invalid_target"
        assert manager.exec_command.await_count == before

    asyncio.run(scenario())


def test_missing_wordlist_only_suggests_verified_paths():
    server = FastMCP("Fuzz fixture")
    register_web_scanner_tools(server)
    manager = SimpleNamespace(exec_command=AsyncMock(return_value=ExecResult(1, "", "", 0, "test")))
    ctx = SimpleNamespace(lifespan_context={"docker": manager, "config": HerculesConfig(),
                                          "concurrency": ConcurrencyManager()})

    async def scenario():
        tool = await server.get_tool("fuzz_dirs")
        result = await tool.fn(target_url="http://127.0.0.1", wordlist="missing.txt", ctx=ctx)
        assert result["error_type"] == "resource_missing"
        assert "examples" not in result
        assert isinstance(result["expected"], str)

    asyncio.run(scenario())


def test_job_inventory_is_recorded_not_live_and_missing_id_is_actionable(workspace):
    manager, session = workspace
    docker = object.__new__(DockerManager)
    docker._workspace, docker._session_id, docker._generation = manager, session, 4
    manager.max_inline_bytes = 8192
    docker._save_job_metadata("owned-job", {"state": "running", "generation": 3})
    inventory = docker.job_inventory()
    assert inventory["state_source"] == "recorded_metadata"
    assert inventory["jobs"][0]["stale"]
    result = asyncio.run(docker.check_job("harness-task"))
    assert result["state"] == "missing" and result["known_job_ids"] == ["owned-job"]
    assert "harness" in " ".join(result["next_steps"])
    def unsafe_entry(*args, **kwargs):
        raise ValueError("unsafe entry")
    docker._workspace = SimpleNamespace(inspect=unsafe_entry)
    inaccessible = docker.job_inventory()
    assert inaccessible["truncated"] and inaccessible["error"]


def test_guardian_settlement_keeps_failed_process_identity_for_retry():
    manager = object.__new__(DockerManager)

    def denied():
        raise PermissionError("fixture denial")

    guardian = SimpleNamespace(pid=123, poll=lambda: None, terminate=denied, wait=lambda: 0)
    manager._orphan_guardian = guardian
    assert asyncio.run(manager._settle_orphan_guardian()) is False
    assert manager._orphan_guardian is guardian
    guardian.terminate = lambda: None
    assert asyncio.run(manager._settle_orphan_guardian()) is True
    assert manager._orphan_guardian is None
