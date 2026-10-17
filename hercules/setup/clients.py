"""Explicit, scope-aware local STDIO adapters. Importing this module writes nothing."""

from __future__ import annotations

import copy
import os
import platform
import shutil
from dataclasses import dataclass
from pathlib import Path

from hercules.core.config_io import SECRET_KEY
from hercules.setup.documents import ConfigError, edit, lookup, parse

CLIENTS = (
    "claude-code",
    "claude-desktop",
    "codex",
    "cursor",
    "vscode",
    "gemini",
    "opencode",
    "windsurf",
    "hermes",
    "generic",
)


def native_argv(name: str) -> list[str] | None:
    """Resolve native executables or known npm entrypoints without cmd.exe."""
    command = {"claude-code": "claude", "codex": "codex"}.get(name)
    resolved = shutil.which(command) if command else None
    if not resolved:
        return None
    path = Path(resolved)
    if path.suffix.lower() not in (".cmd", ".ps1", ".bat"):
        return [str(path)]
    if name == "claude-code":
        native = path.parent / "node_modules/@anthropic-ai/claude-code/bin/claude.exe"
        if native.is_file():
            return [str(native)]
    package = {
        "claude-code": "@anthropic-ai/claude-code/cli.js",
        "codex": "@openai/codex/bin/codex.js",
    }[name]
    script = path.parent / "node_modules" / package
    node = shutil.which("node")
    return [node, str(script)] if node and script.is_file() else None


def validate_native_entry(adapter, transaction, entry, scope):
    """Ask the installed CLI to render into an isolated profile, then merge only
    its server entry. Native CLIs must not rewrite the live user's whole file.
    """
    command = native_argv(adapter.name)
    if not command:
        return "document_adapter"
    shadow = transaction.directory / "native-client"
    shadow.mkdir()
    env = dict(os.environ)
    try:
        if adapter.name == "claude-code":
            import json

            env["CLAUDE_CONFIG_DIR"] = str(shadow)
            argv = [
                *command,
                "mcp",
                "add-json",
                "--scope",
                scope,
                "hercules",
                json.dumps(entry),
            ]
            result_path = shadow / (".claude.json" if scope == "user" else ".mcp.json")
        else:
            env["CODEX_HOME"] = str(shadow)
            argv = [*command, "mcp", "add", "hercules"]
            for key, value in entry.get("env", {}).items():
                argv.extend(["--env", f"{key}={value}"])
            argv.extend(["--", entry["command"], *entry.get("args", [])])
            result_path = shadow / "config.toml"
        transaction.run(argv, env=env, cwd=shadow, timeout=60)
        native = lookup(
            parse(result_path.read_text(encoding="utf-8-sig"), adapter.format),
            adapter.keys,
        )
        if (
            not native
            or native.get("command") != entry["command"]
            or native.get("args", []) != entry.get("args", [])
            or native.get("env", {}) != entry.get("env", {})
        ):
            raise ConfigError(
                "Native client registration disagrees with the requested local command"
            )
        return "native_cli"
    finally:
        # This private shadow profile was allocated by this transaction only.
        if shadow.resolve().parent != transaction.directory:
            raise ConfigError("Native profile cleanup escaped the transaction")
        shutil.rmtree(shadow)


@dataclass
class Adapter:
    name: str
    path: Path | None
    keys: tuple[str, ...]
    format: str = "json"
    skill: Path | None = None
    reload: str = "Reload the MCP connection or start a new agent session."

    def document(self):
        text = (
            self.path.read_text(encoding="utf-8-sig")
            if self.path and self.path.exists()
            else ""
        )
        return text, parse(text, self.format)

    def entry(self):
        _, document = self.document()
        return lookup(document, self.keys)

    def render(self, launcher: Path, environment: dict[str, str]):
        text, document = self.document()
        old = lookup(document, self.keys)
        if old is not None and not isinstance(old, dict):
            raise ConfigError("Existing Hercules entry is not a local server object")
        if old and any(key in old for key in ("url", "serverUrl", "headers", "oauth")):
            raise ConfigError(
                "Hercules is registered as a remote server; select the local entry explicitly"
            )
        entry = copy.deepcopy(old or {})
        env_key = "environment" if self.name == "opencode" else "env"
        existing_env = entry.get(env_key, {})
        if not isinstance(existing_env, dict):
            raise ConfigError("Hercules environment must be an object")
        if any(SECRET_KEY.search(key) for key in existing_env):
            raise ConfigError(
                "Existing client entry contains secret-like environment keys; move them to the protected dotenv file before setup"
            )
        if "cwd" in entry:
            del entry["cwd"]
        if self.name == "opencode":
            entry.update(type="local", command=[str(launcher)])
            entry.setdefault("timeout", 120000)
        else:
            entry.update(command=str(launcher), args=[])
            if self.name not in ("codex", "hermes", "gemini", "claude-desktop"):
                entry["type"] = "stdio"
            if self.name == "codex":
                entry.setdefault("startup_timeout_sec", 120)
            if self.name == "gemini":
                entry.setdefault("timeout", 120000)
        entry[env_key] = {**existing_env, **environment}
        # Do not enable a user-disabled entry or change its approval policy.
        updated = edit(text, self.format, self.keys, entry)
        return updated.encode("utf-8"), entry


