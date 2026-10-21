from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from hercules.setup.clients import CLIENTS, duplicate_entries, resolve
from hercules.setup.documents import ConfigError, JsonDocument, edit, lookup, parse
from hercules.setup.engine import Engine
from hercules.setup.transaction import InstallLock, SetupError, Transaction, recover
from hercules.setup_cli import parser


def test_browser_only_runtime_verification_does_not_require_curl(monkeypatch, tmp_path):
    import asyncio
    import shlex
    import urllib.request
    from types import SimpleNamespace
    from unittest.mock import Mock

    import fastmcp

    from hercules.setup.runtime import verify

    opener = Mock()
    build_opener = Mock(return_value=opener)
    monkeypatch.setattr(urllib.request, "build_opener", build_opener)
    readiness_commands = []

    class Client:
        def __init__(self, *args, **kwargs):
            self.running = False

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def list_tools(self):
            return []

        async def list_resources(self):
            return []

        async def call_tool(self, name, arguments=None, **kwargs):
            result = {"status": "success", "exit_code": 0}
            if name == "system_start_container":
                result.update(session_id="fixture", start_mode="already_running" if self.running else "created")
                self.running = True
            elif name == "shell_exec":
                command = arguments["command"]
                if not self.running:
                    result = {"error_type": "runtime_not_started"}
                elif command == "printf hercules-local-ok":
                    result["stdout"] = "hercules-local-ok"
                elif command != "true":
                    readiness_commands.append(command)
                    executable, flag, code = shlex.split(command)
                    assert (executable, flag) == ("python3", "-c")
                    exec(code, {})  # noqa: S102 — execute only the literal local readiness fixture
            elif name == "system_network_info":
                result["port_allocation"] = {"effective": {"metasploit_rpc": 0, "browser_stream": 0, "listeners": []}}
            elif name == "system_stop_container":
                self.running = False
            return SimpleNamespace(structured_content=result)

    monkeypatch.setattr(fastmcp, "Client", Client)
    result = asyncio.run(verify(
        tmp_path / "hercules", {},
        {"selection": {"capabilities": ["shell", "session", "browser"]},
         "mcp_surface": {"tool_names": [], "resource_uris": []}},
        tmp_path / "workspace", runtime=True,
    ))
    assert result["runtime"] == "passed"
    assert "local_browser" in result["checks"]
    assert len(readiness_commands) == 1
    assert not build_opener.call_args.args[0].proxies
    opener.open.assert_called_once_with("http://127.0.0.1:18080/", timeout=2)
    opener.open.return_value.close.assert_called_once_with()


@pytest.mark.parametrize(
    "text",
    [
        "{}",
        '{/*keep*/ "other": [1, {"x": "comma, //not a comment"}],}',
        '{"mcpServers": {"other": {"command": "keep"}}}',
        '{"mcpServers": {"hercules": {"command": "old"}, // leave this\n"other": {}}}',
    ],
)
def test_jsonc_target_edit_and_delete(text):
    path = ("mcpServers", "hercules")
    original = parse(text, "json")
    result = edit(
        text, "json", path, {"command": "C:/Mihir Katoch/😀/hercules.exe", "args": []}
    )
    assert lookup(parse(result, "json"), path)["args"] == []
    assert parse(result, "json").get("other") == original.get("other")
    restored = edit(result, "json", path, lookup(original, path))
    assert lookup(parse(restored, "json"), path) == lookup(original, path)
    if "leave this" in text:
        assert "leave this" in restored


@pytest.mark.parametrize(
    "text", ['{"x":1,"x":2}', '{"a": [}', '{"a":1 "b":2}', "{} trailing"]
)
def test_jsonc_rejects_ambiguous_input(text):
    with pytest.raises(ValueError):
        JsonDocument(text)


@pytest.mark.parametrize(
    "format,text,path",
    [
        (
            "toml",
            '# keep\nmodel = "test"\n[mcp_servers.other]\ncommand="safe"\n',
            ("mcp_servers", "hercules"),
        ),
        (
            "yaml",
            "# keep\nmodel: test\nmcp_servers:\n  other:\n    command: safe\n",
            ("mcp_servers", "hercules"),
        ),
    ],
)
def test_roundtrip_preserves_comments_and_other_settings(format, text, path):
    modified = edit(text, format, path, {"command": "/absolute/hercules", "args": []})
    assert "# keep" in modified
    assert parse(modified, format)["model"] == "test"
    assert parse(modified, format)["mcp_servers"]["other"]["command"] == "safe"


@pytest.fixture
def isolated_home(monkeypatch, tmp_path):
    home = tmp_path / "User Space 😀"
    home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)
    for key in (
        "APPDATA",
        "LOCALAPPDATA",
        "XDG_CONFIG_HOME",
        "CLAUDE_CONFIG_DIR",
        "CODEX_HOME",
        "HERMES_HOME",
        "OPENCODE_CONFIG",
        "OPENCODE_CONFIG_CONTENT",
        "OPENCODE_CONFIG_DIR",
    ):
        monkeypatch.delenv(key, raising=False)
    return home


@pytest.mark.parametrize("name", CLIENTS)
def test_adapter_only_renders_selected_client(name, isolated_home):
    if name == "claude-desktop" and sys.platform not in ("win32", "darwin"):
        pytest.skip("claude-desktop user scope is Windows/macOS only")
    adapter = resolve(name, "user", isolated_home)
    content, entry = adapter.render(
        isolated_home / "release/hercules.exe",
        {"HERCULES_ENV_FILE": str(isolated_home / ".env")},
    )
    assert not list(isolated_home.iterdir())
    if name == "opencode":
        assert isinstance(entry["command"], list)
    else:
        assert Path(entry["command"]).is_absolute()
    assert lookup(parse(content.decode(), adapter.format), adapter.keys) == entry


