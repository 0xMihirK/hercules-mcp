from __future__ import annotations

import asyncio
import importlib.util
import io
import json
import tarfile
from dataclasses import replace
from pathlib import Path, PurePosixPath
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastmcp import Client, FastMCP
from fastmcp.tools.base import ToolResult
from mcp.types import ImageContent
from test_lifecycle_regressions import runtime as lifecycle_runtime

from hercules.core.build_info import (
    ALL_CAPABILITIES,
    BROWSER_ASSETS_SHA256,
    image_identity,
)
from hercules.core.concurrency import ConcurrencyManager
from hercules.core.docker_manager import ExecResult
from hercules.core.firewall import _browser_metadata
from hercules.setup.images import prebuilt_references
from hercules.setup.transaction import SetupError
from hercules.tools.browser import browser_tool

ROOT = Path(__file__).resolve().parents[1]


def test_browser_fixture_waits_for_every_listener(tmp_path):
    from test_browser_acceptance import FIXTURE

    ports = []
    ready = tmp_path / "ready"

    class Server:
        def __init__(self, address, _handler):
            assert not ready.exists(), "Fixture advertised readiness too early"
            ports.append(address[1])
            self.socket = object()

        def serve_forever(self):
            pass

    tls = SimpleNamespace(
        load_cert_chain=lambda *_: None,
        wrap_socket=lambda connection, **_: connection,
    )
    context = {
        "ROOT": tmp_path,
        "ThreadingHTTPServer": Server,
        "Handler": object,
        "ConnectProxy": object,
        "SocksProxy": object,
        "socketserver": SimpleNamespace(ThreadingTCPServer=Server),
        "threading": SimpleNamespace(
            Thread=lambda **_: SimpleNamespace(start=lambda: None),
            Event=lambda: SimpleNamespace(wait=lambda: None),
        ),
        "ssl": SimpleNamespace(SSLContext=lambda _: tls, PROTOCOL_TLS_SERVER=object()),
    }
    exec(FIXTURE[FIXTURE.index("def _bind("):], context)
    assert ports == [18080, 18081, 18083, 18084, 18085]
    assert ready.read_text() == "ready"


@pytest.fixture
def runtime(monkeypatch, tmp_path):
    return lifecycle_runtime.__wrapped__(monkeypatch, tmp_path)


def test_full_image_identity_is_independent_of_tool_visibility():
    assert image_identity(ROOT, ALL_CAPABILITIES) == image_identity(ROOT, {"shell", "session", "workspace"})
    assert len(BROWSER_ASSETS_SHA256) == 64


def test_timeout_clamp_is_visible_on_success(runtime):
    async def scenario():
        manager = runtime.manager
        manager._config = replace(manager._config, max_exec_timeout=2)
        await manager.operator_start()
        try:
            result = (await manager.exec_command("printf local-ok", timeout=60)).to_dict()
            assert result["requested_timeout_seconds"] == 60
            assert result["effective_timeout_seconds"] == 2
            assert "MAX_EXEC_TIMEOUT" in result["warnings"][0]
        finally:
            await manager.operator_stop()
    asyncio.run(scenario())


@pytest.mark.parametrize("final_code,confirmed", [(3, True), (7, False), (4, False), (0, False)])
def test_termination_uses_verified_final_group_status(runtime, final_code, confirmed):
    async def scenario():
        manager = runtime.manager
        await manager.operator_start()
        try:
            manager._save_job_metadata("owned", {"generation": manager.generation, "pid": 321, "pgid": 321, "start_ticks": "123"})
            manager.exec_command = AsyncMock(side_effect=[
                ExecResult(0, "running", "", 0, "probe"),
                ExecResult(1, "", "", 0, "signal"),
                ExecResult(final_code, "", "", 0, "probe"),
            ])
            result = await manager.terminate_job("owned")
            assert result["confirmed"] is confirmed
            assert result["terminated"] is confirmed
            signal = manager.exec_command.call_args_list[1].args[0]
            assert "kill -TERM -- -321" in signal
            assert '"$ticks" = "$expected"' in signal
            assert result["signal_exit_code"] == 1
        finally:
            await manager.operator_stop()
    asyncio.run(scenario())


def test_browser_warnings_preserve_native_image_and_existing_warnings():
    result = ToolResult(structured_content={"warnings": ["existing"]})
    result.content.append(ImageContent(type="image", mimeType="image/png", data="AA=="))
    annotated = _browser_metadata(result, "browser_screenshot")
    assert annotated.structured_content["csp_enforced"] is False
    assert annotated.structured_content["native_browser_downloads"] is False
    assert annotated.structured_content["warnings"][0] == "existing"
    assert any(block.type == "image" for block in annotated.content)


