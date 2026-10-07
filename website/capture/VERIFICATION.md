# Native recording verification

Verified on 2026-10-07 before publication.

- All 48 sessions completed: four pinned clients, six examples, two terminal
  grids. Every session called Hercules's lifecycle, operation, evidence read,
  and report write tools through the fixture's actual exported STDIO schemas.
- The containers used no accounts, external network, host configuration, or
  Docker socket. Scan findings and container startup are scripted responses.
- `npm test`: 21 passing tests. The native regression compares text, character
  widths, foreground/background colors, and cursor positions at five checkpoints
  per recording. Original output chunks and fresh catch-up playback match.
- TypeScript checks and the production build passed.
- Browser layouts checked at 320, 360, 390, 799, 800, 1100, and 1440 pixels. Controls
  fit without horizontal overflow. Desktop/mobile recordings retain 36/28 rows.
- Checked DPR 1 and 2, 125% page zoom, and loading with 600ms network latency and
  cache disabled. Terminal initialization waits for IBM Plex Mono.
- Checked pause, replay, automatic random example changes, resizing during playback,
  enlargement, Escape, focus trapping with disabled controls, reduced-motion
  still frames, explicit Play, and offscreen pause. A visibility-change listener
  resets the playback clock so hidden-tab time cannot become a resume jump.
- Compared native OpenCode's wordmark/MCP menu, Claude's MCP tool count, Codex's
  MCP inventory/plan, and Hermes's loaded-server list against their raw captures.
  No browser console errors remained in the final local check.
- Added DNS, header review, and browser inspection cases. Random selection reaches
  all six cases and excludes the immediately previous case. The selector, footer
  status, and progress bar are absent; header playback controls remain.
- Verified the local CTF extraction, XOR/base64 decode, recovered flag, SHA-256
  match, decoy rejection, and reproducible report. Substituting the decoy payload
  fails verification and produces no verified solution.
- Every replay opens on visible native output. Hermes's 11–14 second blank
  startup is skipped through metadata, with raw bytes and timestamps preserved.
  Paused Hermes replay visibly opens on its native wordmark.
- Re-recorded all Claude cases in truecolor. Native orange mascot animation has
  distinct captured frames in every recording. Compared mascot shapes/colors
  and native progress presentation with the supplied Keploy tutorial reference.
  xterm's glyph renderer fixes font fallback gaps; normal panel proportions use
  measured terminal dimensions. Claude's configuration wizard is skipped while
  its native application entrance remains animated.
- Per-recording hash query strings prevent recaptured files from using stale
  HTTP cache entries. The final production preview was checked without cache.

Native timing plays at 1×; provider and tool delays remain authored examples.
Hermes's shallow checkout displays `vunknown` in its native banner; provenance
records the exact pinned revision. No CLI output is replaced with drawn artwork.
