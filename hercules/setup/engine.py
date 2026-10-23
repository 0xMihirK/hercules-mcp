"""Versioned installations: prepare at a permanent path, then activate one client."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import secrets
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

from hercules.core.config_io import (
    atomic_write_private_bytes,
    load_setup_state,
    read_dotenv_value,
)
from hercules.core.setup_info import setup_state_locations
from hercules.core.tool_catalog import (
    format_capabilities,
    parse_capabilities,
    required_wordlists,
)
from hercules.setup.clients import duplicate_entries, resolve, validate_native_entry
from hercules.setup.runtime import image_status
from hercules.setup.transaction import (
    InstallLock,
    SetupError,
    new_transaction,
    read,
    recover,
)

REPOSITORY = "https://github.com/0xMihirK/hercules-mcp.git"


def data_root() -> Path:
    home = Path.home()
    if platform.system() == "Windows":
        return (
            Path(os.getenv("LOCALAPPDATA") or home / "AppData/Local") / "hercules-mcp"
        )
    if platform.system() == "Darwin":
        return home / "Library/Application Support/hercules-mcp"
    return Path(os.getenv("XDG_DATA_HOME") or home / ".local/share") / "hercules-mcp"


def executable(name: str) -> str:
    result = shutil.which(name)
    if not result:
        raise SetupError(
            "prerequisite_missing",
            f"{name} is not installed or discoverable",
            f"Install {name} using your normal approved process, then resume.",
        )
    return str(Path(result).absolute())


def launcher(root: Path, name="hercules") -> Path:
    return (
        root
        / ".venv"
        / ("Scripts/" + name + ".exe" if os.name == "nt" else "bin/" + name)
    )


def skill_fingerprint(path: Path | None) -> str:
    if path is None or not path.exists():
        return "missing"
    if path.is_symlink():
        raise SetupError("unsafe_skill", "Skill destination is a symbolic link")
    checksum = hashlib.sha256()
    for item in sorted(path.rglob("*")):
        if item.is_file():
            checksum.update(item.relative_to(path).as_posix().encode())
            checksum.update(hashlib.sha256(read(item)).digest())
    return checksum.hexdigest()


SKILL_NAMES = (
    "hercules-mcp",
    "hercules-nmap-nse",
    "hercules-nuclei",
    "hercules-operator",
    "hercules-application-testing",
    "hercules-infrastructure",
    "hercules-wireless-embedded",
    "hercules-binary-analysis",
    "hercules-assessment-operations",
)


def skill_paths(main: Path | None, checkout: Path) -> list[Path]:
    if main is None:
        return []
    if not (checkout / "skills/hercules-mcp/SKILL.md").is_file():
        return []
    paths = [
        main if name == "hercules-mcp" else main.parent / name
        for name in SKILL_NAMES
        if (checkout / "skills" / name / "SKILL.md").is_file()
    ]
    if len({path.resolve() for path in paths}) != len(paths):
        raise SetupError(
            "skill_path_conflict",
            "The selected skill path overlaps a bundled peer skill",
            "Choose a separate --skill-path for the general Hercules skill.",
        )
    return paths


def readonly(argv, cwd=None, env=None):
    try:
        result = subprocess.run(
            argv,
            check=False,
            cwd=cwd,
            env=env,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            shell=False,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise SetupError(
            "discovery_failed", f"Read-only discovery failed ({type(exc).__name__})"
        ) from exc
    if result.returncode:
        raise SetupError(
            "discovery_failed",
            f"{Path(argv[0]).name} could not inspect the selected installation",
        )
    return result.stdout.strip()


class Engine:
    def __init__(self, args):
        self.args = args
        self.project = args.project.expanduser().resolve()
        self.scope = args.scope or "user"
        locations = setup_state_locations(self.project)
        if (
            not args.scope
            and not args.root
            and not args.state
            and Path(locations["project"]).is_file()
        ):
            if Path(locations["user"]).is_file():
                raise SetupError(
                    "scope_ambiguous",
                    "User and project installations both exist",
                    "Select --scope user or --scope project.",
                )
            self.scope = "project"
        project_key = hashlib.sha256(str(self.project).encode()).hexdigest()[:16]
        self.root = (
            (
                args.root
                or (
                    data_root()
                    if self.scope == "user"
                    else data_root() / "projects" / project_key
                )
            )
            .expanduser()
            .resolve()
        )
        self.state_path = (
            args.state
            or (
                self.root / "install.json"
                if args.root
                else Path(setup_state_locations(self.project)[self.scope])
            )
        ).absolute()
        self.state, errors = load_setup_state(self.state_path)
        self.state_snapshot = read(self.state_path)
        if errors:
            raise SetupError(
                "state_invalid",
                "; ".join(errors),
                "Repair or explicitly select the non-secret state file; do not delete the installation.",
            )
        self.client = args.client
        if not args.scope and self.state.get("scope"):
            self.scope = self.state["scope"]
        self.adapter = resolve(
            self.client, self.scope, self.project, args.config_path, args.skill_path
        )
        self.old = self.state.get("registrations", {}).get(
            self.client,
            self.state
            if self.client in self.state.get("clients", [self.client])
            else {},
        )
        self.transaction = None
        self.result = {
            "status": "ok",
            "client": self.client,
            "host": "not_installed",
            "registration": "not_configured",
            "runtime_preparation": "unknown",
            "verification": {"host": "not_run", "runtime": "not_run"},
            "cleanup": {"status": "complete", "retained": []},
            "next_action": "",
        }
        if self.old.get("config_path") and not args.config_path:
            self.adapter = resolve(
                self.client,
                self.scope,
                self.project,
                Path(self.old["config_path"]),
                args.skill_path,
            )
        if self.old.get("skill_paths") and not args.skill_path:
            self.adapter.skill = Path(self.old["skill_paths"][0])
        self.client_snapshot = read(self.adapter.path) if self.adapter.path else None
        if not self.old:
            entry = self.adapter.entry() or {}
            command = entry.get("command", "")
            command = command[0] if isinstance(command, list) and command else command
            if command and Path(command).is_absolute():
                path = Path(command)
                candidate = path.parent.parent.parent
                if (
                    candidate / "pyproject.toml"
                ).is_file() and path.parent.parent.name == ".venv":
                    client_env = entry.get(
                        "environment" if self.client == "opencode" else "env", {}
                    )
                    facts = json.loads(
                        readonly(
                            [str(path), "--setup-info-json"],
                            env={**os.environ, **client_env},
                        )
                    )
                    self.old = {
                        "checkout": str(candidate),
                        "commit": facts["source"]["revision"],
                        "installed_capabilities": facts["selection"]["capabilities"],
                        "image_fingerprint": facts["image"]["fingerprint"],
                        "image": facts["image"]["tag"],
                        "image_platform": facts["image"]["target_platform"],
                    }
                elif path.is_file() and path.stem.lower() == "hercules":
                    client_env = entry.get(
                        "environment" if self.client == "opencode" else "env", {}
                    )
                    facts = json.loads(
                        readonly(
                            [str(path), "--setup-info-json"],
                            env={**os.environ, **client_env},
                        )
                    )
                    if (
                        not facts.get("source", {}).get("checkout")
                        or facts.get("status") == "error"
                    ):
                        raise SetupError(
                            "legacy_launcher_unknown",
                            "Legacy source discovery failed",
                            "Select its existing schema-4 --state before migration.",
                        )
                    self.old = {
                        "checkout": facts["source"]["checkout"],
                        "commit": facts["source"]["revision"],
                        "installed_capabilities": facts["selection"]["capabilities"],
                        "image_fingerprint": facts["image"]["fingerprint"],
                        "image": facts["image"]["tag"],
                        "image_platform": facts["image"]["target_platform"],
                    }
                else:
                    raise SetupError(
                        "legacy_launcher_unknown",
                        "Existing launcher cannot be associated with a checkout",
                        "Select the existing schema-4 --state, or inspect the registration before migrating it.",
                    )

    def status(self):
        entry = self.adapter.entry()
        checkout = self.old.get("checkout")
        if not checkout:
            legacy = Path.home() / ".hercules-mcp"
            if (legacy / "pyproject.toml").is_file():
                self.result["legacy_checkout"] = str(legacy)
                self.result["next_action"] = (
                    "Run install to adopt the existing checkout configuration without moving it."
                )
        if checkout:
            self.result.update(
                host="installed" if Path(checkout).exists() else "source_missing",
                revision=self.old.get("commit"),
                checkout=checkout,
            )
        if entry:
            command = entry.get("command")
            command = command[0] if isinstance(command, list) and command else command
            self.result["registration"] = (
                "configured"
                if isinstance(command, str)
                and Path(command).is_absolute()
                and Path(command).is_file()
                else "stale"
            )
        self.result["current_session_loaded"] = "unknown"
        self.result["verification"] = self.old.get(
            "verification", self.result["verification"]
        )
        self.result["runtime_preparation"] = self.old.get(
            "runtime_preparation", "unknown"
        )
        pending = self.pending()
        if pending:
            self.result["pending_revision"] = pending.get("commit")
            self.result["next_action"] = (
                "Run runtime prepare for the pending version, verify --runtime --pending for a browser replacement, then resume."
            )
            self.result["pending_runtime_verification"] = pending.get("runtime_verification", {"runtime": "not_run"})
            blockers = pending.get("activation_blockers", [])
            if blockers:
                self.result["pending_activation_blockers"] = blockers
                self.result["next_action"] = (
                    "Pending activation is blocked: " + ", ".join(blockers)
                    + ". Keep the working version and review the blocker; runtime preparation cannot resolve it. Do not erase scope settings."
                )
        if not self.result["next_action"]:
            self.result["next_action"] = (
                "Run install to update or repair only this client."
            )
        self.result["config_path"] = (
            str(self.adapter.path) if self.adapter.path else None
        )
        self.result["duplicates"] = duplicate_entries(self.adapter)
        self.result["state_path"] = str(self.state_path)
        self.result["scope"] = self.scope
        self.result["installed_capabilities"] = self.old.get(
            "installed_capabilities", []
        )
        self.result["runtime_preparation_source"] = "last_recorded"
        return self.result

    def pending(self):
        path = self.root / "pending" / f"{self.client}.json"
        if path.exists():
            value = json.loads(path.read_text(encoding="utf-8"))
            if value.get("client") != self.client or value.get("state_path") != str(
                self.state_path
            ):
                raise SetupError(
                    "pending_conflict",
                    "Pending setup belongs to a different client/scope",
                )
            return value
        return None

    def environment(self, candidate):
        env = {**os.environ, **candidate["environment"]}
        # Unrelated inherited Hercules preferences must not select another profile.
        for key in list(env):
            if (
                key.startswith("HERCULES_")
                and key not in candidate["environment"]
                and key not in ("HERCULES_RUN_DOCKER_ACCEPTANCE",)
            ):
                env.pop(key)
        return env

    def save_pending(self, candidate):
        from hercules.setup.transaction import digest

        candidate["client_fingerprint"] = digest(self.client_snapshot)
        candidate["state_fingerprint"] = digest(self.state_snapshot)
        path = self.root / "pending" / f"{self.client}.json"
        atomic_write_private_bytes(path, json.dumps(candidate, indent=2).encode())
        self.transaction.data["retained"] = list(
            dict.fromkeys(
                [*self.transaction.data["retained"], candidate["checkout"], str(path)]
            )
        )
        self.transaction.save()

    def source(self, *, repair=False):
        git = executable("git")
        old_root = Path(self.old["checkout"]) if self.old.get("checkout") else None
        if old_root and old_root.exists() and not self.args.reinstall:
            dirty = readonly(
                [git, "status", "--porcelain", "--untracked-files=normal"], old_root
            )
            if dirty:
                raise SetupError(
                    "source_modified",
                    "The installed checkout has uncommitted work; it was not changed",
                    "Preserve/review that work, or explicitly request install --reinstall.",
                )
        if repair and (not old_root or not old_root.exists()):
            raise SetupError(
                "source_missing",
                "Repair needs the existing source",
                "Run install to prepare a new version.",
            )
        source = str(self.args.source.resolve()) if self.args.source else REPOSITORY
        if repair:
            source = str(old_root)
        if (
            old_root
            and launcher(old_root).is_file()
            and not self.args.reinstall
            and not repair
        ):
            remote = readonly([git, "ls-remote", source, "HEAD"]).split()
            if remote and remote[0] == self.old.get("commit"):
                entry = self.adapter.entry() or {}
                environment = entry.get(
                    "environment" if self.client == "opencode" else "env", {}
                )
                try:
                    readonly(
                        [str(launcher(old_root)), "--validate-mcp-json"],
                        env={**os.environ, **environment},
                    )
                except SetupError:
                    self.progress(
                        "Existing environment needs repair; preparing a separate locked copy"
                    )
                else:
                    return old_root, self.old["commit"]
        # A new UUID permits a fresh reinstall of the same commit without moving
        # or reusing a potentially locked or modified environment.
        releases = self.root / "releases"
        if os.name == "nt" and len(str(releases)) > 100:
            raise SetupError(
                "path_too_long",
                "This storage root leaves insufficient room for Windows dependency paths",
                "Select a shorter --root outside synced folders; no OS policy change is needed.",
            )
        releases.mkdir(parents=True, exist_ok=True)
        candidate = releases / uuid.uuid4().hex
        self.transaction.data["retained"].append(str(candidate))
        self.transaction.save()
        self.progress("Preparing a permanent source directory")
        self.transaction.run(
            [git, "clone", "--quiet", "--no-hardlinks", source, str(candidate)],
            timeout=300,
        )
        revision = readonly([git, "rev-parse", "HEAD"], candidate)
        if old_root and self.old.get("commit") and not self.args.reinstall:
            result = subprocess.run(
                [git, "merge-base", "--is-ancestor", self.old["commit"], revision],
                check=False,
                cwd=candidate,
                capture_output=True,
                timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            if result.returncode:
                raise SetupError(
                    "source_diverged",
                    "The candidate is not a fast-forward from the installed revision",
                    "Review the revisions or explicitly request reinstall; no checkout was reset.",
                )
        return candidate, revision

    def preferences(self, root: Path, revision: str):
        old_root = (
            Path(self.old["checkout"])
            if self.old.get("checkout")
            else self.root / "data"
        )
        current_entry = self.adapter.entry() or {}
        old_environment = current_entry.get(
            "environment" if self.client == "opencode" else "env", {}
        )
        if not isinstance(old_environment, dict) or not all(
            isinstance(value, str) for value in old_environment.values()
        ):
            raise SetupError(
                "client_environment_invalid",
                "Existing client environment must contain string values",
            )
        from hercules.core.config_io import SECRET_KEY

        if any(SECRET_KEY.search(key) for key in old_environment):
            raise SetupError(
                "client_contains_secrets",
                "Move existing client secrets into the protected dotenv file before setup",
            )
        old_env = Path(
            old_environment.get("HERCULES_ENV_FILE")
            or self.old.get("env_file")
            or old_root / ".env"
        )
        if (
            old_environment.get("HERCULES_ENV_FILE") or self.old.get("env_file")
        ) and not old_env.is_file():
            raise SetupError(
                "environment_missing",
                "The configured dotenv file is missing; secrets were not regenerated",
                "Restore the recorded dotenv file before continuing setup.",
            )
        env_file = old_env if old_env.is_file() else self.root / "data/.env"
        capabilities = (
            self.args.capabilities
            or old_environment.get("HERCULES_INSTALLED_CAPABILITIES")
            or ",".join(self.old.get("installed_capabilities", []))
            or read_dotenv_value(env_file, "HERCULES_INSTALLED_CAPABILITIES")
            or "all"
        )
        capabilities = format_capabilities(
            parse_capabilities(capabilities, legacy_all=True)
        )
        workspace = (
            old_environment.get("HERCULES_WORKSPACE_ROOT")
            or self.old.get("workspace_root")
            or read_dotenv_value(env_file, "HERCULES_WORKSPACE_ROOT")
            or str(
                old_root / "workspace"
                if old_root.is_dir()
                else self.root / "data/workspace"
            )
        )
        wordlists = (
            old_environment.get("HERCULES_WORDLIST_ROOT")
            or self.old.get("wordlist_root")
            or read_dotenv_value(env_file, "HERCULES_WORDLIST_ROOT")
            or str(
                old_root / "wordlists"
                if old_root.is_dir()
                else self.root / "data/wordlists"
            )
        )
        workspace = (
            Path(workspace) if Path(workspace).is_absolute() else old_root / workspace
        )
        wordlists = (
            Path(wordlists) if Path(wordlists).is_absolute() else old_root / wordlists
        )
        if not env_file.exists():
            if self.args.command in ("verify", "runtime"):
                raise SetupError(
                    "environment_missing",
                    "The recorded dotenv file is missing",
                    "Run repair before verification or runtime preparation.",
                )
            # New persisted configuration is durable, not a temporary backup.
            lines = [f"HERCULES_INSTALLED_CAPABILITIES={capabilities}"]
            if "metasploit" in capabilities.split(","):
                lines.append(f"MSF_PASSWORD={secrets.token_urlsafe(32)}")
            self.transaction.write(
                env_file,
                ("\n".join(lines) + "\n").encode(),
                expected=None,
                durable=True,
            )
        if (
            self.args.command not in ("verify", "runtime")
            and "metasploit" in capabilities.split(",")
            and not read_dotenv_value(env_file, "MSF_PASSWORD")
        ):
            before = read(env_file)
            content = before + f"\nMSF_PASSWORD={secrets.token_urlsafe(32)}\n".encode()
            self.transaction.write(env_file, content, expected=before, durable=True)
        environment = {
            **old_environment,
            "HERCULES_ENV_FILE": str(env_file),
            "HERCULES_WORKSPACE_ROOT": str(Path(workspace).absolute()),
            "HERCULES_WORDLIST_ROOT": str(Path(wordlists).absolute()),
            "HERCULES_INSTALLED_CAPABILITIES": capabilities,
        }
        selected_network = getattr(self.args, "docker_network", None)
        existing_network = old_environment.get("HERCULES_DOCKER_NETWORK", self.old.get("docker_network") or read_dotenv_value(env_file, "HERCULES_DOCKER_NETWORK") or "")
        previous_network = existing_network or "host"
        if selected_network is not None:
            from hercules.core.config import _parse_docker_network

            environment["HERCULES_DOCKER_NETWORK"] = _parse_docker_network(selected_network)
        elif existing_network:
            environment["HERCULES_DOCKER_NETWORK"] = existing_network
        elif "browser" in capabilities.split(","):
            # Host networking is the default; the browser runs without an SSRF
            # boundary (no bridge/gateway). Pin host explicitly for clarity.
            environment["HERCULES_DOCKER_NETWORK"] = "host"
        for state_key, env_key in [
            ("image_platform", "HERCULES_IMAGE_PLATFORM"),
            ("build_ca_sha256", "HERCULES_BUILD_CA_SHA256"),
            ("cloakbrowser_version", "HERCULES_CLOAKBROWSER_VERSION"),
            ("cloakbrowser_sha256", "HERCULES_CLOAKBROWSER_SHA256"),
            ("cloakbrowser_wheel_url", "HERCULES_CLOAKBROWSER_WHEEL_URL"),
        ]:
            if self.old.get(state_key) and read_dotenv_value(env_file, env_key) is None:
                environment.setdefault(env_key, self.old[state_key])
        if self.args.platform:
            environment["HERCULES_IMAGE_PLATFORM"] = self.args.platform
        if self.args.build_ca_bundle:
            from hercules.core.setup_info import validate_build_ca_bundle

            _, checksum = validate_build_ca_bundle(self.args.build_ca_bundle)
            environment["HERCULES_BUILD_CA_SHA256"] = checksum
        return {
            "client": self.client,
            "state_path": str(self.state_path),
            "installation_root": str(self.root),
            "checkout": str(root),
            "commit": revision,
            "environment": environment,
            "docker_network": environment.get("HERCULES_DOCKER_NETWORK", ""),
            "network_changed": bool(self.old or current_entry) and environment.get("HERCULES_DOCKER_NETWORK", previous_network) != previous_network,
            "env_file": str(env_file),
            "workspace_root": environment["HERCULES_WORKSPACE_ROOT"],
            "wordlist_root": environment["HERCULES_WORDLIST_ROOT"],
            "installed_capabilities": capabilities.split(","),
            "launcher": str(launcher(root)),
            "scope": self.scope,
            "config_path": str(self.adapter.path) if self.adapter.path else None,
            "skill_paths": [str(path) for path in skill_paths(self.adapter.skill, root)],
            "skill_fingerprint": skill_fingerprint(self.adapter.skill),
            "skill_fingerprints": {
                str(path): skill_fingerprint(path)
                for path in skill_paths(self.adapter.skill, root)
            },
        }

    def progress(self, message):
        self.result["phase"] = message
        print(message, file=sys.stderr, flush=True)

    def facts(self, candidate):
        self.progress("Validating the candidate source and read-only setup facts")
        args = [candidate["launcher"], "--setup-info-json"]
        if self.args.build_ca_bundle:
            args += ["--build-ca-bundle", str(self.args.build_ca_bundle.resolve())]
        output = self.transaction.run(args, env=self.environment(candidate))
        facts = json.loads(output)
        if (
            facts.get("status") == "error"
            or not facts.get("mcp_surface", {}).get("catalog_matches")
            or facts["mcp_surface"].get("errors")
        ):
            raise SetupError(
                "setup_facts_invalid", "Candidate setup facts failed validation"
            )
        if (
            facts["source"]["revision"] != candidate["commit"]
            or Path(facts["source"]["checkout"]).resolve()
            != Path(candidate["checkout"]).resolve()
        ):
            raise SetupError(
                "source_association_invalid", "Candidate source and launcher disagree"
            )
        if not facts["source"]["clean"]:
            raise SetupError(
                "source_modified",
                "The prepared source has local changes; activation was stopped",
            )
        if not facts.get("skill_guidance", {}).get("ok"):
            raise SetupError(
                "skill_invalid",
                "Candidate portable skill does not match its MCP surface",
            )
        candidate.update(
            image=facts["image"]["tag"],
            image_fingerprint=facts["image"]["fingerprint"],
            image_platform=facts["image"]["target_platform"],
            expected_tool_count=facts["mcp_surface"]["tools"],
            resources_count=facts["mcp_surface"]["resources"],
            lockfile_sha256=facts["python_environment"]["lockfile_sha256"],
        )
        candidate.update(
            build_ca_sha256=facts["image"]["custom_ca"]["sha256"],
            cloakbrowser_version=facts["cloakbrowser"]["version"],
            cloakbrowser_sha256=facts["cloakbrowser"]["wheel_sha256"],
            cloakbrowser_wheel_url=facts["cloakbrowser"]["wheel_url"],
        )
        return facts

    def sync(self, root):
        if self.old.get("checkout") == str(root) and launcher(root).is_file():
            # Running Windows launchers must never be reinstalled in place.
            return
        self.progress("Resolving the candidate environment from uv.lock")
        self.transaction.run(
            [executable("uv"), "sync", "--locked", "--project", str(root)], timeout=600
        )

    def candidate_worker(self, candidate, facts, action, *extra, timeout=600):
        python = launcher(Path(candidate["checkout"]), "python")
        if not python.is_file():
            raise SetupError("candidate_environment_missing", "Candidate Python environment is missing", "Run install or resume to resolve its locked environment.")
        facts_path = self.transaction.directory / "facts.json"
        atomic_write_private_bytes(facts_path, json.dumps(facts).encode())
        try:
            output = self.transaction.run(
                [str(python), "-I", "-m", "hercules.setup.runtime", action,
                 "--facts", str(facts_path), *extra],
                cwd=Path(candidate["checkout"]), env=self.environment(candidate), timeout=timeout,
                minimum_free_bytes=8 * 1024**3 if action == "assets" else 0,
            )
            result = json.loads(output)
            if not isinstance(result, dict):
                raise SetupError("candidate_worker_invalid", "Candidate worker returned an unsupported result")
            return result
        finally:
            facts_path.unlink(missing_ok=True)

    def assets_ready(self, candidate, facts):
        result = self.candidate_worker(candidate, facts, "assets-ready")
        if not isinstance(result.get("ready"), bool):
            raise SetupError("candidate_worker_invalid", "Candidate asset readiness contract is unsupported")
        return result["ready"]

    def verify_candidate(self, candidate, facts, *, runtime=False):
        self.progress(
            "Running local container verification"
            if runtime
            else "Checking cold STDIO; no container or execution tool calls"
        )
        workspace = self.transaction.directory / "verification"
        candidate["verification_workspace"] = str(workspace)
        self.transaction.data["verification"] = {
            "workspace": str(workspace),
            "checkout": candidate["checkout"],
            "runtime": runtime,
        }
        self.transaction.save()
        arguments = ["--workspace", str(workspace)]
        if runtime:
            arguments.append("--runtime")
        try:
            binding = self.verification_binding(candidate, facts) if runtime else None
            result = self.candidate_worker(candidate, facts, "verify", *arguments)
            if runtime and result.get("runtime") == "passed":
                if binding != self.verification_binding(candidate, facts):
                    raise SetupError("verification_stale", "Image or configuration changed during verification", "Verify the pending candidate again before activation.")
                result["binding"] = binding
                candidate["runtime_verification"] = result
            candidate["verification"] = result
            self.result["verification"] = result
            return result
        except BaseException:
            self.result["verification"] = {
                "host": "failed",
                "runtime": "failed" if runtime else "not_run",
            }
            raise
        finally:
            from hercules.setup.runtime import cleanup_verification

            cleanup_verification(
                self.transaction.directory, self.transaction.data["verification"]
            )
            self.transaction.save()

    def verification_binding(self, candidate, facts):
        """Observe effective settings in the candidate, not the setup process."""
        result = self.candidate_worker(candidate, facts, "binding", timeout=60)
        if not all(result.get(key) for key in ("revision", "image_id", "docker_daemon_id", "dotenv_sha256", "configuration_sha256", "network")):
            raise SetupError("verification_binding_invalid", "Candidate identity observation is incomplete", "Repair the candidate before verification.")
        return result

    def activate(self, candidate, facts):
        if duplicate_entries(self.adapter):
            raise SetupError(
                "duplicate_registration",
                "Another Hercules entry/plugin is configured",
                "Choose the existing registration to retain; do not add a second server.",
            )
        before_state = self.state_snapshot
        before_client = self.client_snapshot
        if read(self.state_path) != before_state or (
            self.adapter.path and read(self.adapter.path) != before_client
        ):
            raise SetupError(
                "configuration_changed",
                "Configuration changed while the candidate was being prepared",
                "Review the edit, then resume with a fresh discovery.",
            )
        replacement, entry = self.adapter.render(
            Path(candidate["launcher"]), candidate["environment"]
        )
        candidate["registration_method"] = validate_native_entry(
            self.adapter, self.transaction, entry, self.scope
        )
        if self.client == "generic":
            self.result["export"] = entry
        self.progress(
            f"Activating only {self.client}; existing MCP processes remain running"
        )
        self.transaction.phase("activating")
        if self.adapter.skill:
            if not candidate["skill_paths"]:
                raise SetupError(
                    "skill_missing", "The candidate has no general Hercules skill"
                )
            destinations = list(zip(SKILL_NAMES, map(Path, candidate["skill_paths"])))
            source_root = Path(candidate["checkout"]) / "skills"
            for client in self.state.get("clients", []):
                if client == self.client:
                    continue
                association = self.state.get("registrations", {}).get(
                    client, self.state
                )
                for name, destination_root in destinations:
                    source = source_root / name
                    if any(
                        Path(path).resolve() == destination_root.resolve()
                        for path in association.get("skill_paths", [])
                    ) and any(
                        read(destination_root / item.relative_to(source))
                        != item.read_bytes()
                        for item in source.rglob("*")
                        if item.is_file()
                    ):
                        raise SetupError(
                            "shared_skill_path",
                            "Another client uses this skill directory; its guidance was not replaced",
                            "Select a client-specific --skill-path or explicitly coordinate both client updates.",
                        )
            from hercules.setup.transaction import digest

            file_maps = {}
            for name, destination_root in destinations:
                source = source_root / name
                previous = self.old.get("skill_file_maps", {}).get(name, {})
                if name == "hercules-mcp" and not previous:
                    previous = self.old.get("skill_files", {})
                hashes = {}
                for item in source.rglob("*"):
                    if not item.is_file():
                        continue
                    if item.is_symlink():
                        raise SetupError(
                            "unsafe_skill", "Portable skill contains a symlink"
                        )
                    relative = item.relative_to(source).as_posix()
                    destination = destination_root / relative
                    actual = read(destination)
                    content = item.read_bytes()
                    if (
                        actual is not None
                        and actual != content
                        and digest(actual) != previous.get(relative)
                    ):
                        legacy_source = (
                            Path(self.old.get("checkout", ""))
                            / "skills"
                            / name
                            / relative
                        )
                        if (
                            not legacy_source.is_file()
                            or actual != legacy_source.read_bytes()
                        ):
                            raise SetupError(
                                "skill_modified",
                                "The installed skill contains unrecognized local edits",
                                "Preserve those edits and choose an explicit --skill-path.",
                            )
                    self.transaction.write(destination, content, expected=actual)
                    hashes[relative] = digest(content)
                file_maps[name] = hashes
            candidate["skill_file_maps"] = file_maps
            candidate["skill_files"] = file_maps["hercules-mcp"]
            candidate["skill_fingerprint"] = skill_fingerprint(self.adapter.skill)
            candidate["skill_fingerprints"] = {
                str(path): skill_fingerprint(path) for _, path in destinations
            }
        if self.adapter.path:
            self.transaction.write(
                self.adapter.path,
                replacement,
                expected=before_client,
                entry={"keys": self.adapter.keys, "format": self.adapter.format},
            )
            if self.adapter.entry() != entry:
                raise SetupError(
                    "registration_failed",
                    "Effective client entry differs from the intended registration",
                )
        metadata = {
            key: value
            for key, value in candidate.items()
            if key
            not in (
                "environment",
                "verification_workspace",
                "client",
                "state_path",
                "client_fingerprint",
                "state_fingerprint",
            )
        }
        metadata["config_paths"] = [str(self.adapter.path)] if self.adapter.path else []
        associations = dict(self.state.get("registrations", {}))
        legacy = {
            key: value
            for key, value in self.state.items()
            if key not in ("registrations", "clients", "schema_version")
        }
        for client in self.state.get("clients", []):
            associations.setdefault(client, legacy)
        state = {
            **self.state,
            **metadata,
            "schema_version": 4,
            "clients": sorted(set(self.state.get("clients", [])) | {self.client}),
            "registrations": {**associations, self.client: metadata},
        }
        # State is the last live write; it cannot claim container verification
        # merely because client registration succeeded.
        self.transaction.write(
            self.state_path, json.dumps(state, indent=2).encode(), expected=before_state
        )
        self.transaction.commit()
        self.result.update(
            host="installed",
            registration="exported" if self.client == "generic" else "configured",
            revision=candidate["commit"],
            checkout=candidate["checkout"],
            runtime_preparation=candidate["runtime_preparation"],
            verification=candidate["verification"],
            current_session_loaded="unknown",
            next_action=self.adapter.reload,
        )
        if candidate["runtime_preparation"] != "ready":
            self.result["next_action"] += (
                " Run runtime prepare before Docker-backed work; runtime verification is separate."
            )
        pending_path = self.root / "pending" / f"{self.client}.json"
        pending_path.unlink(missing_ok=True)
        self.transaction.data["retained"] = [candidate["checkout"]]
        self.transaction.save()

    def prepare_runtime(self, candidate, facts):
        self.progress(
            "Preparing runtime image/assets; this phase can download large files"
        )
        status = image_status(facts)
        if status == "docker_unavailable":
            raise SetupError(
                "docker_unavailable",
                "Docker is not available; host installation remains intact",
                "Start your approved Docker daemon, then run runtime prepare.",
            )
        if status in {"mismatch", "unverified"}:
            raise SetupError("image_unverified", "The existing runtime tag has a mismatched or unverified identity", "Inspect that exact image without pruning; retain the working installation. Prepare a trusted published digest or an explicitly reviewed rebuild.")
        if status != "ready":
            from hercules.setup.images import prebuilt_references

            source = getattr(self.args, "image_source", "auto")
            references = prebuilt_references(facts) if source != "build" else []
            # Prefer GHCR, fall back to the identical-digest Docker Hub mirror.
            # shortcut: registry preference is hardcoded; make it configurable if a
            # deployment needs a different primary.
            references = sorted(references, key=lambda r: 0 if r.startswith("ghcr.io/") else 1)
            if source == "prebuilt" and not references:
                raise SetupError("prebuilt_unavailable", "No trusted prebuilt digest matches this runtime", "Use --image-source build explicitly, or select a published release. The working installation remains active.")
            if references:
                # A transport failure can use an identical digest mirror. An
                # identity/label failure is never retried via a different image.
                last_error = None
                for reference in references:
                    try:
                        self.transaction.run([executable("docker"), "pull", "--platform", facts["image"]["target_platform"], reference], timeout=7200, minimum_free_bytes=8 * 1024**3)
                    except SetupError as exc:
                        if exc.code != "command_failed":
                            raise
                        last_error = exc
                        continue
                    self.transaction.run([executable("docker"), "tag", reference, facts["image"]["tag"]])
                    if image_status(facts) != "ready":
                        raise SetupError("image_mismatch", "Pulled digest failed runtime identity validation; activation stopped")
                    last_error = None
                    break
                if last_error:
                    raise last_error
                candidate["image_source"] = "prebuilt"
                status = "ready"
            elif source == "auto":
                raise SetupError("prebuilt_unavailable", "This revision has no published matching image", "Run runtime prepare with --image-source build to authorize a local full-image build. The working installation remains active.")
        if status != "ready":
            command = [
                executable("docker"),
                "build",
                "--platform",
                facts["image"]["target_platform"],
                "-t",
                facts["image"]["tag"],
            ]
            for key, value in facts["image"]["build_arguments"].items():
                command += ["--build-arg", f"{key}={value}"]
            for key, value in facts["image"]["labels"].items():
                command += ["--label", f"{key}={value}"]
            if facts["image"]["custom_ca"]["configured"]:
                if not self.args.build_ca_bundle:
                    raise SetupError(
                        "build_ca_required",
                        "This image requires the previously selected certificate-only build trust",
                        "Supply --build-ca-bundle without changing TLS verification.",
                    )
                command += [
                    "--secret",
                    f"id=hercules_build_ca,src={self.args.build_ca_bundle.resolve()}",
                ]
            command += [candidate["checkout"]]
            self.transaction.run(command, timeout=7200, minimum_free_bytes=8 * 1024**3)
            from hercules.core.build_info import record_local_image

            image_id = self.transaction.run([executable("docker"), "image", "inspect", "--format", "{{.Id}}", facts["image"]["tag"]])
            record_local_image(facts["image"]["fingerprint"], image_id)
            candidate["image_id"] = image_id
            candidate["image_source"] = "build"
        if image_status(facts) != "ready":
            raise SetupError(
                "image_mismatch", "Built image labels/platform do not match setup facts"
            )
        self.candidate_worker(candidate, facts, "assets", timeout=3600)
        if not self.assets_ready(candidate, facts):
            raise SetupError("assets_not_ready", "Candidate assets failed verification", "Run runtime prepare after resolving the reported asset issue.")
        candidate["runtime_preparation"] = "ready"

    def execute(self, command):
        if command == "status":
            return self.status()
        if not self.args.yes and command in ("install", "repair", "resume", "runtime"):
            if not sys.stdin.isatty():
                raise SetupError(
                    "confirmation_required",
                    "Host mutations require --yes in a non-interactive invocation",
                    "Review status, then repeat the requested command with --yes. This does not bypass harness permissions.",
                )
            action = (
                "Prepare the runtime image and assets; substantial downloads may be needed"
                if command == "runtime"
                else f"Configure only {self.client} ({self.scope}); preserve evidence and existing preferences"
            )
            print(f"{action}. Continue? [y/N] ", end="", file=sys.stderr)
            if input().lower() not in ("y", "yes"):
                raise SetupError("cancelled", "No setup changes made")
        with InstallLock(self.root / "setup.lock"):
            recover(self.root)
            if read(self.state_path) != self.state_snapshot:
                raise SetupError(
                    "state_changed",
                    "Setup state changed since discovery",
                    "Repeat the command to discover the recovered/current state.",
                )
            self.transaction = new_transaction(
                self.root,
                {
                    "command": command,
                    "client": self.client,
                    "state_path": str(self.state_path),
                },
            )
            try:
                pending_verification = command == "verify" and getattr(self.args, "pending", False)
                if pending_verification and not self.pending():
                    raise SetupError("no_pending_candidate", "No pending candidate exists", "Run install to prepare a candidate first.")
                if (command in ("runtime", "resume") or pending_verification) and self.pending():
                    candidate = self.pending()
                    if getattr(self.args, "docker_network", None) is not None and self.args.docker_network != candidate["environment"].get("HERCULES_DOCKER_NETWORK", ""):
                        raise SetupError("pending_network_changed", "Pending network selection changed", "Run install --docker-network with the desired bridge, then prepare and verify that candidate.")
                    if "skill_paths" not in candidate or "skill_fingerprint" not in candidate:
                        raise SetupError("pending_skill_unknown", "Pending candidate has no verified guidance destination", "Run install with an explicit --skill-path to prepare a new candidate.")
                    saved_skill = Path(candidate["skill_paths"][0]) if candidate["skill_paths"] else None
                    if self.args.skill_path and self.args.skill_path.resolve() != (saved_skill.resolve() if saved_skill else None):
                        raise SetupError("pending_skill_changed", "Resume selected a different skill destination", "Use the original skill destination or prepare a new candidate.")
                    self.adapter.skill = saved_skill
                    fingerprints = candidate.get("skill_fingerprints") or (
                        {str(saved_skill): candidate["skill_fingerprint"]}
                        if saved_skill else {}
                    )
                    if any(
                        skill_fingerprint(Path(path)) != fingerprint
                        for path, fingerprint in fingerprints.items()
                    ):
                        raise SetupError("pending_skill_changed", "Guidance changed since this candidate was prepared", "Preserve the edits and run install against the current guidance.")
                    from hercules.setup.transaction import digest

                    if candidate.get("client_fingerprint") != digest(
                        self.client_snapshot
                    ) or candidate.get("state_fingerprint") != digest(
                        self.state_snapshot
                    ):
                        raise SetupError(
                            "pending_configuration_changed",
                            "Configuration changed since this candidate was prepared",
                            "Run install again to prepare against the current preferences; the old candidate is retained.",
                        )
                    if candidate.get("config_path") != (
                        str(self.adapter.path) if self.adapter.path else None
                    ):
                        raise SetupError(
                            "pending_config_changed",
                            "Pending setup targets a different client config",
                            "Use its original --config-path or inspect status.",
                        )
                    self.sync(Path(candidate["checkout"]))
                elif command in ("runtime", "verify"):
                    if not self.old.get("checkout"):
                        raise SetupError(
                            "not_installed",
                            "No selected-client installation was found",
                            "Run install first.",
                        )
                    candidate = self.preferences(
                        Path(self.old["checkout"]), self.old["commit"]
                    )
                else:
                    root, revision = self.source(repair=command == "repair")
                    candidate = self.preferences(root, revision)
                    self.save_pending(candidate)
                    self.sync(root)
                facts = self.facts(candidate)
                release_blockers = facts.get("browser", {}).get("release_blockers", [])
                if release_blockers and command in {"install", "repair", "resume"}:
                    candidate["activation_blockers"] = release_blockers
                    self.save_pending(candidate)
                    raise SetupError("runtime_compatibility_blocked", "Replacement not activated: " + ", ".join(release_blockers), "Keep the working version active. Run install --docker-network bridge (or an explicitly selected bridge network), prepare, then verify --runtime --pending. Do not clear target restrictions.")
                blockers = facts.get("browser", {}).get("unsupported_configurations", [])
                if blockers and command != "runtime":
                    candidate["activation_blockers"] = blockers
                    self.save_pending(candidate)
                    raise SetupError("browser_configuration_unsupported", "Replacement not activated: " + ", ".join(blockers), "Keep the working version active. Review the unsupported Obscura settings deliberately, then resume; setup will not silently erase them.")
                if command == "verify":
                    verification = self.verify_candidate(
                        candidate, facts, runtime=self.args.runtime
                    )
                    self.result.update(
                        host="installed",
                        verification=verification,
                        next_action=verification.get("next_action", "Reload the selected client if its current session has not loaded Hercules."),
                    )
                    if pending_verification:
                        self.save_pending(candidate)
                        self.result.update(host="candidate_prepared", registration="unchanged",
                                           next_action="Run resume only after pending runtime verification passes.")
                        self.transaction.commit()
                        return self.result
                    state = {
                        **self.state,
                        "verification": verification,
                        "registrations": {
                            **self.state.get("registrations", {}),
                            self.client: {**self.old, "verification": verification},
                        },
                    }
                    self.transaction.write(
                        self.state_path,
                        json.dumps(state, indent=2).encode(),
                        expected=self.state_snapshot,
                    )
                    self.transaction.commit()
                    return self.result
                if command == "runtime":
                    self.prepare_runtime(candidate, facts)
                    self.save_pending(candidate)
                    self.result.update(
                        host="prepared",
                        runtime_preparation="ready",
                        next_action=("Image/assets are prepared, but browser activation remains blocked. Keep the working version; a verified browser-boundary repair is required."
                                     if facts.get("browser", {}).get("release_blockers")
                                     else "Run verify --runtime --pending before resuming a browser replacement; the working registration is unchanged."),
                    )
                    self.transaction.commit()
                    return self.result
                candidate["runtime_preparation"] = (
                    "ready"
                    if image_status(facts) == "ready"
                    and self.assets_ready(candidate, facts)
                    else "required"
                )
                self.verify_candidate(candidate, facts)
                replacing_browser = bool(self.old.get("checkout")) and "browser" in candidate["installed_capabilities"] and (
                    candidate["commit"] != self.old.get("commit") or
                    candidate["image_fingerprint"] != self.old.get("image_fingerprint") or
                    candidate.get("network_changed", False)
                )
                if replacing_browser and candidate["runtime_preparation"] != "ready":
                    self.save_pending(candidate)
                    self.transaction.commit()
                    self.result.update(status="pending", registration="unchanged", host="update_prepared", runtime_preparation="required",
                                       next_action="Working version kept active. Restore Docker access/prepare the candidate runtime, then verify --runtime --pending and resume.")
                    return self.result
                if replacing_browser:
                    proof = candidate.get("runtime_verification", {})
                    if proof.get("runtime") != "passed":
                        self.save_pending(candidate)
                        self.transaction.commit()
                        self.result.update(status="pending", registration="unchanged", host="update_prepared", runtime_preparation="ready",
                                           next_action="Working version kept active. Run verify --runtime --pending, then resume.")
                        return self.result
                    if proof.get("binding") != self.verification_binding(candidate, facts):
                        raise SetupError("verification_stale", "Pending verification no longer matches source, image or configuration", "Run verify --runtime --pending again; the working version is unchanged.")
                    candidate["verification"] = proof
                old_image = self.old.get("image_fingerprint")
                added_assets = set(required_wordlists(candidate["installed_capabilities"])) - set(required_wordlists(self.old.get("installed_capabilities", [])))
                if (
                    old_image
                    and (old_image != candidate["image_fingerprint"] or added_assets)
                    and candidate["runtime_preparation"] != "ready"
                ):
                    self.save_pending(candidate)
                    self.transaction.commit()
                    self.result.update(
                        status="pending",
                        host="update_prepared",
                        registration="unchanged",
                        runtime_preparation="required",
                        verification=candidate["verification"],
                        next_action="Working version kept active. Run runtime prepare, then resume.",
                    )
                    return self.result
                self.activate(candidate, facts)
                return self.result
            except BaseException as exc:
                if isinstance(exc, SetupError) and exc.code.startswith(
                    ("cleanup_", "verification_still")
                ):
                    self.result["cleanup"]["status"] = "blocked"
                if self.transaction.data["phase"] != "committed":
                    leftovers = self.transaction.rollback()
                    if leftovers:
                        self.result["cleanup"] = {
                            "status": "blocked",
                            "retained": leftovers,
                        }
                raise
            finally:
                try:
                    self.transaction.cleanup_temporaries()
                except OSError:
                    self.result["cleanup"]["status"] = "blocked"
                    self.result.update(
                        status="error",
                        message="Temporary cleanup is blocked; the exact transaction directory was retained.",
                        next_action="Close only the process holding the named temporary files, then run resume.",
                    )
                    self.result["cleanup"]["retained"].append(
                        str(self.transaction.directory)
                    )
                versions = self.root / "releases"
                self.result["cleanup"]["deferred_versions"] = (
                    [str(path) for path in versions.iterdir() if path.is_dir()]
                    if versions.exists()
                    else []
                )
                metadata = self.transaction.data.get("verification", {})
                if metadata.get("retained_evidence"):
                    self.transaction.data["retained"].append(
                        metadata["retained_evidence"]
                    )
                self.result["cleanup"]["retained"].extend(
                    self.transaction.data["retained"]
                )
                self.result["transaction"] = str(self.transaction.path)
