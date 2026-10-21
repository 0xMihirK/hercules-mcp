from __future__ import annotations

import asyncio
import json
import logging
import os
import shlex
import subprocess
import tempfile
import threading
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastmcp import FastMCP

from test_lifecycle_regressions import runtime as lifecycle_runtime
from hercules.core.concurrency import ConcurrencyManager
from hercules.core.config import HerculesConfig
from hercules.core.config_io import read_dotenv_value, render_dotenv
from hercules.core.docker_manager import ContainerUnavailable, DockerManager, ExecResult, RuntimeNotStarted
from hercules.core.instance_lock import workspace_lock
from hercules.core.workspace import WorkspaceManager
from hercules.output.sanitizer import render_terminal_result
from hercules.setup import workspace_migration
from hercules.setup.transaction import SetupError, Transaction, recover
from hercules.tools.exploitation import metasploit_tool
from hercules.tools.system.shell_tool import register_shell_tools


@pytest.fixture
def coordination(monkeypatch):
    with tempfile.TemporaryDirectory(prefix="hc-coord-") as directory:
        root = Path(directory)
        monkeypatch.setattr(
            "hercules.core.instance_lock._runtime_state_root", lambda: root
        )
        monkeypatch.setattr(
            "hercules.core.instance_lock._persistent_state_root", lambda: root
        )
        yield root


@pytest.fixture
def runtime(monkeypatch, tmp_path, coordination):
    return lifecycle_runtime.__wrapped__(monkeypatch, tmp_path)


def test_target_policy_validates_syntax_without_scope():
    # With no allow/block list, a well-formed target passes and a malformed one
    # still raises (structural validation survived the feature removal).
    from hercules.core.target_policy import TargetPolicy

    policy = TargetPolicy()
    policy.validate_target("example.com")
    policy.validate_target("10.0.0.5")
    with pytest.raises(ValueError):
        policy.validate_target("bad\x00name")


def test_dotenv_grammar_and_runtime_interpolation(tmp_path, monkeypatch):
    monkeypatch.setenv("AUDIT_BASE", "inherited")
    path = tmp_path / ".env"
    path.write_text(
        'AUDIT_BASE=file\nROOT=C:/ctf # evidence\nQUOTED="space # keep"\nEXPANDED=${AUDIT_BASE}/child\nDUP=one\nDUP=two\nEMPTY=\n',
        encoding="utf-8",
    )
    assert read_dotenv_value(path, "ROOT") == "C:/ctf"
    assert read_dotenv_value(path, "QUOTED") == "space # keep"
    assert read_dotenv_value(path, "EXPANDED") == "inherited/child"
    assert read_dotenv_value(path, "DUP") == "two"
    assert read_dotenv_value(path, "EMPTY") == ""
    text = render_dotenv(path.read_text(), {"ROOT": "C:\\space 😀\\#notes"})
    path.write_text(text, encoding="utf-8")
    assert read_dotenv_value(path, "ROOT") == "C:\\space 😀\\#notes"
    assert 'QUOTED="space # keep"' in text


def test_shell_audit_logs_do_not_contain_commands_or_secrets(caplog):
    manager = SimpleNamespace(
        session_id="owned",
        generation=2,
        write_file=AsyncMock(),
        exec_command=AsyncMock(return_value=ExecResult(0, "ok", "", 0, "script")),
        exec_background=AsyncMock(return_value="owned-job"),
    )
    server = FastMCP("audit fixture")
    register_shell_tools(server)
    context = SimpleNamespace(
        lifespan_context={"docker": manager, "concurrency": ConcurrencyManager()}
    )

    async def scenario():
        foreground = await server.get_tool("shell_exec")
        background = await server.get_tool("shell_exec_background")
        for command in (
            "sshpass -p FAKE_AUDIT_PASSWORD ssh local",
            "hydra -p FAKE_AUDIT_PASSWORD local ssh",
            "SSHPASS=FAKE_AUDIT_PASSWORD sshpass -e ssh local",
        ):
            await foreground.fn(command=command, ctx=context)
            await background.fn(command=command, job_id="owned-job", ctx=context)

    with caplog.at_level(logging.DEBUG):
        asyncio.run(scenario())
    assert "FAKE_AUDIT_PASSWORD" not in caplog.text
    assert "sshpass" not in caplog.text and "hydra" not in caplog.text
    assert caplog.text.count("invoked:") == 6
    assert "sha256=" in caplog.text and "generation=2" in caplog.text


def test_renderer_distinguishes_controls_from_hard_limits():
    assert not render_terminal_result("hello\x1b").clipped
    assert not render_terminal_result("hello\rworld\x1b[0m\n").clipped
    assert render_terminal_result("x" * 40000).column_clipped
    assert render_terminal_result("a\nb\nc", max_characters=3).character_clipped
    assert render_terminal_result("😀" * 12, max_columns=10).clipped
    assert not render_terminal_result("\x1b[999999G").clipped


