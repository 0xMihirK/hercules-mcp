# Cryptographic protocol review

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`workspace_inspect` for specifications and captures; bounded `shell_exec` for local test vectors. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Identify the asset, adversary model, primitive, mode, nonce lifecycle, and key boundary. Construct a small local vector that exercises a documented valid message and a tampered message, then compare authentication and error handling. Do not infer key secrecy from algorithm names.
2. Positive control: Known vector verifies and decrypts exactly once as intended.
3. Negative control: Modified ciphertext, nonce, or associated data is rejected without revealing plaintext.

## Evidence and decision

Retain algorithm/version, vector source, nonce usage, redacted outcome, and implementation path. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

Timing noise and undocumented key rotation can mimic flaws; avoid live key extraction or broad oracle probing without authorization. Terminate owned local processes and background jobs, keep the original binary and minimized reproducers unchanged, and stop the container after other workers release it.
