---
name: hercules-setup-contract
description: Ordered outcome and safety contract for an AI agent installing or upgrading Hercules MCP
---

# Install or upgrade Hercules MCP

This is an ordered contract for a capable terminal agent, not a shell recipe.
Adapt actions to the actual operating system, CPU, shell, Docker context,
security policy, and active AI client. Do not assume a package manager, init
system, filesystem layout, inherited `PATH`, or client configuration shape.

Authoritative context:

- [Docker's complete LLM context](https://docs.docker.com/llms-full.txt)
- [Kali branch policy](https://www.kali.org/docs/general-use/kali-branches/)
- [uv tool storage](https://docs.astral.sh/uv/reference/storage/)
- [CloakBrowser's official repository](https://github.com/CloakHQ/cloakbrowser)
- [CloakBrowser on PyPI](https://pypi.org/project/cloakbrowser/)

The supported interoperability boundary is a terminal-capable host with Git,
`uv`, a working Docker-compatible daemon, and an AI client that can start a
local STDIO MCP server. Agent Skills support is useful but optional. Stop and
report an unsupported client if local STDIO MCP is unavailable.

## Completion checkpoint

Installation is complete only when all nine checkpoints below pass in order:

1. The user confirmed intended use, capability set, scope, and any browser
   proxy preference.
2. Host, Docker, architecture, trust, and active-client prerequisites passed.
3. A durable checkout at an exact revision and a locked absolute launcher exist.
4. Read-only setup facts match the confirmed choices and current source.
5. The capability-specific image matches every reported identity and readiness
   field.
6. Required assets, protected `.env`, and non-secret state are complete.
7. The independent portable skill is installed when supported.
8. Only the active client's Hercules entry points to the absolute STDIO launcher.
9. Local MCP acceptance reports the expected tools and all seven resources.

No external target, public-IP service, exploit, payload, credential service, or
public browser page may be touched during setup. If a checkpoint fails, do not
claim success and do not continue to later checkpoints.

## 1. Confirm the installation choices

First understand what the user intends to do. Explain important omissions,
recommend the smallest useful capability set, and get confirmation. Core shell,
workspace, and lifecycle support is mandatory. Optional bundles determine both
which backends enter the image and which MCP tools are registered; consolidated
browser, Nmap/NSE, and Nuclei families remain intact.

Confirm user-wide or project-local scope. User-wide is the default. Ask about
an authenticated browser proxy only when browser capability is selected. Never
place proxy credentials in setup state, build arguments, logs, command display,
or MCP configuration.

A first unattended installation requires explicit capability and scope input.
Do not silently select every capability. An upgrade preserves the committed
choices unless the user explicitly changes them.

## 2. Inspect the host, Docker, and active client

Identify the real host OS, CPU architecture, Docker context, daemon state,
rootless or desktop mode, corporate trust requirements, and active AI harness.
Use native help and current vendor documentation to resolve facts. Never make
unrequested privileged package, daemon, service, group, or shell-profile changes.

Hercules images support `linux/amd64` and `linux/arm64`. An unsupported host may
proceed only when the selected Docker context intentionally provides compatible
emulation. Record the effective image platform; do not infer it solely from the
host when a remote Docker context is active.

Select one confidently active MCP client. The presence of several installed
clients is not permission to configure all of them. Ask the user only when the
active harness remains ambiguous after checking process and environment markers.

## 3. Prepare the source and locked launcher

Place a managed checkout in a durable, non-synced user-data location. Prefer
the latest stable Hercules release. When no release exists, use the default
branch and record its exact commit. Update an existing successful checkout only
when it is clean and can advance without rewriting history. A checkout without
committed schema-4 state is an incomplete first installation, not an upgrade.

Create a persistent locked Python tool environment from the checkout and
`uv.lock`. Hercules must remain associated with that durable source because the
runtime needs its Dockerfile, entrypoint, skill, and configuration. Resolve the
launcher from the active `uv` tool executable directory and verify its absolute
path directly. Do not depend on a GUI client inheriting the user's shell `PATH`.

Only after this checkpoint may the agent invoke Hercules' setup-information
mode. Before it, inspect repository metadata directly rather than assuming an
already installed `hercules` command.

## 4. Read and validate setup facts

Use the launcher's `--setup-info-json` mode with the confirmed capability and
target-platform choices. It is strictly read-only: it must not build, download,
write configuration, modify `PATH`, register clients, or select preferences.

Treat its output as the source of truth for:

- normalized capabilities, required backends and assets, and expected MCP counts;
- source revision, Python and lockfile identity, and launcher invariants;
- Docker context inputs, target platform, stable Kali base and APT suite;
- image tag, fingerprint, labels, and capability-manifest checksum;
- CloakBrowser artifact and browser readiness requirements;
- optional certificate-only BuildKit secret metadata; and
- retryable versus deterministic diagnostic categories.

Stop if setup facts describe different source, capabilities, platform, trust,
or browser inputs from those the user confirmed.

## 5. Build and verify the runtime image

Build the exact image described by setup facts, using the reported context,
Dockerfile, platform, tag, arguments, and optional BuildKit secret. The default
runtime is the digest-pinned `kali-last-release` image using only the
`kali-last-snapshot` suite. Rolling packages are not an installation option.

The Dockerfile bootstraps a pinned public CA bundle before the first verified
HTTPS APT request. If authorized TLS interception requires custom trust, accept
only a bounded PEM bundle containing certificates and no private keys. Pass it
as the reported BuildKit secret, record only its normalized SHA-256, and never
copy its contents into the checkout or non-secret state.

Package cleanup is dependency-safe. A helper may be removed only when APT's
simulation proves no other installed package would be removed. Never compensate
for a build failure by deleting a confirmed capability. In particular,
`commix`, Metasploit, and their `git` dependency must survive a selected build.

Validate the image labels, target architecture, stable APT suite, capability
manifest checksum, runtime evidence, every required backend, and browser
readiness before proceeding. The image identity changes whenever source build
inputs, platform, capabilities, CA fingerprint, or browser pin changes.

## 6. Commit assets, environment, and state

Provision only checksum-verified wordlists required by the confirmed profile.
Keep reusable assets in `HERCULES_WORDLIST_ROOT`, preferably outside the
checkout, and reuse valid caches. An unselected wordlist is not required rather
than failed.

Preserve every existing `.env` value. Generate a strong URL-safe Metasploit RPC
secret when needed, store it only in the protected `.env`, and never display it.
Keep browser proxy credentials there as well. Apply private file permissions
where supported.

Maintain schema-4 non-secret state in the platform's user configuration area or
the ignored project `.hercules/install.json`. Preserve unknown non-secret
fields. Record the exact revision, scope, launcher, capability selection,
platform, base digest, APT suite, image identity, expected count, workspace,
asset root, CA fingerprint, browser artifact, skill path, and active client.
Never store passwords, tokens, cookies, proxy URLs, or certificate contents.

## 7. Install the independent skill

Install the canonical `skills/hercules-mcp` directory in the active client's
current Agent Skills discovery location when that feature is supported. Keep
one provider-neutral skill; do not embed or declare a skill in plugin adapters.
For OpenCode, honor its effective configuration/XDG locations and use
`.agents/skills/hercules-mcp` where its current documentation requires it.

Lack of Agent Skills support does not block MCP installation. Report that the
portable skill was omitted because the client lacks the feature, then continue
with STDIO registration.

## 8. Register only the active MCP client

Prefer the active client's current native registration interface. Otherwise,
atomically edit only its effective Hercules entry while preserving unrelated
JSON, JSONC, TOML, comments, and servers. Inspect the installed client rather
than assuming a historical schema. OpenCode may use a direct or nested MCP
layout; honor `OPENCODE_CONFIG` and XDG locations.

Repository MCP JSON files are templates. Render the installed copy with the
absolute launcher before registration; never install the bare `hercules`
command verbatim. The entry uses STDIO, contains no secrets or checkout-relative
working directory, and changes no unrelated client. Snapshot the existing
Hercules entry, validate the effective replacement, and restore it on failure.

Apply the same contract to Codex, Claude Code, Cursor, OpenCode, or another
STDIO MCP harness. For an unknown compatible client, provide its native generic
STDIO entry and exact optional skill destination. For a client without local
STDIO support, stop as unsupported rather than leaving partial configuration.

## 9. Run local acceptance and commit success

Validate through the real STDIO transport and server lifespan. Confirm image
identity, protected runtime configuration, skill status, effective client
registration, clean startup and shutdown, expected tool schemas, and read
access to all seven resources. A full profile exposes 45 tools with Metasploit
or 40 when Metasploit registration is disabled; custom profiles expose fewer.

Exercise browser readiness only against an isolated local page. Confirm native
screenshots and loopback-only streaming without navigating externally. Only
after every selected check passes may the agent atomically commit setup state
and report success.

## Failure classification and rollback

Do not blindly retry an unchanged failure:

| Failure | Retry policy | Required response |
| --- | --- | --- |
| Missing Git, uv, Docker, architecture, or STDIO support | Deterministic | Request the smallest operator prerequisite or report unsupported |
| Docker daemon/context temporarily unavailable | Retryable after repair | Recheck the same confirmed context |
| Public or corporate TLS trust failure | Deterministic | Correct verified trust; never disable TLS or hostname checks |
| Same Docker layer fails with unchanged inputs | Source defect | Stop, preserve the complete log, and identify the failing layer |
| Backend or capability manifest missing | Deterministic | Rebuild the same confirmed profile; never silently omit it |
| MCP registration or validation fails | Deterministic | Restore the prior Hercules entry and preserve unrelated settings |

Treat installation as a transaction. Before changing committed state, snapshot
only non-secret state and the active Hercules client entry. On failure, restore
the last known-good configuration and remove only transaction-owned staging
data. Retain checksum-valid downloads, immutable build cache, existing images,
secrets, workspace evidence, and unrelated client configuration.

Tests, local evidence, workspaces, `.env`, downloaded assets, and transaction
remnants must remain ignored, untracked, and absent from distributed packages.
