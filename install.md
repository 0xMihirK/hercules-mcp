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

Installation is complete only when all ten checkpoint barriers below pass in
order. Independent work explicitly identified in the fast path may overlap,
but no mutation may cross a barrier whose prerequisites have not passed:

1. The user confirmed intended use, capability set, scope, and any browser
   proxy preference.
2. Host, Docker, architecture, trust, and active-client prerequisites passed.
3. A durable checkout at an exact revision and a locked absolute launcher exist.
4. Read-only setup facts match the confirmed choices and current source.
5. The capability-specific image matches every reported identity and readiness
   field.
6. Required assets, protected `.env`, and the non-secret state candidate are
   complete.
7. The independent portable skill is installed when supported.
8. Only the active client's Hercules entry points to the absolute STDIO launcher.
9. A real cold MCP connection reports the expected tools and all seven resources.
10. Every transaction-owned temporary path, process, container, and port is gone,
    and the schema-4 success state is committed last.

No external target, public-IP service, exploit, payload, credential service, or
public browser page may be touched during setup. If a checkpoint fails, do not
claim success or commit work belonging to a later checkpoint.

## Fast path and safe parallel execution

Prefer verified reuse over repeated work. On an upgrade, retain the confirmed
preferences and skip a checkout update, Python environment refresh, image
build, asset download or extraction, skill copy, or client rewrite when its
exact source, lockfile, fingerprint, checksum, content, and effective
configuration already match. A matching name or successful process exit alone
is not sufficient evidence.

Use bounded, resource-aware concurrency only for independent work:

1. After the user confirms choices, inspect the host and image platform, Docker
   context and trust, existing state and assets, and active-client schema in
   parallel.
2. Prepare the durable source, locked launcher, and setup facts sequentially;
   each establishes the identity required by the next operation.
3. After setup facts validate, put the single Docker image build on the critical
   path. In parallel, prepare only private transaction-staged candidates for the
   skill, environment/state, and client entry. Do not install or commit them.
4. Do not start missing multi-gigabyte downloads until deterministic image
   preflight has passed. Existing cache discovery may overlap the build, but do
   not run a full multi-gigabyte hash beside a local disk-heavy build on the same
   constrained disk.
5. After image identity and basic runtime validation pass, fetch independent
   missing assets with at most two large transfers at once. Verify each checksum
   independently and promote it atomically under the asset lock.
6. Serialize `.env`, state, skill, and active-client changes so their snapshots
   and rollback order remain deterministic.
7. Run independent read-only acceptance checks and resource reads in parallel.
   Serialize runtime readiness, browser state changes, disconnect recovery, and
   preparation of the final success-state candidate.
8. Stop and settle every transaction task before removing independent,
   exact-owned temporary artifacts. Commit success state only after cleanup.

Use less concurrency when CPU, memory, bandwidth, Docker capacity, or local
storage would make parallel work slower or less reliable. Never launch two
setup flows that can mutate the same `.env`, state, skill destination, client
entry, asset root, or Docker identity.

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

Inspect the host's TCP dynamic and excluded ranges before accepting runtime
ports. New installations use loopback-only `MSF_RPC_PORT=15553`; it is below
the standard Windows and Linux ephemeral ranges. Preserve an existing explicit
value, including the historical `55553`, but keep automatic allocation enabled
so Hercules can select and report a dispersed low service port when that value
is unavailable. Do not rewrite an existing port merely because it is historical.

Perform the independent read-only inspections from the fast path concurrently
when the host can support them. Consolidate their results at this checkpoint
before creating or updating the durable installation.

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

Capture setup JSON as UTF-8 stdout and keep stderr separate. Parse and validate
the JSON rather than accepting a zero process exit alone. A
`source_association_invalid` result means the launcher imported Hercules from
an incomplete or non-editable package location; repair its association with the
durable checkout before any image build.

Stop if setup facts describe different source, capabilities, platform, trust,
or browser inputs from those the user confirmed.

## 5. Build and verify the runtime image

Build the exact image described by setup facts, using the reported context,
Dockerfile, platform, tag, arguments, and optional BuildKit secret. The default
runtime is the digest-pinned `kali-last-release` image using only the
`kali-last-snapshot` suite. Rolling packages are not an installation option.

First inspect an existing image with the reported identity. Reuse it only when
every required label, platform, capability-manifest field, backend, and runtime
readiness check passes. Otherwise perform one build for the confirmed identity.
While it runs, prepare only the private staged candidates allowed by the fast
path; do not modify the effective installation or begin missing large downloads.

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

