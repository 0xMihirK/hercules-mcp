# Bluetooth Classic pairing and profiles

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`workspace_inspect` for controller logs; verified `shell_exec` utilities only when a local adapter is attached. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Inventory discoverability, pairing policy, and active profiles on an owned device. Compare an approved paired transfer with an unpaired connection attempt to one profile. Check device prompts and logs rather than inferring acceptance from a socket opening.
2. Positive control: Paired client completes the documented profile operation.
3. Negative control: Unpaired client cannot reach the protected profile or data.

## Evidence and decision

Retain device model/firmware, pairing state, profile, prompts, and trace. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

No physical adapter or target device is implied by Hercules. Pairing cache may persist between trials; reset the lab state. Restore lab pairing/commissioning and credentials when applicable, preserve original captures and hashes, stop any owned processes, and report absent hardware or unverified teardown.
