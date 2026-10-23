# Concurrent state transitions

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`network_curl` with a bounded local script through `shell_exec` only when sequential checks cannot reveal the race. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Measure the normal single-request transition and its idempotency key. Run a small, authorized synchronized batch against disposable state, then reconcile all resulting records. Cap concurrency and stop on rate limits or unintended load.
2. Positive control: One request produces exactly one permitted transition.
3. Negative control: Concurrent duplicates never exceed the intended total or create conflicting states.

## Evidence and decision

Retain request IDs, start times, final records, and concurrency bound. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

Timing-dependent negatives are weak; repeat a small number of times and distinguish network jitter from application serialization. Remove disposable records and markers only within the approved fixture, retain request/response artifacts, settle owned jobs, and stop the Hercules container after coordinated work.
