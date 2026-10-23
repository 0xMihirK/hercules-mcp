# Wi-Fi management-frame resilience

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`workspace_inspect` for supplied frame captures; live test only with separately authorized radio hardware and tooling. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Record AP/client capabilities, channel, PMF negotiation, and baseline association. In an isolated RF lab, compare behavior when a controlled management-frame test is presented to a PMF-capable versus legacy client; observe reconnect and logs without disrupting others.
2. Positive control: Authorized station remains associated under ordinary AP operation.
3. Negative control: Protected station ignores unauthenticated management frames as required.

## Evidence and decision

Retain association frames, PMF flags, station log, and RF isolation evidence. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

Do not transmit in shared spectrum without explicit authorization. A capture-only review cannot prove client resilience. Restore lab pairing/commissioning and credentials when applicable, preserve original captures and hashes, stop any owned processes, and report absent hardware or unverified teardown.
