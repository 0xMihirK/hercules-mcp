# Wi-Fi reassembly and patch posture

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`workspace_inspect` for firmware/driver versions and supplied packet traces. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Inventory AP and station chipsets, firmware, encryption mode, and patch advisories. Compare normal protected traffic with a vendor-provided regression trace or isolated test fixture for fragmentation/reassembly handling. Validate only a benign marker at the receiving endpoint.
2. Positive control: Normal protected frames reach the intended endpoint.
3. Negative control: Malformed/replayed fragments do not become accepted application traffic.

## Evidence and decision

Retain versions, negotiated cipher, trace, receiving log, and advisory mapping. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

Patch presence is not behavioral proof; absence of a live fixture is a coverage limit. Avoid malformed RF traffic on production channels. Restore lab pairing/commissioning and credentials when applicable, preserve original captures and hashes, stop any owned processes, and report absent hardware or unverified teardown.
