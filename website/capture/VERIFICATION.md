# Native pixel fidelity verification

Native capture validation completed on 2026-10-12; playback and redesign verification updated on 2026-10-16. GitHub Pages publication is gated by the repository's build and deployment workflow.

The schema-3 player displays independent XTerm/Xvfb graphical captures. Earlier comparisons between ANSI/xterm reconstructions did not establish native appearance or motion and are superseded by this verification.

## Capture gates

- All 120 recordings passed: four pinned clients, ten real local-lab investigations, three geometries per client. The twelve pilots passed before expansion.
- Claude 2.1.289 uses its native full-screen conversation renderer, selected by the user to match the reference's docked composer. Cascadia Mono, native mascot entrance, medium effort, auto mode, progress glyphs and labels are captured without website replacements. Codex 0.160.1, OpenCode 1.18.35 and Hermes 0.21.5 retain their native interfaces; Hermes uses its modern TUI.
- XTerm 379 under Xvfb runs in an immutable Docker image. Measured cells are 11 × 24 pixels. Profiles identify emulator, fonts, palette, model, permission mode, image and source fingerprints. Actual emulator capability responses are forwarded and retained.
- Agents receive no host Docker socket or personal configuration. Scripted providers bind loopback; actual Hercules processes own isolated Kali runtimes and internal fixture networks. Every expected branch, MCP call, artifact, report, forensic flag checksum and transaction-owned cleanup passed validation. Missing evidence rejects capture.
- FFmpeg's first encoded frame gates native startup. Original master timestamps must cover the recorder interval. Lossless RGB masters remain locally; every delta frame was checked against decoded master pixels. Browser screenshots and Nuclei templates retain their original bytes.
- Seven independent checkpoints per recording passed at canonical size: startup, native entrance, MCP inspection, details, investigation, report and completion. This is **840 native RGB comparisons**, including independent master PNGs.

## Timing and payload limits

Canvas2D playback uses original presentation timestamps and elapsed time with pause accounting; it has no capped frame-step slowdown. Duplicate timestamps select the last original frame. The visible loop holds the report for six seconds and ends before process teardown clears the terminal. Raw recordings and masters retain teardown unchanged.

Requested sampling is 60 fps, but the host sometimes stalls. The largest accepted sampling gap is **2.333 seconds**. Missing sampling intervals are not filled with fabricated animation. The independent UTC/monotonic clock guard rejects discontinuities exceeding 16.67 ms; the largest accepted jump is 14.286 ms. Failed captures, including simultaneous Hermes clock discontinuities, were retained and recaptured. No timing threshold was relaxed.

A browser Claude progress sample recorded 154 changes, zero timestamp-selection mismatches, maximum paint latency 6.90 ms and maximum presentation lateness 12.60 ms. A final Hermes narrow-player sample recorded 11 changes, zero mismatches and maximum paint latency 4.40 ms. These bounded samples do not establish gap-free capture or guarantee browser scheduling on every device.

Recording assets occupy **914,646,930 bytes**; the production site is approximately 920.7 MB, below the 1 GB Pages limit. Timestamped PTY downloads use lossless ZIP wrapping: exactly one original `.cast` file, with archive and payload hashes verified separately. Untouched `.ansi` remains directly downloadable. Shared large evidence downloads preserve identical original bytes and each recording's original workspace path and checksum.

## Current playback and visual redesign — 2026-10-15

The source matrix is unchanged. The visible player remains a composition of independently captured native pixels. Current verification passed all **39 Node tests**, including the 840 canonical RGB comparisons, raw bytes and evidence hashes, CTF checksums, bounded cache/decode behavior, progressive first-frame readiness, playback clocks, cancellation, all background primitives/effects, and summary availability gates. All **38 Python capture/lab regressions** passed. These regressions validate retained data and harness behavior; no new Docker captures were run for this visual update.

The player buffers five source seconds initially and maintains twelve ahead. Verified compressed assets are shared with a 32MiB LRU cap. Decoded bitmaps are limited to 64MiB and dependencies compose sequentially. Long dependency seeks and large cache entries are covered by regressions. The first native poster is independent of atlas buffering; failed/stalled assets preserve a valid frame and suspend time. Agent changes restart the same case with explicit pause preserved, and use a 200ms decoded-frame fade. Downloads and zoom were removed from player controls.

Current browser checks observed:

- Warm opening commits of 88.7ms (Hermes), 98.7ms (Claude), and 188.8ms (Hermes after an initially offscreen/paused entrance), below the 250ms target in these local samples. Cold loading remains network/decoding dependent. A cold narrow Hermes poster took 447.6ms and subsequent atlas reconstruction took 1.29s while the poster remained visible. This is not a latency guarantee for all networks or devices.
- Rapid Codex → OpenCode → Claude switching settled on one Claude canvas, the same case, matching prompt/summary, and explicit pause intact. Discarded work did not overwrite the final selection.
- Enlargement produced **zero additional pixel recording requests**, retained source time/120 columns, and fitted the full frame uniformly. Closing retained that same recording. Canonical Hermes entrance shows the complete native wordmark; the 48-column entrance shows the client's genuine compact title. Later native banner scrolling is preserved.
- PageUp moved from 151.246s to 139.246s and paused. Home returned to the entrance. Previously presented maximum remains available for review. Play resumes from the selected point. A long elapsed-time browser sample advanced approximately 2.49 source seconds per wall second, consistent with 2.5× and frame-boundary sampling.
- DPR 2 at 320px retained uniform scaling, a completed actual frame and synchronized report under reduced motion, with zero active animations. The responsive layout has no horizontal page overflow at 320px. Controls retain 44px targets.
- A temporary cold renderer-failure entry disabled visible Canvas2D before React mounted. An actual completed PNG loaded through the image fallback and the verified report remained available. The fixture is removed before production. Blocking atlas assets retained the native poster, showed retry guidance, and recovered through Replay after the block was removed.
- A throttled-asset check retained the previous image during switching and progressive loading. Temporary network, renderer, and media overrides are removed after review.
- The single-prompt action reported success; the exact string passed to the clipboard matched the unchanged canonical `install.txt` (1,124 characters in the deployment revision). Direct clipboard readback is unavailable in this browser.
- Final mobile and desktop axe-core checks found zero WCAG violations. The illustration's accessible label uses a named group. Axe requires manual contrast review for `.diagram-detail` because the connection SVG overlaps its containing scene; its opaque silver text (`#a6afba`) on solid graphite (`#11181e`) has an 8.07:1 contrast ratio.

