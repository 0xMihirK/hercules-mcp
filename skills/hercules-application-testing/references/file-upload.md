# File upload validation

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`browser_*` for upload UI and authenticated flow; `network_curl` for exact multipart requests. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Document allowed MIME type, extension, size, storage path, and retrieval behavior. Upload a benign marker under an allowed name, then vary one metadata field or filename boundary. Retrieve it only through authorized access and compare bytes/checksum.
2. Positive control: Allowed file is stored and retrieved unchanged for its owner.
3. Negative control: Disallowed type or cross-user retrieval is rejected and no executable interpretation occurs.

## Evidence and decision

Retain upload response, stored/retrieved checksum, URL, and access-control check. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

Client-side rejection alone does not prove server validation; check whether a direct request is accepted. Remove disposable records and markers only within the approved fixture, retain request/response artifacts, settle owned jobs, and stop the Hercules container after coordinated work.
