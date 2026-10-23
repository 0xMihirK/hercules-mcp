# Business-logic invariants

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`browser_*` for stateful UI steps; `network_curl` to replay one documented request precisely. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Write the invariant first: who may change what, in which order, and how many times. Observe a valid transition, then change one step, role, amount, or sequence with disposable records. Check authoritative state rather than trusting the UI message.
2. Positive control: A valid operation changes exactly the intended record once.
3. Negative control: An invalid sequence leaves the protected state unchanged.

## Evidence and decision

Retain before/after records, actor, timestamps, and the minimal replay sequence. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

Async jobs or compensating transactions may reverse a temporary effect; check after a bounded settle period. Remove disposable records and markers only within the approved fixture, retain request/response artifacts, settle owned jobs, and stop the Hercules container after coordinated work.
