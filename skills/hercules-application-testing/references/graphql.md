# GraphQL query boundaries

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`network_curl` for reproducible queries and variables; `browser_*` for an interactive application state. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Use schema documentation or authorized query traffic to identify objects and resolvers. Compare a shallow owner query with a single foreign object ID and a bounded depth/cost variation. Inspect field-level authorization independently of top-level access.
2. Positive control: Permitted identity receives only its own expected fields.
3. Negative control: Foreign object or restricted field is denied without partial sensitive data.

## Evidence and decision

Retain query, variables, role, response errors, and bounded cost observations. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

Disabled introspection is not proof of authorization; compare observed resolvers and avoid unbounded depth tests. Remove disposable records and markers only within the approved fixture, retain request/response artifacts, settle owned jobs, and stop the Hercules container after coordinated work.
