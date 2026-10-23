# TLS configuration and identity

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`network_curl` for a verified HTTPS handshake; `nmap_scan` script mode for a scoped service check. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Record hostname, certificate chain, SNI, negotiated protocol/cipher, and trust store. Compare the intended hostname to one deliberate mismatch against an owned fixture; distinguish server configuration from client verification behavior.
2. Positive control: Correct hostname validates under the expected trust roots.
3. Negative control: Wrong name, expired cert, or invalid chain fails in the test client.

## Evidence and decision

Retain handshake transcript, cert metadata, client version, and verification flags. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

`-k` or disabled verification invalidates the negative control. Browser engine behavior may differ from standard clients. Terminate owned local processes and background jobs, keep the original binary and minimized reproducers unchanged, and stop the container after other workers release it.
