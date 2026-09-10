---
name: hercules-setup-contract
description: Safe install, update, and reinstall contract for Hercules MCP
---

# Install or update Hercules MCP

This is an ordered contract for a terminal-capable agent. Adapt commands to the
host, Docker context, CPU architecture, shell, security policy, and active AI
client. Do not assume a package manager, inherited PATH, or client config
format.

Hercules requires Git, uv, a working Docker-compatible daemon, and a client
that supports local STDIO MCP servers. Stop and report the missing prerequisite
when fulfilling it needs privileged changes; never silently alter system
packages, services, groups, or Docker daemon configuration.

Installation and verification are local-only. Do not scan, exploit, browse to,
or test public egress against an external target.

## 1. Detect the current state and ask before mutation

Inspect, without changing anything:

- managed Hercules checkouts and their current commits/working-tree state;
- schema-4 setup state and its recorded scope, capabilities, platform, paths,
  active client, and image identity;
- the protected .env, reporting only whether required values are present;
- installed portable skills and native MCP adapters;
- the active client's effective Hercules registration; and
- matching images, verified wordlists, workspace evidence, and live containers.

If no complete installation exists, run the first-install flow. Ask the user to
confirm intended authorized use, the smallest useful capability set, user-wide
or project-local scope, the active client, and a browser proxy only when browser
support is selected.

If an installation exists, summarize its revision and non-secret configuration,
then ask the user to choose **Update in place** or **Reinstall**. Do not mutate
anything until they answer. Preserve the existing capability set, scope, proxy
preference, paths, and client unless the user explicitly changes them.

An update may fetch and fast-forward only a clean managed checkout. If it is
dirty or diverged, stop and report the exact condition; never reset, overwrite,
or rewrite history. Reuse matching locked environments, images, assets, skills,
and client entries.

A reinstall uses a fresh staged checkout and locked environment. Preserve .env,
generated secrets, setup state, workspaces, evidence, wordlists, valid image
cache, and unrelated client settings. Validate the replacement before an atomic
swap. If the old checkout contains uncommitted work, retain it and report its
path instead of deleting it.

## 2. Track one reversible transaction

Before the first write, create a transaction ledger containing every temporary
path, process, redirected stream, marker, backup, container ID and ownership
label, and port binding created by this run. Snapshot only the existing Hercules
client entry and non-secret setup state needed for rollback.

Use a finally-equivalent cleanup path on success, failure, cancellation, and
interruption. Serialize writes to .env, setup state, the skill destination, and
client configuration. Staged independent checks may run concurrently, but only
one image build and one large asset transfer should consume local resources at
a time.

## 3. Prepare source, launcher, and setup facts

Place the managed checkout in a durable, non-synced user-data directory. Use
the repository's default branch and record the exact commit. Create or refresh
the persistent Python tool environment from pyproject.toml and uv.lock; the
lockfile is the only dependency lock. Resolve the installed hercules launcher
to an absolute path and prove that it imports this complete checkout.

Run the launcher's read-only --setup-info-json mode with the confirmed
capabilities and platform. Stop on source_association_invalid or when the
reported revision, lock hash, capability selection, image identity, platform,
or expected MCP counts do not match the intended installation.

Hercules supports linux/amd64 and linux/arm64. Cross-architecture use needs an
operator-approved Docker context with working emulation. Do not infer the
runtime platform from the host alone.

## 4. Build or reuse the exact runtime

Reuse an existing image only when its complete setup-facts identity, labels,
platform, capability manifest, required binaries, and readiness checks match.
Otherwise build the exact reported image from the durable checkout.

Keep TLS and hostname verification enabled. In an authorized intercepted-TLS
environment, pass only an approved bounded certificate PEM as a BuildKit secret
and record only its SHA-256; never copy certificate contents into source, state,
or logs. Retry transient registry EOF, reset, timeout, or retryable 5xx failures
at most twice with unchanged inputs. Do not retry deterministic Dockerfile,
platform, checksum, package, or capability failures unchanged.

For browser capability, use the exact official CloakBrowser artifact and
checksum reported by setup facts. For required SecLists or rockyou assets,
verify archives before atomic extraction into HERCULES_WORDLIST_ROOT. Never
remove a selected capability to hide a build or asset failure.