def test_preserve_overrides_and_disabled_state(isolated_home):
    adapter = resolve("opencode", "user", isolated_home)
    adapter.path.parent.mkdir(parents=True)
    adapter.path.write_text(
        '{//comment\n"model":"keep", "mcp":{"hercules":{"type":"local","command":["old"],"enabled":false,"environment":{"MSF_RPC_PORT":"56000"}}}}'
    )
    output, entry = adapter.render(
        isolated_home / "new", {"HERCULES_ENV_FILE": str(isolated_home / ".env")}
    )
    assert "//comment" in output.decode()
    assert entry["enabled"] is False
    assert entry["environment"]["MSF_RPC_PORT"] == "56000"
    assert parse(output.decode(), "json")["model"] == "keep"


def test_nested_opencode_and_duplicate_detection(isolated_home, monkeypatch):
    path = isolated_home / "custom.jsonc"
    path.write_text(
        '{"mcp":{"servers":{"hercules":{"command":["old"]},"hercules-other":{"command":["else"]}}}}'
    )
    monkeypatch.setenv("OPENCODE_CONFIG", str(path))
    adapter = resolve("opencode", "user", isolated_home)
    assert adapter.keys == ("mcp", "servers", "hercules")
    assert duplicate_entries(adapter) == ["mcp.servers.hercules-other"]


def test_secret_values_never_enter_rendered_registration(isolated_home):
    adapter = resolve("claude-code", "user", isolated_home)
    adapter.path.write_text(
        '{"mcpServers":{"hercules":{"env":{"MSF_PASSWORD":"do-not-print"}}}}'
    )
    with pytest.raises(ConfigError) as error:
        adapter.render(isolated_home / "new", {})
    assert "do-not-print" not in str(error.value)


def test_transaction_rolls_back_only_its_entry(tmp_path):
    path = tmp_path / "config.jsonc"
    original = b'{// keep\n"model":"old","mcpServers":{"hercules":{"command":"old"}}}'
    path.write_bytes(original)
    tx = Transaction(tmp_path / "tx")
    updated = edit(
        original.decode(), "json", ("mcpServers", "hercules"), {"command": "new"}
    ).encode()
    tx.write(
        path,
        updated,
        expected=original,
        entry={"keys": ["mcpServers", "hercules"], "format": "json"},
    )
    path.write_text(path.read_text().replace('"model":"old"', '"model":"concurrent"'))
    assert tx.rollback() == []
    restored = path.read_text()
    assert "// keep" in restored
    assert parse(restored, "json")["model"] == "concurrent"
    assert parse(restored, "json")["mcpServers"]["hercules"]["command"] == "old"


def test_concurrent_entry_edit_is_not_overwritten(tmp_path):
    path = tmp_path / "config"
    path.write_bytes(b"old")
    tx = Transaction(tmp_path / "tx")
    tx.write(path, b"ours", expected=b"old")
    path.write_bytes(b"user-change")
    assert tx.rollback() == [str(path)]
    assert path.read_bytes() == b"user-change"
    assert (tmp_path / "tx/0.before").exists()


def test_recovery_after_write_before_commit(tmp_path):
    path = tmp_path / "config"
    tx = Transaction(tmp_path / "transactions/one")
    tx.write(path, b"new", expected=None)
    recover(tmp_path)
    assert not path.exists()
    assert not list((tmp_path / "transactions/one").glob("*.before"))


def test_committed_transaction_survives_recovery(tmp_path):
    path = tmp_path / "config"
    tx = Transaction(tmp_path / "transactions/one")
    tx.write(path, b"new", expected=None)
    tx.phase("committed")
    recover(tmp_path)
    assert path.read_bytes() == b"new"


def test_installation_lock_prevents_concurrent_writers(tmp_path):
    with InstallLock(tmp_path / "setup.lock"), pytest.raises(SetupError, match="Another setup"), InstallLock(tmp_path / "setup.lock"):
        pass


@pytest.fixture
def fake_engine(monkeypatch, tmp_path, isolated_home):
    root = tmp_path / "managed"
    source = tmp_path / "source"
    (source / "skills/hercules-mcp").mkdir(parents=True)
    (source / "skills/hercules-mcp/SKILL.md").write_text("fixture skill")
    args = parser().parse_args(
        ["install", "--client", "claude-code", "--root", str(root), "--yes"]
    )
    instance = Engine(args)
    monkeypatch.setattr(instance, "source", lambda **kw: (source, "a" * 40))
    monkeypatch.setattr(instance, "sync", lambda path: None)
    facts = {
        "image": {"tag": "fixture", "fingerprint": "a"},
        "selection": {"capabilities": ["shell", "session", "workspace"]},
    }

    def fake_facts(candidate):
        candidate.update(
            image="fixture",
            image_fingerprint="a",
            image_platform="linux/amd64",
            expected_tool_count=12,
            resources_count=7,
        )
        return facts

    monkeypatch.setattr(instance, "facts", fake_facts)

    def verify(candidate, facts, **kw):
        candidate["verification"] = {"host": "passed", "runtime": "not_run"}
        return candidate["verification"]

    monkeypatch.setattr(instance, "verify_candidate", verify)
    monkeypatch.setattr("hercules.setup.engine.image_status", lambda facts: "missing")
    monkeypatch.setattr(instance, "assets_ready", lambda *args: True)
    monkeypatch.setattr(
        "hercules.setup.engine.validate_native_entry", lambda *args: "document_adapter"
    )
    return instance


def test_first_install_only_writes_current_client(fake_engine, isolated_home):
    result = fake_engine.execute("install")
    assert result["host"] == "installed"
    assert result["runtime_preparation"] == "required"
    assert result["verification"]["runtime"] == "not_run"
    assert resolve("claude-code", "user", isolated_home).path.exists()
    assert not resolve("opencode", "user", isolated_home).path.exists()
    state = json.loads(fake_engine.state_path.read_text())
    assert state["clients"] == ["claude-code"]
    assert state["schema_version"] == 4


