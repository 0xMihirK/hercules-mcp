# Cross-site scripting validation

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`network_curl` for input/output pairs; `browser_open` and `browser_eval` for an authorized local rendering fixture. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Identify reflected, stored, or DOM sink and its HTML/attribute/URL context. Use a benign unique marker to map encoding, then a non-exfiltrating proof only in the authorized fixture. Test the same context with a harmless negative string.
2. Positive control: Legitimate markup or text appears where expected.
3. Negative control: Untrusted input cannot execute in the tested engine/context.

## Evidence and decision

Retain input, DOM snapshot, console or local marker, and screenshot when visual behavior matters. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

Obscura does not enforce CSP; its execution is not evidence of a Chromium CSP bypass. Verify browser fidelity limitations before reporting. Remove disposable records and markers only within the approved fixture, retain request/response artifacts, settle owned jobs, and stop the Hercules container after coordinated work.
