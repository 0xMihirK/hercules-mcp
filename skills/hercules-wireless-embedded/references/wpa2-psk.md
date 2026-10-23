# WPA2 personal-network hygiene

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`workspace_inspect` for AP settings and authorized capture metadata; live RF requires supplied adapter. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Review key rotation, cipher suite, WPS state, and client isolation without recording the passphrase. In a disposable lab, compare one station with the approved key against one with an invalid key, then check guest-to-client access.
2. Positive control: Approved station associates and receives the intended network role.
3. Negative control: Invalid-key station fails and isolated clients remain unreachable.

## Evidence and decision

Retain aP config, association result, roles, and isolation logs. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

A captured handshake is not permission to perform offline guessing. Do not claim key strength from a single connection. Restore lab pairing/commissioning and credentials when applicable, preserve original captures and hashes, stop any owned processes, and report absent hardware or unverified teardown.