def resolve(
    name: str,
    scope: str,
    project: Path,
    config_path: Path | None = None,
    skill_path: Path | None = None,
) -> Adapter:
    if name not in CLIENTS:
        raise ConfigError("Select a supported --client or use --client generic")
    home = Path.home()
    project = project.resolve()
    user = scope == "user"
    system = platform.system()
    xdg = Path(os.getenv("XDG_CONFIG_HOME") or home / ".config")
    appdata = Path(os.getenv("APPDATA") or home / "AppData/Roaming")
    root = home if user else project
    keys = ("mcpServers", "hercules")
    format = "json"
    skill = None
    if name == "generic":
        return Adapter(name, None, keys)
    if name == "claude-code":
        claude = Path(os.getenv("CLAUDE_CONFIG_DIR") or home / ".claude")
        path = (
            (
                claude / ".claude.json"
                if os.getenv("CLAUDE_CONFIG_DIR")
                else home / ".claude.json"
            )
            if user
            else project / ".mcp.json"
        )
        skill = (claude if user else project / ".claude") / "skills/hercules-mcp"
    elif name == "claude-desktop":
        if not user or system not in ("Windows", "Darwin"):
            raise ConfigError(
                "Claude Desktop supports user scope on Windows/macOS; use generic export elsewhere"
            )
        path = (
            appdata / "Claude"
            if system == "Windows"
            else home / "Library/Application Support/Claude"
        ) / "claude_desktop_config.json"
    elif name == "codex":
        base = (
            Path(os.getenv("CODEX_HOME") or home / ".codex")
            if user
            else project / ".codex"
        )
        path, keys, format = base / "config.toml", ("mcp_servers", "hercules"), "toml"
        skill = base / "skills/hercules-mcp"
    elif name == "cursor":
        path, skill = root / ".cursor/mcp.json", root / ".cursor/skills/hercules-mcp"
    elif name == "vscode":
        base = (
            appdata / "Code/User"
            if system == "Windows"
            else (
                home / "Library/Application Support/Code/User"
                if system == "Darwin"
                else xdg / "Code/User"
            )
        )
        if user and (base / "profiles").exists() and not config_path:
            raise ConfigError(
                "VS Code has profiles; provide the active profile --config-path"
            )
        path, keys = (
            (base / "mcp.json" if user else project / ".vscode/mcp.json"),
            ("servers", "hercules"),
        )
        skill = root / (
            ".copilot/skills/hercules-mcp" if user else ".github/skills/hercules-mcp"
        )
    elif name == "gemini":
        path, skill = (
            root / ".gemini/settings.json",
            root / ".gemini/skills/hercules-mcp",
        )
    elif name == "opencode":
        if os.getenv("OPENCODE_CONFIG_CONTENT"):
            raise ConfigError(
                "OPENCODE_CONFIG_CONTENT can shadow disk settings; use generic export or remove that override explicitly"
            )
        base = (
            Path(os.getenv("OPENCODE_CONFIG_DIR") or xdg / "opencode")
            if user
            else project
        )
        explicit = config_path or (
            Path(os.environ["OPENCODE_CONFIG"])
            if os.getenv("OPENCODE_CONFIG")
            else None
        )
        candidates = [base / "opencode.json", base / "opencode.jsonc"]
        existing = [p for p in candidates if p.exists()]
        if len(existing) > 1 and not explicit:
            raise ConfigError(
                "Multiple OpenCode config files exist; provide the effective --config-path"
            )
        path = explicit or (existing[0] if existing else candidates[0])
        keys = ("mcp", "hercules")
        if path.exists():
            document = parse(path.read_text(encoding="utf-8-sig"), "json")
            mcp = document.get("mcp", {})
            if not isinstance(mcp, dict):
                raise ConfigError("Unknown OpenCode MCP layout; use generic export")
            if "servers" in mcp:
                if "hercules" in mcp:
                    raise ConfigError(
                        "Duplicate direct/nested OpenCode Hercules entries"
                    )
                keys = ("mcp", "servers", "hercules")
        skill = (base if user else project / ".opencode") / "skills/hercules-mcp"
    elif name == "windsurf":
        if not user:
            raise ConfigError("Windsurf MCP configuration is user-scoped")
        path = home / ".codeium/windsurf/mcp_config.json"
        skill = home / ".codeium/windsurf/skills/hercules-mcp"
        devin = (appdata if system == "Windows" else xdg) / "devin/mcp_config.json"
        if devin.exists() and not config_path:
            raise ConfigError(
                "A newer Devin/Cascade layout exists; select the active MCP file with --config-path and its skill destination with --skill-path, or use generic export"
            )
    else:
        if not user:
            raise ConfigError(
                "Hermes uses user/profile scope; select its HERMES_HOME or --config-path"
            )
        base = Path(os.getenv("HERMES_HOME") or home / ".hermes")
        path, keys, format = base / "config.yaml", ("mcp_servers", "hercules"), "yaml"
        skill = base / "skills/hercules-mcp"
    path = (config_path or path).expanduser().absolute()
    if path.is_symlink():
        raise ConfigError(
            "Client config is a symlink; explicitly select its resolved --config-path"
        )
    reload = {
        "claude-code": "Start a new Claude Code session and inspect /mcp; existing sessions may keep the previous version.",
        "claude-desktop": "Restart Claude Desktop and inspect its MCP server status.",
        "codex": "Start a new Codex chat/session and inspect its MCP inventory.",
        "cursor": "Refresh Hercules in Cursor MCP settings or reload the window.",
        "vscode": "Restart Hercules from VS Code MCP: List Servers in the selected profile.",
        "gemini": "Restart Gemini CLI and inspect /mcp.",
        "opencode": "Start a new OpenCode session and inspect its MCP status.",
        "windsurf": "Refresh Hercules in the selected Cascade MCP panel or reload the editor.",
        "hermes": "Start a new Hermes session using the selected profile.",
    }[name]
    return Adapter(name, path, keys, format, skill_path or skill, reload)


