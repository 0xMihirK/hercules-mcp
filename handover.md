# Hercules MCP handover for Claude Code

Updated: 22 October 2026. Branch: `codex/finish-release-handover`.
Baseline: `c542601d08108b98e31c00a7a49d1523cd60fb47` on `main`.

## Start here

Read this file, inspect `git status`, and preserve existing work. This handover
records verified results and explicit blockers; it is not permission to change
client registrations, permission policies, Docker settings, or publish images.
The delivery is one focused draft pull request, intentionally left unmerged
while the recorded acceptance/cleanup blockers remain.

The current architecture supersedes the earlier bridge/firewall proposals:

- The host Python MCP server manages one explicit-start Kali runtime container.
  Connecting an MCP client must not create a container.
- Host networking is the default; an explicit bridge override is supported.
  Docker Desktop does not provide the same localhost/listener behavior as native
  Linux. Use observed network/stream metadata, not a Linux CI pass, as evidence
  that a host-side endpoint is reachable.
- Obscura 0.2.5 and agent-browser 0.39.1 remain pinned. Obscura runs unprivileged,
  but there is **no browser SSRF boundary** or target allow/block enforcement.
  Authorized use is an operator/agent responsibility; host-local, LAN, and
  metadata endpoints are not isolated. Do not restore the retired firewall or
  validating gateway as part of this maintenance PR.
- CSP is **not enforced**. Script execution is not evidence of a Chromium CSP
  bypass. Browser-native downloads are unsupported. Use explicit HTTP/shell
  downloads into the workspace and verify the resulting file.
- Workspaces/evidence survive stop/start. A new MCP connection has a different
  session; a new-session operation intentionally rotates the workspace. Harness
  task IDs are not Hercules background-job IDs.

## Changes in this PR

1. Finalize the pending prebuilt catalog for the already published AMD64 and
   ARM64 images. Preserve source identity, GHCR-primary/Docker-Hub-fallback order,
   and immutable digests; no image rebuild or publication is needed.
2. Repair Windows bootstrap syntax verification: prefer Git Bash over a PATH
   entry that resolves to the WSL shim. If only System32/WindowsApps shims exist,
   mark the Bash check unavailable instead of invoking it on a Windows path.
   Four regression cases cover both shim locations with/without Git Bash.
   PowerShell parsing and POSIX `sh -n` remain unchanged.
3. Supply this handover with current evidence, cleanup accounting, limitations,
   and remaining operator actions. No production MCP inputs or responses change.
4. Document Docker Desktop's opt-in host-network prerequisite in the install
   guide; include the reported stream metadata when a real WebSocket connection
   fails in acceptance. Do not alter Docker settings or hide a failed stream test.
5. Repair fixture readiness: wait for a marker written after TLS and every proxy
   starts, not just HTTP. Remove orphaned deny/control listeners belonging to the
   retired boundary tests; no current assertion uses them. This does not remove
   active browser, TLS, authenticated proxy, or protocol checks.

## Published runtime identities

Source revision for both entries: `c542601d08108b98e31c00a7a49d1523cd60fb47`.

| Platform | Build fingerprint | Registry manifest digest |
| --- | --- | --- |
| linux/amd64 | `0ad888087a649c2c460a806f59169e81fc518e3744d4eca8dde00a0a1b4cf38f` | `sha256:c7a3a3d4bb4eaf2165da5a70073b996799b4d772f3a3f3574af6e37770eec7a9` |
| linux/arm64 | `60e66104383f571dbcf858059ad86df4fa83464cfb10dceb66d954343037394c` | `sha256:88d10e1db84b472a2859fbfc9e3c710c4dfa4a1cf46e38537747f9d11966dc9f` |

Both registries use these digests: `ghcr.io/0xmihirk/hercules-mcp` and
`0xmihirk/hercules-mcp` on Docker Hub. The matching manifest payloads were read
from both registries. `gh attestation verify` verified GHCR provenance against
the repository, `.github/workflows/runtime-image.yml`, and exact source commit
for each architecture. Provenance records origin; it is not a blanket security
or license assessment of all bundled Kali tools.

Published workflow evidence:

