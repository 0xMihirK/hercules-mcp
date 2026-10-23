# CI/CD secret exposure

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`workspace_inspect` for manifests and logs; `network_curl` for scoped CI metadata. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Inventory where a secret is injected and where logs/artifacts can persist. Use a synthetic canary secret in a disposable workflow to verify masking and artifact retention; avoid printing real credentials. Check forked/untrusted jobs separately.
2. Positive control: A permitted job can consume the synthetic value without revealing it.
3. Negative control: Untrusted job, log, and downloadable artifact contain no canary bytes.

## Evidence and decision

Retain redacted workflow config, job role, canary search result, artifact list, and retention setting. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

Masking a log is not sufficient if artifacts or child processes expose values; mark untested surfaces explicitly. Revoke disposable credentials and resources through the approved owner workflow, retain raw observations, settle Hercules jobs, and stop the container after checking parallel dependencies and cleanup confirmation.
