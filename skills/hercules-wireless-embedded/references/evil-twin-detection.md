# Lookalike access-point detection

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`workspace_inspect` for beacon/certificate captures; local isolated radio fixture only when supplied. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Define the legitimate SSID, BSSID set, certificate trust, and captive-portal behavior. Compare a known AP with a controlled lookalike in a shielded or approved lab. Focus on client decision and user warning rather than collecting credentials.
2. Positive control: Client joins the legitimate AP and validates the expected server certificate.
3. Negative control: Client rejects or clearly warns on the lookalike and unexpected portal.

## Evidence and decision

Retain beacon/certificate fingerprints, client prompts, association outcome, and lab isolation. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

SSID equality is not identity. Do not create a public lookalike network or solicit real user credentials. Restore lab pairing/commissioning and credentials when applicable, preserve original captures and hashes, stop any owned processes, and report absent hardware or unverified teardown.
