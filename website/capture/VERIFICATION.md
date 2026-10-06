# Native recording verification

Verified on 2026-10-07 before publication.

- All 24 sessions completed: four pinned clients, three examples, two terminal
  grids. Every session called Hercules's lifecycle, operation, evidence read,
  and report write tools through the fixture's actual exported STDIO schemas.
- The containers used no accounts, external network, host configuration, or
  Docker socket. Scan findings and container startup are scripted responses.
- `npm test`: 18 passing tests. The native regression compares text, character
  widths, foreground/background colors, and cursor positions at four checkpoints
  per recording. Original output chunks and fresh catch-up playback match.
- TypeScript checks and the production build passed.
- Browser layouts checked at 320, 360, 390, 800, 1100, and 1440 pixels. Controls
  fit without horizontal overflow. Desktop/mobile recordings retain 36/28 rows.
- Checked DPR 1 and 2, 125% page zoom, and loading with 600ms network latency and
  cache disabled. Terminal initialization waits for IBM Plex Mono.
- Checked pause, replay, rapid example changes, resizing during playback,
  enlargement, Escape, focus trapping with disabled controls, reduced-motion
  still frames, explicit Play, and offscreen pause. A visibility-change listener
  resets the playback clock so hidden-tab time cannot become a resume jump.
- Compared native OpenCode's wordmark/MCP menu, Claude's MCP tool count, Codex's
  MCP inventory/plan, and Hermes's loaded-server list against their raw captures.
  No browser console errors remained in the final local check.

Native timing plays at 1×; provider and tool delays remain authored examples.
Hermes's shallow checkout displays `vunknown` in its native banner; provenance
records the exact pinned revision. No CLI output is replaced with drawn artwork.
