# OSINT collection method

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`recon_whois`, `recon_dns`, and `recon_amass` in passive mode; `workspace_inspect` for supplied evidence. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Define the legal entities, domains, and date range before collection. Keep source URL, collection time, and confidence for each observation, and distinguish an inferred relationship from a DNS/registration fact. Switch to active verification only if the scope permits.
2. Positive control: A known owned domain resolves to the expected authoritative record.
3. Negative control: An unrelated lookalike is excluded from the asset set.

## Evidence and decision

Retain source URL, record, timestamp, ownership rationale, and uncertainty. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

Public sources lag; stale WHOIS and passive DNS are leads, not current ownership proof. Revoke disposable credentials and resources through the approved owner workflow, retain raw observations, settle Hercules jobs, and stop the container after checking parallel dependencies and cleanup confirmation.
