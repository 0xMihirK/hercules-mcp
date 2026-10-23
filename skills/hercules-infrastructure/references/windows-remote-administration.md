# Windows remote administration checks

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`nmap_scan` for SMB/WinRM reachability; `shell_exec` only after confirming a supported installed client and explicit credential-testing scope. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Inventory exposed management services and permitted accounts. Test one known-good low-privilege login, then inspect only its documented shares or endpoint access. Compare denied operations to an authorized administrative control supplied by the engagement.
2. Positive control: Test account authenticates only to its intended service.
3. Negative control: The same account cannot perform a protected administrative operation.

## Evidence and decision

Retain endpoint, protocol, redacted account role, authentication result, and event IDs. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

This image does not promise a dedicated remote-administration suite; verify installed binaries before planning commands. Lockout and spray limits govern every attempt. Revoke disposable credentials and resources through the approved owner workflow, retain raw observations, settle Hercules jobs, and stop the container after checking parallel dependencies and cleanup confirmation.
