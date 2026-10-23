# Windows trust boundary review

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`workspace_inspect` for policy/configuration exports; `nmap_scan` only for scoped exposed services. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Identify the exact boundary: user versus admin, service versus interactive session, or local versus domain identity. Review ACL/token evidence for a normal permitted action and a protected action; specify the Windows host/build to which it applies.
2. Positive control: Permitted identity completes its documented operation.
3. Negative control: Lower-privilege identity cannot perform the protected operation.

## Evidence and decision

Retain build number, account role, ACL/token, action, and event log. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

Kali is not a Windows execution environment; static policy review does not confirm live enforcement. Remove only test-owned artifacts and processes through an approved path, verify the resulting state, retain evidence, and stop the Hercules container after coordinated work. Report cleanup uncertainty rather than claiming success.
