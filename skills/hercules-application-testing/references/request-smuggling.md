# HTTP request-framing disagreement

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`network_curl` for baseline HTTP behavior; use a dedicated, approved local fixture via `shell_exec` only when exact framing is required. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Confirm the proxy/backend pair and permitted testing window. Establish one normal keep-alive request, then test a bounded malformed framing variant against a disposable local endpoint with a unique marker. Stop immediately if another user's traffic could be affected.
2. Positive control: A well-framed request is interpreted consistently by both hops.
3. Negative control: Malformed framing is rejected without a second hidden request or response desynchronization.

## Evidence and decision

Retain raw bytes, connection IDs, two-hop logs, and isolation proof. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

Timeouts and 400s do not prove safety or smuggling; production shared connections make this check unsafe without coordination. Remove disposable records and markers only within the approved fixture, retain request/response artifacts, settle owned jobs, and stop the Hercules container after coordinated work.
