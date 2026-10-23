# Template-expression handling

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`network_curl` for exact input; `browser_read` when rendering alters the output. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Find the rendering context and establish how literal metacharacters appear. Compare a harmless arithmetic expression with a quoted literal in one controlled field. Use the observed output to distinguish server evaluation from client-side rendering or simple text substitution.
2. Positive control: Ordinary text renders exactly as intended.
3. Negative control: Expression syntax is escaped or treated as literal data.

## Evidence and decision

Retain input, rendered output, template context, and any server error. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

Arithmetic output alone can be coincidental; verify with a second benign expression and no side effects. Remove disposable records and markers only within the approved fixture, retain request/response artifacts, settle owned jobs, and stop the Hercules container after coordinated work.
