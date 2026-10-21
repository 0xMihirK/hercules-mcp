# Hercules MCP — current handover

Updated 22 October 2026. Base: `4ec3385b44d2945b5675556b3359663bef4cf26d`.
Working branch: `codex/finalize-runtime-catalog`.

## Current state and scope

PRs #44, #33, #45 and #46 have been merged. The earlier handover at
[5927dac](https://github.com/0xMihirK/hercules-mcp/blob/5927daca2fc687e05a8f243d21d3ee80f2258951/handover.md)
is historical evidence, not today's source/image identity or cleanup status.

Merging #33 changed the image fingerprint. Both replacement publish workflows
completed successfully from 4ec3385; the catalog now points to those images,
not the older c542601 images. This follow-up verified the published artifacts,
repaired a test polling race and inaccurate diagnostics/security reporting,
and repeated Windows acceptance. No new build, publication,
personal installation activation, Docker setting change, or permission-policy
change is part of this follow-up. Leave its PR unmerged pending user review.

Runtime behavior remains explicit: a cold MCP connection creates no container;
start/reuse one owned Kali runtime when needed, save evidence, then stop it.
Stop/start preserves the workspace; session rotation is a separate operation.
Coordinate parallel workers before stopping/rotating. Harness task IDs are not
Hercules job IDs.

The default is host networking, with an explicit bridge override available.
Obscura 0.2.5 / agent-browser 0.39.1 remain pinned. The browser is unprivileged,
but has **no SSRF boundary or target allow/block enforcement**. CSP is **not
enforced**; script execution is not proof of a Chromium CSP bypass.
Browser-native downloads remain unsupported: use explicit HTTP/shell downloads
into validated workspace paths and verify the file. Do not claim Chrome parity.

## Verified published identities

Source revision: `4ec3385b44d2945b5675556b3359663bef4cf26d`.

| Platform | Fingerprint | Immutable registry manifest digest |
| --- | --- | --- |
| linux/amd64 | `00fe9757d64eda5914c9085e885f6823f3388c37655192a08c71ffda94d08c80` | `sha256:bfd19a6ba9021ea92b0782b415dc845301eb4c1eeacc3afc849366dcc4de814c` |
| linux/arm64 | `95aa4fec14de0a3a4e5c08d5ecbe0ef981dbcd9d645a6cadccb77a11a3af0b98` | `sha256:2f422dd1e660acb38e10ca126534f92517c1a284eb7735e43a5c97ac892eb8d6` |

GHCR primary: `ghcr.io/0xmihirk/hercules-mcp`.
Identical-digest fallback: `0xmihirk/hercules-mcp` on Docker Hub.

- [AMD64 publish and acceptance](https://github.com/0xMihirK/hercules-mcp/actions/runs/39679160196).
- [ARM64 publish and acceptance](https://github.com/0xMihirK/hercules-mcp/actions/runs/39679174183).

Both downloaded JUnit artifacts contain six tests with zero failures, errors
or skips. Catalog fields exactly match their published artifacts and the
current source fingerprints. Both registry manifests match. GHCR provenance
verifies against the repository, runtime-image workflow and exact source commit
on both architectures. Provenance is not a blanket vulnerability/license audit.

## Docker endpoint discovery — important on this host

Docker CLI's selected `desktop-linux` endpoint is healthy:
`npipe:////./pipe/dockerDesktopLinuxEngine`.
The Python SDK's default Windows pipe timed out without an explicit endpoint.
Therefore a generic SDK failure is not proof Docker is stopped or uninstalled.

Verification uses the already selected, verified local endpoint through
**process-scoped DOCKER_HOST only**. No personal client registration, system
environment, Docker context, or Docker Desktop setting was rewritten. This
does not establish that an unconfigured launcher using the other pipe works.

If CLI works but Hercules does not, compare `docker context inspect` against
the Hercules process's `DOCKER_HOST`, `DOCKER_TLS_VERIFY` and
`DOCKER_CERT_PATH`. Pass the verified endpoint and matching TLS configuration
only to the selected client through an authorized registration update.
Do not silently choose another daemon, weaken TLS, or alter other clients.
See [Docker SDK environment configuration](https://docker-py.readthedocs.io/en/stable/client.html)
and [Docker CLI contexts](https://docs.docker.com/engine/manage-resources/contexts/).

Docker Desktop host networking is now **enabled**, observed read-only.
This differs from the earlier failed Windows runs. It remains an operator
prerequisite for host-facing streams/listeners in default host mode; it is
separate from selecting a Docker API endpoint. No agent enabled it here.

## Verification ledger

Fresh evidence is ignored by Git under
`artifacts/runtime-probes/release-20261022-followup/`.
Older reports remain under `artifacts/runtime-probes/release-20261022/`.
Do not publish private logs, credentials, account metadata or transcripts.

| Check | Current result |
| --- | --- |
| Published AMD64 and ARM64 runtime acceptance | 6 passed / 0 skipped on each Linux CI architecture |
| Registry identity / manifests / provenance | Verified against exact source and workflow on both architectures |
| Old orphan sessions ce02afe1 and 9cebdc3b | Confirmed absent through the healthy selected endpoint; `cleanup-existing.json` |
| Locked host suite including all new regressions | 266 passed, 13 skipped; `unit-complete.xml` |
| Windows full Docker/STDIO/browser matrix, three serial repetitions | Initial run: 5 passed / 1 test-polling race. Post-fix: **6 passed / 0 skipped in each repetition**; `runtime-final-1.xml` through `runtime-final-3.xml` |
| Isolated install/no-op/update/repair/reinstall, live old process, native Claude/Codex registration | 3 passed, using disposable destinations |
| Runtime setup / pending verification, stale-proof rejection and activation | 2 passed using disposable registrations; `setup-runtime.xml` |
| Live Claude auto mode | BLOCKED: fresh real auto-mode attempt exited 1; no recorded denial, no host activation. Cause not established; `claude-auto.xml` |
| Schema baselines / 47/7, 42/7, 12/7 profiles | 6 passed: five full/disabled/core/selectively hidden profiles plus schema baseline; `profiles.xml` |
| Lint, compilation, package privacy, setup facts, diff checks | Passed, including all production/tests Ruff and both wheel/sdist privacy checks |
| Final cleanup | Confirmed: zero containers, guardians or fixture listeners; build cache 0 bytes; `cleanup-final-docker.json` / `cleanup-final-host.json` |
| Native Windows symlink creation | Skipped: unavailable without additional OS privileges; junction rejection passed. No permission change made |
| Physical macOS/Apple Silicon, Windows ARM64 | Not executed here; Linux ARM64 CI is not equivalent |

The endpoint diagnostic changes only error guidance: it does not add an
automatic context fallback or change MCP schemas/security checks. The first
Windows runtime run passed all ten browser tools, streaming, proxies, and file
checks. Its forced-owner test hit a Docker SDK list/inspect 404 while the
guardian successfully deleted the container. Polling now uses the SDK's
`ignore_removed=True`; a deterministic regression verifies disappeared entries
are omitted but other API failures still propagate. Ownership filters remain.

The setup report also incorrectly retained
`private_addresses_denied_unconditionally: true` after the boundary was removed.
It now reports false, with a regression against the actual structural-only
target policy. This changes no access behavior. PR #45's post-install reminder
and PR #46's bounded fixture budgets are already present; do not reimplement them.

The 13 default-suite skips are 12 separately opted-in acceptance checks and the
unavailable native symlink fixture. The acceptance checks have their own results
above; the live auto-mode blocker is not converted into a passing skip.

## Runtime inventory and measurements

The AMD64 immutable local image ID equals its registry manifest digest above.
`docker image ls` reports **5.22 GB disk usage**; `docker image inspect .Size`
reports **1,335,559,107 bytes**, consistent with the registry's compressed-layer
bytes plus image metadata. These are different Docker storage metrics, not two
different images. No Kali-versus-Debian or percentage-improvement claim is made.
Package inventories are retained in `ci-amd64/inventory.txt` (462 entries) and
`ci-arm64/inventory.txt` beside their build/facts/image-inspect artifacts.

Post-fix Windows browser-contract fixture measurements, three fresh sessions:

| Metric | Observed range |
| --- | --- |
| Explicit full-runtime readiness, browser initially lazy | 2.50–2.89 seconds |
| Stabilized idle container RAM | 286.0–288.8 MiB |
| Stabilized active-browser container RAM | 313.5–316.8 MiB |
| Separate, unattributed Docker/WSL host working set | 1.75–2.08 GiB |

RAM figures use the median of each stabilized sample window's final three
samples, excluding inactive file cache. Docker/WSL figures are separate host
working-set snapshots: they include shared VM/cache overhead, not Hercules-only
memory or a measured workload peak. These are fixture observations, not universal
startup/memory guarantees. The JUnit properties retain individual samples.

## Reproduce safely

Use separate shell processes for temporary environment overrides. On this host,
the following endpoint was verified; do not copy it blindly to another system.

```powershell
$env:DOCKER_HOST = 'npipe:////./pipe/dockerDesktopLinuxEngine'
uv sync --locked --extra dev
uv run --locked pytest -q
ruff check hercules tests/test_explicit_lifecycle.py
uv run --locked python -m compileall -q hercules
uv pip check
uv run --locked hercules --setup-info-json
uv run --locked hercules --validate-mcp-json
git diff --check
```

Profile selectors are `SKIP_METASPLOIT` and
`HERCULES_INSTALLED_CAPABILITIES`. Core tools remain protected; all profiles
have seven resources. Cold connection success is not runtime verification.

Prepare/reuse only the catalog's immutable image matching current fingerprints
and labels. Runtime downloads/testing remain separate from host installation.
Keep an 8 GiB disk reserve, preserve working installations, and use local-only
fixtures; never scan an external target for setup acceptance.

```powershell
$env:HERCULES_RUN_DOCKER_ACCEPTANCE = '1'
$env:HERCULES_WORDLIST_ROOT = Join-Path (Get-Location) 'wordlists'
uv run --locked pytest tests/test_docker_acceptance.py tests/test_browser_acceptance.py -q -rs
```

Run three fresh repetitions serially, and do not overlap same-project runtime
setup verification: host-network fixtures share ports.

```powershell
$env:HERCULES_RUN_SETUP_ACCEPTANCE = '1'
uv run --locked pytest tests/test_setup_acceptance.py -q -k 'not auto'
```

The live classifier check additionally requires an authorized authenticated
Claude session and `HERCULES_RUN_CLAUDE_AUTO=1`. Stop on denial. Use Claude's
supported auth/usage/permission interface; do not change modes, install allow
rules/hooks, mock the classifier, or retry via another tool.

## Cleanup and remaining actions

The two historical orphan containers are confirmed absent. No additional manual
container deletion was needed in this follow-up. Tests settled their exact-owned
resources in their cleanup paths. Preserve unrelated images, all three pre-existing user
volumes, verified assets, other live MCP owners, and nonempty evidence. No broad
pruning or retry of historical policy-denied filesystem cleanup is authorized.

Final accounting through the healthy endpoint observed zero containers and zero
guardian Python processes. No Windows TCP listeners remain on fixture ports
18080/18081/18083/18084/18085/18484; allocated RPC/listener/stream ports also passed
the per-run release assertions. Build cache is zero bytes. The three pre-existing
volumes and older runtime images remain intact. The selected published runtime
is intentionally cached; verified assets, private measurements and evidence are
retained, not abandoned temporary build resources. Final free disk was
72,908,214,272 bytes (67.9 GiB), well above the 8 GiB reserve.
The old cancelled builder/cache removal remains confirmed historical evidence;
historical policy-denied filesystem remnants were not rechecked or deleted here.

1. Live Claude auto-mode acceptance remains blocked, so do not call the entire
   installer/release universally accepted. Local Windows runtime/setup gates
   passed; failed/blocked/skipped checks remain distinct.
2. Leave the focused follow-up PR unmerged for user review. Do not merge or
   delete unrelated work or publish another image.
3. Resolve any remaining Claude auto-mode/auth/permission failure through its
   supported interface. A successful scripted setup is not classifier approval.
4. Confirm Docker Hub credential rotation with the operator; it remains
   unverified. Never copy the previously disclosed credential into code,
   configuration, logs, this handover, or a PR.
5. Only activate/update a personal client when explicitly authorized, preserving
   secrets, environment overrides, workspaces, evidence and other clients.

The website is maintained on its separate branch; this follow-up does not
change or deploy it.
