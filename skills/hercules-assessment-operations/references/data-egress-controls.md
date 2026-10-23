# Data egress controls

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`workspace_inspect` for synthetic test data; `network_curl` or `ncat` only to an owned local receiver. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Define the allowed destination, volume cap, data classification, and alert expectation. Transfer a short synthetic marker through one approved route, then check that an unauthorized destination is blocked without contacting a third party. Reconcile receiver and monitoring logs.
2. Positive control: Approved marker reaches the owned receiver under policy.
3. Negative control: Forbidden route has zero receiver contact and produces the expected denial.

## Evidence and decision

Retain marker checksum, endpoint, volume, policy hit, and cleanup. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

Never send real sensitive data as a probe. A client timeout alone is not evidence that egress was blocked. Remove only test-owned artifacts and processes through an approved path, verify the resulting state, retain evidence, and stop the Hercules container after coordinated work. Report cleanup uncertainty rather than claiming success.
