# Native capture harness

The harness records unmodified Claude Code **2.1.292**, Codex **0.160.1**,
OpenCode **1.18.35** and Hermes **0.21.5** (modern `--tui`, source revision
`f97608f178d1ffeca59860195ab7da295f7c8e5f`). Claude uses the documented standard
conversation renderer, truecolor and a credential-free loopback Foundry gateway.
The other clients use their supported local providers. No personal configuration,
account credentials or paid model calls are used.

`record.py` drives real PTYs, native menus/MCP inspection, prompts and approval
cards. It records the clients' output bytes and monotonic timestamps; it draws
no terminal interface. Native animations run normally; input and model response
delays are authored. Model reasoning, usage counters and example prompts are
scripted and explicitly labeled. Tool responses are real Hercules responses.

## Execution and isolation

`labs/run.py` owns a fresh internal Docker network, lab fixture, capture
container, host-side Hercules process and private relay. Agents receive fresh
allowlisted configuration, a read-only harness and their capture output mount.
They receive no host Docker socket or personal configuration. Providers bind
container loopback. A STDIO bridge connects each client to Hercules through the
private transaction-owned relay; tool arguments/results are passed unchanged.

Hercules starts a real client-owned Kali runtime with selected capabilities and
`HERCULES_DOCKER_NETWORK`. Fixture services supply DNS, HTTP, TLS, login workflows,
CTFs and remediation state on the internal network. No public target is contacted.
Browser/scanner/shell operations, file writes and Markdown/HTML reports execute
through Hercules. Cleanup verifies and removes only exact transaction-owned
resources. These protections do not imply that all Docker deployments are a
complete security boundary; operator networking and privileges matter.

`labs/program.py` advances authored model responses only after observed tool
results satisfy the expected branch. It derives job IDs, evidence references
and CTF keys from those results. Unexpected or missing evidence stops validation.
The forensic CTF follows PCAP fragments through an appended archive, PBKDF2/AES
and compressed hidden data, rejects a decoy and verifies a checksum. There is
no prewritten solver available to the agent.

## Reproduce

Use the repository's Python environment and working Docker. Build the capture
image and fixture image, then run the ten-case matrix:

```sh
docker build -t hercules-showcase-capture:20261007-v2 website/capture
docker build -t hercules-showcase-lab:20261007 -f website/capture/labs/Dockerfile website/capture/labs
uv run python -m website.capture.labs.batch --workers 3
uv run python -m unittest website.capture.labs.test_program
```

The matrix is four clients × ten cases × three geometries (120×36, 80×28,
48×28): **120 recordings**. Individual arguments and image configuration are
available through `uv run python -m website.capture.labs.run --help`. Selected Kali
capabilities are shell, session, workspace, DNS, Nmap, curl, ncat, WhatWeb,
fuzzing, Nuclei, SearchSploit, binwalk, steghide and browser.

```sh
# A separate partial development preview; never publishes approximations:
uv run python -m website.capture.labs.publish --development
cd website
npm run dev
```

Use development-only `frame-review.html` to render each recording's actual
first native frame. Browser screenshots and SHA/time/geometry proofs go under
`test-results/labs/browser-stills/`. `first-frame.mjs` finds the first application
frame, excluding blank startup waits and one-time onboarding. It does not
change raw casts or later animation timing.

```sh
# Requires all 120 validated captures and matching actual browser stills:
uv run python -m website.capture.labs.publish
cd website
npm test
npm run build
```

The publisher verifies versions, meaningful tool sequence, lifecycle, report
contents, CTF evidence, every evidence-index checksum and owned cleanup. It
archives prior staging directories recoverably before staging a fresh matrix.
Failed captures remain diagnostic data and are never substitute demonstrations.
Visitors receive static casts, stills, transcripts and artifacts.

## Provenance

The manifest separates real tools from scripted models, preserves cast bytes,
records capture image/source/profile, native geometry, milestones, input timing,
MCP schema hash and artifact links/hashes. Actual result excerpts and report
availability follow observed completion. Character measurements include the
whole structured response; approximate tokens use `ceil(characters / 4)` and
are not tokenizer counts. Output completeness and evidence completeness are
separate. A bounded response is not automatically a semantically filtered one.
Catalog provenance uses consistent LF; casts retain original ANSI/CR/LF.

See [website capture documentation](../CAPTURE.md) for client references and
the public provenance contract.
