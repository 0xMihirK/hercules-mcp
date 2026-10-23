# Input-capture and privacy threats

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`workspace_inspect` for supplied source/binary and OS policy; no live capture without explicit authorization. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Map which process can read keyboard or clipboard events and which storage/network sinks could retain them. In a local synthetic fixture, use generated non-secret events to verify consent, OS permission prompts, and data retention limits. Inspect access control before any runtime instrumentation.
2. Positive control: Approved test application receives only its own synthetic input.
3. Negative control: Unauthorized process cannot access protected input stream or stored trace.

## Evidence and decision

Retain process identity, permission setting, synthetic event ID, and retention result. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

Do not record real keystrokes, credentials, or users. The container cannot test another OS's input permissions by inference. Remove only test-owned artifacts and processes through an approved path, verify the resulting state, retain evidence, and stop the Hercules container after coordinated work. Report cleanup uncertainty rather than claiming success.
