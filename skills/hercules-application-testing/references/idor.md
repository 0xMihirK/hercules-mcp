# Object-reference authorization

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`network_curl` for paired object IDs and sessions; `browser_read` only when the result is UI-only. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Create or identify one object per authorized test identity. Replay the same read and write operation while changing only the object reference; check both response and persisted state. Keep identifiers redacted if they reveal sensitive records.
2. Positive control: Owner accesses and updates the test object.
3. Negative control: Other identity cannot read or mutate it.

## Evidence and decision

Retain paired actor/object matrix, request paths, response summaries, and after-state. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

Uniform 200 responses may hide different content; compare record identity and side effects. Remove disposable records and markers only within the approved fixture, retain request/response artifacts, settle owned jobs, and stop the Hercules container after coordinated work.
