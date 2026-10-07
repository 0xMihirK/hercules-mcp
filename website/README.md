# Hercules showcase

A React single-page showcase published through the existing GitHub Pages
workflow. Product counts, the tool catalog and the installation prompt come
from Hercules source. Docker is required for capturing demonstrations, not for
building the website or viewing it.

```sh
cd website
npm ci
npm run dev
# Verify the complete public recording matrix before publishing:
npm test
npm run build
```

Requires Node 22.16+ and Python 3.11+. Development uses port 4173.
`scripts/prepare_site.py` generates source facts and a recording bootstrap.
Development recordings stay in a separate preview asset directory; production
preparation rebuilds copied assets without retaining that directory.
Generated public/dist directories, dependencies and private capture diagnostics
are ignored. Relative URLs support the `/hercules-mcp/` Pages path.

## Design

Graphite, silver and copper; Archivo with IBM Plex Sans and Mono; the existing
lion wordmark. Native terminal palettes and geometry remain native. The page
order is hero, agent player, tool chains, architecture, evidence and setup.
Architecture and evidence use separate scoped GSAP timelines. Mobile and
reduced-motion layouts present complete information without scroll pinning.
Generated supporting illustrations are labeled and have embedded prompts.
`../DESIGN.md` and `../PRODUCT.md` document the design and product facts.

`recipe.json` preserves the supplied procedural background parameters. The
independent Canvas2D recreation renders seeded domain-warped smoke, samples
average cell colors and applies hatch, shimmer and halftone. No photograph or
video is sampled. `renderer.js` supports the 25 specified primitive modes and
ordered adjustments/effects. The supplied smoke source is supported; arbitrary
shader code and other source presets are not. OffscreenCanvas uses a worker
with a main-thread fallback. Hidden documents, pause and reduced motion stop
continuous rendering. See the [source effect](https://21st.dev/community/ascii).

## Native sessions

One player has four agent tabs and ten randomly cycled cases. Switching agents
keeps the case; replay restarts it. There is no case dropdown or keyboard
takeover. The browser replays untouched ANSI/CR/LF and timestamps at 1× with
xterm 6's DOM renderer and Unicode 11. Fonts load before reconstruction. The
120×36, 80×28 and 48×28 grids scale uniformly without terminal reflow.

Each recording comes from an unmodified pinned client in a disposable Docker
container. Model responses and usage counters are scripted. Hercules tools,
runtime startup, evidence and reports execute in isolated local labs. No public
target, personal account or paid provider is used. The publisher requires the
complete 120-session matrix and verifies each report, evidence index and owned
cleanup. The public manifest records versions, capture configuration, hashes,
milestones, transcripts, actual browser-rendered stills and artifact availability.

Playback reconstructs a new terminal before replacing the visible frame,
serializes writes and cancels discarded sessions. Captured stills support
loading, reduced motion and rendering failures. Hidden/offscreen playback
pauses, independently of explicit pause. Controls include pause, replay,
transcript and accessible enlargement. Findings, files and report previews are
synchronized with actual tool completion, rather than authored observations.

[Capture provenance](CAPTURE.md) explains execution, estimates and completeness.
[The harness](capture/README.md) documents reproducible capture commands.
Docker is not needed by visitors. These four clients illustrate compatibility
with any agent, worker or custom integration supporting STDIO MCP on Windows,
macOS or Linux with Docker.

## Verification

`npm test` covers procedural rendering, playback timing and cancellation,
fixed geometry, shuffle cycling, source provenance, all published artifact
hashes, CTF checksums and native VT frame equivalence. The capture program has
additional Python regressions for evidence-gated advancement and recovery.
Browser review covers desktop/mobile, controls, resizing, fonts, DPR, reduced
motion and failure states. `REPO_ANALYSIS.md` records source-grounded claims.