def test_fake_docker_render_clipping_keeps_complete_raw_evidence(runtime, caplog):
    manager = runtime.manager
    manager._config = replace(manager._config, max_inline_response_chars=100000)
    runtime.client.api.exec_start.side_effect = lambda *args, **kw: iter(
        [(b"x" * 40000, b"")]
    )

    async def scenario():
        await manager.operator_start()
        try:
            result = await manager.exec_command(
                "sshpass -p FAKE_AUDIT_PASSWORD ssh local",
                max_output_chars=100000,
                compact_output=False,
            )
            assert (
                result.truncated
                and result.stdout_truncated
                and not result.output_complete
            )
            assert result.evidence_complete
            assert any(
                item["type"] == "terminal_limit" for item in result.output_transform
            )
            assert b"x" * 40000 in await manager.read_file_bytes(result.raw_artifact)
        finally:
            await manager.operator_stop()

    with caplog.at_level(logging.DEBUG):
        asyncio.run(scenario())
    assert "FAKE_AUDIT_PASSWORD" not in caplog.text


@pytest.mark.parametrize(
    "uuid,session_uuid,expected",
    [("own", "other", None), (None, "other", None), ("own", "own", "10")],
)
def test_metasploit_never_attributes_competing_session(
    monkeypatch, uuid, session_uuid, expected
):
    module = SimpleNamespace(execute=lambda **kw: {"job_id": 1, "uuid": uuid})
    msf = SimpleNamespace(
        sessions=SimpleNamespace(list={"10": {"exploit_uuid": session_uuid}})
    )
    monkeypatch.setattr(metasploit_tool, "_get_msf", AsyncMock(return_value=msf))
    monkeypatch.setattr(metasploit_tool, "_get_module", AsyncMock(return_value=module))
    monkeypatch.setattr(metasploit_tool, "_set_options", AsyncMock())
    monkeypatch.setattr(
        metasploit_tool, "_validate_options", AsyncMock(return_value={})
    )
    monkeypatch.setattr(metasploit_tool, "EXPLOIT_POLL_TIMEOUT", 0.01)
    monkeypatch.setattr(metasploit_tool, "EXPLOIT_POLL_INTERVAL", 0.001)

    async def rpc(call, **kw):
        return call()

    monkeypatch.setattr(metasploit_tool, "_rpc", rpc)
    server = FastMCP("attribution fixture")
    metasploit_tool.register_metasploit_tools(server)
    ctx = SimpleNamespace(lifespan_context={"concurrency": ConcurrencyManager()})

    async def scenario():
        tool = await server.get_tool("metasploit_run_module")
        return await tool.fn(
            module_type="exploit", module_name="fixture/local", options={}, ctx=ctx
        )

    result = asyncio.run(scenario())
    assert result["session_id"] == expected
    assert result["status"] == ("success" if expected else "warning")


def test_incomplete_background_identity_never_signals_stdout_pid(runtime):
    manager = runtime.manager

    async def scenario():
        await manager.operator_start()
        manager.exec_command = AsyncMock(
            return_value=ExecResult(0, "1234\n", "", 0, "launch")
        )
        manager.read_file = AsyncMock(side_effect=OSError("missing identity"))
        with pytest.raises(RuntimeError, match="Cleanup is unverified"):
            await manager.exec_background("true", "incomplete")
        assert manager.exec_command.await_count == 1
        metadata = manager._load_job_metadata("incomplete")
        assert metadata["cleanup_confirmed"] is False
        assert manager._workspace.read_chunk(
            manager.session_id, "jobs/incomplete.wrapper.sh"
        ).data
        await manager.operator_stop()

    asyncio.run(scenario())


def test_background_wrapper_owns_identity_and_handles_fast_completion(runtime):
    manager = runtime.manager

    async def scenario():
        await manager.operator_start()
        try:
            manager.exec_command = AsyncMock(
                return_value=ExecResult(0, "321\n", "", 0, "launch")
            )
            manager.read_file = AsyncMock(side_effect=["321", "321", "12345"])
            assert await manager.exec_background("true", "fast") == "fast"
            wrapper = manager._workspace.read_chunk(
                manager.session_id, "jobs/fast.wrapper.sh"
            ).data.decode()
            assert wrapper.index("pid=$$") < wrapper.index(
                "bash /opt/workspace/jobs/fast.command.sh"
            )
            launch = manager.exec_command.await_args.args[0]
            assert "ps -o pgid=" not in launch and "pid=$!" not in launch
            assert manager._load_job_metadata("fast")["start_ticks"] == "12345"
        finally:
            await manager.operator_stop()

    asyncio.run(scenario())


