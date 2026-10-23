# CI/CD pipeline trust

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`workspace_inspect` for checked-in definitions; `network_curl` for an authorized CI API, if available. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Trace untrusted contribution through triggers, runner permissions, artifact promotion, and deployment credentials. Evaluate a benign test branch or local fixture with an inert marker rather than executing untrusted code in production. Compare trusted and untrusted event contexts.
2. Positive control: A trusted release event receives only documented privileges.
3. Negative control: An untrusted event cannot access protected variables or publish a release artifact.

## Evidence and decision

Retain trigger YAML, event type, runner context, artifact digest, and audit log. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

A skipped job is not evidence of correct secret isolation; inspect effective permissions and forks/PR trigger rules. Revoke disposable credentials and resources through the approved owner workflow, retain raw observations, settle Hercules jobs, and stop the container after checking parallel dependencies and cleanup confirmation.