def test_bridge_override_is_selected_client_only(fake_engine):
    fake_engine.args.capabilities = "all"
    fake_engine.args.docker_network = "chosen-lab"
    result = fake_engine.execute("install")
    assert result["registration"] == "configured"
    entry = fake_engine.adapter.entry()
    assert entry["env"]["HERCULES_DOCKER_NETWORK"] == "chosen-lab"
    state = json.loads(fake_engine.state_path.read_text())
    assert "HERCULES_DOCKER_NETWORK" not in Path(state["env_file"]).read_text()
    assert state["clients"] == ["claude-code"]


def test_fresh_selected_root_does_not_adopt_unrelated_legacy_home(fake_engine, isolated_home):
    legacy = isolated_home / ".hercules-mcp"
    (legacy / "workspace").mkdir(parents=True)
    environment = legacy / ".env"
    original = b"HERCULES_INSTALLED_CAPABILITIES=all\nMSF_PASSWORD=unrelated-fixture-secret\n"
    environment.write_bytes(original)
    (legacy / "workspace/retained.txt").write_text("unrelated evidence")
    fake_engine.execute("install")
    state = json.loads(fake_engine.state_path.read_text())
    assert Path(state["env_file"]) == fake_engine.root / "data/.env"
    assert Path(state["workspace_root"]) == fake_engine.root / "data/workspace"
    assert Path(state["wordlist_root"]) == fake_engine.root / "data/wordlists"
    assert environment.read_bytes() == original
    assert (legacy / "workspace/retained.txt").read_text() == "unrelated evidence"


def test_existing_linux_install_defaults_to_host(fake_engine, monkeypatch):
    # Host networking is the default; a browser install pins host explicitly.
    monkeypatch.setattr("hercules.setup.engine.platform.system", lambda: "Linux")
    fake_engine.args.capabilities = "all"
    fake_engine.old = {"image_fingerprint": "old"}
    fake_engine.execute("install")
    assert fake_engine.pending()["environment"]["HERCULES_DOCKER_NETWORK"] == "host"


def test_pending_runtime_verification_does_not_touch_active_state(fake_engine, monkeypatch):
    fake_engine.old = {"image_fingerprint": "old"}
    fake_engine.execute("install")
    before = (fake_engine.adapter.path.read_bytes() if fake_engine.adapter.path.exists() else None)
    fake_engine.args.pending, fake_engine.args.runtime = True, True
    def verified(candidate, facts, **kwargs):
        assert kwargs["runtime"] is True
        candidate["verification"] = {"host": "passed", "runtime": "passed"}
        candidate["runtime_verification"] = {"runtime": "passed", "binding": {"image_id": "immutable"}}
        return candidate["verification"]
    monkeypatch.setattr(fake_engine, "verify_candidate", verified)
    result = fake_engine.execute("verify")
    assert result["registration"] == "unchanged"
    assert not fake_engine.state_path.exists()
    assert (fake_engine.adapter.path.read_bytes() if fake_engine.adapter.path.exists() else None) == before
    assert fake_engine.pending()["runtime_verification"]["binding"]["image_id"] == "immutable"


def test_stale_pending_browser_proof_blocks_resume(fake_engine, monkeypatch):
    fake_engine.args.capabilities = "all"
    source, _ = fake_engine.source()
    fake_engine.old = {"checkout": str(source), "commit": "old", "image_fingerprint": "old"}
    fake_engine.execute("install")
    candidate = fake_engine.pending()
    candidate["runtime_verification"] = {"runtime": "passed", "binding": {"image_id": "old-image"}}
    fake_engine.save_pending(candidate)
    monkeypatch.setattr("hercules.setup.engine.image_status", lambda facts: "ready")
    monkeypatch.setattr(fake_engine, "verification_binding", lambda *args: {"image_id": "changed-image"})
    with pytest.raises(SetupError) as caught:
        fake_engine.execute("resume")
    assert caught.value.code == "verification_stale"
    assert not fake_engine.adapter.path.exists()


def test_runtime_binding_rejects_dotenv_edits_masked_by_inherited_values(monkeypatch, tmp_path):
    from unittest.mock import Mock

    import docker
    from hercules.core.config import HerculesConfig
    from hercules.setup.runtime import verification_binding

    environment = tmp_path / ".env"
    environment.write_text("MAX_CONCURRENT_LIGHT=10\n")
    monkeypatch.setenv("HERCULES_ENV_FILE", str(environment))
    config = HerculesConfig(project_root=tmp_path, skip_metasploit=True, max_concurrent_light=10)
    monkeypatch.setattr(HerculesConfig, "from_env", classmethod(lambda cls: config))
    monkeypatch.setattr("hercules.core.setup_info._source_facts", lambda path: {"clean": True, "revision": "fixture"})
    monkeypatch.setattr("hercules.setup.runtime.image_status", lambda facts: "ready")
    client = Mock()
    client.info.return_value = {"ID": "local-daemon"}
    client.images.get.return_value.id = "sha256:immutable"
    monkeypatch.setattr(docker, "from_env", lambda **kwargs: client)
    facts = {"source": {"checkout": str(tmp_path), "revision": "fixture"}, "image": {"tag": "fixture"}}
    before = verification_binding(facts)
    environment.write_text("MAX_CONCURRENT_LIGHT=7\n")
    after = verification_binding(facts)
    assert before["configuration_sha256"] == after["configuration_sha256"]
    assert before["dotenv_sha256"] != after["dotenv_sha256"]


def test_same_image_browser_update_stays_pending_when_docker_is_unavailable(fake_engine, monkeypatch):
    from hercules.core.tool_catalog import ALL_CAPABILITIES

    fake_engine.args.capabilities = "all"
    source, _ = fake_engine.source()
    fake_engine.old = {"checkout": str(source), "commit": "previous", "image_fingerprint": "a",
                       "installed_capabilities": list(ALL_CAPABILITIES)}
    monkeypatch.setattr("hercules.setup.engine.image_status", lambda facts: "docker_unavailable")
    result = fake_engine.execute("install")
    assert result["status"] == "pending" and result["registration"] == "unchanged"
    assert not fake_engine.adapter.path.exists()
    assert "verify --runtime --pending" in result["next_action"]


