---
name: hercules-nuclei
description: Author, validate, or troubleshoot a custom Nuclei YAML template with Hercules when installed templates and tags cannot express an authorized check. Do not use for routine Nuclei scans or unrelated YAML work.
---

# Hercules Nuclei authoring

Prefer installed templates and tags when they answer the question. For a missing authorized detection, read [the Nuclei handbook](references/handbook.md) before writing YAML; use its protocol, matcher, extractor, validation, and debugging guidance relevant to the template. Confirm the target and permitted techniques before active execution.

Use `nuclei_write_template` to save the complete template, validate it in the managed workspace, then use `nuclei_run` on the scoped target. Inspect validation errors and raw artifacts before revising or claiming a result. Start the Hercules container only when the first Docker-backed operation is needed, and stop it after the work when no other worker depends on it.
