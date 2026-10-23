# Endpoint control validation

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`workspace_inspect` for policy/log exports; `shell_exec` only in an isolated permitted endpoint fixture. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Identify the control, its documented detection condition, and alert destination. Use a vendor-approved inert test artifact or controlled local behavior; compare telemetry with an allowed benign control. Record the exact endpoint policy and user context.
2. Positive control: Expected test event is observed and correlated in the console.
3. Negative control: Benign control does not generate the same security alert.

## Evidence and decision

Retain policy version, test ID, endpoint/console timestamps, and alert record. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

Hercules cannot attest to a Windows EDR from its Kali container. Do not disable controls or introduce bypass code to obtain a passing demonstration. Remove only test-owned artifacts and processes through an approved path, verify the resulting state, retain evidence, and stop the Hercules container after coordinated work. Report cleanup uncertainty rather than claiming success.
