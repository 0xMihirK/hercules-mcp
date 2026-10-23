# Mobile application trust boundaries

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`workspace_inspect` for provided APK/IPA and logs; `network_curl` for an owned backend API. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Map package identity, declared permissions, storage, and network endpoints from supplied artifacts. Compare a valid app session with an expired or second-user API request; distinguish client-side controls from server authorization. Use a device/emulator only if separately provided.
2. Positive control: Legitimate app identity can reach its assigned data.
3. Negative control: Altered client request cannot read another user's data.

## Evidence and decision

Retain package hash, manifest, redacted traffic, API response, and device context. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

Hercules does not include a mobile emulator or instrumentation stack by contract; static findings need runtime confirmation. Restore lab pairing/commissioning and credentials when applicable, preserve original captures and hashes, stop any owned processes, and report absent hardware or unverified teardown.
