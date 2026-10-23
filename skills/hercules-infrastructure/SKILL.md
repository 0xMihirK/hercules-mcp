---
name: hercules-infrastructure
description: Assess authorized identity, cloud, CI/CD, container, network, reconnaissance, and privilege boundaries with Hercules when infrastructure evidence needs focused validation.
---

# Hercules infrastructure

Pick the exact boundary below and read only its reference. Confirm ownership before active contact, test with supplied low-privilege identities and disposable resources, and compare allowed and denied behavior. A cloud credential, Windows host, cluster context, or specialized client is never implied by the Kali image. Verify prerequisites before using `shell_exec`.

## Select one topic

- [Directory identity boundaries](references/directory-boundaries.md)
- [Windows remote administration checks](references/windows-remote-administration.md)
- [CI/CD pipeline trust](references/pipeline-trust.md)
- [CI/CD secret exposure](references/pipeline-secrets.md)
- [Cloud identity and configuration](references/cloud-identity.md)
- [Container privilege boundaries](references/container-boundaries.md)
- [Kubernetes authorization](references/kubernetes-authorization.md)
- [Network segmentation and protocol exposure](references/network-segmentation.md)
- [Linux local privilege review](references/linux-privilege-review.md)
- [Windows local privilege review](references/windows-privilege-review.md)
- [OSINT collection method](references/osint-method.md)
- [OSINT asset correlation](references/osint-asset-correlation.md)

The reference is guidance, not authorization. Check the current MCP schema and installed backend before executing a suggested route. If a prerequisite is absent, report the coverage gap instead of inventing a tool or widening scope.

## Finish

Revoke disposable credentials and resources through the approved owner workflow, retain raw observations, settle Hercules jobs, and stop the container after checking parallel dependencies and cleanup confirmation.
