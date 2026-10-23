# OSINT asset correlation

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`recon_amass` passive, `recon_dns`, and `recon_whois`; no broad scans until ownership is established. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Merge passive names by canonical hostname, then correlate DNS, certificate, and registration clues within the authorized entity. Check one positive owned asset and one similarly named non-owned asset before adding hosts to the scan list. Preserve conflicting evidence instead of forcing a match.
2. Positive control: Owned control has matching domain and organization evidence.
3. Negative control: Lookalike or third-party SaaS endpoint is not silently treated as owned.

## Evidence and decision

Retain candidate table, source timestamps, resolver output, and scope decision. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

CDNs and shared hosting break IP-to-owner inference; ask for scope clarification before active contact. Revoke disposable credentials and resources through the approved owner workflow, retain raw observations, settle Hercules jobs, and stop the container after checking parallel dependencies and cleanup confirmation.