def test_browser_cold_error_includes_csp_warning(runtime, monkeypatch):
    from hercules import main
    monkeypatch.setattr(main, "DockerManager", lambda *args, **kwargs: runtime.manager)
    async def scenario():
        async with Client(main.mcp) as client:
            result = await client.call_tool("browser_open", {"url": "http://127.0.0.1/"})
            assert result.structured_content["error_type"] == "runtime_not_started"
            assert result.structured_content["csp_enforced"] is False
    asyncio.run(scenario())


@pytest.mark.parametrize("arguments", ["--engine chrome open example.test", "--profile=/tmp/profile open example.test", "download e1 /tmp/a", "state save a.json", "--ca-cert a.pem open example.test"])
def test_browser_rejects_unsupported_options_without_launch(arguments):
    async def scenario():
        server = FastMCP("obscura")
        browser_tool.register_browser_tools(server)
        tool = await server.get_tool("browser_cmd")
        result = await tool.fn(args=arguments, ctx=None)
        assert result["status"] == "unsupported_option"
    asyncio.run(scenario())


def test_backend_has_no_fallback_and_resets_by_generation():
    async def scenario():
        browser_tool.reset_browser_runtime_state()
        manager = SimpleNamespace(generation=999, exec_command=AsyncMock(return_value=ExecResult(0, "obscura 0.2.5", "", 0, "check")))
        ctx = SimpleNamespace(lifespan_context={"docker": manager, "concurrency": ConcurrencyManager()})
        prepared = await browser_tool._backend(ctx, "browser_open")
        assert prepared[2]["AGENT_BROWSER_ENGINE"] == "obscura"
        assert prepared[2]["OBSCURA_BLOCK_TRACKERS"] == "0"
        # Direct launch (no gateway): the engine is the minimal privilege-drop launcher.
        assert prepared[2]["AGENT_BROWSER_EXECUTABLE_PATH"] == "/opt/hercules/browser-launch.py"
        assert "boundary_enforced" not in prepared[2]
        manager.generation += 1
        manager.exec_command.return_value = ExecResult(1, "", "missing", 0, "check")
        assert isinstance(await browser_tool._backend(ctx, "browser_open"), dict)
        browser_tool.reset_browser_runtime_state()
    asyncio.run(scenario())


def test_prebuilt_catalog_requires_locked_identical_mirror_digests(tmp_path):
    catalog = tmp_path / "hercules/core/prebuilt_images.json"
    catalog.parent.mkdir(parents=True)
    facts = {"source": {"checkout": str(tmp_path)}, "image": {"fingerprint": "a" * 64, "target_platform": "linux/amd64", "custom_ca": {"configured": False}}}
    entry = {"fingerprint": "a" * 64, "source_revision": "b" * 40, "platform": "linux/amd64", "references": ["ghcr.io/owner/hercules@sha256:" + "c" * 64]}
    catalog.write_text(json.dumps({"schema_version": 1, "images": [entry]}))
    assert prebuilt_references(facts) == entry["references"]
    entry["references"].append("owner/hercules@sha256:" + "d" * 64)
    catalog.write_text(json.dumps({"schema_version": 1, "images": [entry]}))
    with pytest.raises(SetupError, match="invalid identity"):
        prebuilt_references(facts)