Preserve all existing .env values. Generate a strong URL-safe Metasploit RPC
secret only when missing and needed. Store secrets and proxy URLs only in the
protected .env; never display, log, echo, or place them in client config or
non-secret state. Rotate any secret that reaches output.

Prepare the schema-4 non-secret success state privately, preserving unknown
fields. Record the exact revision, launcher, scope, capabilities, platform,
image identity, paths, asset fingerprints, skill destination, active client,
and expected MCP counts. Do not commit success state yet.

## 5. Install the skill and active-client entry

Install the canonical skills/hercules-mcp directory in the active client's
documented skill location when supported. Keep it provider-neutral and separate
from native plugin adapters. Validate content, not just directory presence.

Configure only the confidently active client. Prefer its native MCP management
interface; otherwise atomically replace only its Hercules entry while preserving
unrelated servers, comments, and settings. The entry must use STDIO, the absolute
launcher, no secrets, no checkout-relative working directory, and the client's
current local-command shape. A bare hercules command is invalid.

Repository MCP JSON files are templates, not finished registrations. For an
unsupported client without local STDIO MCP, stop rather than inventing a proxy
or remote transport.

## 6. Run local acceptance

Validate through a real disposable STDIO connection with
PRESERVE_CONTAINER=false for the verification instance:

1. A cold connection lists the tools and resources reported by the selected
   profile's --setup-info-json mcp_surface, while creating no Docker container.
   A full profile exposes 46 tools, or 41 with Metasploit disabled; custom
   capability selections and hidden tools reduce that count. Every profile
   exposes seven resources.
2. A Docker-backed tool returns runtime_not_started and tells the agent to call
   system_start_container; it must not create a container.
3. system_start_container creates exactly one exact-owned container, waits for
   readiness, and is idempotent when called again.
4. One harmless local command succeeds. If browser capability is selected, use
   a transaction-owned HTTP fixture inside the container and container loopback;
   do not contact a public page.
5. system_network_info reports the effective ports only after startup.
6. system_stop_container removes the verification container, preserves its
   workspace, and releases every RPC, listener, fixture, and stream port.
7. A second cold STDIO connection creates no container and does not disturb any
   already-running Hercules client.

Also verify all resource reads, image labels, setup facts, skill content, the
secret-free effective client entry, and exact-owner guardian cleanup after a
disposable forced disconnect. Never stop another live client's container or use
a broad Docker prune to make acceptance pass.

## 7. Clean up, commit success, and activate

Always execute cleanup before reporting success:

- terminate transaction-owned background processes and confirm they exited;
- stop and remove only containers whose exact ID and full Hercules ownership
  labels match this transaction, then verify their ports are released;
- remove transaction-owned scripts, logs, markers, staging directories, empty
  verification workspaces, and obsolete backups; and
- verify no secret entered logs, setup state, or client configuration.

On failure, restore only the prior Hercules client entry and non-secret setup
state. Preserve the committed checkout, protected .env, generated secrets,
installed skill, selected image and valid Docker cache, verified wordlists,
non-empty workspace evidence, and unrelated configuration. Report every item
that could not be cleaned. Never perform a broad Docker, temporary-directory,
or filesystem prune.

After cleanup passes, atomically commit schema-4 success state as the final
mutation. Then determine whether the active client needs an MCP reload, a new
agent session, or an IDE restart, and ask for the smallest required action.
Do not repeat installation merely to activate already-written settings.

Print this line once only after a successful, fully cleaned transaction:

~~~text
Remember, with great power comes great responsibility ;)
~~~

## Failure classification

| Failure | Action |
| --- | --- |
| Missing Git, uv, Docker, permissions, or STDIO support | Stop for operator action |
| Dirty or diverged update checkout | Preserve it and ask; never reset |
| Source/launcher mismatch | Repair the locked source association before building |
| Deterministic image, checksum, platform, or capability failure | Fix the cause; do not retry unchanged inputs |
| Transient registry transport failure | Retry at most twice with identical identity |
| Client registration or acceptance failure | Restore the prior Hercules entry and setup state |
| Partial cleanup | Report exact leftovers; do not claim success |