@pytest.fixture
def migration(tmp_path, monkeypatch, coordination):
    project = tmp_path / "project"
    project.mkdir()
    source = tmp_path / "original evidence"
    destination = tmp_path / "new 😀 evidence"
    manager = WorkspaceManager(source)
    session = manager.allocate_session()
    manager.atomic_write(session, "handout.bin", b"\x00\xffevidence", mode=0o600)
    env = tmp_path / "external.env"
    env.write_text(
        f'# keep comment\nSECRET_KEEP=fixture-secret\nHERCULES_WORKSPACE_ROOT="{source.as_posix()}"\n'
    )
    monkeypatch.setenv("HERCULES_ENV_FILE", str(env))
    monkeypatch.setattr(
        workspace_migration, "setup_state_locations", lambda project: {}
    )
    # All maintenance tests remain Docker-free, including mount checks.
    monkeypatch.setattr(
        WorkspaceManager, "assert_quiescent", lambda self: _owners_only(self)
    )
    config = HerculesConfig(project_root=project, workspace_root=source)
    return SimpleNamespace(
        manager=manager,
        session=session,
        source=source,
        destination=destination,
        config=config,
        env=env,
        project=project,
        tmp=tmp_path,
    )


def _owners_only(manager):
    from hercules.core.process_identity import owner_state

    for session in manager.list_sessions():
        state = owner_state(manager.read_manifest(session["session_id"]))
        if state != "dead":
            raise ValueError(f"owner is {state}")


def _registration(fixture, client="codex", *, state=None, env_override=None):
    from hercules.setup.clients import resolve

    path = fixture.tmp / f"{client}.json"
    adapter = resolve(client, "user", fixture.project, path)
    content, _ = adapter.render(
        Path(sys.executable),
        {
            "HERCULES_ENV_FILE": str(fixture.env),
            "HERCULES_WORKSPACE_ROOT": str(env_override or fixture.source),
        },
    )
    path.write_bytes(content)
    state = state or fixture.tmp / "managed/install.json"
    state.parent.mkdir(parents=True, exist_ok=True)
    data = (
        json.loads(state.read_text())
        if state.exists()
        else {
            "schema_version": 4,
            "clients": [],
            "registrations": {},
            "unknown_field": "keep",
        }
    )
    association = {
        "checkout": str(fixture.project),
        "scope": "user",
        "env_file": str(fixture.env),
        "workspace_root": str(fixture.source),
        "config_path": str(path),
    }
    data["clients"].append(client)
    data["registrations"][client] = association
    state.write_text(json.dumps(data))
    return state, adapter


def test_migration_cuts_over_selected_client_and_external_dotenv(migration):
    state, adapter = _registration(migration)
    result = workspace_migration.migrate(
        migration.config,
        migration.manager,
        migration.destination,
        states=[state],
        clients=["codex"],
    )
    assert not result["source_deleted"] and migration.source.exists()
    assert (
        migration.destination / migration.session / "handout.bin"
    ).read_bytes() == b"\x00\xffevidence"
    assert adapter.entry()["env"]["HERCULES_WORKSPACE_ROOT"] == str(
        migration.destination
    )
    assert read_dotenv_value(migration.env, "HERCULES_WORKSPACE_ROOT") == str(
        migration.destination
    )
    assert read_dotenv_value(migration.env, "SECRET_KEEP") == "fixture-secret"
    assert "# keep comment" in migration.env.read_text()
    assert not (migration.project / ".env").exists()
    assert json.loads(state.read_text())["unknown_field"] == "keep"


def test_migration_refuses_unselected_shared_client(migration):
    state, _ = _registration(migration)
    _registration(migration, "claude-code", state=state)
    with pytest.raises(ValueError, match="include it with --client"):
        workspace_migration.migrate(
            migration.config,
            migration.manager,
            migration.destination,
            states=[state],
            clients=["codex"],
        )
    assert not migration.destination.exists()
    result = workspace_migration.migrate(
        migration.config,
        migration.manager,
        migration.destination,
        states=[state],
        clients=["codex", "claude-code"],
    )
    assert result["source_retained"]


def test_live_cold_owner_blocks_copy_and_inline_deletion(migration):
    owner = DockerManager(
        replace(migration.config, project_root=Path(__file__).resolve().parents[1])
    )
    with pytest.raises(ValueError, match="owner is live"):
        migration.manager.migrate(migration.destination)
    assert owner.workspace_path.exists() and not migration.destination.exists()
    with pytest.raises(ValueError, match="retains the source"):
        migration.manager.migrate(migration.destination, delete_source=True)


def test_migration_detects_source_changes_and_cleans_staging(migration, monkeypatch):
    original = migration.manager._copy_anchor_tree

    def changed(*args, **kwargs):
        result = original(*args, **kwargs)
        (migration.source / migration.session / "handout.bin").write_bytes(b"changed")
        return result

    monkeypatch.setattr(migration.manager, "_copy_anchor_tree", changed)
    with pytest.raises(RuntimeError, match="source changed"):
        migration.manager.migrate(migration.destination)
    assert migration.source.exists() and not migration.destination.exists()
    assert not list(migration.tmp.glob(".*.hercules-migrate-*"))


