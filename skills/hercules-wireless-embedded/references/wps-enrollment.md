# WPS enrollment policy

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`workspace_inspect` for controller settings and WPS event logs; live checks require isolated authorized AP. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Determine whether PIN, push-button, or disabled enrollment is intended. Observe one operator-approved enrollment, then verify unsolicited enrollment attempts are denied or rate-limited without repeated guesses. Reset the test credential afterward.
2. Positive control: Authorized physical-button flow joins the device when enabled.
3. Negative control: Unsolicited or disabled-mode attempt cannot enroll.

## Evidence and decision

Retain mode, attempt count, AP logs, lockout setting, and new-device list. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

Do not run PIN brute force or exhaust lockout thresholds without separate authorization. Restore lab pairing/commissioning and credentials when applicable, preserve original captures and hashes, stop any owned processes, and report absent hardware or unverified teardown.
