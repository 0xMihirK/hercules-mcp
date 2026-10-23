# IoT firmware and exposed services

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`workspace_inspect` for supplied firmware; `ctf_binwalk` and bounded `shell_exec` for offline triage; `nmap_scan` for an owned lab device. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Hash the firmware, identify architecture and filesystem, and inspect credentials/config without copying secrets into notes. Compare embedded service configuration with one safe network request to the test device. Keep extracted files in the owned workspace.
2. Positive control: Documented service responds in its intended role.
3. Negative control: Disabled management endpoint remains inaccessible to the test identity.

## Evidence and decision

Retain firmware hash, extraction paths, version, service banners, and response. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

Binwalk extraction is not code execution proof; firmware may differ from the running device. No physical access is assumed. Restore lab pairing/commissioning and credentials when applicable, preserve original captures and hashes, stop any owned processes, and report absent hardware or unverified teardown.
