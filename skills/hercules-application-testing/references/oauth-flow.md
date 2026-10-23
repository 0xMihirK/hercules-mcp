# OAuth and OpenID flow

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`browser_open`, `browser_snapshot`, and `browser_act` for redirects and consent; `network_curl` for an isolated callback check. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Record the authorized client, redirect URI, scopes, PKCE challenge, and state binding through one complete login. Attempt one controlled mismatch in state, verifier, or redirect target using test accounts. Verify both the browser result and server-side token/account binding.
2. Positive control: The original flow binds the correct account and requested scopes.
3. Negative control: A mismatched verifier or state cannot complete login or bind another account.

## Evidence and decision

Retain redirect chain, redacted parameters, consent scope, callback response, and account identity. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

Provider error pages can conceal successful background sessions; verify account state after the callback. Remove disposable records and markers only within the approved fixture, retain request/response artifacts, settle owned jobs, and stop the Hercules container after coordinated work.
