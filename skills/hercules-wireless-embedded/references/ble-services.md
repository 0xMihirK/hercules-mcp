# Bluetooth Low Energy services

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`workspace_inspect` for imported HCI/pcap traces; `shell_exec` only with a verified adapter and authorized local fixture. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Record device identity, advertising mode, GATT services, pairing requirement, and characteristic permissions. Observe a normal read or notification, then test one unauthenticated or unpaired access to a non-sensitive characteristic. Correlate over-the-air and application state.
2. Positive control: Paired test device accesses the intended characteristic.
3. Negative control: Unpaired client cannot read or write protected characteristics.

## Evidence and decision

Retain trace timestamps, service UUIDs, pairing state, and device-side log. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

A Docker container does not guarantee a Bluetooth controller. Imported captures support analysis, not a live-radio security claim. Restore lab pairing/commissioning and credentials when applicable, preserve original captures and hashes, stop any owned processes, and report absent hardware or unverified teardown.
