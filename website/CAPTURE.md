# Native pixel recording provenance

The player displays pixels captured from real agents inside XTerm and Xvfb in Docker. Canvas2D composes lossless PNG deltas at their original presentation timestamps. It does not redraw terminal glyphs, logos, menus, or progress indicators. Untouched ANSI bytes remain directly downloadable; lossless ZIP downloads contain unchanged timestamped PTY recordings with separate archive and original-payload hashes.

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

The player keeps the selected agent, shuffles cases without immediate repetition, replays the same case when switching agents, and holds completion for six seconds. It scales uniformly without reflow. Decoded native frames replace the display atomically; loading and failures retain the previous frame or a verified captured poster. Hidden and offscreen players pause. Reduced motion starts on an actual completed frame until visitors select Play.

The visible loop ends after the report hold, before the native process-exit screen clear. Raw terminal recordings and lossless masters preserve those exit bytes and frames unchanged.

Readable transcripts pair each actual tool call, arguments and observed result with the labeled scripted text sent to that client. Full-screen VT redraws are retained in the separate raw downloads rather than concatenated into an unreadable text transcript.

## Verification status

All 120 schema-3 sessions passed capture/tool/evidence/report/cleanup validation on 2026-10-12. Seven independent native RGB checkpoints per recording passed: 840 comparisons. All 32 website regressions and 38 capture/lab regressions passed, along with TypeScript, the production build and final browser review. GitHub Pages publication is gated by the existing workflow. See [verification status](capture/VERIFICATION.md) for measured timing, sampling gaps and unavailable checks, and [reproduction instructions](capture/README.md). Earlier schema-2 comparisons do not establish native graphical fidelity.

Claude uses its documented full-screen renderer, selected to match the reference’s docked composer. The real emulator palette is black/white, with line-height configured through XTerm and cell dimensions measured after mapping. No terminal labels, artwork, colors, or positions are replaced in playback. Lossless live capture writes to the container filesystem before retaining the master, so Windows/OneDrive asset writes do not stall sampling. Each capture records the actual immutable Docker image ID.