def duplicate_entries(adapter: Adapter) -> list[str]:
    """Identify additional Hercules entries without returning configuration values."""
    _, document = adapter.document()
    found = []

    def visit(value, path=()):
        if not isinstance(value, dict):
            return
        for key, item in value.items():
            location = (*path, key)
            if isinstance(item, dict):
                command = str(item.get("command", ""))
                if (
                    ("hercules" in key.lower() or "hercules" in command.lower())
                    and "command" in item
                    and location != adapter.keys
                ):
                    found.append(".".join(location))
                visit(item, location)

    visit(document)
    # Native plugin registries live outside MCP configuration. Do not create a
    # second manual server while a known Hercules plugin is enabled.
    if adapter.name == "claude-code":
        base = Path(os.getenv("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
        settings_paths = {base / "settings.json"}
        if adapter.path and adapter.path.name == ".mcp.json":
            settings_paths.add(adapter.path.parent / ".claude/settings.json")
        for settings in settings_paths:
            if settings.exists():
                enabled = parse(settings.read_text(encoding="utf-8-sig"), "json").get(
                    "enabledPlugins", {}
                )
                found.extend(
                    "plugin:" + key
                    for key, active in enabled.items()
                    if active and "hercules" in key.lower()
                )
    plugins = document.get("plugins", {})
    if isinstance(plugins, dict):
        found.extend(
            "plugin:" + key
            for key, value in plugins.items()
            if "hercules" in key.lower()
            and isinstance(value, dict)
            and value.get("enabled", True)
        )
    return found
