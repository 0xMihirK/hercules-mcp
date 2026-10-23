# Wi-Fi asset inventory

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`workspace_inspect` for site surveys/captures; live discovery only with explicitly supplied monitor-capable adapter. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. List approved SSIDs, BSSIDs, channels, security modes, and survey boundaries. Compare a known owned AP with one neighboring non-owned AP so the latter stays out of active testing. Correlate advertised security with controller configuration.
2. Positive control: Known owned AP matches inventory and policy.
3. Negative control: Nearby third-party AP is excluded from scope.

## Evidence and decision

Retain survey time/location, BSSID/channel, controller record, and scope rationale. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

Passive visibility is not ownership; channel hopping and device roaming can miss assets. Restore lab pairing/commissioning and credentials when applicable, preserve original captures and hashes, stop any owned processes, and report absent hardware or unverified teardown.
