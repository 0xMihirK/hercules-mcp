# Crash reproduction and triage

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`workspace_inspect` for reproducer and logs; `shell_exec` in an isolated local fixture for bounded execution. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Pin binary hash, arguments, environment, and input bytes. Reproduce once with the supplied crashing input and once with a nearby valid control; record signal, instruction pointer, and faulting access where available. Reduce the input while preserving the crash signature.
2. Positive control: Valid control completes normally under the same environment.
3. Negative control: Candidate input reproduces the same fault signature, not merely a timeout.

## Evidence and decision

Retain binary/input hashes, exit signal, stack or fault address, and minimization steps. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

ASLR, race conditions, and missing symbols affect reproducibility; a crash does not itself prove exploitability. Terminate owned local processes and background jobs, keep the original binary and minimized reproducers unchanged, and stop the container after other workers release it.
