# Phishing control review

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`workspace_inspect` for approved templates and headers; `network_curl` only to an owned local mail/web fixture. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Define the authorized audience, consent, sending domain, and measurement boundaries before any simulation. Compare one benign approved message with a clearly invalid sender in a closed fixture; check mail authentication and user-reporting workflow without collecting credentials.
2. Positive control: Approved test message is labeled and routed as expected.
3. Negative control: Spoofed fixture message is rejected or flagged, with no user-facing delivery.

## Evidence and decision

Retain sPF/DKIM/DMARC evidence, fixture headers, report event, and campaign closure. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

Do not send real messages or build a credential-harvesting page unless separately authorized. Remove only test-owned artifacts and processes through an approved path, verify the resulting state, retain evidence, and stop the Hercules container after coordinated work. Report cleanup uncertainty rather than claiming success.
