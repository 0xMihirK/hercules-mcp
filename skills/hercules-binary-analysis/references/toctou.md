# Time-of-check/time-of-use review

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`workspace_inspect` for source/logs; `shell_exec` for a disposable filesystem or API fixture. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Locate the check and the later use of the same mutable object. Reproduce the normal sequence, then alter only the object between check and use under controlled timing. Observe the used object and resulting privilege boundary, not just a successful race loop.
2. Positive control: Stable object produces the documented result.
3. Negative control: Changed object cannot redirect the privileged operation.

## Evidence and decision

Retain check/use timestamps, object identity, final effect, and trial count. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

Filesystem caching and scheduler jitter make negatives weak; do not stress shared services or privileged files. Terminate owned local processes and background jobs, keep the original binary and minimized reproducers unchanged, and stop the container after other workers release it.
