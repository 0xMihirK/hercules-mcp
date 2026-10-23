# Linux local privilege review

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`workspace_inspect` for supplied configs; `shell_exec` and post-exploitation resources only after authorized local execution. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Record current UID, groups, sudo policy, SUID/capability binaries, and scheduled-task ownership in the approved container or host. Choose one plausible permission boundary and verify it with a read-only operation first. Do not execute escalation chains from a checklist alone.
2. Positive control: Current identity performs its documented local task.
3. Negative control: Protected root-owned action remains denied.

## Evidence and decision

Retain identity, exact policy or file mode, selected binary version, and denial evidence. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

Enumeration output can be incomplete or stale; a writable path is not proof of escalation without a safe, authorized demonstration. Revoke disposable credentials and resources through the approved owner workflow, retain raw observations, settle Hercules jobs, and stop the container after checking parallel dependencies and cleanup confirmation.
