# Dependency namespace and registry trust

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`workspace_inspect` for lockfiles and registry configuration; `network_curl` for metadata from an approved registry. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Identify package names, namespaces, registry precedence, pinning, and install scripts. Test resolution with an inert locally hosted package fixture rather than publishing a competing public package. Compare locked install with an intentionally ambiguous test configuration.
2. Positive control: Pinned dependency resolves to the approved digest/source.
3. Negative control: Untrusted namespace candidate is rejected or cannot outrank the approved source.

## Evidence and decision

Retain resolver log, package source, digest, lockfile, and test-registry setup. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

Do not publish lookalike packages or run install hooks in a user's environment without explicit authorization. Remove only test-owned artifacts and processes through an approved path, verify the resulting state, retain evidence, and stop the Hercules container after coordinated work. Report cleanup uncertainty rather than claiming success.
