---
name: hercules-setup-contract
description: Install, update, repair, and verify Hercules through its shared setup CLI
---

# Install or update Hercules MCP

Use `hercules-setup`, not an agent-written installer or acceptance script.
Configure **only the current agent**, unless the user explicitly names others.
Never infer the active agent from installed executables.

## Bootstrap once; reuse on updates

Host installation requires Git and uv. Docker is required only for runtime
preparation and use. Missing privileged prerequisites need operator action;
never alter system packages, services, groups, permissions, or Docker settings.

If installed, use the absolute `hercules-setup` launcher beside the client's
recorded `hercules` launcher. Otherwise obtain the official repository, review
the bootstrap, and run one of:

```powershell
.\scripts\setup.ps1 install --client claude-code --yes
```

```sh
sh scripts/setup.sh install --client claude-code --yes
```

Both bootstraps prepare source and its locked Python environment at a permanent,
non-synced path, print the exact revision, then delegate to the same Python CLI.
They do not prepare Kali or call MCP execution tools. Failed bootstraps report
their retained path; reuse its launcher once its locked environment is ready.
Do not repeatedly clone successful bootstrap environments.

From a development checkout use `uv run --locked hercules-setup ...`.
Registrations always use the absolute release launcher, never `uv run`, a bare
PATH command, or a temporary checkout. Never globally replace a live editable
tool with `uv tool install --editable --force`.

## Commands and separate phases

Examples abbreviate the absolute setup launcher as `hercules-setup`:

| Command | Effect |
| --- | --- |
| `status --client claude-code --json` | Read-only discovery; no downloads, Docker start, or config writes |
| `install --client claude-code --yes` | Install/update/repair this client, with cold STDIO validation |
| `repair --client claude-code --yes` | Repair the recorded version without upgrading |
| `install --client claude-code --reinstall --yes` | Fresh replacement; retain the old checkout |
| `runtime prepare --client claude-code --yes` | Explicit image build/reuse and verified asset downloads |
| `resume --client claude-code --yes` | Recover unfinished writes and activate retained work when ready |
| `verify --client claude-code` | Cold STDIO checks without execution-tool calls |
| `verify --client claude-code --runtime` | Explicit local container start, harmless tools, and stop |
| `install --client generic --yes` | Export a secret-free STDIO entry without editing a client |

Use the same selectors on later commands. `--root` isolates managed storage and
state; `--state` selects an existing schema-4 file. `--project` identifies the
project without relying on the caller's current directory. Fresh installs
default to user scope and full capabilities; use `--scope project` or
`--capabilities shell,session,workspace,nmap` for a deliberate alternative.
Existing preferences are preserved. Reinstall is never a mandatory question
on an ordinary update.

`--yes` confirms only the named setup operation, not harness permissions.
Ask separately before large runtime downloads or container testing. A host-only
installation can succeed with runtime preparation still required.

## Client adapters

Supported identifiers: `claude-code`, `claude-desktop`, `codex`, `cursor`,
`vscode`, `gemini`, `opencode`, `windsurf`, `hermes`, and `generic`.

Adapters preserve unrelated settings, comments, servers, environment overrides,
and disabled/approval policy. Available Claude/Codex native CLIs validate the
command in a disposable private profile before only the Hercules entry is
merged into the real file. Other adapters use round-trip document edits.
A failed native invocation is not retried through another method.

Use `--config-path` for an explicitly selected non-default profile/config and
`--skill-path` for a custom portable-skill destination. The adapters honor
`CLAUDE_CONFIG_DIR`, `CODEX_HOME`, `HERMES_HOME`, XDG paths, and OpenCode's disk
config overrides. OpenCode supports direct `mcp.hercules` and nested
`mcp.servers.hercules`. Conflicting files/layouts and inline config overrides
require explicit resolution. VS Code profiles require the actual config path.
Claude Desktop, Windsurf, and Hermes use their supported user scope.
For a migrated Windsurf/Devin installation, explicitly select the active
Cascade configuration and skill path; do not guess which agent is running.

Duplicate Hercules entries/plugins are reported, not deleted or silently
enabled. Unknown clients use the generic export. Clients without local STDIO
support need manual resolution; never invent a remote proxy. Install the
portable skill independently from native plugin adapters.
Prefer client-specific skill directories. When a recorded skill path is shared
with another client, setup refuses to overwrite different guidance there;
select an independent `--skill-path` for the client being updated.

Client entries contain no secrets. Move existing secret-bearing client values
to the protected dotenv file before setup; never print them.
`HERCULES_ENV_FILE` is an absolute file path. Without it, an existing checkout
continues loading its original `.env`.

## Safe updates and recovery

Each version keeps its permanent path. Never move or copy its `.venv`, replace
a running launcher, or kill a live user MCP process to complete an update.
Activation changes only the selected client's entry. Other clients and existing
sessions continue using their original versions.

Updates are fast-forward only and refuse dirty or diverged source. Explicit
reinstall retains modified old source. Preserve `.env`, generated secrets,
capabilities, scope, proxy preference, image cache, verified wordlists, workspaces,
and non-empty evidence. Legacy evidence paths are adopted without relocation.

