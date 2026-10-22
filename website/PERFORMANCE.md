# Sharing and loading verification — 22 October 2026

Baseline: website commit `b9b7766`. After: the implementation accompanying this
report. No runtime, client registration, recording bytes, or dependencies changed.

## Measured loading

Three serial cold Lighthouse 13.0.1 runs per profile, before and after, on the
same Windows host and Python HTTP server (127.0.0.1:4183). Chrome's reported
host user agent was HeadlessChrome/140.0.0.0. Desktop used the desktop preset;
mobile used Lighthouse's default simulated mobile profile (412×823, 150 ms RTT,
1638.4 Kbps throughput, 4× CPU slowdown). The server sends uncompressed files.
These are laboratory medians, not GitHub Pages or real-user measurements.

| Measurement | Before | After |
|---|---:|---:|
| Main JavaScript, gzip | 241.39 kB | 145.66 kB |
| All shipped JavaScript, gzip | — | 157.3 KiB |
| Social image | 914,854 B PNG | 86,549 B JPEG |
| Embedded recording bootstrap | 683,831 B | Cases/client metadata only |
| Compact playback catalog | None | 121,493 B JSON, content-addressed |
| Redundant complete-manifest request | 2.68 MB | Removed |
| Desktop LCP | 3.786 s | 0.961 s |
| Desktop CLS | 0.00031 | 0 |
| Desktop blocking time | 28 ms | 0 ms |
| Desktop transferred bytes | 6,817,223 | 1,499,897 |
| Mobile LCP | 22.603 s | 4.716 s |
| Mobile CLS | 0.31806 | 0 |
| Mobile blocking time | 304 ms | 128 ms |
| Mobile transferred bytes | 6,454,663 | 1,285,059 |

All six after-runs: desktop LCP 1.084/0.957/0.961 s, mobile LCP
7.660/4.716/4.702 s. The **2.5 s mobile LCP target remains unmet** on this
uncompressed local server. Both CLS and the 160 KiB JavaScript budget pass.
Blocking time is not INP; field INP and real-device mobile performance are not
verified. The final diagram error action changes to a page reload and its
explanatory copy/help URLs are corrected; these recovery/copy-only changes are
not included in the timed samples.

The initial scenario remains intentionally randomized. Before desktop selected
TLS/TLS/web-CTF; after selected browser/network/TLS. Before mobile selected
reporting/recovery/recovery; after selected forensics/website/forensics. Transfer
size and poster timing therefore include capture variation: these are whole-page
samples, not a controlled per-recording percentage claim. Raw Lighthouse reports
are retained locally under ignored `test-results/performance/`.

## What changed

- Static Open Graph/X metadata and a versioned 1200×630 JPEG; old PNG retained.
- One compact JSON catalog instead of embedded provenance plus a full fetch.
- Selected poster before the pixel index; no unused-agent index/poster warming.
- Exact captured pixels, integrity checks, all 120 sessions, timing and evidence
  remain intact. Buffering and memory bounds are unchanged.
- Container-query space reservation, critical font preloads, and the existing
  small raster lion instead of the 380 kB SVG for tiny on-page logos.
- Deferred architecture module with an accessible heading/space reservation,
  direct-anchor loading, and visible recovery guidance.
- Decorative frame scheduling leaves CPU headroom and parks hidden workers;
  the original rendering recipe is unchanged.
- Browser explanation matches the current runtime: no claimed traffic boundary
  on host networking; CSP and native-download limitations remain explicit.
  Recording-help links now point to the standalone website branch.

## Functional verification

- Complete host website suite: **48 passed, 1 expected skip** (the source-coupled
  Hercules filter check cannot run on the standalone website branch).
- All 120 native captures passed byte/provenance and independent RGB pixel
  reconstruction tests. Their source files are unchanged in Git.
- Browser tests loaded verified native frames for all **4 agents × 10 cases**;
  explicit pause survived every switch. These are opening-frame checks, not
  forty complete session playthroughs.
- Keyboard tab selection, history pause, enlargement/Escape, replay, reduced
  motion, and 320/390px layouts passed; no horizontal page overflow and all
  three player buttons measured 44×44px.
- Blocking capture assets retained the last good frame and exposed Replay;
  blocking the catalog exposed Retry; blocking the diagram exposed Reload.
  Each recovered after requests were restored.
- A local fixture delayed every recording request by 750 ms. The selected
  verified poster appeared before its pixel index/frames; rapid scenario
  switching settled on the final selection without an alert. A sample poster
  commit took 786 ms; the first native paint took 803 ms. These are diagnostic
  observations, not before/after performance percentages.
- Offscreen playback retained its frame while the architecture was inspected.
  Worker parking/cancellation is regression-tested. The available browser did
  not report a hidden document when switching tabs, so a real hidden-tab check
  remains **unverified**, not passed.

Three-run navigation-to-poster instrumentation was blocked by the browser
interface's unsupported new-document scripting command. No alternate injection
was used. The twelve Lighthouse runs above are complete; a controlled three-run
poster/playback latency benchmark remains unverified.

## Reproduction and preview limitations

See [README](README.md#performance-checks) for pinned Lighthouse commands and
sharing-cache refresh instructions. `npm test` audits original recordings and
new loading/metadata regressions; `npm run build` checks TypeScript, generates
the static site, and enforces the full JavaScript budget.

Raw metadata and image HTTP checks do not prove a platform's rendered preview.
WhatsApp/Facebook/LinkedIn/X can cache cards, omit descriptions, or crop images.
Authenticated app-preview checks require an operator; no account posts are
created for verification. Existing posts/messages may retain old cards.

## Cleanup

Local preview servers and temporary browser probes are stopped/closed. No
Docker resources or client configuration were used. Raw measurement reports
are intentionally retained in ignored `test-results/performance/`.

Deletion of these five exact build-owned asset-copy backups was **blocked by
execution policy**; no alternate deletion route was attempted. They remain
under ignored `test-results/site-assets/` and are not part of the public build:
`1792667283999358900`, `1792667458931186600`, `1792667556996377100`,
`1792667889697161100`, `1792668502780410100`. The older archive and all source
recordings/evidence were left untouched. Operator removal is deferred.
