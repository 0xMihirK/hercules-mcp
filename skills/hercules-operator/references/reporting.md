# Evidence-led security reporting

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`workspace_inspect` and `workspace_read_file` for retained raw evidence; no new target contact for drafting. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. For each finding, separate observed fact, inference, impact conditional on assumptions, and recommended remediation. Include the minimal reproducible sequence, affected identity/asset, controls, timestamps, and artifact paths. Mark rejected candidates and untested branches explicitly.
2. Positive control: A reviewer can follow saved evidence to reproduce the supported claim.
3. Negative control: A decoy or rejected candidate is not restated as accepted.

## Evidence and decision

Retain finding ID, scope, method, response/log excerpt, artifact hash, and cleanup state. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

Do not equate exit_code zero with success or a scanner label with confirmation. Never include secrets or claim cleanup without checked response fields. Close owned jobs, preserve useful artifacts and notes, and stop the container only when no parallel worker still needs it. Confirm the stop response; report any unverified cleanup.
