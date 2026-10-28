# Hercules showcase

A React single-page showcase published through the existing GitHub Pages
workflow. Product counts, the tool catalog and the installation prompt come
from Hercules source. Docker is required for capturing demonstrations, not for
building the website or viewing it.

The current plugin also bundles nine agent skills with 79 on-demand topic
guides. These guide tool choice and testing workflows; they do not add MCP
tools or authorize new targets. The standalone website branch receives its
tool/resource counts from `main` through `site-sync`.

```sh
cd website
npm ci
npm run dev
# Verify the complete public recording matrix before publishing:
npm test
npm run build
```

Requires Node 22.16+ and Python 3.11+. Development uses port 4173.
`scripts/prepare_site.py` generates source facts, a small recording bootstrap,
and a content-addressed playback catalog. Full provenance stays in the original
public manifest, not in executable JavaScript. Preparation never rewrites the
source recordings or their checksums.
Development recordings stay in a separate preview asset directory; production
preparation rebuilds copied assets without retaining that directory.
Generated public/dist directories, dependencies and private capture diagnostics
are ignored. Relative URLs support the `/hercules-mcp/` Pages path.

## Design

Graphite, silver and copper; Archivo with IBM Plex Sans and Mono; the existing
lion wordmark. Native terminal palettes and geometry remain native. The page
order is hero and agent player, catalog summary, architecture, and setup.
Architecture loads as it approaches the viewport. Mobile and
reduced-motion layouts present complete information without scroll pinning.
`DESIGN.md` and `PRODUCT.md` document the design and product facts.

`recipe.json` preserves the supplied procedural background parameters. The
independent Canvas2D recreation renders seeded domain-warped smoke, samples
average cell colors and applies hatch, shimmer and halftone. No photograph or
video is sampled. `renderer.js` supports the 25 specified primitive modes and
ordered adjustments/effects. The supplied smoke source is supported; arbitrary
shader code and other source presets are not. OffscreenCanvas uses a worker
with a main-thread fallback. Expensive decorative frames leave CPU headroom
for playback; hidden documents, pause and reduced motion stop continuous
rendering. See the [source effect](https://21st.dev/community/ascii).

## Native sessions

One Canvas2D player has four agent tabs and ten randomly cycled cases, with a
scenario picker alongside it (below on phones). Switching agents keeps the
case; replay restarts it. Playback reconstructs verified native graphical
captures at 2.5×, preserving original timestamps and pixels. The fixed
120/80/48-column captures scale uniformly without terminal reflow.

Each recording comes from an unmodified pinned client in a disposable Docker
container. Model responses and usage counters are scripted. Hercules tools,
runtime startup, evidence and reports execute in isolated local labs. No public
target, personal account or paid provider is used. The publisher requires the
complete 120-session matrix and verifies each report, evidence index and owned
cleanup. The public manifest records versions, capture configuration, hashes,
milestones, transcripts, actual browser-rendered stills and artifact availability.

Playback verifies and decodes a poster before replacing the visible frame,
then loads only the selected capture near the viewport. Other clients' pixel
indexes and posters are not speculatively downloaded. Captured stills support
loading, reduced motion and rendering failures. Hidden/offscreen playback
pauses, independently of explicit pause. Controls include pause, replay,
recorded history and accessible enlargement. Full transcripts, reports and
artifact provenance remain available in the recording assets.

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
motion and failure states.

## Shared-link previews

Open Graph and X large-card metadata live in `index.html`, so crawlers do not
need JavaScript. The canonical URL is
<https://0xmihirk.github.io/hercules-mcp/>. The 1200×630 JPEG uses the existing
logo, fonts and procedural artwork; regenerate it with
`node scripts/social-preview.mjs`. The generator enforces a 250 KiB limit.
Use a new versioned filename when changing the card, update both image tags,
and retain previous assets for cached previews.

Facebook, WhatsApp, LinkedIn, X and other apps choose their own crop, displayed
fields and caching. Metadata is not a guarantee that every app displays a
description or identical domain label. After deployment, use
[LinkedIn Post Inspector](https://www.linkedin.com/post-inspector/) and
[Facebook Sharing Debugger](https://developers.facebook.com/tools/debug/) where
available. Existing posts/messages may retain old previews; refreshing metadata
usually affects new shares, not historical posts. Account-gated app previews
must be checked manually; do not publish a post merely to test one.

## Performance checks

The production build checks static preview metadata and font preload paths,
and enforces **160 KiB gzip for all shipped JavaScript**, including deferred
chunks and the background worker. Recording images and JSON are measured
separately; moving data out of JavaScript is not reported as eliminating its
transfer cost. The capture masters, raw terminal streams, and evidence retain
their original bytes. Public pixel atlases are repacked as lossless WebP; the
publisher verifies that every decoded RGB pixel matches the captured PNG.

For a repeatable local baseline, serve `dist` with Python on port 4183 and run
three serial Lighthouse measurements for each profile, using fresh browser
storage. Keep the same server, Lighthouse version, viewport and throttling
settings before and after. Normal case selection is randomized; record the
chosen captures and use medians rather than attributing individual differences
to one optimization.

```sh
python -m http.server 4183 --bind 127.0.0.1 --directory dist
# In another terminal; change output names for each run:
npx --yes --package=lighthouse@13.0.1 lighthouse http://127.0.0.1:4183/ --only-categories=performance --preset=desktop --output=json --output-path=test-results/performance/desktop-1.json --chrome-flags="--headless=new --no-first-run" --quiet
# Omit --preset=desktop for the simulated mobile profile.
```

Create the report directory first. Python's simple server does not compress
responses; do not equate these transfer timings with GitHub Pages compression
or real-user Core Web Vitals. Preserve raw reports in ignored test results and
report any unmet LCP/CLS targets explicitly. Lab blocking time is not field INP.
