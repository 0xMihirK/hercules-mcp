# Windows local privilege review

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`workspace_inspect` for provided policy exports; Windows-specific commands through `shell_exec` only in an authorized reachable Windows environment. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Record token privileges, local group membership, service ACLs, scheduled tasks, and patch level. Separate configuration weakness from an exploitable path by checking the exact principal and object permissions. Prefer a reversible test artifact over service disruption.
2. Positive control: Test principal can perform its expected local operation.
3. Negative control: Same principal cannot alter the protected service or file.

## Evidence and decision

Retain token/ACL output, service identity, object path, and event log. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

The Kali container is not a Windows host. Do not claim Windows local privilege findings without a real, authorized Windows context. Revoke disposable credentials and resources through the approved owner workflow, retain raw observations, settle Hercules jobs, and stop the container after checking parallel dependencies and cleanup confirmation.
