# Bug localization from artifacts

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`workspace_inspect` for inputs, code, and logs; `shell_exec` for local-only reduced tests. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Classify the observed failure by parser stage, trust boundary, and reproducibility. Reduce one failing input and compare it with a valid neighbor, then inspect the smallest code path accounting for the divergence. Maintain observed, inferred, and unknown columns.
2. Positive control: Control input exercises the intended path without failure.
3. Negative control: Reduced candidate still triggers the same class of failure.

## Evidence and decision

Retain input hashes, stack/log slice, affected function, and reduction history. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

A changed error message is not the same bug; verify signature stability before expanding the hypothesis. Terminate owned local processes and background jobs, keep the original binary and minimized reproducers unchanged, and stop the container after other workers release it.
