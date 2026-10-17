"""Opt-in, offline-cached installation tests with disposable source and profiles."""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import sys
import tempfile
import shlex
from pathlib import Path

import pytest

from hercules.setup.clients import resolve, validate_native_entry
from hercules.setup.engine import Engine, launcher
from hercules.setup.transaction import Transaction
from hercules.setup_cli import parser

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(
    os.getenv("HERCULES_RUN_SETUP_ACCEPTANCE") != "1",
    reason="set HERCULES_RUN_SETUP_ACCEPTANCE=1 for isolated real setup/STDIO checks",
)


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


@pytest.fixture
def source(tmp_path, monkeypatch):
    source = tmp_path / "source"
    source.mkdir()
    for name in (
        "hercules",
        "skills",
        "docker",
        ".claude-plugin",
        ".codex-plugin",
        ".cursor-plugin",
    ):
        shutil.copytree(
            ROOT / name,
            source / name,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
    for name in (
        "pyproject.toml",
        "uv.lock",
        "README.md",
        "install.md",
        "Dockerfile",
        ".gitignore",
        ".env.example",
        ".mcp.json",
        "mcp.json",
        "hercules-mcp.json",
    ):
        shutil.copy2(ROOT / name, source / name)
    git(source, "init", "-q")
    git(source, "config", "user.email", "fixture@localhost")
    git(source, "config", "user.name", "Setup fixture")
    git(source, "config", "core.autocrlf", "false")
    git(source, "add", ".")
    git(source, "commit", "-qm", "Disposable candidate")
    monkeypatch.setenv("UV_OFFLINE", "1")
    monkeypatch.delenv("HERCULES_ENV_FILE", raising=False)
    return source


@pytest.fixture
def storage():
    # Keep Windows dependency paths below MAX_PATH without changing OS policy.
    with tempfile.TemporaryDirectory(prefix="hercules-setup-") as directory:
        yield Path(directory)


def test_install_noop_update_repair_reinstall_and_live_old_session(
    source, tmp_path, storage
):
    config = tmp_path / "client.jsonc"
    skill = tmp_path / "skill"
    config.write_text('{// keep\n"other":true}')
    base = [
        "--client",
        "cursor",
        "--root",
        str(storage),
        "--config-path",
        str(config),
        "--skill-path",
        str(skill),
        "--source",
        str(source),
        "--yes",
        "--capabilities",
        "shell,session,workspace",
    ]

    def run(command, *extra):
        return Engine(parser().parse_args([command, *base, *extra])).execute(command)

    first = run("install")
    original = Path(first["checkout"])
    original_state = json.loads((storage / "install.json").read_text())
    assert first["verification"]["runtime"] == "not_run"
    assert first["host"] == "installed"
    assert run("install")["checkout"] == str(original)
    assert "// keep" in config.read_text()
    env_file = Path(original_state["env_file"])
    original_env = env_file.read_bytes()

    async def update_with_live_server():
        from fastmcp import Client
        from fastmcp.client.transports import StdioTransport

        environment = json.loads(config.read_text().replace("// keep", ""))[
            "mcpServers"
        ]["hercules"]["env"]
        async with Client(
            StdioTransport(str(launcher(original)), [], env=environment)
        ) as client:
            before = [tool.name for tool in await client.list_tools()]
            with (source / "README.md").open("a", encoding="utf-8") as output:
                output.write("\nDisposable update.\n")
            git(source, "add", "README.md")
            git(source, "commit", "-qm", "Disposable fast-forward")
            updated = await asyncio.to_thread(run, "install")
            assert updated["checkout"] != str(original)
            assert launcher(original).is_file()
            assert [tool.name for tool in await client.list_tools()] == before
            return updated

    updated = asyncio.run(update_with_live_server())
    current = Path(updated["checkout"])
    repaired = run("repair")
    assert repaired["revision"] == updated["revision"]
    assert repaired["checkout"] != str(current)
    assert launcher(current).is_file()
    current = Path(repaired["checkout"])
    assert env_file.read_bytes() == original_env
    # An explicit reinstall preserves modified source and uses a fresh venv path.
    (current / "README.md").write_text("user edits")
    from hercules.setup.transaction import SetupError

    with pytest.raises(SetupError, match="uncommitted"):
        run("install")
    replaced = run("install", "--reinstall")
    assert replaced["checkout"] not in (str(current), str(original))
    assert (current / "README.md").read_text() == "user edits"
    assert env_file.read_bytes() == original_env
    assert json.loads(config.read_text().replace("// keep", ""))["other"] is True
    cursor_entry = config.read_bytes()
    second = list(base)
    second[second.index("cursor")] = "gemini"
    second[second.index(str(config))] = str(tmp_path / "gemini.json")
    second[second.index(str(skill))] = str(tmp_path / "gemini-skill")
    Engine(parser().parse_args(["install", *second])).execute("install")
    assert config.read_bytes() == cursor_entry
    state = json.loads((storage / "install.json").read_text())
    assert set(state["registrations"]) == {"cursor", "gemini"}
    assert state["registrations"]["cursor"]["checkout"] == replaced["checkout"]


@pytest.mark.parametrize("name", ["claude-code", "codex"])
def test_installed_native_cli_in_isolated_profile(name, tmp_path):
    from hercules.setup.clients import native_argv

    if not native_argv(name):
        pytest.skip(f"{name} native CLI is not available")
    adapter = resolve(
        name,
        "user",
        tmp_path,
        tmp_path / ("config.toml" if name == "codex" else "config.json"),
        tmp_path / "skill",
    )
    _, entry = adapter.render(
        Path(sys.executable), {"HERCULES_ENV_FILE": str(tmp_path / "example.env")}
    )
    transaction = Transaction(tmp_path / "transaction")
    assert validate_native_entry(adapter, transaction, entry, "user") == "native_cli"
    assert not (transaction.directory / "native-client").exists()
    assert not adapter.path.exists()


@pytest.mark.skipif(
    os.getenv("HERCULES_RUN_DOCKER_ACCEPTANCE") != "1",
    reason="runtime preparation/testing is a separate explicit phase",
)
def test_setup_runtime_verifier_with_cached_image(tmp_path):
    from hercules.setup.runtime import verify, image_status, cleanup_verification

    environment = {
        **os.environ,
        "HERCULES_INSTALLED_CAPABILITIES": "all",
        "HERCULES_DISABLED_TOOLS": "",
        "SKIP_METASPLOIT": "false",
        "HERCULES_WORDLIST_ROOT": str(ROOT / "wordlists"),
    }
    facts = json.loads(
        subprocess.check_output(
            [str(launcher(ROOT)), "--setup-info-json"], env=environment, text=True
        )
    )
    if image_status(facts) != "ready":
        pytest.skip(
            "Matching runtime image is not cached; no build/download authorized"
        )
    directory = (tmp_path / "transaction").resolve()
    workspace = directory / "verification"
    metadata = {"workspace": str(workspace), "checkout": str(ROOT), "runtime": True}
    try:
        result = asyncio.run(
            verify(launcher(ROOT), environment, facts, workspace, runtime=True)
        )
        assert result["runtime"] == "passed"
        assert "local_browser" in result["checks"]
        assert "stop_and_ports_released" in result["checks"]
    finally:
        cleanup_verification(directory, metadata)
    assert metadata["cleaned"]


@pytest.mark.skipif(
    os.getenv("HERCULES_RUN_CLAUDE_AUTO") != "1",
    reason="live Claude auto-mode check requires an explicitly authorized signed-in session",
)
def test_live_claude_auto_mode(source, tmp_path, storage):
    """A real classifier check, not a replay, allowlist, or mocked verdict."""
    from hercules.setup.clients import native_argv

    command = native_argv("claude-code")
    if not command:
        pytest.skip("Claude Code is not available")
    version = subprocess.check_output([*command, "--version"], text=True).strip()
    selectors = [
        "--client",
        "claude-code",
        "--root",
        str(storage),
        "--config-path",
        str(tmp_path / "client.json"),
        "--skill-path",
        str(tmp_path / "skill"),
        "--source",
        str(source),
        "--capabilities",
        "shell,session,workspace",
        "--json",
    ]
    calls = [
        shlex.join(
            [
                str(Path(sys.executable).as_posix()),
                "-m",
                "hercules.setup_cli",
                action,
                *[value.replace("\\", "/") for value in selectors],
                *(["--yes"] if action == "install" else []),
            ]
        )
        for action in ("status", "install")
    ]
    prompt = (
        "This is an authorized local Hercules setup acceptance test. Execute these two commands in order using Bash. "
        "They configure only disposable fixture paths, not my real client. Do not start Docker, download assets, "
        "edit permission settings, use approval hooks or allow rules, or contact an external target. "
        "If any operation is denied, stop immediately and report the exact denied operation; never retry through another tool. "
        "Do not improvise other setup commands. Report the actual outcomes. Commands:\n"
        + "\n".join(calls)
    )
    result = subprocess.run(
        [
            *command,
            "-p",
            prompt,
            "--permission-mode",
            "auto",
            "--setting-sources",
            "",
            "--strict-mcp-config",
            "--mcp-config",
            '{"mcpServers":{}}',
            "--tools",
            "Bash,Read",
            "--no-session-persistence",
            "--output-format",
            "stream-json",
            "--verbose",
        ],
        cwd=source,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=360,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    events = [
        json.loads(line) for line in result.stdout.splitlines() if line.startswith("{")
    ]
    initialization = next(
        (
            event
            for event in events
            if event.get("type") == "system" and event.get("subtype") == "init"
        ),
        {},
    )
    final = next(
        (event for event in reversed(events) if event.get("type") == "result"), {}
    )
    denied = final.get("permission_denials", [])
    mode = initialization.get("permissionMode")
    report = {
        "version": version,
        "mode": mode,
        "denied_operations": [item.get("tool_name") for item in denied],
        "host_activated": (storage / "install.json").exists(),
        "exit_code": result.returncode,
    }
    print("CLAUDE_AUTO_RESULT=" + json.dumps(report))
    if denied or mode != "auto" or result.returncode:
        pytest.skip("Live auto-mode acceptance blocked: " + json.dumps(report))
    assert (storage / "install.json").is_file(), (
        "Claude did not execute the authorized fixture installation"
    )
    assert (
        json.loads((storage / "install.json").read_text())["verification"]["runtime"]
        == "not_run"
    )
