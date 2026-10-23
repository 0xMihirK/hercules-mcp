---
name: hercules-assessment-operations
description: Plan and validate authorized assessment operations involving endpoint controls, forensics, initial access, movement, egress, persistence, social workflows, or supply chains with Hercules.
---

# Hercules assessment-operations

Choose the exact operation below and read only its reference. These are assessment playbooks, not standing permission. Before any delivery, credential testing, control alteration, persistence, data transfer, or user contact, require explicit task authorization, a bounded target and impact limit, and a reversible local fixture when possible. Prefer reviewing saved policy and logs before running active checks.

## Select one topic

- [Multi-stage assessment sequencing](references/engagement-sequencing.md)
- [Endpoint control validation](references/endpoint-control-validation.md)
- [Initial access exposure review](references/initial-access-review.md)
- [Input-capture and privacy threats](references/input-capture-threats.md)
- [Shellcode artifact analysis](references/shellcode-safety.md)
- [Windows trust boundary review](references/windows-trust-boundaries.md)
- [Windows mitigation posture](references/windows-exploit-mitigations.md)
- [Evidence integrity and anti-tamper review](references/evidence-integrity.md)
- [Command-channel observability](references/command-channel-observability.md)
- [Data egress controls](references/data-egress-controls.md)
- [Lateral movement boundaries](references/lateral-movement-boundaries.md)
- [Persistence and teardown validation](references/persistence-detection.md)
- [Phishing control review](references/phishing-control-review.md)
- [Human workflow social-engineering controls](references/human-workflow-controls.md)
- [Dependency namespace and registry trust](references/dependency-namespace.md)
- [Software supply-chain provenance](references/supply-chain-provenance.md)

The reference is guidance, not authorization. Check the current MCP schema and installed backend before executing a suggested route. If a prerequisite is absent, report the coverage gap instead of inventing a tool or widening scope.

## Finish

Remove only test-owned artifacts and processes through an approved path, verify the resulting state, retain evidence, and stop the Hercules container after coordinated work. Report cleanup uncertainty rather than claiming success.
