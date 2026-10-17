# Workspace, Evidence, and Jobs

## Select and preserve the right session

Hercules mounts one owned host session at `/opt/workspace`. Keep the current
system session while working on the same engagement. Call
`system_start_new_session` only when changing engagements or when a clean
workspace is required. It stops the current container, creates the workspace,
and leaves the new session stopped. Call `system_start_container` when ready to
use Docker-backed tools; failure to create the new session leaves the previous
session and evidence intact.

`system_list_sessions` reports ownership, state, generation, timestamps, bytes,
pinning, and retention eligibility. An `active`, `pinned`, `unowned`, or
running-job session must not be pruned. Host operators use
`hercules-workspace pin`, `unpin`, `prune`, and `migrate`; pruning is a report
unless they explicitly pass `--apply`.

The agent chooses isolation when the engagement needs it. Related/parallel
challenges normally use separate folders in one event workspace. Never rotate
or stop while another worker depends on this runtime. Historical manifests and
`job_inventory` contain recorded state, not an observed Docker/process census;
workspace counts do not count containers.

Lifecycle responses separate `host_workspace` from `container_workspace`.
Native host tools use the host path; Hercules/container tools use `/opt/workspace`.
Use `workspace_inspect(action='list', path='challenge')`, `action='stat'`, or
`action='read'` for bounded file access even when stopped. Select `session_id`
to read prior owned evidence; retained sessions are not mounted in the current
container. Inspect/copy relevant notes deliberately rather than guessing paths.

## Transfer local files explicitly

Use the selected installation's absolute `hercules-workspace` launcher, or its
absolute Python with `-m hercules.workspace_cli`. Approve the exact paths and
session; these commands copy one regular file and verify its SHA-256:

```text
hercules-workspace --root "<host-workspace-root>" import --session <session-id> --source "<host-handout-path>" --destination challenge/handout.zip --json
hercules-workspace --root "<host-workspace-root>" export --session <session-id> --source challenge/report.md --destination "<host-report-path>" --json
```

The host destination directory must already exist. Existing destinations are
refused unless `--overwrite` is explicit. Links/reparse points and ownership
manifest transfers are rejected. Successful imports are immediately available
at `/opt/workspace/challenge/handout.zip` in that session's running container;
no restart is needed. Do not implicitly import files into another worker's
challenge folder. MCP tools never browse arbitrary host folders.

The native harness shell does not inherit environment overrides from its MCP
registration. Use the selected registration's `HERCULES_WORKSPACE_ROOT` or setup
state's `workspace_root`. Lifecycle `host_workspace` is the session directory,
not the root: only after its final component matches the reported `session_id`,
use its parent as `--root`. Do not guess it from the launcher checkout.
`HERCULES_ENV_FILE` selects an
external dotenv when running host-side maintenance commands.

## Migrate without losing another client's workspace

Close every MCP connection using the source, including cold connections with
no container. Resolve any container still mounting it; migration never stops
another owner. Use explicit `--state` paths and repeated `--client` selectors
for affected registrations. Cutover preserves launchers, secrets, other servers,
and unrelated configuration; follow the returned reload instructions.

```text
hercules-workspace --root "<old-root>" migrate --destination "<new-root>" --state "<setup-state>" --client <client> --json
```

The original is retained even after successful cutover. `--delete-source` is
not accepted during migration. Only after reviewing custom/unlisted client
configurations and old launchers may an operator explicitly request
`hercules-workspace --root "<old-root>" retire --references-reviewed --json`.
Retirement rechecks owners, mappings, checksums, and pinned evidence. Unknown
owners, changed files, or unresolved references block removal. A retired root
cannot be recreated by an updated Hercules client.

## Read and write safely

- Use `workspace_write_file` with either `content` or `content_base64`, never
  both.
- Use `workspace_read_file(encoding="base64")` for binary evidence.
- For a large file, start with a bounded `max_bytes`. If `truncated=true`,
  continue with `offset=next_offset`; never assume one response contains the
  entire artifact.
- Treat `total_bytes`, `offset`, and `next_offset` as authoritative paging
  metadata.
- Keep generated NSE, Nuclei, payload, screenshot, and retrieval paths inside
  `/opt/workspace`.
- Do not follow or create host-path shortcuts. Hercules rejects traversal,
  alternate-drive paths, and symlink/reparse-point escapes.

## Preserve command evidence

Foreground results may return compact head/tail output while the complete
stream is written incrementally to an artifact. Follow `raw_artifact`,
`stdout_artifact`, and `stderr_artifact` when:

- `output_complete=false`;
- either stream is truncated;
- filtering notes are present;
- a timeout captured partial output.

Terminal rendering has safety caps independent of the requested inline budget.
Hitting one makes inline output incomplete/truncated even if the raw artifact
is complete. Persistent execution audit logs contain IDs/digests and ownership
metadata, not full commands; keep required diagnostics in private evidence.

`timed_out=true` remains a timeout even if findings appear. Check
`terminated=true` before assuming the process group is gone.

## Manage long jobs

Give every `shell_exec_background` call a unique, non-secret job ID. Hercules
rejects a duplicate active ID and applies a configured concurrency ceiling.
Poll with `shell_check_job`; record its generation, state, timestamps, exit
code, and log path. A stale job belongs to an older container generation:
preserve its log, but never signal its old PID because the PID may have been
reused.

Harness deferred-task IDs are not Hercules job IDs. Use the harness's task
interface for a foreground MCP call that it deferred; `shell_check_job` only
accepts the ID used for `shell_exec_background`. Inventory entries are cached;
check a current-generation job before acting on it. `confirmed=false` does not
mean successful termination.

Incomplete launch identity is not permission to kill the PID printed on stdout.
An unverified launch retains controls/evidence: inspect it or explicitly stop
its owned runtime after checking parallel-worker dependencies.

Use `shell_kill_job` only for a current-generation running job and confirm the
returned termination state. Completed and terminated job evidence remains in
the workspace even after private wrapper scripts are cleaned up.

## Recover without confusing state

Container replacement invalidates browser refs/daemons, Metasploit clients and
channels, and running background processes. Workspace evidence persists.
Reopen browser state, reconnect Metasploit, and relaunch necessary jobs from
their recorded inputs. After `system_stop_container`, explicitly call
`system_start_container` to resume the same workspace. Ordinary tools never
start a stopped container. Use `system_start_new_session` only for a clean one.

At task completion/abandonment, record final evidence and unresolved hypotheses,
coordinate parallel workers, and stop only your current owned runtime.
Check `cleanup.confirmed`, `container_disposition`, `guardian_settled`, and
`ports_released`. A cold/unattached session cannot certify external Docker
state. `stopped_preserved` intentionally retains a stopped container when
`PRESERVE_CONTAINER` is enabled. Keep evidence; never broadly prune containers
or workspaces to make a count smaller. There is no idle auto-stop.