def test_unsupported_browser_config_keeps_candidate_pending(fake_engine, monkeypatch):
    original = fake_engine.facts

    def incompatible(candidate):
        return {**original(candidate), "browser": {"unsupported_configurations": ["BROWSER_LOCALE"]}}

    monkeypatch.setattr(fake_engine, "facts", incompatible)
    with pytest.raises(SetupError, match="Replacement not activated"):
        fake_engine.execute("install")
    assert not fake_engine.adapter.path.exists()
    assert fake_engine.pending()["activation_blockers"] == ["BROWSER_LOCALE"]


def test_browser_release_blocker_prevents_activation_even_with_ready_image(fake_engine, monkeypatch):
    original = fake_engine.facts

    def blocked(candidate):
        return {**original(candidate), "browser": {"release_blockers": ["obscura_network_scope_not_enforced"]}}

    monkeypatch.setattr(fake_engine, "facts", blocked)
    monkeypatch.setattr("hercules.setup.engine.image_status", lambda facts: "ready")
    with pytest.raises(SetupError) as caught:
        fake_engine.execute("install")
    assert caught.value.code == "runtime_compatibility_blocked"
    assert not fake_engine.adapter.path.exists()
    assert fake_engine.pending()["activation_blockers"] == ["obscura_network_scope_not_enforced"]
    status = fake_engine.status()
    assert status["pending_activation_blockers"] == ["obscura_network_scope_not_enforced"]
    assert "runtime preparation cannot resolve it" in status["next_action"]


def test_unpublished_image_never_silently_builds(fake_engine, monkeypatch, tmp_path):
    from types import SimpleNamespace
    from unittest.mock import Mock

    fake_engine.args = SimpleNamespace(image_source="auto", build_ca_bundle=None)
    fake_engine.transaction = Mock()
    facts = {"source": {"checkout": str(tmp_path)}, "image": {
        "tag": "fixture", "fingerprint": "a" * 64, "target_platform": "linux/amd64",
        "custom_ca": {"configured": False}}}
    monkeypatch.setattr("hercules.setup.engine.image_status", lambda facts: "missing")
    with pytest.raises(SetupError, match="no published matching image"):
        fake_engine.prepare_runtime({}, facts)
    fake_engine.transaction.run.assert_not_called()


def test_auto_pulls_ghcr_before_docker_hub(fake_engine, monkeypatch, tmp_path):
    from types import SimpleNamespace
    from unittest.mock import Mock

    ghcr = "ghcr.io/owner/hercules@sha256:" + "c" * 64
    hub = "owner/hercules@sha256:" + "c" * 64
    # Catalog lists Docker Hub first; the engine must still try GHCR first.
    monkeypatch.setattr("hercules.setup.images.prebuilt_references", lambda facts: [hub, ghcr])
    statuses = iter(["missing", "ready", "ready"])
    monkeypatch.setattr("hercules.setup.engine.image_status", lambda facts: next(statuses))
    fake_engine.args = SimpleNamespace(image_source="auto", build_ca_bundle=None)
    fake_engine.transaction = Mock()
    fake_engine.candidate_worker = Mock()
    facts = {"source": {"checkout": str(tmp_path)}, "image": {
        "tag": "fixture", "fingerprint": "a" * 64, "target_platform": "linux/amd64",
        "custom_ca": {"configured": False}, "build_arguments": {}, "labels": {}}}
    candidate = {}
    fake_engine.prepare_runtime(candidate, facts)
    first_pull = next(c for c in fake_engine.transaction.run.call_args_list if "pull" in c.args[0])
    assert ghcr in first_pull.args[0], first_pull
    assert candidate["image_source"] == "prebuilt"


def test_new_asset_requirement_keeps_same_image_update_pending(fake_engine, monkeypatch):
    fake_engine.old = {"image_fingerprint": "a", "installed_capabilities": ["shell", "session", "workspace"]}
    fake_engine.args.capabilities = "shell,session,workspace,fuzz"
    monkeypatch.setattr(fake_engine, "assets_ready", lambda *args: False)
    monkeypatch.setattr("hercules.setup.engine.image_status", lambda facts: "ready")
    result = fake_engine.execute("install")
    assert result["status"] == "pending"
    assert result["registration"] == "unchanged"
    assert not fake_engine.adapter.path.exists()


def test_candidate_workers_use_isolated_revision_environments(fake_engine, tmp_path, monkeypatch):
    import os
    import venv

    shadow = tmp_path / "shadow/hercules"
    shadow.mkdir(parents=True)
    (shadow / "__init__.py").write_text('raise RuntimeError("inherited Python path used")')
    monkeypatch.setenv("PYTHONPATH", str(shadow.parent))
    fake_engine.transaction = Transaction(tmp_path / "transaction")
    for pin in ("old-pins", "new-pins"):
        root = tmp_path / pin
        venv.EnvBuilder(with_pip=False).create(root / ".venv")
        python = root / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        site = root / ".venv" / ("Lib/site-packages" if os.name == "nt" else f"lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages")
        package = site / "hercules/setup"
        package.mkdir(parents=True)
        (package.parent / "__init__.py").write_text("")
        (package / "__init__.py").write_text("")
        (package / "runtime.py").write_text(
            'import json,sys\nfrom pathlib import Path\n'
            'facts=json.loads(Path(sys.argv[sys.argv.index("--facts")+1]).read_text())\n'
            f'print(json.dumps({{"pin":{pin!r},"ready":facts["expected"]=={pin!r}}}))\n'
        )
        candidate = {"checkout": str(root), "environment": {}}
        for action in ("assets", "assets-ready", "verify"):
            result = fake_engine.candidate_worker(candidate, {"expected": pin}, action)
            assert result == {"pin": pin, "ready": True}
        assert not Engine.assets_ready(fake_engine, candidate, {"expected": "different-pins"})
        assert str(python) != sys.executable
    assert not (fake_engine.transaction.directory / "facts.json").exists()


