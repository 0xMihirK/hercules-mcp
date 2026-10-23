# Enterprise Wi-Fi identity validation

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`workspace_inspect` for EAP/certificate settings and sanitized supplicant logs; live test needs authorized station/AP. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Document EAP method, server-certificate validation, accepted CAs/names, and identity provisioning. In a lab, compare normal authentication with an unexpected server certificate and verify the client fails before credentials are sent.
2. Positive control: Station authenticates to the approved identity service.
3. Negative control: Station rejects a mismatched certificate or name.

## Evidence and decision

Retain supplicant configuration, certificate chain, EAP trace, and authentication log. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

Containerized analysis cannot attest to a real station's UI prompts; do not capture live credentials. Restore lab pairing/commissioning and credentials when applicable, preserve original captures and hashes, stop any owned processes, and report absent hardware or unverified teardown.