def test_migration_rolls_back_cutover_on_interruption(migration, monkeypatch):
    state, adapter = _registration(migration)
    before = {path: path.read_bytes() for path in (state, adapter.path, migration.env)}
    original = Transaction.write

    def interrupted(self, path, *args, **kwargs):
        if Path(path) == migration.env:
            raise KeyboardInterrupt()
        return original(self, path, *args, **kwargs)

    monkeypatch.setattr(Transaction, "write", interrupted)
    with pytest.raises(KeyboardInterrupt):
        workspace_migration.migrate(
            migration.config,
            migration.manager,
            migration.destination,
            states=[state],
            clients=["codex"],
        )
    assert all(path.read_bytes() == content for path, content in before.items())
    assert migration.source.exists() and migration.destination.exists()


def test_retirement_rechecks_evidence_and_prevents_old_root_recreation(migration):
    workspace_migration.migrate(
        migration.config, migration.manager, migration.destination
    )
    with pytest.raises(ValueError, match="references-reviewed"):
        workspace_migration.retire(migration.config, migration.manager)
    source_file = migration.source / migration.session / "handout.bin"
    source_file.write_bytes(b"late evidence")
    with pytest.raises(ValueError, match="every source file"):
        workspace_migration.retire(
            migration.config, migration.manager, references_reviewed=True
        )
    source_file.write_bytes(b"\x00\xffevidence")
    result = workspace_migration.retire(
        migration.config, migration.manager, references_reviewed=True
    )
    assert result["source_deleted"] and not migration.source.exists()
    with pytest.raises(ValueError, match="retired"):
        WorkspaceManager(migration.source)


