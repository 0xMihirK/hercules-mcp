# Binary mitigation inventory

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`shell_exec` for verified `readelf`, `objdump`, and local compiler metadata; `workspace_inspect` for supplied binary. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Identify PIE, RELRO, NX, canaries, CFI, and sandbox settings from binary metadata and runtime launch context. Check one representative control-flow or write-protection behavior in a local fixture if permitted. Separate build-time flags from effective runtime policy.
2. Positive control: Expected mitigation appears in metadata and affects the fixture as designed.
3. Negative control: A binary missing the flag is identified without assuming it is exploitable.

## Evidence and decision

Retain binary hash, tool output, process maps, and runtime policy. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

Loader differences or stripped metadata can change interpretation; cross-check architecture and launch environment. Terminate owned local processes and background jobs, keep the original binary and minimized reproducers unchanged, and stop the container after other workers release it.
