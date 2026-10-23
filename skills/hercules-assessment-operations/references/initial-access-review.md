# Initial access exposure review

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`recon_dns`, `nmap_scan`, and `network_curl` for scoped endpoints; `browser_*` for an authorized login flow. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Enumerate externally reachable owned services and map each to authentication, MFA, and patch ownership. Validate one known-good test account and one rejected attempt within lockout limits; report exposed pathways before considering exploitation.
2. Positive control: Approved test user reaches only the intended service.
3. Negative control: Invalid or underprivileged user cannot enter the protected workflow.

## Evidence and decision

Retain endpoint, service version, authentication outcome, and lockout budget. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

An open port is exposure, not compromise. Credential spraying and delivery campaigns require explicit authorization. Remove only test-owned artifacts and processes through an approved path, verify the resulting state, retain evidence, and stop the Hercules container after coordinated work. Report cleanup uncertainty rather than claiming success.