def test_workspace_lock_serializes_other_processes(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "LOCALAPPDATA" if os.name == "nt" else "XDG_RUNTIME_DIR",
        str(tmp_path / "runtime-state"),
    )
    root = tmp_path / "space 😀 root"
    code = 'import sys; from pathlib import Path; from hercules.core.instance_lock import workspace_lock\nwith workspace_lock(Path(sys.argv[1])): print("acquired", flush=True)'
    with workspace_lock(root):
        process = subprocess.Popen(
            [sys.executable, "-c", code, str(root)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        try:
            try:
                stdout, stderr = process.communicate(timeout=0.3)
            except subprocess.TimeoutExpired:
                pass
            else:
                pytest.fail(
                    f"lock child exited early ({process.returncode}): {stdout!r} {stderr!r}"
                )
        finally:
            # Only this exact fixture subprocess is managed; release before waiting.
            pass
    try:
        stdout, stderr = process.communicate(timeout=10)
        assert process.returncode == 0, stderr
        assert stdout.strip() == "acquired"
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=5)


def test_workspace_root_lock_is_reentrant(tmp_path):
    manager = WorkspaceManager(tmp_path / "root")
    with workspace_lock(manager.root):
        session = manager.allocate_session()
        manager.atomic_write(session, "a", b"a", mode=0o600)
        assert manager.read_chunk(session, "a").data == b"a"


def test_recovery_removes_only_identity_verified_migration_staging(tmp_path):
    destination = tmp_path / "destination"
    staging = tmp_path / ".destination.hercules-migrate-owned"
    staging.mkdir()
    (staging / "partial").write_bytes(b"owned")
    details = staging.stat()
    tx = Transaction(
        tmp_path / "journal/transactions/one",
        operation={"destination": str(destination)},
    )
    tx.data["workspace_staging"] = {
        "path": str(staging),
        "device": details.st_dev,
        "inode": details.st_ino,
    }
    tx.save()
    recover(tmp_path / "journal")
    assert not staging.exists()
    staging.mkdir()
    (staging / "unrelated").write_bytes(b"keep")
    tx.data["workspace_staging"]["inode"] = -1
    tx.save()
    with pytest.raises(SetupError, match="identity changed"):
        tx.cleanup_temporaries()
    assert (staging / "unrelated").exists()


def test_unknown_owner_blocks_migration_without_docker(migration, monkeypatch):
    from hercules.core.docker_manager import _process_start_token

    migration.manager.update_manifest(
        migration.session,
        state="active",
        owner_pid=os.getpid(),
        owner_start_token=_process_start_token(os.getpid()),
        container_started=False,
    )
    monkeypatch.setattr(
        "hercules.core.docker_manager._process_start_token", lambda pid: ""
    )
    with pytest.raises(ValueError, match="owner is unknown"):
        migration.manager.migrate(migration.destination)
    assert not migration.destination.exists()


def test_allocation_and_claim_cannot_race_workspace_copy(migration, monkeypatch):
    original = migration.manager._copy_anchor_tree
    started = threading.Event()
    allocated = []
    failures = []

    def connect():
        started.set()
        try:
            allocated.append(
                DockerManager(
                    replace(
                        migration.config,
                        project_root=Path(__file__).resolve().parents[1],
                    )
                )
            )
        except BaseException as exc:
            failures.append(exc)

    thread = threading.Thread(target=connect)

    def copy(*args, **kwargs):
        thread.start()
        assert started.wait(timeout=5)
        assert not allocated
        return original(*args, **kwargs)

    monkeypatch.setattr(migration.manager, "_copy_anchor_tree", copy)
    try:
        result = migration.manager.migrate(migration.destination)
    finally:
        if thread.ident is not None:
            thread.join(timeout=10)
    assert not thread.is_alive() and not failures
    assert result["migrated"] and len(allocated) == 1
    assert allocated[0]._client is None
    assert len(list(migration.destination.iterdir())) == 1
    assert len(migration.manager.list_sessions()) == 2


def test_retirement_failure_is_fenced_and_exact_retry_is_possible(
    migration, monkeypatch
):
    workspace_migration.migrate(
        migration.config, migration.manager, migration.destination
    )
    remove = migration.manager._remove_tree_at
    monkeypatch.setattr(
        migration.manager,
        "_remove_tree_at",
        lambda *args: (_ for _ in ()).throw(OSError("locked fixture file")),
    )
    with pytest.raises(SetupError, match="Source cleanup was interrupted"):
        workspace_migration.retire(
            migration.config, migration.manager, references_reviewed=True
        )
    assert migration.source.exists() and migration.destination.exists()
    with pytest.raises(ValueError, match="retired"):
        WorkspaceManager(migration.source)
    resumed = WorkspaceManager(migration.source, allow_retired=True)
    monkeypatch.setattr(resumed, "_remove_tree_at", remove)
    assert workspace_migration.retire(
        migration.config, resumed, references_reviewed=True
    )["source_deleted"]
    absent = WorkspaceManager(migration.source, allow_retired=True)
    assert not migration.source.exists()
    assert workspace_migration.retire(
        migration.config, absent, references_reviewed=True
    )["already_retired"]


def test_retirement_refuses_pinned_or_unowned_root_data(migration):
    workspace_migration.migrate(
        migration.config, migration.manager, migration.destination
    )
    migration.manager.pin(migration.session, True)
    with pytest.raises(ValueError, match="pinned"):
        workspace_migration.retire(
            migration.config, migration.manager, references_reviewed=True
        )
    migration.manager.pin(migration.session, False)
    (migration.source / "unrelated.txt").write_bytes(b"not-owned")
    with pytest.raises(ValueError, match="unowned root entry"):
        workspace_migration.retire(
            migration.config, migration.manager, references_reviewed=True
        )
    assert migration.source.exists()


def test_direct_metasploit_render_cap_keeps_raw_artifact():
    manager = SimpleNamespace(write_file=AsyncMock())
    ctx = SimpleNamespace(lifespan_context={"docker": manager})
    result = asyncio.run(
        metasploit_tool._session_output_result(
            ctx, session_id=1, status="success", message="fixture", output="x" * 40000
        )
    )
    assert not result["output_complete"] and result["evidence_complete"]
    assert result["truncated"] and result["raw_artifact"]
    assert any(item["type"] == "terminal_limit" for item in result["output_transform"])
    assert manager.write_file.await_args.args[1] == "x" * 40000


def test_real_renderer_character_cap():
    from hercules.output.sanitizer import MAX_RENDERED_CHARACTERS

    result = render_terminal_result("x\n" * (MAX_RENDERED_CHARACTERS // 2 + 10))
    assert result.character_clipped
    assert len(result.text) == MAX_RENDERED_CHARACTERS


@pytest.mark.parametrize(
    "identity", [("0", "0", "123"), ("321", "322", "123"), ("321", "321", "unknown")]
)
def test_invalid_background_group_identity_does_not_signal(runtime, identity):
    manager = runtime.manager

    async def scenario():
        await manager.operator_start()
        try:
            manager.exec_command = AsyncMock(
                return_value=ExecResult(0, "321", "", 0, "fixture launch")
            )
            manager.read_file = AsyncMock(side_effect=identity)
            with pytest.raises(RuntimeError, match="invalid process-group identity"):
                await manager.exec_background("true", "invalid-group")
            assert manager.exec_command.await_count == 1
        finally:
            await manager.operator_stop()

    asyncio.run(scenario())


def test_cancelled_background_launch_settles_then_uses_verified_termination(runtime):
    manager = runtime.manager

    async def scenario():
        await manager.operator_start()
        entered = asyncio.Event()
        release = asyncio.Event()

        async def launch(*args, **kwargs):
            entered.set()
            await release.wait()
            return ExecResult(0, "321", "", 0, "fixture launch")

        manager.exec_command = AsyncMock(side_effect=launch)
        manager.read_file = AsyncMock(side_effect=["321", "321", "123"])
        manager.terminate_job = AsyncMock(return_value={"confirmed": True})
        try:
            task = asyncio.create_task(manager.exec_background("true", "cancelled"))
            await asyncio.wait_for(entered.wait(), timeout=5)
            task.cancel()
            release.set()
            with pytest.raises(asyncio.CancelledError):
                await task
            manager.terminate_job.assert_awaited_once_with("cancelled")
            assert manager._load_job_metadata("cancelled")["start_ticks"] == "123"
        finally:
            await manager.operator_stop()

    asyncio.run(scenario())


def test_cancelled_duplicate_launch_does_not_terminate_existing_job(runtime):
    manager = runtime.manager

    async def scenario():
        await manager.operator_start()
        entered = asyncio.Event()
        release = asyncio.Event()
        metadata = {
            "state": "running", "pid": 321, "pgid": 321, "start_ticks": "123",
            "generation": manager.generation,
        }
        manager._save_job_metadata("existing", metadata)

        async def status(_metadata):
            entered.set()
            await release.wait()
            return {"running": True}

        manager._job_process_status = AsyncMock(side_effect=status)
        manager.terminate_job = AsyncMock()
        try:
            task = asyncio.create_task(manager.exec_background("true", "existing"))
            await asyncio.wait_for(entered.wait(), timeout=5)
            task.cancel()
            release.set()
            with pytest.raises(asyncio.CancelledError):
                await task
            manager.terminate_job.assert_not_awaited()
            assert manager._load_job_metadata("existing") == metadata
        finally:
            await manager.operator_stop()

    asyncio.run(scenario())


@pytest.mark.parametrize("suffix", [".lock", ".migration-state", ".migration.json", ".retired.json"])
@pytest.mark.parametrize("custom_state", [False, True])
def test_workspace_coordination_is_durable_across_runtime_directory_changes(
    monkeypatch, tmp_path, suffix, custom_state,
):
    from hercules.core import instance_lock

    monkeypatch.setattr(instance_lock.platform, "system", lambda: "Linux")
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")
    if custom_state:
        monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
        base = tmp_path / "state"
    else:
        monkeypatch.delenv("XDG_STATE_HOME", raising=False)
        base = tmp_path / "home/.local/state"
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path / "runtime-before"))
    before = instance_lock.workspace_state_path(tmp_path / "evidence", suffix)
    assert before.is_relative_to(base)
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path / "runtime-after"))
    assert instance_lock.workspace_state_path(tmp_path / "evidence", suffix) == before
    assert instance_lock._runtime_state_root().is_relative_to(tmp_path / "runtime-after")


