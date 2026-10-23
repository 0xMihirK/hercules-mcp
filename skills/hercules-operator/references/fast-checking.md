# Fast, reliable hypothesis checks

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`workspace_inspect` before Docker; then one narrow structured tool chosen from `network_curl`, `nmap_scan`, `nuclei_run`, or browser tools. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. State a falsifiable question and the smallest observation that could answer it. Reuse an existing raw artifact if it already contains that observation; otherwise run one bounded probe with a known positive and negative control. Expand only when evidence changes the next decision.
2. Positive control: Known-positive fixture produces the expected observation.
3. Negative control: Known-negative fixture does not produce it under the same conditions.

## Evidence and decision

Retain hypothesis, tool call, raw artifact, controls, time budget, and next decision. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

A timeout, 429, hidden tool, or incomplete output is failed coverage, not a negative result. Avoid repeated broad scans or unchanged polling. Close owned jobs, preserve useful artifacts and notes, and stop the container only when no parallel worker still needs it. Confirm the stop response; report any unverified cleanup.
