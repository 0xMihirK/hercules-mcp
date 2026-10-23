# Shellcode artifact analysis

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`workspace_inspect` for supplied bytes; `shell_exec` for offline disassembly only in a controlled workspace. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Hash and identify architecture/encoding before interpretation. Disassemble without executing, map system calls/import resolution and network destinations, and compare the artifact to the engagement's allowed behavior. Keep candidate behavior labeled inferred until an isolated lab confirms it.
2. Positive control: Known benign sample decodes under the expected architecture.
3. Negative control: Truncated or wrong-architecture bytes are not given a confident behavior label.

## Evidence and decision

Retain byte hash, offsets, decoded instructions, and uncertainty notes. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

Do not run unknown payload bytes in Hercules or on the host. No emulation/decompiler capability is promised. Remove only test-owned artifacts and processes through an approved path, verify the resulting state, retain evidence, and stop the Hercules container after coordinated work. Report cleanup uncertainty rather than claiming success.
