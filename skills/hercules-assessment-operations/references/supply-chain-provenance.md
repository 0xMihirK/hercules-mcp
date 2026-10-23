# Software supply-chain provenance

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`workspace_inspect` for SBOM, build logs, signatures, and lockfiles; `network_curl` for an approved artifact registry. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Trace source revision through build inputs, signed artifact, and deployment record. Verify one known-good signature/digest and one tampered local copy with the same verifier; check that the runtime resolves the pinned artifact.
2. Positive control: Approved artifact validates and maps to the intended revision.
3. Negative control: Tampered copy or wrong signer is rejected before use.

## Evidence and decision

Retain revision, builder identity, digest, attestation result, and deployment record. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

A package name or tag is not immutable identity. Missing provenance is unknown, not proof of a compromised build. Remove only test-owned artifacts and processes through an approved path, verify the resulting state, retain evidence, and stop the Hercules container after coordinated work. Report cleanup uncertainty rather than claiming success.