def test_explicit_state_selection_does_not_modify_other_scope(migration, monkeypatch):
    selected, adapter = _registration(migration)
    other, _ = _registration(
        migration, state=migration.tmp / "other-scope/install.json"
    )
    monkeypatch.setattr(
        workspace_migration,
        "setup_state_locations",
        lambda project: {"other": str(other)},
    )
    before = adapter.path.read_bytes()
    with pytest.raises(ValueError, match="was not selected"):
        workspace_migration.migrate(
            migration.config,
            migration.manager,
            migration.destination,
            states=[selected],
            clients=["codex"],
        )
    assert adapter.path.read_bytes() == before and not migration.destination.exists()


def test_migration_does_not_remove_preexisting_unowned_staging(migration, monkeypatch):
    hex_id = "0" * 32
    staging = migration.destination.with_name(f".{migration.destination.name}.hercules-migrate-{hex_id}")
    staging.mkdir()
    (staging / "keep.txt").write_bytes(b"unowned")
    monkeypatch.setattr("hercules.core.workspace.uuid.uuid4", lambda: SimpleNamespace(hex=hex_id))
    with pytest.raises(FileExistsError):
        migration.manager.migrate(migration.destination)
    assert (staging / "keep.txt").read_bytes() == b"unowned"


def test_empty_destination_race_cannot_delete_new_user_file(migration, monkeypatch):
    migration.destination.mkdir()
    original = migration.manager._list_anchor_names
    def raced(anchor):
        names = original(anchor)
        (migration.destination / "late-user-file.txt").write_bytes(b"retain")
        return names
    monkeypatch.setattr(migration.manager, "_list_anchor_names", raced)
    with pytest.raises(OSError):
        migration.manager.migrate(migration.destination)
    assert (migration.destination / "late-user-file.txt").read_bytes() == b"retain"
    assert migration.source.exists()


def test_migration_can_replace_an_empty_destination(migration):
    migration.destination.mkdir()
    assert migration.manager.migrate(migration.destination)["migrated"]
    assert (migration.destination / migration.session / "handout.bin").read_bytes() == b"\x00\xffevidence"


