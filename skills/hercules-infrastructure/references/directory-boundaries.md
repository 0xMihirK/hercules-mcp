# Directory identity boundaries

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`nmap_scan` and `recon_dns` for service discovery; `shell_exec` for a verified installed directory client only. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Map the domain, trust relationships, service accounts, and authorized test identities from supplied evidence. Compare one normal account's access to a protected object with an explicitly permitted lower-privilege account; record the effective group/token and target ACL. Treat ticket and replication operations as separate high-impact steps.
2. Positive control: Permitted group can access its assigned object.
3. Negative control: Unpermitted identity cannot read or change the object.

## Evidence and decision

Retain domain naming, principal roles, ACL, access attempt, and server-side event IDs. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

Do not infer domain compromise from an open LDAP/Kerberos port. A host-network container is not an isolated directory client; check credentials and scope before binding. Revoke disposable credentials and resources through the approved owner workflow, retain raw observations, settle Hercules jobs, and stop the container after checking parallel dependencies and cleanup confirmation.
