# Server-side outbound request control

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`network_curl` for the input endpoint and an owned local callback fixture. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Identify where the server accepts a URL and what destinations are permitted. Send a unique marker to an authorized callback; separately test one forbidden destination representation without contacting private or external systems outside scope. Observe callback logs and returned content.
2. Positive control: Allowed URL is fetched only under the documented policy.
3. Negative control: Forbidden address or redirect is blocked before any contact.

## Evidence and decision

Retain input URL, resolved destination, callback receipt, response, and redirect trace. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

A blocked response alone does not prove no contact; use zero-contact fixture logs for the negative control. Remove disposable records and markers only within the approved fixture, retain request/response artifacts, settle owned jobs, and stop the Hercules container after coordinated work.
