# Cloud identity and configuration

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`workspace_inspect` for provided policy/config exports; `network_curl` for explicitly authorized provider APIs. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Start with the exact account/subscription and role in scope. Compare effective permissions to declared policy for one disposable resource, and test a denied action with a low-privilege identity. Inspect metadata endpoints only when explicitly authorized; host networking gives access to the host's network context.
2. Positive control: Declared role can read or modify only its assigned test resource.
3. Negative control: Low-privilege role cannot perform the selected protected action.

## Evidence and decision

Retain policy version, role, resource ID, API response, and audit event. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

The image does not bundle provider-specific assessment CLIs by contract. Avoid assuming provider credentials or inferring cloud isolation from container boundaries. Revoke disposable credentials and resources through the approved owner workflow, retain raw observations, settle Hercules jobs, and stop the container after checking parallel dependencies and cleanup confirmation.
