# Efficient Execution and Output

## Contents

- [Plan the least expensive useful stage](#plan-the-least-expensive-useful-stage)
- [Parallelism and reuse](#parallelism-and-reuse)
- [Interpret results](#interpret-results)
- [Raw output and artifacts](#raw-output-and-artifacts)
- [Background jobs](#background-jobs)

## Plan the least expensive useful stage

Use the smallest call that can answer the current question:

1. Reuse prior target, service, technology, and artifact evidence.
2. Run passive or light discovery only for missing facts.
3. Narrow targets, ports, paths, tags, scripts, and rates before active work.
4. Verify one signal before escalating to broad scanning or exploitation.
5. Stop when the evidence answers the request or a scope boundary is reached.

Do not run a broad scanner merely to reproduce information already returned by
DNS, HTTP, Nmap, Nuclei, or browser evidence.

## Parallelism and reuse

Parallelize independent passive DNS/WHOIS queries and small light probes when
the server has capacity. Serialize:

- steps that consume the previous step's result;
- actions within one browser or Metasploit session;
- intrusive scanning, credential testing, and exploitation;
- operations that write the same workspace path or job ID.

Normalize and deduplicate targets before multi-target calls. Reuse a scan's
`parsed`, `matches`, `results`, or artifact fields instead of starting it again.

## Interpret results

Read result fields before interpreting stdout:

- `status` and `error_type`: execution or validation state.
- `exit_code`: process completion, not proof of a finding.
- `timed_out` and `terminated`: deadline and confirmed cleanup are separate.
- `partial_output`: evidence captured before timeout.
- `output_filtered`: the inline representation intentionally omitted noise.
- `output_complete`: the inline output contains complete process output.
- `evidence_complete`: complete evidence is inline or in a verified artifact.
- `filter_notes` or `output_transform`: what changed.
- `parsed`, `matches`, `results`, `summary`: prefer these over duplicate text.

Empty compact stdout is not proof of absence. Check stderr, exit state,
completeness fields, and artifacts. Preserve explicit no-finding messages and
scanner capability warnings in the report.

## Raw output and artifacts

Default to compact output. Set `include_raw=true` only for exact evidence,
parser debugging, legal text, request/response details, or ambiguous compact
output. Raw output remains bounded inline.

Follow `raw_artifact`, `stdout_artifact`, or `stderr_artifact` rather than
rerunning a scan. Use `workspace_read_file` with `offset` and `max_bytes`; keep
advancing from `next_offset` until the required record is complete.

For binary output, use validated workspace paths and base64 paging. Do not ask
shell tools to print large binary, base64, hex, XML, HTML, or JSON blobs when a
file or parsed representation is available.

## Background jobs

Use foreground execution for short bounded work. For long raw commands:

1. Start one `shell_exec_background` job with a unique non-secret ID.
2. Poll `shell_check_job` with a small `tail_lines` value.
3. Increase the tail only when a boundary or error is missing.
4. Back off between unchanged polls; do not submit the command again.
5. Stop with `shell_kill_job`, then confirm the terminal state.

Treat `stale=true` as a generation change. Preserve the log, but never signal a
recorded PID from an older generation.
