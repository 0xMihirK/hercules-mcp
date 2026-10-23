---
name: hercules-nmap-nse
description: Author, validate, or troubleshoot a custom Nmap NSE Lua script with Hercules when installed NSE scripts cannot express an authorized check. Do not use for routine Nmap scanning or unrelated Lua work.
---

# Hercules Nmap NSE authoring

Prefer an installed script when it answers the question. For a missing authorized check, read [the NSE handbook](references/handbook.md) before writing Lua; use its rule, library, validation, and debugging guidance relevant to the script. Confirm the target and permitted techniques before active execution.

Use `nmap_write_nse_script` to save the complete script, then `nmap_run_nse_script` for the scoped target. Inspect validation errors and raw artifacts before revising or claiming a result. Start the Hercules container only when the first Docker-backed operation is needed, and stop it after the work when no other worker depends on it.
