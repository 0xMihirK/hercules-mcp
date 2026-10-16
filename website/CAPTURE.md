# Native pixel recording provenance

The player displays pixels captured from real agents inside XTerm and Xvfb in Docker. Canvas2D composes lossless PNG deltas from their original presentation timestamps. The website plays that timeline at 2.5×; raw downloads and capture timing remain at 1×. It does not redraw terminal glyphs, logos, menus, or progress indicators. Untouched ANSI bytes remain directly downloadable; lossless ZIP downloads contain unchanged timestamped PTY recordings with separate archive and original-payload hashes.

| Client | Pinned release | Native renderer | Terminal geometries |
| --- | --- | --- | --- |
| Claude Code | 2.1.289 | Native full-screen conversation | 120x28, 80x28, 48x28 |
| Codex | 0.160.1 | Native default TUI | 120x36, 80x28, 48x28 |
| OpenCode | 1.18.35 | Native default TUI | 120x36, 80x28, 48x28 |
| Hermes | 0.21.5, revision f97608f178d1ffeca59860195ab7da295f7c8e5f | Modern --tui | 120x36, 80x28, 48x28 |

Capture profiles pin XTerm 379, Cascadia Mono 2407.24 with Noto Sans Symbols2 (fonts-noto-core 20201225-1) and Noto Color Emoji (2.042-0+deb12u1), native dark themes, model configuration, permission mode, and terminal colors. The graphical emulator supplies its own capability responses. Measured cell dimensions and captured pixel dimensions determine presentation size; website fonts do not affect recorded pixels.

Model observations, hypotheses, plan changes, response delays, and usage counters are scripted. Hercules tool results are real. Claude uses its documented local gateway configuration and a disposable local API credential. Providers bind container loopback. No personal accounts, saved configuration, or paid model calls are used.

Each agent has a fresh allowlisted environment and a STDIO bridge to a separate host-side Hercules process through a private relay. Agents receive no host Docker socket. Hercules starts actual client-owned Kali runtimes on transaction-owned internal lab networks. Scanners, browser operations, files, and reports execute against local fixtures. No public target is contacted. Docker containment still depends on the operator's networking and privileges.

Ten investigations cover inventory, service assessment, website assessment, TLS and redirects, browser login behavior, layered forensic CTF, web CTF, evidence reconciliation, background-job recovery, and remediation rechecks. Each requires 8-16 meaningful MCP calls and verified Markdown/HTML reports. CTF steps follow discovered clues, reject decoys, and verify checksums. Missing or unexpected evidence stops validation.

Schema 3 records atlas assets and hashes, exact presentation timestamps, independent master checkpoints, pixel dimensions, profiles, native versions, raw output hashes, transcripts, milestones, artifacts, and cleanup provenance. Lossless graphical masters stay with local capture results; visitors receive static PNGs and evidence files.

Capture timing records the measured largest sampling gap and an independent UTC/monotonic clock check. Original graphical timestamps retain OS clock slewing. A clock discontinuity larger than one 60 fps frame rejects capture; cumulative UTC/PTY drift is disclosed separately. Requested 60 fps sampling is not a claim that the machine never stalls.

The player keeps the selected agent and shuffles cases without immediate repetition. Agent changes restart the same case, including its native entrance, and preserve explicit pause state. Six recorded seconds of completion occupy 2.4 wall seconds at 2.5×. Frames fit uniformly without reflow or cropping. Enlargement retains the same recording, geometry, and time; it performs no recording reload. The player has pause/play, replay, and enlargement controls. Recording and evidence downloads remain in this repository's assets and documentation rather than player controls.

The verified opening frame appears before progressive buffering of five source seconds. A rolling twelve-second buffer follows; stalls suspend the source clock instead of skipping unseen screens. A shared integrity-checked compressed cache is capped at 32MiB and decoded bitmaps at 64MiB. Patches compose sequentially offscreen. Incoming frames and their prompt/summary commit together and crossfade for approximately 200ms; reduced motion swaps directly. Discarded sessions cannot write to the active display. Previous pixels remain visible during loading and failures; Canvas failure falls back to an actual captured image.

Desktop scrolling and Arrow/Page/Home/End keys pause and review previously presented native screens. Play resumes from the selected history point, while Replay restarts. Phone swipes scroll the page during playback; after Pause, they review history. Navigation releases page scrolling at history boundaries. Hidden and offscreen players pause. Reduced motion starts on a completed captured frame until Play.

Hermes starts from its independently verified `nativeIntro` PNG and timestamp. This frame retains the complete native title before later startup scrolls can move the tall wordmark out of view. The original pixel indexes, review assets, raw bytes, timestamps, and hashes remain unchanged. The synchronized summary uses actual call-completion and artifact-availability timestamps; reports appear only after verification.

The visible loop ends after the report hold, before the native process-exit screen clear. Raw terminal recordings and lossless masters preserve those exit bytes and frames unchanged.

Readable transcripts pair each actual tool call, arguments and observed result with the labeled scripted text sent to that client. Full-screen VT redraws are retained in the separate raw downloads rather than concatenated into an unreadable text transcript.

## Verification status

The existing 120-session matrix passed capture/tool/evidence/report/cleanup validation on 2026-10-12. Current playback regressions again compare seven independent native RGB checkpoints per session: 840 comparisons. See [verification status](capture/VERIFICATION.md) for current checks, measured behavior, sampling gaps, and unavailable checks, and [reproduction instructions](capture/README.md). Earlier schema-2 comparisons do not establish native graphical fidelity.

Claude uses its documented full-screen renderer, selected to match the reference’s docked composer. The real emulator palette is black/white, with line-height configured through XTerm and cell dimensions measured after mapping. No terminal labels, artwork, colors, or positions are replaced in playback. Lossless live capture writes to the container filesystem before retaining the master, so Windows/OneDrive asset writes do not stall sampling. Each capture records the actual immutable Docker image ID.


## Presentation correction — 2026-10-16

Source recordings, ANSI bytes, timestamps, hashes, MCP calls, and APIs are unchanged. The frame now uses the full available phone width. The recorded-history range is horizontal beneath the image. A lazy-loaded complete transcript is available below the player, with discarded requests aborted when the selected recording changes. Enlargement keeps the existing source geometry and fits within the viewport; it does not choose or request a different recording.

The compact companion shows the current action and recent observations; the objective appears once in the prompt bar. Actual browser imagery is used only for the browser workflow, gated by artifact availability. JSON response screenshots are excluded from marketing imagery. Cropped previews link to their unchanged originals.

The lower showcase uses plain-language capabilities, a software boundary containing the Kali tools, independent session ownership, and an actual registered-filter specimen. The specimen is labeled illustrative input, not a newly captured lab run. No generated chassis, blank paper, fabricated agent UI, or numerical filter-performance claim is shown.
