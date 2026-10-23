# Untrusted deserialization

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`network_curl` for a minimal typed payload; `workspace_inspect` for supplied serialized samples. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Identify the parser and accepted media type from observed traffic or local artifacts. Start with a harmless structural variant that should fail validation; compare parser errors and resulting state. Do not attempt gadget execution unless explicitly authorized and isolated.
2. Positive control: A valid serialized sample round-trips as documented.
3. Negative control: An unexpected type or disallowed field is rejected without side effects.

## Evidence and decision

Retain payload shape, parser error, content type, and state check. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

A generic 500 does not identify deserialization; distinguish transport, parser, and application errors. Remove disposable records and markers only within the approved fixture, retain request/response artifacts, settle owned jobs, and stop the Hercules container after coordinated work.
