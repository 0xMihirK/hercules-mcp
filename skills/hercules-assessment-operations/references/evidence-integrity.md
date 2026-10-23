# Evidence integrity and anti-tamper review

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`workspace_inspect` for logs and checksums; `workspace_read_file` for bounded comparisons. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Record original hashes, capture time, collection identity, and retention policy before analysis. In a disposable fixture, alter a synthetic log copy to confirm that monitoring or chain-of-custody checks detect the change; never modify real case evidence.
2. Positive control: Original artifact hash matches the collection manifest.
3. Negative control: Tampered copy is flagged and not substituted for the original.

## Evidence and decision

Retain hashes, timestamps, collection tool, tamper-test copy, and alert. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

Absence of an alert may mean the test was not instrumented; do not treat log deletion as an approved action. Remove only test-owned artifacts and processes through an approved path, verify the resulting state, retain evidence, and stop the Hercules container after coordinated work. Report cleanup uncertainty rather than claiming success.