If a new image is required, keep the working installation active and report the
replacement as pending. Run `runtime prepare`, then `resume`, when the user
chooses to proceed.

An installation lock serializes writers. A private journal records owned paths,
process identities, and fingerprinted backups. Recovery restores unfinished
activation before resuming. Unrelated concurrent client edits survive rollback;
conflicting edits to the Hercules entry retain a private backup for review.

Cleanup runs on success, failure, cancellation, and interruption. Hard process
termination cannot execute a finally block; the next mutating command recovers
the journal. Still-running processes are identified, not indiscriminately killed.
Remove only owned temporary files/profiles and exact-owned verification containers.
Retain useful verification evidence and recorded resumable candidates.
Newly generated dotenv secrets are journaled, fingerprint-checked durable
progress and retained for resume, not regenerated or deleted on failure.
Locked/referenced versions remain available. Never perform a broad Docker or
filesystem prune.

## Runtime preparation and local verification

Reuse images only when identity, labels, and platform match setup facts.
Use checksum-pinned assets and never drop capabilities to mask failures.
Preserve the Docker producer's exit status. Keep TLS and hostname verification
enabled. `--build-ca-bundle` accepts only an approved certificate-only PEM;
record its fingerprint, not certificate contents.

Cold verification compares actual STDIO tools/resources with setup facts and
reads bundled skill resources. Remote resource catalogs are listed but not
fetched during local-only verification.

Explicit runtime verification uses a disposable workspace and
`PRESERVE_CONTAINER=false`: pre-start guard, explicit/idempotent start,
harmless local command, optional container-loopback browser fixture, an actual
second cold connection, stop, and port release. Never contact a public target or
perform an egress test. Never stop another client's container.

## Claude Code auto mode

Keep discovery, host setup, registration, image preparation, and runtime
verification distinct. Host setup never calls `shell_exec` or
`system_start_container`.

If Claude denies a command, stop that action and report its exact scope and
retained transaction. Wait for the user to resolve it through Claude's supported
permission interface. Never change permission modes, add blanket allow rules,
install approval hooks, conceal operations, or retry through another tool.
A user-approved resume does not guarantee every classifier or organization
policy will approve. See [Claude's permission documentation](https://code.claude.com/docs/en/permission-modes).

Scripted demos and blanket MCP approvals do not prove real auto-mode compatibility.
Record live classifier checks separately with actual version, outcome, and
blocked steps.

## Report precisely

Report host revision, selected-client registration, runtime preparation, actual
host/runtime verification results, cleanup, retained items, and one next action.
A cold connection does not prove Kali is ready. `current_session_loaded: unknown`
means an MCP reload, new session, or IDE restart may still be needed.
Do not reinstall merely to activate settings.

Runtime images include the small SSH, unzip, and Python virtual-environment
baseline. Image changes are prepared separately; an existing working client
stays on its version until the candidate runtime is ready. Custom packages are
installed only deliberately inside an explicitly started container through
`shell_exec`, never as part of host setup or automatically during startup.
Container-layer installs are temporary; keep custom scripts and dependency
records in the workspace.

Agents can use `workspace_inspect` without starting Docker. Use the installed
absolute `hercules-workspace` launcher for explicit regular-file `import` and
`export` with `--session`, `--source`, and `--destination`; checksum verification
is mandatory and replacement requires `--overwrite`. Stop only the current
owned runtime when work is complete, confirm its cleanup fields, and retain
evidence. There is no idle auto-stop or broad cleanup.

`--json` emits one non-secret report on stdout; progress goes to stderr.
Failed subprocess diagnostics stay in a private transaction log; the report
names its path without echoing potentially secret-bearing stderr.
Only actual error/status fields indicate failures. Setup facts' diagnostic
catalog is reference information, not a list of active errors.

Candidate verification and asset preparation run in that candidate's own locked
Python environment. Pending updates retain their selected guidance destination;
resume refuses changed guidance or a conflicting `--skill-path`.

For host file transfers and maintenance, pass the explicit host workspace root:
the harness shell does not inherit MCP registration environment overrides.
Workspace migration honors `HERCULES_ENV_FILE` and requires explicit affected
`--client`/`--state` selections. It refuses live/uncertain owners, including cold
connections, verifies a copy, updates selected configuration transactionally,
and retains the original. `--delete-source` is refused during migration; use
the separately verified `retire --references-reviewed` operation only after
reviewing every custom/unlisted reference and resolving pinned evidence.

## Development checks

Run `uv sync --locked --extra dev --inexact`, then `uv run --locked pytest`.
The default suite uses fixtures, not real client registrations.
Opt into `HERCULES_RUN_SETUP_ACCEPTANCE=1` for disposable real installs/native
registration, and `HERCULES_RUN_DOCKER_ACCEPTANCE=1` for cached-image lifecycle
checks including Windows console events. `HERCULES_RUN_CLAUDE_AUTO=1` additionally
uses a signed-in Claude session for an actual auto-mode fixture installation;
it has no approval allowlist, permission hooks, or mocked classifier. A blocked
or unavailable live check is reported separately, never counted as a pass.
