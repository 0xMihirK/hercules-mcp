# Hercules showcase

A React single-page showcase, published through GitHub Pages. Counts, capabilities
and the complete installation prompt are generated from the Hercules source.
Docker is unnecessary to build or view the site.

```sh
cd website
npm ci
npm run dev
# Production:
npm test
npm run build
npm run preview
```

Requires Node 22.16+ and Python 3.11+. Development/preview use port 4173.
`scripts/prepare_site.py` imports only the standard-library tool catalog, removes
unmeasured token estimates, and copies the public asset directory. Generated
`public/`, `dist/`, dependencies and private QA captures are ignored by Git.
Relative URLs support the `/hercules-mcp/` Pages path.

## Design and background

Graphite `#101317`, silver `#EDF1F5`, muted silver `#A6AFBA`, copper `#D87950`.
Self-hosted Archivo, IBM Plex Sans and Mono carry their OFL notices in
`assets/fonts/`. The existing lion remains the project mark. The clients retain
their own terminal palettes.

`recipe.json` preserves every supplied parameter. References:
[Thread Light](https://21st.dev/@tempforall9/components/thread-light) and
[its ASCII editor preset](https://21st.dev/community/ascii/editor?from=7001ac36-260f-4f13-b9b4-8f5f6b02e546).
This is an independent Canvas2D recreation, not the unpublished original shader
or baked video. It samples no photo or video.

`renderer.js` produces domain-warped, seeded fBm smoke with the source palette,
upscales the low-frequency field, and averages pixels over the cell grid. It
implements all 25 primitives. Brightness, contrast, saturation, grayscale, tone
curve, tint and blur precede nine post-effects, then lights and reveal masks.
Masks reveal the plain procedural source. The page uses the supplied eight-pixel
hatch, shimmer, monochrome and halftone-30 preset. Disabled stages do no work.

The monochrome hatch path caches 32 raster tiles and folds color adjustments
into their palette; other modes use Canvas2D primitives. A fixed viewport canvas
runs in an OffscreenCanvas worker, with a main-thread fallback. Hidden documents
and pause controls stop animation. Reduced motion uses a deterministic still
and removes scroll pinning. FPS adapts from 24 to 15 above 40ms measured cost.

The raster factory exposes `renderAt`, `resize`, `ready`, `getStats`, `destroy`.
`createThreadLight` also exposes `update`, `pause`, `resume`, `setPointer`.
Source generation supports the supplied smoke recipe, excluding custom shader
code and other source presets.

## Native terminal recordings

The four panels play asciicast v2 recordings in xterm.js. The supplied React
Terminal component provides their header/body slots. Native client applications
run in disposable Docker containers, each with fresh configuration and a local
scripted model provider. Hercules's actual 46 tool and seven resource schemas
are exported from the repository and served over STDIO MCP with fixture results.

| Client | Version / source |
| --- | --- |
| Claude Code | 2.1.291; credential-free Microsoft Foundry gateway configuration. |
| Codex CLI | [0.147.0](https://github.com/openai/codex/tree/be6e8eac029b183056b7e4402879f15d2c85f61b). |
| OpenCode | [1.18.34](https://github.com/anomalyco/opencode/tree/aec0b9a6d8898f68f923aaf08b7306d931fd9d76). |
| Hermes | [Classic revision](https://github.com/NousResearch/hermes-agent/tree/3f524a2459efe4ab32061c418e309e5da1a931fd). |

Each client randomly plays six examples without immediately repeating the last:
a network report, a layered file-forensics CTF, a fictional lab website assessment,
DNS lookup, HTTP header review, and browser inspection. The CTF uses a real local
PNG with an appended archive, metadata clues, an XOR/base64 payload, a decoy flag,
and SHA-256 verification before saving a reproducible write-up.
The clients render their own logos,
menus, task lists, tool calls, and progress animations. Model responses, findings,
container startup, and response delays are scripted. No external targets are
scanned, and no personal credentials or paid model calls are used.

Recordings preserve raw ANSI, CR/LF, timestamps and fixed terminal grids:
120x36 desktop and 80x28 mobile. The presentation scales uniformly and never
reflows the captured artwork. Fonts load before xterm initializes. xterm's
WebGL renderer joins block/quadrant glyphs correctly, with a DOM
fallback when WebGL is unavailable. Panel proportions follow the measured native
grid, keeping letterboxing out of the normal cards.
Output writes are serialized; switching examples or replaying disposes the old terminal and
cancels its scheduler. Playback opens at the first visible native frame, skipping
the initial blank startup wait and Claude's one-time setup wizard; all later
animation timing remains at 1×. Claude's native orange theme, mascot entrance,
and progress frames come from truecolor captures of the pinned CLI.
Pause, replay, and enlargement stay in the header. There is no case selector or
footer status bar. Hidden/offscreen panels pause; reduced motion starts with a
report still frame and offers explicit Play.

[The capture harness](capture/README.md) documents configuration, isolation,
protocol fixtures, and validation. Public `assets/recordings/manifest.json`
contains per-recording hashes, geometry, timing, versions, and source provenance.
Docker is needed only to create recordings; visitors receive static assets.
The four clients illustrate compatibility with any STDIO MCP agent, worker, or
custom integration on Windows, macOS, or Linux with Docker.

## Verification

`npm test` checks procedural background rendering and playback regressions,
including byte preservation, timing, serialized output and discarded sessions.
Browser QA covers responsive layouts, pause/replay, random case transitions,
enlargement, zoom, fonts, device pixel ratios and reduced motion.
`REPO_ANALYSIS.md` records the source-grounded claims used on the page.
