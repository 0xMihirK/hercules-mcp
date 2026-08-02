---
name: hercules-setup-contract
description: Outcome and safety contract for an AI agent installing or upgrading Hercules MCP
---

# Install or upgrade Hercules MCP

This document is a contract for a capable terminal agent, not a shell recipe.
Inspect the actual host, repository metadata, client documentation, and native
help before acting. Choose commands and recovery steps that fit the operating
system, CPU architecture, shell, Docker context, security policy, and AI client
in front of you. Do not assume a package manager, init system, filesystem
layout, or client configuration shape.

Authoritative context:

- [Docker's complete LLM context](https://docs.docker.com/llms-full.txt)
- [CloakBrowser's official repository](https://github.com/CloakHQ/cloakbrowser)
- [CloakBrowser on PyPI](https://pypi.org/project/cloakbrowser/)

## Completion checkpoint

Installation is complete only when all of these outcomes are true:

- The user confirmed the intended security work, installation scope, and the
  smallest useful Hercules capability set.
- A durable, non-synced checkout is at a known revision and a locked Python
  environment exposes an absolute `hercules` launcher.
- A capability-specific Docker image was built from the repository inputs and
  its labels, binaries, assets, and readiness manifest match the selected
  profile.
- The existing `.env`, secrets, non-secret setup state, workspace evidence,
  verified assets, and unrelated client settings were preserved.
- The independent portable `hercules-mcp` skill was installed, and the active
  client's Hercules STDIO entry points at the absolute launcher without any
  secret or checkout-relative working directory.
- Local, non-destructive MCP checks report the expected tool surface and all
  seven resources. No external target, public IP service, exploit, payload, or
  credential service was touched during setup.

If any checkpoint fails, do not represent the installation as successful.
Restore the last known-good client configuration and setup state, retain
checksum-valid caches, and give the user the smallest actionable prerequisite
or recovery step.

## First-install decisions

First understand what the user intends to do. Explain the important omissions
of a smaller profile, recommend the minimum useful capability bundles, and get
confirmation before building. Core shell, workspace, and lifecycle support is
always present. Optional bundles determine both which binaries enter the image
and which MCP tools are registered; consolidated families such as browser,
Nmap/NSE, and Nuclei should remain intact.

Also confirm whether installation is user-wide or project-local. User-wide is
normally the least surprising default. Ask about an authenticated browser proxy
only if browser capability is selected. Never put proxy credentials in setup
state, image arguments, logs, command display, or MCP client configuration.

An unattended first installation needs an explicit capability and scope
decision supplied by the user or calling environment. Do not silently infer
"everything". During an upgrade, preserve the recorded choices unless the user
explicitly asks to change them.

## Inspect Hercules' read-only setup facts

The existing `hercules` executable provides a read-only setup-information mode
through `--setup-info-json`. Consult it whenever capability, image, dependency,
state-location, or acceptance facts are needed. It normalizes a requested
profile and reports the exact catalog, build inputs, deterministic image
identity, labels, required binaries and wordlists, expected MCP counts,
CloakBrowser artifact, optional CA-secret metadata, non-secret environment
values, schema-4 state locations, and local acceptance assertions.

This interface is deliberately non-mutating. It does not build or update an
image, download assets, write configuration, modify `PATH`, register clients,
or choose preferences. Treat repository metadata and this declarative output as
more authoritative than remembered commands or historical documentation.

## Prepare the host and checkout

Confirm that the host can supply Git, `uv`, and a working Docker-compatible CLI
and daemon. Hercules requires the Docker runtime contract; do not claim
Podman-only compatibility without a separately validated Docker API layer. Use
the host's native mechanism and official vendor guidance to resolve missing
prerequisites. Never silently perform privileged package installation, daemon
changes, group membership changes, or service operations.

Place a fresh managed checkout in a durable user-data location that is not a
cloud-synced project folder. Use a locked editable Python tool environment so
the installed command can still reach the Dockerfile, skill, wordlists, and
runtime configuration. Resolve the absolute launcher location rather than
depending on the client's `PATH`.

For an existing successful installation, update only a clean managed checkout
using a non-rewriting Git operation. Preserve local data and stop if tracked or
nonignored untracked modifications would be overwritten. A checkout without a
committed schema-4 setup state is an incomplete first installation, not proof
that an upgrade succeeded.

## Build the selected runtime image

Use the normalized setup facts to build the exact capability profile. The image
identity covers the selected capabilities, repository build inputs, optional
custom-CA fingerprint, and the pinned CloakBrowser version and artifact hash.
Validate the resulting ownership and identity labels before making it active.
Do not delete older images automatically.

The Dockerfile bootstraps a public CA bundle from a separately pinned image
before Kali's first HTTPS APT request. Repository signature, certificate, and
hostname verification must remain enabled. If the environment performs TLS
interception, accept only a bounded PEM bundle containing certificates and no
private keys. Supply it to BuildKit as the `hercules_build_ca` secret, record
only its normalized SHA-256 in non-secret state and image identity, and never
copy the certificate into the checkout or persist its content.

Use [Docker's complete LLM context](https://docs.docker.com/llms-full.txt) and
the locally installed Docker help to adapt the build to the current Docker
version, context, platform, proxy, and trust policy.

## Resolve and validate CloakBrowser

CloakBrowser source is not bundled in Hercules and should not be installed on
the host merely for Hercules runtime use. When browser capability is selected,
install it inside the Docker image and require all browser readiness checks to
pass.

The repository-supported default is the official PyPI wheel for exact version
`0.5.3`, SHA-256
`9082cfd2f104342fd718d9882984da7674ef6616308dd7932bff4b8bd5cf3cfe`.
The Dockerfile installs that verified artifact and then installs
CloakBrowser's managed Chromium. Validate the installed Python distribution
version, the managed Chromium readiness result, and agent-browser integration.
Hercules must fail browser capability validation if any of these are missing or
incompatible; it must never fall back to a different browser while claiming
CloakBrowser behavior.

If the supported artifact is unavailable or incompatible with the selected
platform, inspect both [the official repository](https://github.com/CloakHQ/cloakbrowser)
and [PyPI](https://pypi.org/project/cloakbrowser/). Prefer the official PyPI
distribution, choose the latest stable compatible release, and avoid a
prerelease unless the user explicitly accepts it. Do not install an unpinned
Git default branch. Resolve the exact version, official artifact URL, and
SHA-256 before building, then include the version and digest in the image
fingerprint, labels, environment facts, and schema-4 state. A fallback is not
complete until the same local readiness checks pass.

Browser operation remains headless-only. Screenshots, native MCP image content,
loopback streaming, and proxy support do not require a headed desktop. Docker
does not provide residential egress, and CloakBrowser cannot guarantee CAPTCHA
or bot-detection avoidance.

## Assets, environment, and state

Keep reusable checksum-validated wordlists in the configured
`HERCULES_WORDLIST_ROOT`, preferably outside the checkout. Provision only the
assets required by the confirmed capability profile, reuse valid caches, and
identify an omitted wordlist as not required rather than failed. Existing
installations may retain their legacy wordlist location.

Treat `.env` as the runtime authority and preserve every unknown value during
upgrades. Generate a strong URL-safe Metasploit RPC secret when needed, store it
only in the protected `.env`, and never print it. Browser proxy URLs and
credentials are likewise secrets. Apply a secure private file mode where the
platform supports it.

Maintain schema-4 non-secret setup state in the platform configuration location
for user scope or the ignored `.hercules/install.json` for project scope.
Preserve unknown non-secret fields. State may record the checkout, revision,
scope, clients, absolute launcher, capabilities, image identity, expected tool
count, workspace and asset roots, CA fingerprint, CloakBrowser version/artifact
URL/digest,
skill paths, and client configuration paths. It must never contain passwords,
tokens, proxy URLs, cookies, certificate contents, or other credentials.

## Skill and MCP client registration

Install the canonical portable skill from `skills/hercules-mcp` independently
of native MCP-only plugin adapters. Do not copy or generate agent-specific skill
content. Use the current client's supported user or project skill location and
configuration model.

Change only the Hercules entry in the client's MCP configuration. Preserve
comments, formatting, unrelated servers, and unknown settings when the format
supports them. The STDIO command must be the absolute `hercules` launcher and
must not contain passwords, tokens, proxy credentials, certificate data, or a
checkout-relative working directory. Snapshot the affected configuration,
update it atomically where possible, validate the effective registration, and
restore the snapshot if validation fails.

For OpenCode, keep the independent skill at
`.agents/skills/hercules-mcp`, honor `OPENCODE_CONFIG` and XDG locations, and
preserve JSON/JSONC comments. Inspect the installed OpenCode version and support
its effective direct `mcp.hercules` or nested `mcp.servers.hercules` layout
rather than assuming one. Apply the same evidence-based approach to Codex,
Claude Code, Cursor, or another STDIO MCP and Agent Skills client.

## Transaction and recovery boundary

Treat installation as a transaction even though the active agent chooses the
host-native mechanics. Resolve preferences and prerequisites first; prepare a
staged checkout; build and validate the selected image before downloading large
optional assets; verify assets; then promote the checkout and locked launcher.
Commit `.env`, skill placement, client registration, and non-secret state only
after their dependent checks pass.

Before changing an existing installation, snapshot non-secret state and only
the relevant Hercules client entry. Never include secrets in a transaction log.
On failure or interruption, restore the last committed configuration and remove
only agent-created pending files. Keep checksum-valid downloads and immutable
Docker build cache for reuse. Never remove an existing workspace, evidence,
secret, successful image, or unrelated client configuration as cleanup.

## Local acceptance

Validate through the real STDIO transport and lifespan without external
security activity. Confirm Docker availability, image identity and capability
manifest, protected runtime configuration, portable skill presence, effective
client registration, clean startup/shutdown, and read access to all seven MCP
resources. A full profile exposes 45 tools with Metasploit or 40 without it;
custom profiles expose fewer according to the declarative setup facts and may
hide additional installed tools through `HERCULES_DISABLED_TOOLS`.

Exercise browser readiness only against a local page or fixture. Do not scan,
navigate to, exploit, authenticate to, or verify public egress against an
external target during installation. Clearly distinguish a missing prerequisite
from an unsupported platform, a Docker trust failure, a capability mismatch,
an MCP startup failure, and a client-registration failure.

Testing and setup must not stage or distribute `tests/`, local evidence,
workspaces, `.env`, downloaded assets, transaction remnants, or secrets.