Trust the Docker build result only when the Docker producer's real exit status
was captured. A logging or display pipeline must propagate that status; a
successful logger such as `tee` cannot turn a failed build into success. Keep
stdout and stderr separate when needed for reliable classification.

A registry EOF, connection reset, timeout, or retryable registry 5xx while
fetching the pinned base is a transport failure rather than a Dockerfile defect.
With the exact image identity unchanged, retain valid cache and make at most two
bounded retries. Stop after that limit. Do not retry certificate, checksum,
manifest, package, architecture, or command failures without correcting their
reported cause.

## 6. Commit assets, environment, and state

Provision only checksum-verified wordlists required by the confirmed profile.
Keep reusable assets in `HERCULES_WORDLIST_ROOT`, preferably outside the
checkout, and reuse valid caches. An unselected wordlist is not required rather
than failed.

After image preflight passes, independent missing archives may download with a
maximum concurrency of two. Each uses a distinct private temporary destination,
passes its pinned checksum and archive validation, and is promoted under the
interprocess asset lock. Extraction remains protected by that lock. A failed
transfer must not invalidate another verified cache.

Preserve every existing `.env` value. Generate a strong URL-safe Metasploit RPC
secret when needed, store it only in the protected `.env`, and never display it.
Keep browser proxy credentials there as well. Apply private file permissions
where supported.

Never print, dump, echo, or read the complete `.env` back into the agent
transcript. Validate secrets only through non-disclosing presence, persistence,
and file-protection status; setup information reports those booleans without the
values. If a secret reaches output, logs, a transcript, or client configuration,
treat it as burned, rotate it before acceptance, and never display its replacement.

Prepare the schema-4 non-secret state candidate for the platform's user
configuration area or the ignored project `.hercules/install.json`. Preserve
unknown non-secret fields. Record the exact revision, scope, launcher,
capability selection, platform, base digest, APT suite, image identity, expected
count, workspace, asset root, CA fingerprint, browser artifact, skill path, and
active client. Never store passwords, tokens, cookies, proxy URLs, or
certificate contents. The candidate remains provisional until acceptance and
cleanup pass; commit the success record last.

Across this checkpoint and checkpoints 7-8, the protected `.env`, skill, and
client entry may need to become effective for real transport acceptance. Apply
each change serially at its own checkpoint and retain exact prior snapshots.
Treat the changes as provisional during acceptance and restore the previous
committed versions on failure.

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

Hercules completes MCP initialization and exposes schemas before its Docker
runtime is ready. Validate the active client's cold-start timeout against its
current schema. Use a 120000 millisecond startup timeout through the client's
native local-STDIO setting when it supports one. OpenCode's local entry must use
its current `type: "local"` shape, an absolute command array, and
`timeout: 120000` milliseconds. Preserve unrelated JSON/JSONC content and
confirm the effective setting rather than only the source file that was edited.

Apply the same contract to Codex, Claude Code, Cursor, OpenCode, or another
STDIO MCP harness. For an unknown compatible client, provide its native generic
STDIO entry and exact optional skill destination. For a client without local
STDIO support, stop as unsupported rather than leaving partial configuration.

Do not assume the active client is the only Hercules user. A healthy MCP server
from another coding agent or IDE owns its own container and must remain running.
Keep automatic runtime-port allocation enabled unless the user explicitly needs
fixed ports. After startup, obtain the effective RPC, reverse-listener, and
browser-stream ports from that session's `system_network_info` result instead of
hard-coding defaults in client configuration or acceptance checks.

## 9. Run local acceptance and commit success

Validate through the real STDIO transport and server lifespan. Confirm image
identity, protected runtime configuration, skill status, effective client
registration, an immediate cold connection, expected tool schemas, and read
access to all seven resources while runtime bootstrap continues in the
background. A successful launcher process exit is not MCP acceptance. Wait for
core readiness, require a local Docker-backed tool call to succeed, and treat a
structured tool error as a failed check. A full profile exposes 45 tools with
Metasploit or 40 when Metasploit registration is disabled; custom profiles
expose fewer.

Image-label validation, skill-content verification, configuration secret
checks, and the seven resource reads may run concurrently when independent.
Keep operations that mutate one runtime or browser session ordered, and do not
commit schema-4 success state until every required result has passed.

When another Hercules client is already live, repeat the cold check without
stopping it. The new client must connect immediately, preserve the existing
container, select different effective ports, complete one local Docker-backed
call, and remove only its own container on shutdown.