def test_pending_resume_restores_selected_skill_destination(fake_engine, tmp_path, monkeypatch):
    chosen = tmp_path / "chosen 😀 guidance"
    fake_engine.args.skill_path = chosen
    fake_engine.adapter.skill = chosen
    fake_engine.old = {"image_fingerprint": "old"}
    assert fake_engine.execute("install")["status"] == "pending"
    assert fake_engine.pending()["skill_paths"] == [str(chosen)]
    fake_engine.args.skill_path = None
    fake_engine.adapter.skill = tmp_path / "old guidance"
    monkeypatch.setattr("hercules.setup.engine.image_status", lambda facts: "ready")
    result = fake_engine.execute("resume")
    assert result["registration"] == "configured"
    assert (chosen / "SKILL.md").read_text() == "fixture skill"
    assert not (tmp_path / "old guidance").exists()


def test_pending_resume_rejects_new_skill_override(fake_engine, tmp_path):
    fake_engine.old = {"image_fingerprint": "old"}
    fake_engine.execute("install")
    fake_engine.args.skill_path = tmp_path / "other guidance"
    with pytest.raises(SetupError, match="different skill destination"):
        fake_engine.execute("resume")


def test_pending_resume_rejects_concurrent_skill_edits(fake_engine):
    chosen = fake_engine.adapter.skill
    chosen.mkdir(parents=True)
    (chosen / "SKILL.md").write_text("original guidance")
    fake_engine.old = {"image_fingerprint": "old"}
    fake_engine.execute("install")
    (chosen / "SKILL.md").write_text("user edits")
    with pytest.raises(SetupError, match="Guidance changed"):
        fake_engine.execute("resume")
    assert (chosen / "SKILL.md").read_text() == "user edits"


def test_new_image_keeps_old_version_active(fake_engine):
    fake_engine.old = {"image_fingerprint": "old", "launcher": "old-launcher"}
    result = fake_engine.execute("install")
    assert result["status"] == "pending"
    assert result["registration"] == "unchanged"
    assert not fake_engine.adapter.path.exists()
    assert fake_engine.pending()["image_fingerprint"] == "a"


def test_failed_activation_restores_prior_configuration(fake_engine, monkeypatch):
    fake_engine.adapter.path.write_text('{"unrelated":true}')
    original = fake_engine.adapter.path.read_bytes()
    fake_engine.client_snapshot = original

    def fail(_):
        raise OSError("disk full")

    monkeypatch.setattr(Transaction, "commit", fail)
    with pytest.raises(OSError):
        fake_engine.execute("install")
    assert fake_engine.adapter.path.read_bytes() == original
    assert not fake_engine.state_path.exists()


def test_status_does_not_write_or_start_processes(isolated_home, tmp_path, monkeypatch):
    root = tmp_path / "absent"
    args = parser().parse_args(
        ["status", "--client", "codex", "--root", str(root), "--json"]
    )
    result = Engine(args).execute("status")
    assert result["host"] == "not_installed"
    assert not root.exists()


def test_explicit_dotenv_validation(monkeypatch, tmp_path):
    from hercules.core.config_io import dotenv_path

    monkeypatch.delenv("HERCULES_ENV_FILE", raising=False)
    assert dotenv_path(tmp_path) == tmp_path / ".env"
    monkeypatch.setenv("HERCULES_ENV_FILE", "relative.env")
    with pytest.raises(ValueError):
        dotenv_path(tmp_path)
    config = tmp_path / "outside.env"
    config.write_text("")
    monkeypatch.setenv("HERCULES_ENV_FILE", str(config))
    assert dotenv_path(tmp_path) == config


def test_jsonc_preserves_comments_inside_server():
    source = '{"mcpServers":{"hercules":{/* launcher */"command":"old","env":{/* policy */"SKIP_METASPLOIT":"true"}}}}'
    updated = edit(
        source,
        "json",
        ("mcpServers", "hercules"),
        {
            "command": "new",
            "env": {"SKIP_METASPLOIT": "true", "HERCULES_ENV_FILE": "/config"},
        },
    )
    assert "/* launcher */" in updated and "/* policy */" in updated
    assert parse(updated, "json")["mcpServers"]["hercules"]["command"] == "new"


@pytest.mark.parametrize("text", ['{"x":NaN}', '{"x":Infinity}', '{"x":-Infinity}'])
def test_rejects_non_json_numbers(text):
    with pytest.raises(ConfigError):
        parse(text, "json")


def test_legacy_multi_client_versions_and_unknown_state_preserved(fake_engine):
    fake_engine.state = {
        "schema_version": 4,
        "clients": ["claude-code", "codex"],
        "checkout": "/legacy",
        "commit": "old",
        "unknown_extension": {"keep": True},
    }
    fake_engine.execute("install")
    state = json.loads(fake_engine.state_path.read_text())
    assert state["registrations"]["codex"]["checkout"] == "/legacy"
    assert state["registrations"]["codex"]["commit"] == "old"
    assert state["registrations"]["claude-code"]["commit"] == "a" * 40
    assert state["unknown_extension"] == {"keep": True}


def test_preferences_preserve_client_environment_and_legacy_paths(
    fake_engine, tmp_path
):
    legacy = tmp_path / "legacy"
    legacy.mkdir()
    (legacy / ".env").write_text(
        "HERCULES_WORKSPACE_ROOT=evidence\nHERCULES_WORDLIST_ROOT=lists\nHERCULES_INSTALLED_CAPABILITIES=shell,session,workspace\n"
    )
    fake_engine.old = {"checkout": str(legacy)}
    fake_engine.adapter.path.write_text(
        '{"mcpServers":{"hercules":{"env":{"SKIP_METASPLOIT":"true","MSF_RPC_PORT":"54321"}}}}'
    )
    result = fake_engine.preferences(tmp_path / "candidate", "new")
    assert result["env_file"] == str(legacy / ".env")
    assert result["workspace_root"] == str(legacy / "evidence")
    assert result["wordlist_root"] == str(legacy / "lists")
    assert result["environment"]["SKIP_METASPLOIT"] == "true"
    assert result["environment"]["MSF_RPC_PORT"] == "54321"
    assert "MSF_PASSWORD" not in (legacy / ".env").read_text()


