# Persistence and teardown validation

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`workspace_inspect` for startup definitions; `shell_exec` only against an owned disposable fixture. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Inventory scheduled tasks, services, autoruns, and package hooks for the target platform. In a disposable lab, register one benign short-lived marker, verify detection and ownership, then remove it and confirm no process or entry remains. Record the teardown as part of evidence.
2. Positive control: Authorized temporary marker runs once and is detected.
3. Negative control: Unknown or disabled entry cannot start, and removed marker stays absent.

## Evidence and decision

Retain definition, owner, execution log, removal proof, and follow-up inventory. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

Do not establish persistence on a user system without explicit authorization. Hercules container restart does not prove host cleanup. Remove only test-owned artifacts and processes through an approved path, verify the resulting state, retain evidence, and stop the Hercules container after coordinated work. Report cleanup uncertainty rather than claiming success.
