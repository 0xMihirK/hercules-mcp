# Fuzzing campaign design

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`workspace_inspect` for interface and corpus; `shell_exec_background` plus `shell_check_job` for an approved long local run. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Define a reachable API/format, an input grammar or mutation strategy, and a deterministic reset. Measure useful coverage after a short pilot, then allocate a capped campaign. Deduplicate by stable stack or behavior and preserve every minimized reproducer.
2. Positive control: Seed corpus reaches distinct intended paths.
3. Negative control: Intentionally invalid input does not bypass the harness's rejection path.

## Evidence and decision

Retain harness command, environment, seed set, coverage, unique crash table, and job ID. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

Manage the Hercules job ID, not the harness task ID. Check timeouts/partial output and stop the owned job before container shutdown. Terminate owned local processes and background jobs, keep the original binary and minimized reproducers unchanged, and stop the container after other workers release it.
