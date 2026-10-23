# Binary first look

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`workspace_inspect` for offline metadata; `shell_exec` for `sha256sum` and verified `file`, `readelf`, `objdump`, `strings`, `xxd`; `ctf_binwalk` for packed artifacts. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Preserve the original bytes and hash before running the sample. Identify format, architecture, sections, imports, and likely entry points; search strings as leads, not proof. Build a small hypothesis table with observed addresses and inferred behavior before choosing dynamic execution.
2. Positive control: Known sample type is identified consistently by header and tooling.
3. Negative control: A text decoy or truncated file does not receive a confident executable classification.

## Evidence and decision

Retain hash, format output, relevant offsets, and hypothesis/confidence notes. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

Static analysis alone cannot confirm runtime behavior. Do not execute unknown binaries on the host; use only approved isolation. Terminate owned local processes and background jobs, keep the original binary and minimized reproducers unchanged, and stop the container after other workers release it.
