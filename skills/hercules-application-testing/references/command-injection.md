# Command execution boundary

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`network_curl` for the vulnerable parameter; `web_vuln_scan` only for a narrow authorized check. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Find where input is expected to become a literal argument or data field. Start with a harmless delimiter/control canary that cannot modify state, and compare server behavior to an inert control. Escalate to execution proof only when explicitly authorized and safely isolated.
2. Positive control: Documented input is processed normally.
3. Negative control: Metacharacters remain data or are rejected; no out-of-band effect occurs.

## Evidence and decision

Retain exact request, response, application log or local marker if authorized. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

Reflected punctuation or an error is not execution proof; avoid destructive commands and distinguish parser failures. Remove disposable records and markers only within the approved fixture, retain request/response artifacts, settle owned jobs, and stop the Hercules container after coordinated work.
