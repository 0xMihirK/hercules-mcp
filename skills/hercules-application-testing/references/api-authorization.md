# API authorization and schema

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`network_curl` for paired identities and status/body diffs; `nuclei_run` only for relevant installed checks. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Inventory documented endpoints and one permitted object per test identity. Test object, function, and field authorization separately by changing one identifier or role at a time. Include content-type and schema variations only when the API contract accepts them.
2. Positive control: Owner or permitted role can read or mutate its object.
3. Negative control: A second identity is denied and the object remains unchanged.

## Evidence and decision

Retain request/response pair, token role without secret value, and object state after the call. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

A 404 may mask authorization, and cached responses can mislead; verify state with a fresh authorized read. Remove disposable records and markers only within the approved fixture, retain request/response artifacts, settle owned jobs, and stop the Hercules container after coordinated work.