# --- /ponytail-audit safe-set regression tests ---


def test_browser_ref_selector_is_shlex_quoted():
    """#1: a ref selector with shell metacharacters stays one quoted argument."""
    from hercules.tools.browser.browser_tool import _selector_token

    token = _selector_token("e1; id #", "ref")
    assert token == shlex.quote("@e1; id #")
    assert shlex.split(f"agent-browser click {token}") == [
        "agent-browser",
        "click",
        "@e1; id #",
    ]


def test_render_terminal_drops_bidi_controls():
    """#5: a Trojan-Source RTL override must not survive into returned output."""
    spoof = "safe‮evil‬ text"
    rendered = render_terminal_result(spoof).text
    assert "‮" not in rendered
    assert "‬" not in rendered


def test_nmap_format_result_flags_second_truncation_incomplete():
    """#6: the second stdout trim must flip output_complete, not leave it True."""
    from hercules.tools.network import nmap_tool

    class _Res:
        exit_code = 0
        stdout = "A" * 9000

        def to_dict(self):
            return {
                "stdout": self.stdout,
                "output_complete": True,
                "stdout_truncated": False,
                "exit_code": 0,
            }

    base = nmap_tool._format_result(_Res())
    assert base["truncated"] is True
    assert base["stdout_truncated"] is True
    assert base["output_complete"] is False
    assert len(base["stdout"]) < 9000


def test_background_job_before_start_reports_runtime_not_started(runtime):
    """#9: a background job before start returns the actionable guidance."""
    manager = runtime.manager
    assert manager._operator_stopped is True
    with pytest.raises(RuntimeNotStarted, match="system_start_container"):
        asyncio.run(manager.exec_background("sleep 1", "job-guidance"))


def test_secret_values_are_redacted_in_returned_output(runtime):
    """#2: a secret in command output is redacted in the returned stream."""
    manager = runtime.manager
    manager._config = replace(manager._config, msf_password="s3cr3t-pw-42")

    async def scenario():
        await manager.operator_start()
        try:
            runtime.client.api.exec_start.side_effect = lambda *a, **k: iter(
                [(b"found pass=s3cr3t-pw-42 in config", b"")]
            )
            result = await manager.exec_command("cat creds", clean_output=True)
            assert "s3cr3t-pw-42" not in result.stdout
        finally:
            await manager.operator_stop()

    asyncio.run(scenario())


def test_network_mode_defaults_host_and_honors_override():
    # Host networking is the default; an explicit HERCULES_DOCKER_NETWORK override
    # still selects a named network.
    manager = DockerManager.__new__(DockerManager)
    manager._config = SimpleNamespace(docker_network="")
    assert manager.network_mode == "host"
    manager._config = SimpleNamespace(docker_network="mybridge")
    assert manager.network_mode == "mybridge"


def test_browser_relay_port_matches_host_port_under_host_mode(monkeypatch):
    # Host networking never publishes ports, so the relay must bind the exact
    # port the consumer connects to on every platform — including a non-Linux
    # Docker Desktop VM, where the old code picked a distinct, never-remapped
    # relay port that left the stream unreachable. Faking a non-Linux platform
    # exercises that branch; constructing a real manager would take the
    # workspace lock down the Windows (msvcrt) path on a Linux CI runner.
    from hercules.core import docker_manager as dm

    monkeypatch.setattr(dm.platform, "system", lambda: "Windows")
    host = DockerManager.__new__(DockerManager)
    host._config = SimpleNamespace(docker_network="host")
    assert host._resolve_relay_port(7900) == 7900
    # The named-bridge override still uses a distinct published container port.
    bridge = DockerManager.__new__(DockerManager)
    bridge._config = SimpleNamespace(docker_network="labnet")
    assert bridge._resolve_relay_port(7900) != 7900