- [AMD64 publication, host checks, and six runtime tests](https://github.com/0xMihirK/hercules-mcp/actions/runs/39661705643).
- [ARM64 publication, host checks, and six runtime tests](https://github.com/0xMihirK/hercules-mcp/actions/runs/39661752825).

Both runtime JUnit artifacts contain six tests, zero failures/errors/skips.
Current source fingerprints match the catalog for both architectures. ARM64
was exercised on Linux CI, not on a physical Apple Silicon/macOS Docker host.

## Verification on this Windows host

Local evidence is intentionally ignored by Git at
`artifacts/runtime-probes/release-20261022/`; do not force-add private logs.
The results below must not be conflated with historical ledger claims.

| Check | Result / evidence |
| --- | --- |
| Locked default host suite | **259 passed, 13 skipped**, `unit-final.xml` (initial run: 258 passed); 12 opt-in acceptance skips and one unavailable Windows symlink-creation check, not passing coverage |
| Bootstrap syntax + new shell-selection cases | **5 passed**, `bootstrap.xml` |
| Compilation, production/changed-test Ruff | Passed |
| Locked dependency compatibility | `uv pip check`: all 88 installed packages compatible; `uv lock --check` passed |
| MCP surface and existing schema baselines | **47/7, 42/7, 12/7**; baseline/hidden-tool regressions in host suite, `surfaces.txt` |
| Setup facts / portable guidance | Setup report generated; guidance and setup-report regressions passed in host suite |
| Wheel/sdist privacy | Built successfully; no private artifacts, evidence/workspaces, wordlists, `.env`, tests, or website packaged; catalog included |
| Focused setup/migration/failure regressions | **43 passed**, `setup-faults.xml`; full host suite also covers rollback, configuration conflicts, interruption, and locking |
| Hashed Python toolbox vulnerability check | No known vulnerabilities found; `toolbox-audit.txt`; not an audit of every Kali system package |
| Windows Docker/browser repetition 1 | **5 passed, 1 failed**, `runtime-1.xml`; host WebSocket connection refused |
| Windows Docker/browser repetition 2 | **4 passed, 2 failed**, `runtime-2.xml`; host stream inactive and premature fixture readiness before TLS |
| Windows Docker/browser repetition 3 | **1 passed, 1 failed, 4 errors**, `runtime-3.xml`; Docker API became unavailable during preserved-container stop; later checks blocked at setup |
| Fixture readiness repair | **1 unit regression passed**, `fixture-unit.xml`; post-fix real protocol repetitions blocked by Docker unavailability, not counted as passed |
| Isolated real host setup / native registration | **3 passed**, `setup-host.xml`; install/no-op/update/repair/reinstall, old MCP process survival, isolated Claude/Codex registration |
| Runtime setup verification / pending activation | **2 passed**, `setup-runtime.xml`; local browser verification, pending update, stale-proof rejection, and activation resume |
| Live Claude Code auto mode | **BLOCKED**: actual 2.1.306, mode `auto`, exit 1, no reported permission denials, no disposable installation activated; `claude-auto.xml` and `claude-auto.log` |
| macOS/Desktop, physical Windows ARM64 | Not executed in this handover; Linux ARM64 CI does not establish these |
| Native Windows symlink transfer check | Blocked by unavailable symlink creation; no OS permission change made to force the test |

Docker Desktop's stored host-networking settings are disabled on this machine.
The combined run failed on a refused host WebSocket connection after a positive
TCP-only readiness probe; a focused rerun instead reported `stream_active=false`.
No Docker setting was changed, and neither result counts as successful streaming.
Windows session-isolation/TLS/proxy checks after that assertion were not reached;
the Linux CI results above remain separate evidence for those paths. An operator
must choose the supported host-network setting or an explicit bridge before the
full Windows browser gate can be accepted. Do not change a failed assertion into
a passing skip. The native Windows junction/reparse-directory rejection test did
pass; the separate symlink-creation test remains unavailable.

The second run also exposed an independent fixture startup race: HTTP could
respond while TLS/proxy startup was unfinished. The fixture now advertises a
ready marker only after all required listeners are constructed, and removes
unused listeners from the retired boundary tests. A unit regression rejects an
early marker and checks the exact required ports. Real post-fix confirmation
still requires Docker; unit simulation is not container acceptance.

For prerequisites see [Docker's host-network documentation](https://docs.docker.com/engine/network/drivers/host/#docker-desktop).

The focused browser run recorded 7.234 seconds for explicit startup, stabilized
idle-container samples ending at 302,034,944 bytes and active-browser samples
ending at 331,264,000 bytes. WSL working set was 2,128,441,344 bytes, **unattributed
to this container alone**. These are snapshots, not peak measurements or a
performance comparison. Docker displays 5.22 GB local image storage; image
inspection reports 1,335,560,725 content bytes. Do not conflate those accounting
figures or claim an improvement from them.

The current Claude attempt stopped without retrying through another tool,
changing permission settings, adding allow rules/hooks, or altering personal
client configuration. Its recorded result does not explain the exit-1 cause;
do not invent a denial or diagnose it as a Hercules server defect. Earlier real
auto-mode attempts were denied separately. Full install/update/approval/resume
acceptance is **not established**, and operational readiness must not imply it is.

## Reproduce the checks

Run from the repository with Git, uv, and Docker available. Read-only host
checks do not need a container. Keep Docker/setup-runtime runs serial because
host-network fixtures use common local ports. Use disposable setup destinations,
not the current user's registrations.

```powershell
uv sync --locked --extra dev
uv run --locked pytest -q
ruff check hercules tests/test_setup.py tests/test_browser_acceptance.py tests/test_obscura_runtime.py
uv run --locked python -m compileall -q hercules
uv lock --check
uv pip check
uv run --locked hercules --setup-info-json
uv run --locked hercules --validate-mcp-json
git diff --check
```

Profile selectors are `SKIP_METASPLOIT` and
`HERCULES_INSTALLED_CAPABILITIES` (not `HERCULES_CAPABILITIES`). Clear temporary
overrides after checking profiles. Do not change persistent shared settings.

Use the published digest after confirming the current fingerprint still
matches; never satisfy acceptance with an older image whose labels merely look
similar. Runtime preparation and asset downloads are separate authorized phases.

```powershell
$env:HERCULES_RUN_DOCKER_ACCEPTANCE = '1'
$env:HERCULES_WORDLIST_ROOT = Join-Path (Get-Location) 'wordlists'
uv run --locked pytest tests/test_docker_acceptance.py tests/test_browser_acceptance.py -q -rs
```

Repeat that command three times with fresh owned sessions; do not run another
same-project runtime verifier concurrently. The tests verify their resource
ownership and clean their containers in `finally`.

```powershell
$env:HERCULES_RUN_SETUP_ACCEPTANCE = '1'
uv run --locked pytest tests/test_setup_acceptance.py -q -k 'not auto'
```

The live classifier check additionally requires an authorized, authenticated
Claude session and `HERCULES_RUN_CLAUDE_AUTO=1`. It is not a mock classifier and
can incur model usage. Resolve authentication/usage/permission failures through
Claude's supported interface before retrying. Do not blindly rerun it or modify
permission modes to obtain a green result.

## Cleanup and retained resources

- Removed abandoned builder `hercules-build-6894423b1d9f` and its exact cache
  volume after confirming its cancelled build record pointed to this repository
  at `f02f3c8`, with no active host build process. Docker confirmed both absent.
- Preserved all three pre-existing user volumes; their exact inventory remains
  in the ignored local evidence rather than exposing unrelated workload names.
- Retain the verified published image/cache, pre-existing images, verified
  wordlists, and local test evidence. Do not broadly prune Docker or files.
- Earlier policy-denied benchmark/reparse-point cleanup remains historical and
  unverified; it has not been retried through a different mechanism.
- Docker became unavailable during repetition 3: API timeouts and HTTP 500/502.
  **Final container/VM-port cleanup is unconfirmed.** Last recorded owned
  sessions needing inspection: `ce02afe1` (container prefix `c46dfe293f70`) and
  `9cebdc3b` (prefix `30b96a23bb50`). They are test resources, not user sessions.
  Do not infer removal from a failed Docker API or absent host Python processes.
- Local-only recovery helper: `artifacts/runtime-probes/release-20261022/cleanup-owned.py`.
  It targets only those recorded IDs, validates project/workspace/session labels,
  refuses live/unknown owners, and rechecks identity before removal. Review it,
  restore Docker through its supported operator interface, then run it with
  `--cleanup` using the repository's locked environment and project on PYTHONPATH.
  `cleanup-recovery.json` currently records a blocked API timeout, not success.
- No orphan-guardian Python process was observed after the failed third run.
  Docker/WSL was not restarted, settings were not changed, and no broad cleanup
  or alternate cleanup route was attempted. Retained evidence and the disk reserve
  remain protected.

## Next actions for Claude / operator

1. Read the final verification and cleanup rows above, then inspect the PR diff.
   Merge only with explicit user authorization; leave unrelated branches/PRs alone.
2. Have the operator restore Docker availability, then settle the two exact-owned
   resources above and verify port release. Cleanup remains an acceptance blocker
   until positively confirmed; preserve every unrelated container and session.
3. Have the operator choose the Docker Desktop host-network prerequisite or an
   explicit bridge configuration. Rerun the complete Windows browser/lifecycle
   matrix, including a real host WebSocket handshake, before accepting that
   gate. Investigate protocol-level readiness if TCP-only success still precedes
   a refused stream; do not treat one TCP probe as proof of a usable live view.
4. Resolve the real Claude auto-mode failure using supported authentication,
   usage-limit, and permission diagnostics. Then run isolated install/update and
   any required approval/resume checks; record actual outcomes, not assumptions.
5. Confirm rotation/revocation of the Docker Hub token previously disclosed in
   conversation. Rotation was an operator action; it has **not been verified**.
   Never copy that token into this file, logs, source, or client configuration.
6. Keep existing installations active. Do not activate a candidate or rewrite
   another client's registration merely because image CI passed.
7. Open PR #33 (image-fingerprint label changes) is separate work. Any image-input
   or fingerprint change needs its own matching image/catalog verification;
   do not merge it opportunistically or reuse this catalog as proof afterward.

The website lives on its separate branch. No website source/build is changed by
this PR. There is no claim of Chrome parity, browser network confinement,
universal host compatibility, or guaranteed Claude classifier approval.
