# Wi-Fi configuration baseline

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`workspace_inspect` for controller exports; `network_curl` for an authorized management API if supplied. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Review authentication mode, PMF policy, guest isolation, firmware, and management-plane exposure for each owned WLAN. Test one authorized guest client against a permitted service and a denied internal destination. Compare policy to observed traffic.
2. Positive control: Guest reaches its documented internet or local service.
3. Negative control: Guest cannot reach the protected internal fixture.

## Evidence and decision

Retain controller policy, client role, address assignment, and path logs. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

A network timeout alone is not proof of isolation; use destination or firewall logs. Restore lab pairing/commissioning and credentials when applicable, preserve original captures and hashes, stop any owned processes, and report absent hardware or unverified teardown.
