# WAF and application differential

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`network_curl` for matched requests; `web_scan` with `wafw00f` only for fingerprint context. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. First confirm what the application accepts without a filter using a local or permitted control. Compare a small family of semantically equivalent, harmless requests at the protected edge. Record both edge response and origin behavior rather than inferring bypass from a changed status.
2. Positive control: Known benign request reaches the application.
3. Negative control: A disallowed test never reaches the protected operation.

## Evidence and decision

Retain canonical request, encoded variant, edge/origin logs, and normalization notes. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

Different status codes can come from caching or bot checks; do not claim bypass without origin evidence. Remove disposable records and markers only within the approved fixture, retain request/response artifacts, settle owned jobs, and stop the Hercules container after coordinated work.
