# Workspace, Evidence, and Jobs

## Select and preserve the right session

Hercules mounts one owned host session at `/opt/workspace`. Keep the current
system session while working on the same engagement. Call
`system_start_new_session` only when changing engagements or when a clean
workspace is required. The rotation is transactional: on startup failure,
inspect the returned active session and recovery state instead of assuming the
old evidence was lost.

`system_list_sessions` reports ownership, state, generation, timestamps, bytes,
pinning, and retention eligibility. An `active`, `pinned`, `unowned`, or
running-job session must not be pruned. Host operators use
`hercules-workspace pin`, `unpin`, `prune`, and `migrate`; pruning is a report
unless they explicitly pass `--apply`.

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

`timed_out=true` remains a timeout even if findings appear. Check
`terminated=true` before assuming the process group is gone.

## Manage long jobs

Give every `shell_exec_background` call a unique, non-secret job ID. Hercules
rejects a duplicate active ID and applies a configured concurrency ceiling.
Poll with `shell_check_job`; record its generation, state, timestamps, exit
code, and log path. A stale job belongs to an older container generation:
preserve its log, but never signal its old PID because the PID may have been
reused.

Use `shell_kill_job` only for a current-generation running job and confirm the
returned termination state. Completed and terminated job evidence remains in
the workspace even after private wrapper scripts are cleaned up.

## Recover without confusing state

Container replacement invalidates browser refs/daemons, Metasploit clients and
channels, and running background processes. Workspace evidence persists.
Reopen browser state, reconnect Metasploit, and relaunch necessary jobs from
their recorded inputs. After `system_stop_container`, explicitly call
`system_start_new_session`; ordinary tools will not silently resurrect it.
