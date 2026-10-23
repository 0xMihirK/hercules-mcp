# WPA3 SAE transition policy

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`workspace_inspect` for AP settings and association traces; live test needs an approved WPA3-capable station. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Record SAE-only versus transition mode, PMF requirement, and client support. Compare a normal SAE association with a deliberately incompatible or downgraded test station in a lab; inspect negotiated mode rather than SSID label.
2. Positive control: Capable station negotiates SAE and required PMF.
3. Negative control: Disallowed legacy mode cannot join a SAE-only WLAN.

## Evidence and decision

Retain negotiated AKM/PMF, AP policy, station log, and firmware versions. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

Transition mode deliberately permits older clients; report its policy tradeoff rather than calling every fallback a bypass. Restore lab pairing/commissioning and credentials when applicable, preserve original captures and hashes, stop any owned processes, and report absent hardware or unverified teardown.
