# LoRaWAN and sub-GHz device trust

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`workspace_inspect` for supplied gateway logs and frame captures; live RF requires approved gateway/radio. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Map device EUI, join mode, frame counters, keys' storage locations, and gateway ownership without exposing key values. Compare one normal join/uplink with a stale-counter or unauthorized-device control in a lab. Check network-server acceptance, not only RF reception.
2. Positive control: Registered device joins and increments its counter.
3. Negative control: Unregistered or stale-counter frame is rejected by the network server.

## Evidence and decision

Retain join metadata, counter sequence, gateway log, and server decision. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

An RF capture cannot reveal server-side rejection by itself. Respect regional transmit limits and device battery constraints. Restore lab pairing/commissioning and credentials when applicable, preserve original captures and hashes, stop any owned processes, and report absent hardware or unverified teardown.
