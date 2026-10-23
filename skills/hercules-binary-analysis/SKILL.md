---
name: hercules-binary-analysis
description: Triage authorized binaries, firmware, crashes, fuzzing results, and cryptographic behavior with existing Hercules workspace and shell tools; use only isolated fixtures for execution.
---

# Hercules binary-analysis

Begin offline with `workspace_inspect` to locate and page the supplied artifact. When Docker-backed analysis is needed, hash it with `sha256sum` via bounded `shell_exec`; use `ctf_binwalk` for embedded contents and verified installed `file`, `readelf`, `objdump`, `strings`, or `xxd` for format, sections, imports, and offsets. Track observed facts, inferred behavior, and unknowns separately. Reuse a prior reproducer before running the sample. Hercules does not promise a decompiler, debugger, or fuzzer; verify any extra binary before routing to it.

## Select one topic

- [Cryptographic protocol review](references/crypto-protocol-review.md)
- [TLS configuration and identity](references/tls-configuration.md)
- [Binary first look](references/binary-first-look.md)
- [Crash reproduction and triage](references/crash-reproduction.md)
- [Exploit-development lab progression](references/exploit-development-learning.md)
- [Exploitability assessment](references/exploitability-assessment.md)
- [Binary mitigation inventory](references/binary-mitigations.md)
- [Time-of-check/time-of-use review](references/toctou.md)
- [Bug localization from artifacts](references/bug-localization.md)
- [Fuzzing practice in a local fixture](references/fuzzing-practice.md)
- [Fuzzing campaign design](references/fuzzing-campaign.md)
- [Vulnerability class and impact](references/vulnerability-classification.md)

The reference is guidance, not authorization. Check the current MCP schema and installed backend before executing a suggested route. If a prerequisite is absent, report the coverage gap instead of inventing a tool or widening scope.

## Finish

Terminate owned local processes and background jobs, keep the original binary and minimized reproducers unchanged, and stop the container after other workers release it.