def test_browser_archive_rejects_links_and_traversal(tmp_path):
    spec = importlib.util.spec_from_file_location("browser_installer", ROOT / "docker/install-browser.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    archive = tmp_path / "malicious.tar"
    with tarfile.open(archive, "w") as bundle:
        info = tarfile.TarInfo("../escape")
        info.size = 1
        bundle.addfile(info, io.BytesIO(b"x"))
    with pytest.raises(ValueError, match="Unsafe archive"):
        module.extract_files(archive, tmp_path / "output", lambda p: PurePosixPath(p))


def test_cli_image_source_is_explicit():
    from hercules.setup_cli import parser
    args = parser().parse_args(["runtime", "prepare", "--client", "generic", "--image-source", "build"])
    assert args.image_source == "build"


def test_local_build_receipt_binds_immutable_id(monkeypatch, tmp_path):
    from hercules.core.build_info import locally_built_image, record_local_image
    monkeypatch.setattr("hercules.core.instance_lock._persistent_state_root", lambda: tmp_path)
    fingerprint, image_id = "a" * 64, "sha256:" + "b" * 64
    assert not locally_built_image(fingerprint, image_id)
    record_local_image(fingerprint, image_id)
    assert locally_built_image(fingerprint, image_id)
    assert not locally_built_image(fingerprint, "sha256:" + "c" * 64)
    with pytest.raises(ValueError):
        record_local_image("../escape", image_id)


def test_disk_reserve_stops_before_spawning(monkeypatch, tmp_path):
    from unittest.mock import Mock

    from hercules.setup.transaction import Transaction
    monkeypatch.setattr("shutil.disk_usage", lambda path: SimpleNamespace(free=1))
    spawn = Mock()
    monkeypatch.setattr("subprocess.Popen", spawn)
    transaction = Transaction(tmp_path / "transaction")
    with pytest.raises(SetupError, match="reserve"):
        transaction.run(["docker", "pull", "unused"], minimum_free_bytes=8 * 1024**3)
    spawn.assert_not_called()


def test_generation_sensitive_execution_never_replays(runtime):
    from hercules.core.docker_manager import ContainerUnavailable

    async def scenario():
        manager = runtime.manager
        await manager.operator_start()
        try:
            previous = manager.generation
            manager._generation += 1
            before = runtime.client.api.exec_create.call_count
            with pytest.raises(ContainerUnavailable, match="Generation changed"):
                await manager.exec_command("kill -TERM 321", expected_generation=previous)
            assert runtime.client.api.exec_create.call_count == before
        finally:
            await manager.operator_stop()
    asyncio.run(scenario())


def test_startup_asset_validation_never_downloads_or_extracts(tmp_path, monkeypatch):
    from unittest.mock import Mock

    from hercules.core.wordlists import cached_wordlists
    download, extract = Mock(), Mock()
    monkeypatch.setattr("hercules.core.wordlists._download_wordlist", download)
    monkeypatch.setattr("hercules.core.wordlists.ensure_extracted_wordlists", extract)
    with pytest.raises(RuntimeError, match="runtime prepare"):
        cached_wordlists(tmp_path / "missing", {"fuzz"})
    download.assert_not_called()
    extract.assert_not_called()
    assert not (tmp_path / "missing").exists()


def test_matching_labels_alone_are_not_a_trusted_cache(tmp_path, monkeypatch):
    import docker
    from hercules.core.build_info import record_local_image
    from hercules.setup.runtime import image_status

    monkeypatch.setattr("hercules.core.instance_lock._persistent_state_root", lambda: tmp_path / "receipts")
    image = SimpleNamespace(id="sha256:" + "b" * 64, attrs={"Os": "linux", "Architecture": "amd64", "Config": {"Labels": {"identity": "matches"}}, "RepoDigests": []})
    client = SimpleNamespace(images=SimpleNamespace(get=lambda tag: image), close=lambda: None)
    monkeypatch.setattr(docker, "from_env", lambda **kwargs: client)
    facts = {"source": {"checkout": str(tmp_path)}, "image": {"tag": "fake", "fingerprint": "a" * 64, "target_platform": "linux/amd64", "labels": {"identity": "matches"}, "custom_ca": {"configured": False}}}
    assert image_status(facts) == "unverified"
    record_local_image(facts["image"]["fingerprint"], image.id)
    assert image_status(facts) == "ready"


@pytest.mark.parametrize("cancel", [False, True])
def test_stop_is_serialized_with_termination_and_cancellation(runtime, cancel):
    async def scenario():
        manager = runtime.manager
        entered, release = asyncio.Event(), asyncio.Event()
        await manager.operator_start()

        async def terminating(job_id):
            entered.set()
            await release.wait()
            return {"confirmed": True}

        manager._terminate_current_job = AsyncMock(side_effect=terminating)
        task = asyncio.create_task(manager.terminate_job("owned"))
        await entered.wait()
        stopped = asyncio.create_task(manager.operator_stop())
        await asyncio.sleep(0)
        assert not stopped.done()
        if cancel:
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        else:
            release.set()
            assert (await task)["confirmed"]
        await stopped
        assert not manager._get_recovery_lock().locked()
        assert not runtime.containers
    asyncio.run(scenario())


def test_setup_timeout_has_phase_specific_recovery(monkeypatch, tmp_path):
    import subprocess
    from unittest.mock import Mock

    from hercules.setup.transaction import Transaction

    child = Mock(pid=999999)
    child.poll.return_value = None
    monkeypatch.setattr(subprocess, "Popen", Mock(return_value=child))
    with pytest.raises(SetupError) as caught:
        Transaction(tmp_path / "transaction").run(["fixture"], timeout=0)
    assert caught.value.code == "command_timeout"
    assert "resume" in caught.value.next_action
    child.terminate.assert_called_once()