def test_concurrent_configuration_edit_during_preparation_blocks_activation(
    fake_engine, monkeypatch
):
    old_facts = fake_engine.facts

    def edit_during_facts(candidate):
        fake_engine.adapter.path.write_text('{"concurrent":true}')
        return old_facts(candidate)

    monkeypatch.setattr(fake_engine, "facts", edit_during_facts)
    with pytest.raises(SetupError, match="Configuration changed"):
        fake_engine.execute("install")
    assert fake_engine.adapter.path.read_text() == '{"concurrent":true}'
    assert not fake_engine.state_path.exists()


@pytest.mark.parametrize(
    "failure",
    [OSError("disk full"), PermissionError("Windows file locked"), KeyboardInterrupt()],
)
def test_failed_or_interrupted_write_rolls_back(fake_engine, monkeypatch, failure):
    real_write = Transaction.write

    def fail_state(self, path, content, **kwargs):
        if path == fake_engine.state_path:
            raise failure
        return real_write(self, path, content, **kwargs)

    monkeypatch.setattr(Transaction, "write", fail_state)
    with pytest.raises(type(failure)):
        fake_engine.execute("install")
    assert not fake_engine.adapter.path.exists()
    assert not fake_engine.state_path.exists()
    assert fake_engine.pending()


def test_pending_resume_does_not_fetch_new_source(fake_engine, monkeypatch):
    fake_engine.old = {"image_fingerprint": "old"}
    assert fake_engine.execute("install")["status"] == "pending"
    monkeypatch.setattr(
        fake_engine, "source", lambda **kw: pytest.fail("resume fetched new source")
    )
    monkeypatch.setattr("hercules.setup.engine.image_status", lambda facts: "ready")
    fake_engine.args.command = "resume"
    fake_engine.result["status"] = "ok"
    result = fake_engine.execute("resume")
    assert result["host"] == "installed"
    assert result["runtime_preparation"] == "ready"
    assert fake_engine.pending() is None


def test_registration_repair_never_prepares_runtime(fake_engine, monkeypatch):
    monkeypatch.setattr(
        fake_engine,
        "prepare_runtime",
        lambda *_: pytest.fail("repair prepared runtime"),
    )
    calls = []
    original = fake_engine.source
    monkeypatch.setattr(
        fake_engine, "source", lambda **kw: (calls.append(kw), original())[1]
    )
    fake_engine.args.command = "repair"
    assert fake_engine.execute("repair")["verification"]["runtime"] == "not_run"
    assert calls == [{"repair": True}]


def test_cleaned_runtime_journal_does_not_require_docker(tmp_path, monkeypatch):
    from hercules.setup.runtime import cleanup_verification

    directory = tmp_path / "tx"
    workspace = directory / "verification"
    workspace.mkdir(parents=True)
    (workspace / "evidence").write_text("keep")
    monkeypatch.setattr(
        "docker.from_env",
        lambda **kw: pytest.fail("cleaned transaction contacted Docker"),
    )
    cleanup_verification(
        directory, {"workspace": str(workspace), "runtime": True, "cleaned": True}
    )
    assert (workspace / "evidence").read_text() == "keep"


def test_unsafe_verification_cleanup_rejected(tmp_path):
    from hercules.setup.runtime import cleanup_verification

    with pytest.raises(SetupError, match="outside"):
        cleanup_verification(
            tmp_path / "tx", {"workspace": str(tmp_path), "runtime": False}
        )


def test_tampered_backup_is_not_restored(tmp_path):
    target = tmp_path / "config"
    target.write_bytes(b"old")
    tx = Transaction(tmp_path / "tx")
    tx.write(target, b"new", expected=b"old")
    (tx.directory / "0.before").write_bytes(b"tampered")
    assert tx.rollback() == [str(target)]
    assert target.read_bytes() == b"new"


def test_failed_process_retains_private_diagnostic_without_printing_secret(tmp_path):
    tx = Transaction(tmp_path / "tx")
    with pytest.raises(SetupError) as error:
        tx.run(
            [
                sys.executable,
                "-c",
                'import sys; sys.stderr.write("private-value"); sys.exit(7)',
            ]
        )
    assert "private-value" not in str(error.value)
    assert "private-value" not in error.value.next_action
    assert tx.data["processes"][0]["done"]
    # Interpreter startup diagnostics may precede the child's stderr.
    assert Path(tx.data["retained"][0]).read_text().endswith("private-value")


def test_process_timeout_terminates_exact_child(tmp_path):
    from hercules.core.docker_manager import _is_process_running

    tx = Transaction(tmp_path / "tx")
    with pytest.raises(SetupError) as caught:
        tx.run([sys.executable, "-c", "import time; time.sleep(30)"], timeout=0.1)
    assert caught.value.code == "command_timeout"
    assert not _is_process_running(tx.data["processes"][0]["pid"])


def test_atomic_private_temp_name_can_exceed_windows_path_limit(tmp_path):
    from hercules.core.config_io import atomic_write_private_bytes

    # The destination remains readable by ordinary Windows callers; only the
    # UUID-bearing atomic temp name crosses the legacy 260-character limit.
    destination = tmp_path / ("v" * max(1, 230 - len(str(tmp_path)))) / "settings.json"
    atomic_write_private_bytes(destination, b"first")
    atomic_write_private_bytes(destination, b"replacement")
    assert destination.read_bytes() == b"replacement"
    assert not list(destination.parent.glob("*.tmp"))