Also exercise the active harness's actual disconnect behavior with a disposable
verification session. Some IDEs force-terminate local MCP subprocesses instead
of waiting for lifespan cleanup. Hercules' detached guardian must then validate
the exact container ID, project/workspace labels, owner PID, and process creation
time before removing that session's container. Treat a surviving owned
container or port binding as an installation failure; never compensate with a
broad Docker prune.

Exercise browser readiness against a transaction-owned HTTP fixture running
inside the Hercules container. Use container loopback, confirm a successful
navigation result, native screenshots, and loopback-only streaming, then stop
the fixture and verify its port is released. This must not depend on permission
to start a listener on the coding-agent host.

In bridge mode, browser `localhost` is the Hercules container. To reach a
service on the Docker engine host, use `host.docker.internal`, the name
recommended by [Docker's networking guidance](https://docs.docker.com/desktop/features/networking/networking-how-tos/).
Hercules provides the equivalent `host-gateway` mapping on supported bridge
engines and reports its resolution through `system_network_info`. With a remote
Docker context, that name reaches the remote engine host, not necessarily the
coding-agent machine. The host service must listen on an interface reachable by
Docker and be allowed by the host firewall. When target scopes are active,
explicitly authorize the resolved private address or CIDR for the disposable
check; never weaken the persisted policy or reinterpret `localhost` silently.

Confirm graceful MCP shutdown removes its owned container and releases RPC,
listener, fixture, and stream ports. Only after every selected check passes may
the agent finalize the setup-state candidate; keep it private and uncommitted
until cleanup passes.

## 10. Clean up and close the transaction

Cleanup is mandatory on success, failure, and interruption. From the beginning,
track every temporary path, redirected stream, marker, background process,
container, ownership label, port binding, staging checkout, and client backup
created by the transaction. Use a `finally`-equivalent cleanup path so a failed
acceptance check cannot bypass it.

Terminate transaction-owned background processes and confirm they exited.
Stop and remove verification or failed Hercules containers only after their
exact ownership labels match this transaction, then confirm their ports are
released. Remove transaction-owned scripts, logs, redirected stdout/stderr,
markers, staging directories, and obsolete client snapshots. On failure,
restore only the prior Hercules client entry. Verify that no secret entered a
log or client configuration. Report each exact artifact that could not be
cleaned; never conceal partial cleanup.

Preserve the committed checkout, protected `.env`, generated secrets,
schema-4 state, installed skill, selected image, valid Docker cache, verified
wordlists, workspace evidence, and unrelated configuration. Never perform a
broad Docker, temporary-directory, or filesystem prune. After cleanup passes,
atomically commit the schema-4 success state as the installation's final
mutation. Report installation success only after that commit succeeds.

After that successful commit, print this exact line to the user's screen once:

```text
Remember, with great power comes great responsibility ;)
```

The quote is display-only. Do not store it in `.env`, setup state, logs, MCP
configuration, or client metadata. Do not print it after a failed, rolled-back,
interrupted, or partially cleaned installation. It confirms the installation
transaction, not post-restart activation, so `activation_pending_restart` may
still follow it.

## Activate the client changes

After acceptance and cleanup, determine how the active client discovers MCP
configuration and Agent Skills from its effective schema, native help, or
current authoritative documentation. Ask the user to perform the smallest
necessary activation step:

- reload only the Hercules MCP server when verified MCP hot reload is supported;
- start a new agent session when settings or skills are discovered per session;
- reload the IDE window or restart the application only when required.

Never terminate or restart the user's agent or IDE automatically. If the
effective Hercules connection and installed skill are already visible, report
`installed_and_verified` and explicitly say that no restart is required.
Otherwise report `activation_pending_restart`, state exactly what the user must
reload or restart and why, and ask them to do it. When the user returns, verify
the effective Hercules connection, expected tool and resource surface, and
skill discovery without repeating installation or contacting an external
target.

## Failure classification and rollback

Do not blindly retry an unchanged failure:

| Failure | Retry policy | Required response |
| --- | --- | --- |
| Missing Git, uv, Docker, architecture, or STDIO support | Deterministic | Request the smallest operator prerequisite or report unsupported |
| Docker daemon/context temporarily unavailable | Retryable after repair | Recheck the same confirmed context |
| Pinned base pull EOF, reset, timeout, or retryable registry 5xx | Retryable twice | Preserve identity and cache, verify Docker's real exit status, then stop after two retries |
| Build observed only through a status-masking output pipeline | Untrusted result | Recapture the Docker producer exit status before classifying the build |
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
