# Fuzzing practice in a local fixture

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`shell_exec` for a verified installed fuzzer or a small bounded local harness; `workspace_inspect` for corpus and findings. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Choose an isolated parser with deterministic reset. Seed with a valid input, add invalid boundary cases, and measure coverage or unique crash signatures under a fixed time/CPU budget. Minimize and replay findings outside the fuzzer before labeling them.
2. Positive control: Valid seed reaches the intended parser logic.
3. Negative control: Malformed seed is rejected without corrupting state.

## Evidence and decision

Retain corpus hashes, harness version, budget, coverage trend, and reproducer. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

Hercules does not promise a particular fuzzing framework. Zero crashes with poor coverage is not a safety result. Terminate owned local processes and background jobs, keep the original binary and minimized reproducers unchanged, and stop the container after other workers release it.
