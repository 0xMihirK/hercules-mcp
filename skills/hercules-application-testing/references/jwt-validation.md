# JWT validation

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`workspace_inspect` for a saved token sample; `network_curl` for controlled replay to the authorized application. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Decode header and claims locally without treating decoding as signature verification. Compare expiry, issuer, audience, key identifier, and algorithm handling against the service configuration. Use one test token modified in a non-secret claim to verify rejection without guessing signing keys.
2. Positive control: The original authorized token works within its intended audience and lifetime.
3. Negative control: A modified, expired, or wrong-audience token fails without granting the action.

## Evidence and decision

Retain redacted claims, server response, clock assumptions, and acceptance/rejection matrix. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

Clock skew and alternate issuer configuration can explain unexpected results; do not report a forgery from a decoded token alone. Remove disposable records and markers only within the approved fixture, retain request/response artifacts, settle owned jobs, and stop the Hercules container after coordinated work.