The redesigned page replaces raw tool/API chains, the chassis illustration and the tall tabbed evidence panel with understandable capability examples, a large software-workspace lifecycle, platform compatibility, a visual filtering explanation, synchronized outcomes, and prominent single-prompt installation. Labels remain HTML. Docker networking, privileges, explicit startup and session ownership are explained accurately. The existing logo artwork is reframed without replacing its paths; Docker artwork is attributed to Devicon v2.17.0. No rejected generated image is used.

TypeScript and the production build passed. The measured production tree is approximately 920.7MB, with no temporary QA fixtures. The build retains the existing large-JavaScript-chunk warning.

No numerical filter-savings claim is published. Registered Hydra, Nikto and Nuclei filters were checked locally with characterized input containing noise, findings and diagnostics; they reduced known noise and preserved errors/warnings. A fresh live-lab filter benchmark was unavailable because Docker Desktop did not start. The previous 99.9% response-bounding example is not represented as filter performance.

## Visual corrections — 2026-10-16

The current source passes 40 website regressions, including 840 independent RGB checkpoints, raw/evidence integrity, playback/cache behavior, background rendering, actual-call availability gates, and the newly displayed registered-filter specimen. The Python harness result above belongs to the previous verification date; no new capture or live-lab run is claimed. TypeScript and the production build passed. The existing large-chunk warning remains.

An independent agent visually reviewed the full 1440px page, a 1280×720 laptop, 390/320px phones, capability and lifecycle controls, all four clients, transcript, and reduced motion. It found enlarged-player overflow, phone connector wrapping, and an unreadable browser preview. These were corrected; the reviewer separately inspected the corrected PNGs and confirmed those visible repairs. Its browser became unavailable during confirmation, so that final disposition is screenshot review, not a second browser interaction pass.

Root-browser checks confirmed the enlarged stage fits x24–1256 at 1280px with all controls visible. At 320px the native frame is approximately 305px wide, compared with the prior 219px; source geometry and aspect ratio remain intact. Agent tabs fit inside their grid. The history range no longer removes space from the image. A readable full transcript supplements the unchanged native pixels. Reduced motion and DPR 2 retain actual captured frames.

The architecture now uses a software boundary with tool groups inside the Kali container. Lifecycle changes are explicit rather than driven by scroll position. There is no pin spacer. The filter demonstrator retains opaque findings/warnings and reserves its height; the following section moved less than one CSS pixel between the measured original and filtered states. No numerical token saving is claimed.

Phone axe-core found zero WCAG violations. The filter example now has a named group role. Remaining image-related contrast checks require manual inspection because the clipped original screenshot extends beyond its excerpt window; surrounding text is opaque silver on solid graphite. Current final desktop checks and published verification are recorded in the accompanying visual review. Genuine browser zoom and physical-phone testing remain unavailable.

## Illustration refinement — 2026-10-16

Network routes now meet equal-height service rows; the challenge uses a continuous three-stage route; and the host Hercules process has balanced framing and structural ports. Phone connectors turn vertically into the Docker boundary. The illustrations retain the existing product facts and graphite/copper palette. Original browser captures and native recording pixels are unchanged.

An independent agent inspected desktop network/architecture and 390px phone network/architecture screenshots and found no material visual defect. Root separately confirmed the final challenge at 1440px and 320px, and corrected a 13px internal network overflow at 800px. The final 800px diagram has equal client/scroll widths. At 320px/DPR 2, the page and challenge fit without horizontal overflow, reduced motion exposes all content, and zero animations are running. Final narrow axe-core reports zero WCAG violations; the unchanged playback-speed overlay still requires manual image-related contrast review. The opaque diagram labels remain readable on solid graphite.

TypeScript, the production build, and the focused four showcase regressions pass. The existing large-JavaScript-chunk warning remains. This pass adds no new captures, benchmarks, native-player changes, or genuine browser-zoom claims.

## Explicit limitations

The existing capture's largest sampling gap is still 2.333 seconds; missing motion is not fabricated. Model decisions, observations, delays, and usage counters remain scripted and labeled. Tools in the retained recordings execute in local labs; public targets are not contacted. Raw ANSI/CR/LF, source pixel assets and hashes remain unchanged. Hercules's public MCP APIs are unchanged.

Genuine browser zoom and a real hidden-document transition are unavailable through the in-app browser controls. CSS width and DPR tests are not browser zoom. Offscreen behavior and visibility-clock regressions remain independently checkable.

Impeccable's automated adapter does not support this React/Canvas entry. The user explicitly approved browser review. Automated phases remain open; no receipt or automated visual approval is fabricated. The manual disposition is recorded in `.impeccable/review/finish-verdict.md`.
