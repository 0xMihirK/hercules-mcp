# Redirect destination validation

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`network_curl` with redirects disabled first; `browser_open` for user-visible navigation evidence. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Locate a redirect parameter in an authorized flow and record intended destinations. Try one harmless out-of-scope marker URL only if navigation to it is authorized; otherwise inspect the Location header without following it. Check whether normalization or encoding changes the destination.
2. Positive control: Expected relative or allowlisted destination works.
3. Negative control: Untrusted destination is rejected or normalized to the allowed origin.

## Evidence and decision

Retain initial response, Location header, final origin if followed, and referrer behavior. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

Do not infer phishing impact from a raw Location string alone; verify browser behavior within scope. Remove disposable records and markers only within the approved fixture, retain request/response artifacts, settle owned jobs, and stop the Hercules container after coordinated work.
