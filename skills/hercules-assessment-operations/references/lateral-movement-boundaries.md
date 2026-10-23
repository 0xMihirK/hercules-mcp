# Lateral movement boundaries

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`nmap_scan` for a narrowly scoped service matrix; `workspace_inspect` for identity/policy evidence. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Model identities, source segments, destination services, and delegation paths. Test one intended administrative route with a supplied test identity and one forbidden cross-segment route using disposable endpoints. Correlate authentication and network logs.
2. Positive control: Authorized admin route succeeds only to its assigned host.
3. Negative control: Lower-privilege or wrong-segment attempt fails without a new session.

## Evidence and decision

Retain source/destination, role, service, event IDs, and session inventory. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

Do not reuse harvested credentials or touch production peers without explicit authorization; an open service is not a movement path. Remove only test-owned artifacts and processes through an approved path, verify the resulting state, retain evidence, and stop the Hercules container after coordinated work. Report cleanup uncertainty rather than claiming success.