def test_unknown_profiles_and_inline_overrides_require_manual_selection(
    isolated_home, monkeypatch
):
    monkeypatch.setenv("OPENCODE_CONFIG_CONTENT", "{}")
    with pytest.raises(ConfigError, match="shadow"):
        resolve("opencode", "user", isolated_home)
    for client in ("claude-desktop", "windsurf", "hermes"):
        with pytest.raises(ConfigError):
            resolve(client, "project", isolated_home)


def test_native_registration_failure_is_not_retried(
    isolated_home, tmp_path, monkeypatch
):
    from hercules.setup.clients import validate_native_entry

    monkeypatch.setattr("hercules.setup.clients.native_argv", lambda _: ["client"])
    tx = Transaction(tmp_path / "tx")
    calls = []

    def deny(argv, **kwargs):
        calls.append(argv)
        raise SetupError("command_failed", "denied")

    monkeypatch.setattr(tx, "run", deny)
    with pytest.raises(SetupError, match="denied"):
        validate_native_entry(
            resolve("claude-code", "user", isolated_home),
            tx,
            {"command": "/test"},
            "user",
        )
    assert len(calls) == 1
    assert not (tx.directory / "native-client").exists()
    assert not list(isolated_home.iterdir())


def test_cli_reports_configuration_error_without_traceback(isolated_home, capsys):
    from hercules.setup_cli import main

    assert main(["status", "--client", "hermes", "--scope", "project", "--json"]) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["error_type"] == "client_configuration_invalid"
    assert "--client generic" in report["next_action"]


def test_cli_adds_host_network_reminder_only_on_docker_desktop(isolated_home, capsys, monkeypatch):
    import hercules.setup_cli as setup_cli
    from hercules.setup_cli import main

    # Any completed setup on Docker Desktop (Windows/macOS) must carry the
    # host-networking reminder; native Linux must not.
    monkeypatch.setattr(setup_cli.platform, "system", lambda: "Windows")
    main(["status", "--client", "hermes", "--scope", "project", "--json"])
    assert "Enable host networking" in json.loads(capsys.readouterr().out)["host_network_reminder"]

    monkeypatch.setattr(setup_cli.platform, "system", lambda: "Linux")
    main(["status", "--client", "hermes", "--scope", "project", "--json"])
    assert "host_network_reminder" not in json.loads(capsys.readouterr().out)


def test_yaml_aliases_require_manual_edit():
    with pytest.raises(ConfigError, match="shared settings"):
        edit(
            "shared: &shared {hercules: {command: old}}\nmcp_servers: *shared\n",
            "yaml",
            ("mcp_servers", "hercules"),
            {"command": "new"},
        )


def test_custom_skill_path_cannot_hide_enabled_claude_plugin(isolated_home):
    settings = isolated_home / ".claude/settings.json"
    settings.parent.mkdir()
    settings.write_text('{"enabledPlugins":{"hercules@local":true}}')
    adapter = resolve(
        "claude-code", "user", isolated_home, skill_path=isolated_home / "custom-skill"
    )
    assert duplicate_entries(adapter) == ["plugin:hercules@local"]


def test_recovery_removes_only_named_transaction_temporaries(tmp_path):
    tx = Transaction(tmp_path / "transactions/one")
    shadow = tx.directory / "native-client"
    shadow.mkdir()
    (shadow / "config").write_text("owned fixture")
    (tx.directory / "facts.json").write_text("{}")
    (tx.directory / "keep.log").write_text("diagnostic")
    recover(tmp_path)
    assert not shadow.exists()
    assert not (tx.directory / "facts.json").exists()
    assert (tx.directory / "keep.log").is_file()


def test_pending_candidate_rejects_changed_configuration(fake_engine):
    fake_engine.old = {"image_fingerprint": "old"}
    fake_engine.execute("install")
    fake_engine.client_snapshot = b'{"changed":true}'
    with pytest.raises(SetupError, match="Configuration changed since"):
        fake_engine.execute("resume")


def test_git_source_update_reinstall_and_divergence(fake_engine, tmp_path, monkeypatch):
    import tempfile

    from hercules.setup.engine import launcher

    def git(root, *args):
        return subprocess.check_output(
            ["git", "-C", str(root), *args], text=True, stderr=subprocess.PIPE
        ).strip()

    def repository(name, content):
        directory = tmp_path / name
        directory.mkdir()
        git(directory, "init", "-q")
        (directory / "source").write_text(content)
        (directory / ".gitignore").write_text(".venv/\n")
        git(directory, "add", ".")
        git(
            directory,
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@localhost",
            "commit",
            "-qm",
            content,
        )
        return directory

    original = repository("original", "original")
    unrelated = repository("unrelated", "unrelated")
    launcher(original).parent.mkdir(parents=True)
    launcher(original).write_bytes(b"fixture")
    fake_engine.old = {
        "checkout": str(original),
        "commit": git(original, "rev-parse", "HEAD"),
    }
    fake_engine.args.source = unrelated
    with tempfile.TemporaryDirectory(prefix="hercules-git-") as directory:
        fake_engine.root = Path(directory).resolve()
        fake_engine.transaction = Transaction(fake_engine.root / "tx")
        with pytest.raises(SetupError, match="not a fast-forward"):
            Engine.source(fake_engine)
        (original / "source").write_text("user changes")
        with pytest.raises(SetupError, match="uncommitted work"):
            Engine.source(fake_engine)
        fake_engine.args.reinstall = True
        candidate, revision = Engine.source(fake_engine)
        assert revision == git(unrelated, "rev-parse", "HEAD")
        assert (original / "source").read_text() == "user changes"
        assert candidate.parent == fake_engine.root / "releases"