def test_browser_stream_relay_probe_gates_host_reachability(monkeypatch):
    # The in-container listener can be up while the host cannot reach it (Docker
    # Desktop host networking off). The relay must report that honestly and tear
    # itself down, not claim stream_active on a port the host cannot connect to.
    from hercules.core import docker_manager as dm

    monkeypatch.setattr(dm.platform, "system", lambda: "Windows")
    mgr = DockerManager.__new__(DockerManager)
    mgr._config = SimpleNamespace(docker_network="host")
    mgr._browser_stream_host_port = 7900
    mgr._browser_stream_relay_port = 7900
    mgr._generation = 1
    mgr._browser_stream_lock = None
    mgr._browser_stream_relay_state = {}
    captured: dict[str, str] = {}
    stopped = {"n": 0}

    async def fake_exec(command, **kwargs):
        captured["command"] = command
        return SimpleNamespace(exit_code=0, stdout="111 222 333", stderr="")

    async def running(_state):
        return True

    async def stop(_state):
        stopped["n"] += 1
        return True

    mgr.exec_command = fake_exec
    mgr._browser_relay_is_running = running
    mgr._stop_browser_stream_relay = stop

    async def unreachable(_port):
        return False

    mgr._browser_relay_reachable_from_host = unreachable
    res = asyncio.run(mgr.ensure_browser_stream_relay(session="s", backend_port=9333))
    assert res["relay_status"] == "unreachable_from_host"
    assert res["stream_active"] is False
    assert stopped["n"] == 1  # the orphan relay was torn down
    assert "0.0.0.0" in captured["command"]  # non-Linux host mode binds all interfaces

    async def reachable(_port):
        return True

    mgr._browser_stream_relay_state = {}
    mgr._browser_relay_reachable_from_host = reachable
    res2 = asyncio.run(mgr.ensure_browser_stream_relay(session="s", backend_port=9333))
    assert res2["relay_status"] == "started"
    assert res2["stream_active"] is True


def test_listener_reachability_warning_flags_unforwarded_and_udp(monkeypatch):
    # Workstream E: on bridge, a port outside the forwarded TCP set or a UDP
    # listener is not reachable from an external target — warn loudly, not silently.
    from hercules.core import guidance
    from hercules.core.guidance import listener_reachability_warning

    bridged = SimpleNamespace(network_mode="bridge", listener_ports=(4444, 4445))
    assert listener_reachability_warning(bridged, 4444) == ""
    assert "not forwarded" in listener_reachability_warning(bridged, 9001)
    assert "UDP" in listener_reachability_warning(bridged, 4444, protocol="udp")
    host = SimpleNamespace(network_mode="host", listener_ports=(4444,))
    # Native Linux host networking really binds the host: nothing to warn about.
    monkeypatch.setattr(guidance.platform, "system", lambda: "Linux")
    assert listener_reachability_warning(host, 9001) == ""
    assert listener_reachability_warning(host, 9001, protocol="udp") == ""
    # A Docker Desktop VM (non-Linux) may silently drop the callback: warn for
    # both TCP and UDP instead of returning a falsely reassuring empty string.
    monkeypatch.setattr(guidance.platform, "system", lambda: "Windows")
    assert "Docker Desktop" in listener_reachability_warning(host, 9001)
    assert "Docker Desktop" in listener_reachability_warning(host, 9001, protocol="udp")


def test_exec_aborts_on_session_rotation_but_not_recovery(runtime):
    # #4: abort_if_session_changed aborts cleanly when the pinned session no longer
    # matches (system_stop/new_session rotated it between write and exec), without
    # disabling container auto-recovery for a same-session crash (the lifecycle
    # recovery test, which now relies on this parameter, must still pass — recovery
    # bumps the generation but keeps the session).
    manager = runtime.manager

    async def scenario():
        await manager.operator_start()
        try:
            with pytest.raises(ContainerUnavailable, match="Session rotated"):
                await manager.exec_command(
                    "local-fixture",
                    clean_output=False,
                    abort_if_session_changed="some-other-session",
                )
        finally:
            await manager.operator_stop()

    asyncio.run(scenario())


def test_image_fingerprint_covers_label_keys(monkeypatch):
    # #3: adding/renaming a validated label key must change the build fingerprint,
    # so a stale published image misses the catalog (build fallback) instead of
    # being pulled and then rejected on a label mismatch.
    from hercules.core import build_info

    base = build_info.image_build_fingerprint(Path("."), target_platform="linux/amd64")
    monkeypatch.setattr(
        build_info,
        "IMAGE_LABEL_KEYS",
        build_info.IMAGE_LABEL_KEYS + ("hercules.some_new_label",),
    )
    changed = build_info.image_build_fingerprint(Path("."), target_platform="linux/amd64")
    assert base != changed


def test_validated_image_labels_match_fingerprint_key_set():
    # #3 coupling guard: the labels validated on a pulled image (setup_info) must
    # be exactly the key set folded into the fingerprint, so the two cannot drift.
    from hercules.core.build_info import IMAGE_LABEL_KEYS
    from hercules.core.setup_info import setup_information

    facts = setup_information(Path(__file__).resolve().parents[1])
    assert set(facts["image"]["labels"]) == set(IMAGE_LABEL_KEYS)


def test_setup_facts_do_not_claim_removed_private_address_protection():
    from hercules.core.setup_info import setup_information
    from hercules.core.target_policy import TargetPolicy

    facts = setup_information(Path(__file__).resolve().parents[1])
    assert facts["runtime"]["browser_networking"]["private_addresses_denied_unconditionally"] is False
    assert "no SSRF boundary" in facts["browser"]["boundary"]
    for target in ("http://127.0.0.1/", "http://10.0.0.1/", "http://169.254.169.254/"):
        TargetPolicy().validate_target(target)
