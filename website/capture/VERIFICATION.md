# Native pixel fidelity verification

Local verification completed on 2026-10-12. GitHub Pages publication is gated by the repository's build and deployment workflow.

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

## Playback and browser checks

- All **32 Node tests** passed: background primitives/effects, ANSI/CR/LF, within-channel native timestamps, serialized writes, cancellation, shuffle bags, geometry milestones, original timing, delta reconstruction, integrity, nonconsecutive atlas prefetching, evidence hashes and CTF checksums.
- All **38 Python tests** passed: capture pixels, readiness, clocks, actual lab branches, batch circuit breaking, screenshots, transcript/report selection, ownership cleanup, source provenance, shared evidence and byte-exact ZIP round trips.
- TypeScript and the final production build passed. The build reports a large JavaScript chunk warning. Development recordings and test-only fixtures are excluded from production.
- Actual browser inspection covered desktop, 320px and intermediate widths; enlargement; uniform scaling at DPR 1/2; rapid agent switching; pause/replay; explicit pause preservation; resizing during loading; slow/failed assets; reduced motion; keyboard focus, Escape and offscreen pause. No broken images, stale canvases, overlapping artwork or clipped controls were observed.
- A cold Canvas2D failure fixture shows the actual completed capture with transcript recovery and synchronized completed report evidence. A test-only clock jump exercised automatic cycling: selected agent retained, new progress reset to zero, old canvas retained during loading, and new-case files did not inherit old completion. The fixture and clock override were removed afterward.
- Final axe-core 4.14.0 checks found **zero WCAG violations** on desktop and 320px. Desktop version labels over the procedural background required manual contrast review; their opacity is now 1, with conservative worst-background contrast above 4.5:1. The mobile check had no incomplete results. Evidence labels remain opaque during motion and illustration captions no longer overlap imagery. Source detector checks passed for changed interface files.
- Installation prompt copying, tool chains, architecture controls, original ANSI/ZIP downloads and reports were inspected. Findings retain investigation results after report housekeeping; previews preserve final verification and scope while original reports remain unchanged.

## Explicit limitations

Genuine browser zoom and a real hidden-document transition are unavailable through the in-app browser controls. CSS width tests are not browser zoom. Actual offscreen pause and visibility-clock regressions passed.

Impeccable's automated adapter does not support this React/Canvas entry. The user explicitly approved browser review. Automated phases remain open; no receipt or automated visual approval was fabricated. The manual disposition is recorded separately in `.impeccable/review/finish-verdict.md`.

Model decisions, observations, delays and usage counters are scripted and labeled. Tools execute in local labs; native pixels and labels are not rewritten. Hercules's public MCP APIs are unchanged.
