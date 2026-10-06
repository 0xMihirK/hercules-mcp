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

## Terminal provenance

The supplied React Terminal component is adapted in `src/components/ui/terminal.tsx`.
Sequential typing exports remain usable; four demos use its body/header slots
around a real xterm.js emulator. Version-pinned references:

| Client | Reference |
| --- | --- |
| Claude Code | Local 2.1.291 capture, 2026-10-06: welcome, `/mcp`, server detail, `/config`. [Official MCP docs](https://code.claude.com/docs/en/mcp). |
| Codex CLI | [0.147.0 source](https://github.com/openai/codex/tree/be6e8eac029b183056b7e4402879f15d2c85f61b/codex-rs/tui): transcript MCP inventory and command popups. |
| OpenCode | [1.18.34 source](https://github.com/anomalyco/opencode/tree/aec0b9a6d8898f68f923aaf08b7306d931fd9d76/packages/opencode/src/cli/cmd/tui): wordmark and `/mcps` toggle dialog. |
| Hermes | [Classic CLI snapshot](https://github.com/NousResearch/hermes-agent/tree/3f524a2459efe4ab32061c418e309e5da1a931fd): Rich wordmark/caduceus and `/reload-mcp`. |

These recreate represented screens, not complete client applications. Models,
accounts, fonts, dimensions and future native releases differ. Keyboard input,
command selection, client-specific settings, history, MCP inspection, reconnect/
disable, toggles, cancellation, replay, pause and enlargement work locally.
Settings affect browser memory only. Staged delays mimic terminal pacing, not
measured model/network latency. The illustrated task explicitly starts Kali
before a local-lab httpx call. No demo invokes a model, Docker or Hercules.

Replica/simulation labels sit outside native screens. All four display on desktop
and stack at narrower widths. Character art/license provenance is recorded in
`THIRD_PARTY_NOTICES.md`.

## Verification

`npm test` checks pixels for every primitive, post-effect and blur; deterministic
frames, sampling, coverage, colors, pointer, masks, lifecycle and native command
transitions. Browser QA covers responsive layouts, keyboard interaction, scroll,
copying, enlargement, pause/replay and reduced motion. `REPO_ANALYSIS.md` records
the source-grounded claims used on the page.
