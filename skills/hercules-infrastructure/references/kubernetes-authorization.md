# Kubernetes authorization

Use this playbook only for the named boundary in an authorized target or isolated fixture. Confirm target, identities, impact limits, and stopping condition before active work. Read saved notes and artifacts first; start the container only when a Docker-backed operation is actually needed.

## Hercules route

`workspace_inspect` for manifests and RBAC exports; `shell_exec` for a verified kube client only if the engagement supplies it. Check the live MCP tool list and backend availability; raw shell and browser commands do not inherit structured target guarantees.

## Test sequence

1. Map namespace, service account, API verbs, and workload identity. Use a disposable namespace to test one allowed read and one forbidden create/secret read, then compare admission decisions and audit events. Treat cluster-admin access as a separate approval.
2. Positive control: Scoped account performs its intended verb in its namespace.
3. Negative control: Same account cannot perform a privileged verb or cross-namespace read.

## Evidence and decision

Retain manifest, token audience without value, `SelfSubjectAccessReview` outcome, and audit record. Record what was observed separately from inferred impact. A valid control establishes that the test path worked; a missing result without that control is inconclusive.

## Limits and cleanup

Hercules does not guarantee `kubectl` or a cluster context; missing access is a prerequisite gap, not a negative finding. Revoke disposable credentials and resources through the approved owner workflow, retain raw observations, settle Hercules jobs, and stop the container after checking parallel dependencies and cleanup confirmation.
