# Z-Wave inclusion and command classes

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`workspace_inspect` for controller exports and sanitized RF traces; live test needs approved controller/radio. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Inventory node IDs, security class, inclusion mode, and sensitive command classes. Compare one authorized test-node inclusion with an out-of-window attempt, then check controller authorization before any device action.
2. Positive control: Expected test node joins in the approved inclusion window.
3. Negative control: Unexpected node or protected command is rejected.

## Evidence and decision

Retain controller state, node security class, inclusion events, and device outcome. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

Home automation actions may have physical effects. Captures alone cannot prove controller policy. Restore lab pairing/commissioning and credentials when applicable, preserve original captures and hashes, stop any owned processes, and report absent hardware or unverified teardown.
