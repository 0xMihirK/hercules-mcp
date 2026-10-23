# Zigbee, Thread, and Matter commissioning

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`workspace_inspect` for fabric/network configuration and supplied traces; live commissioning requires owned devices and radio. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Identify protocol, trust anchor, commissioning window, fabric membership, and ACL role. Compare one valid test device commission with an expired or wrong-fabric attempt. Verify the actual controlled device state and revoke the test node.
2. Positive control: Valid device is admitted with its intended role.
3. Negative control: Wrong-fabric or closed-window attempt cannot join or control the device.

## Evidence and decision

Retain commissioning log, fabric/ACL snapshot, device state, and teardown. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

These protocols have different trust models; do not transfer a Zigbee conclusion to Matter or infer authorization from radio reception. Restore lab pairing/commissioning and credentials when applicable, preserve original captures and hashes, stop any owned processes, and report absent hardware or unverified teardown.
