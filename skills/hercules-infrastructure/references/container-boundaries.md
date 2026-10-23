# Container privilege boundaries

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`workspace_inspect` for Dockerfiles/config; `shell_exec` for local fixture inspection; `nmap_scan` only for a scoped daemon endpoint. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Record user, mounts, capabilities, namespaces, and socket exposure for the test container. Compare an intended filesystem/network action with one denied boundary action in a disposable fixture. Keep the host and user workloads out of scope.
2. Positive control: Permitted container operation succeeds within the assigned workspace.
3. Negative control: Container cannot access a protected host file or control socket.

## Evidence and decision

Retain effective UID, mount list, capability set, socket mapping, and denied result. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

Hercules itself uses a privileged managed container; its behavior does not prove another product's isolation. Do not run escape payloads on the host without explicit authorization. Revoke disposable credentials and resources through the approved owner workflow, retain raw observations, settle Hercules jobs, and stop the container after checking parallel dependencies and cleanup confirmation.