def test_bootstrap_shell_syntax():
    import shutil

    root = Path(__file__).resolve().parents[1]
    if sys.platform == "win32":
        shell = shutil.which("pwsh") or shutil.which("powershell")
        if shell:
            script = str(root / "scripts/setup.ps1").replace("'", "''")
            expression = f"$tokens=$null; $errors=$null; [System.Management.Automation.Language.Parser]::ParseFile('{script}',[ref]$tokens,[ref]$errors) > $null; if ($errors.Count) {{ exit 1 }}"
            subprocess.run(
                [shell, "-NoProfile", "-Command", expression],
                check=True,
                capture_output=True,
            )
        git = shutil.which("git")
        candidate = Path(git).parents[1] / "bin/bash.exe" if git else None
        # PATH may resolve bash to a WSL shim that cannot read Windows paths.
        bash = str(candidate) if candidate and candidate.is_file() else None
        if not bash:
            bash = shutil.which("bash")
            if bash and Path(bash).parent.name.lower() in {"system32", "windowsapps"}:
                bash = None
        if not bash:
            pytest.skip("bash unavailable for setup.sh syntax check")
        subprocess.run(
            [bash, "-n", str(root / "scripts/setup.sh")],
            check=True,
            capture_output=True,
        )
    else:
        subprocess.run(
            ["sh", "-n", str(root / "scripts/setup.sh")],
            check=True,
            capture_output=True,
        )


@pytest.mark.parametrize("shim_directory", ["System32", "WindowsApps"])
@pytest.mark.parametrize("git_bash_available", [True, False])
def test_bootstrap_shell_avoids_wsl_shims(
    monkeypatch, tmp_path, shim_directory, git_bash_available
):
    import shutil

    git = tmp_path / "Git" / "cmd" / "git.exe"
    bash = git.parents[1] / "bin" / "bash.exe"
    if git_bash_available:
        bash.parent.mkdir(parents=True)
        bash.touch()
    shim = tmp_path / shim_directory / "bash.exe"
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(
        shutil, "which", lambda name: {"git": str(git), "bash": str(shim)}.get(name)
    )
    commands = []
    monkeypatch.setattr(subprocess, "run", lambda command, **_: commands.append(command))
    if git_bash_available:
        test_bootstrap_shell_syntax()
        assert commands == [[str(bash), "-n", str(Path(__file__).resolve().parents[1] / "scripts/setup.sh")]]
    else:
        with pytest.raises(pytest.skip.Exception, match="bash unavailable"):
            test_bootstrap_shell_syntax()
        assert commands == []


def test_missing_configured_secrets_are_not_regenerated(fake_engine, tmp_path):
    missing = tmp_path / "previous.env"
    fake_engine.old = {"env_file": str(missing)}
    with pytest.raises(SetupError, match="secrets were not regenerated"):
        fake_engine.preferences(tmp_path / "candidate", "revision")
    assert not missing.exists()
    assert not (fake_engine.root / "data/.env").exists()


def test_durable_secret_progress_retained_without_backups(tmp_path):
    tx = Transaction(tmp_path / "transactions/one")
    secret_file = tmp_path / "data/.env"
    tx.write(secret_file, b"MSF_PASSWORD=fixture\n", expected=None, durable=True)
    assert tx.rollback() == []
    assert secret_file.read_bytes() == b"MSF_PASSWORD=fixture\n"
    assert str(secret_file) in tx.data["retained"]
    assert not list(tx.directory.glob("*.after"))


def test_default_skill_paths_are_client_specific(isolated_home):
    paths = [
        resolve(name, "user", isolated_home).skill
        for name in (
            "claude-code",
            "codex",
            "cursor",
            "vscode",
            "gemini",
            "opencode",
            "windsurf",
            "hermes",
        )
    ]
    assert len(set(paths)) == len(paths)


def test_shared_skill_not_changed_for_unselected_client(fake_engine):
    skill = fake_engine.adapter.skill
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("another client version")
    fake_engine.state = {
        "clients": ["claude-code", "codex"],
        "registrations": {"codex": {"skill_paths": [str(skill)]}},
    }
    with pytest.raises(SetupError, match="Another client uses"):
        fake_engine.execute("install")
    assert (skill / "SKILL.md").read_text() == "another client version"
    assert not fake_engine.adapter.path.exists()


def test_legacy_discovery_records_runtime_identity(
    isolated_home, tmp_path, monkeypatch
):
    from hercules.setup.engine import launcher

    source = tmp_path / "legacy"
    source.mkdir()
    (source / "pyproject.toml").write_text("fixture")
    command = launcher(source)
    command.parent.mkdir(parents=True)
    command.write_bytes(b"fixture")
    adapter = resolve("cursor", "user", isolated_home)
    adapter.path.parent.mkdir(parents=True)
    adapter.path.write_text(
        json.dumps({"mcpServers": {"hercules": {"command": str(command)}}})
    )
    facts = {
        "source": {"revision": "old"},
        "selection": {"capabilities": ["shell", "session", "workspace"]},
        "image": {
            "fingerprint": "previous-image",
            "tag": "previous",
            "target_platform": "linux/amd64",
        },
    }
    calls = []

    def probe(argv, **kw):
        calls.append(argv)
        return json.dumps(facts)

    monkeypatch.setattr("hercules.setup.engine.readonly", probe)
    instance = Engine(
        parser().parse_args(
            ["status", "--client", "cursor", "--root", str(tmp_path / "managed")]
        )
    )
    assert instance.old["image_fingerprint"] == "previous-image"
    assert calls == [[str(command), "--setup-info-json"]]


def test_remote_windsurf_entry_is_not_converted_to_stdio(isolated_home):
    adapter = resolve("windsurf", "user", isolated_home)
    adapter.path.parent.mkdir(parents=True)
    adapter.path.write_text(
        '{"mcpServers":{"hercules":{"serverUrl":"https://example.invalid/mcp"}}}'
    )
    before = adapter.path.read_bytes()
    with pytest.raises(ConfigError, match="remote server"):
        adapter.render(isolated_home / "hercules", {})
    assert adapter.path.read_bytes() == before
