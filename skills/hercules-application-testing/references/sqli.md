# SQL injection validation

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`network_curl` for paired requests; `sqlmap_run` for a narrow scan after a manual signal. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Locate one parameter tied to a query and establish a known positive/negative application result. Test a non-destructive value change and compare data, errors, and timing under stable load. If evidence warrants, run `sqlmap_run` against that parameter with bounded scope; do not enumerate or dump data without separate authorization.
2. Positive control: Valid value returns its expected record.
3. Negative control: Invalid value returns no unrelated record and does not alter data.

## Evidence and decision

Retain request pairs, status/body difference, scanner settings, and raw artifacts. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

A scanner timeout or rate limit is incomplete coverage; treat boolean and timing noise cautiously. Remove disposable records and markers only within the approved fixture, retain request/response artifacts, settle owned jobs, and stop the Hercules container after coordinated work.
