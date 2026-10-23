# Duplicate parameter handling

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`network_curl` for byte-exact query/body permutations. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Identify a parameter that affects authorization or routing. Submit a valid single-value control, then duplicate that name once with contrasting values and compare front-end versus back-end interpretation. Repeat only for the relevant encoding and method.
2. Positive control: Single-value request has a known, stable result.
3. Negative control: Conflicting duplicate values cannot bypass the intended rule.

## Evidence and decision

Retain raw request, ordering, both response and resulting state. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

Proxy normalization or caching may change the request before the app sees it; capture the effective request where possible. Remove disposable records and markers only within the approved fixture, retain request/response artifacts, settle owned jobs, and stop the Hercules container after coordinated work.
