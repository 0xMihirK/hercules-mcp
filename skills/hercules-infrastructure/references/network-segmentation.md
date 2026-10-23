# Network segmentation and protocol exposure

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`recon_dns`, `nmap_scan`, and `ncat` for narrowly scoped reachability; `network_hping3` only for approved packet tests. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Build a source/destination/port matrix from the rules of engagement. Test one allowed path and one denied path with controlled endpoints, then correlate with server or firewall logs. Use protocol-specific handshakes before treating an open port as a service.
2. Positive control: Allowed path completes its expected handshake.
3. Negative control: Denied path produces zero application contact.

## Evidence and decision

Retain source interface, route, destination, port, timestamps, handshake, and rule hit. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

Timeouts can reflect routing or rate limiting; report path coverage rather than declaring a firewall effective from silence. Revoke disposable credentials and resources through the approved owner workflow, retain raw observations, settle Hercules jobs, and stop the container after checking parallel dependencies and cleanup confirmation.
