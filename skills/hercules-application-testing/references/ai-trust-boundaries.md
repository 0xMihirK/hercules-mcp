# AI-assisted application trust boundaries

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`network_curl` for a reproducible API exchange; `browser_open` and `browser_snapshot` when the application renders model output. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Trace where untrusted page, document, or tool text enters a prompt and which operations the application can perform afterward. Use a harmless canary instruction in a local or authorized fixture; compare the model's response and any downstream tool action with the stated policy. Keep the original document and the exact submitted request.
2. Positive control: A sanctioned fixture demonstrably follows the canary across the trust boundary.
3. Negative control: The same request without the canary does not trigger the behavior.

## Evidence and decision

Retain input artifact, response, tool-action trace, and the claimed versus observed boundary. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

A refusal or missing tool trace is not proof of safety; inspect logging and test the same boundary with a second benign variant. Remove disposable records and markers only within the approved fixture, retain request/response artifacts, settle owned jobs, and stop the Hercules container after coordinated work.
