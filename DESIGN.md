---
name: Hercules
description: A graphite and copper editorial system for an agent-owned Kali workspace.
colors:
  copper: "#d87950"
  copper-hover: "#f29a72"
  copper-code: "#f2a989"
  graphite: "#101317"
  raised-graphite: "#1b2026"
  silver: "#edf1f5"
  muted-silver: "#a6afba"
  rule: "rgba(237,241,245,.16)"
  action-ink: "#141516"
  evidence-surface: "rgba(16,21,25,.97)"
typography:
  display:
    fontFamily: "Archivo, sans-serif"
    fontSize: "clamp(43px, 4.7vw, 72px)"
    fontWeight: 620
    lineHeight: 1
    letterSpacing: "-0.035em"
  headline:
    fontFamily: "Archivo, sans-serif"
    fontSize: "clamp(32px, 3.7vw, 56px)"
    fontWeight: 580
    lineHeight: 1.08
    letterSpacing: "-0.03em"
  title:
    fontFamily: "Archivo, sans-serif"
    fontSize: "28px"
    fontWeight: 580
    lineHeight: 1.08
    letterSpacing: "-0.03em"
  body:
    fontFamily: "IBM Plex Sans, sans-serif"
    fontSize: "17px"
    fontWeight: 400
    lineHeight: 1.55
  label:
    fontFamily: "IBM Plex Sans, sans-serif"
    fontSize: "14px"
    fontWeight: 400
  code:
    fontFamily: "IBM Plex Mono, monospace"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.8
rounded:
  sharp: "0px"
spacing:
  compact: "8px"
  control-gap: "12px"
  small: "16px"
  inset: "20px"
  medium: "24px"
  large: "28px"
  section-heading: "48px"
  chapter-mobile: "52px"
  chapter-tablet: "70px"
  chapter-desktop: "94px"
  page-gutter: "clamp(20px, 4.3vw, 66px)"
components:
  button-primary:
    backgroundColor: "{colors.copper}"
    textColor: "{colors.action-ink}"
    rounded: "{rounded.sharp}"
    padding: "12px 18px"
    height: "48px"
  button-primary-hover:
    backgroundColor: "{colors.copper-hover}"
    textColor: "{colors.action-ink}"
  button-secondary:
    textColor: "{colors.silver}"
    rounded: "{rounded.sharp}"
    padding: "12px 18px"
    height: "48px"
  agent-tab:
    textColor: "{colors.muted-silver}"
    rounded: "{rounded.sharp}"
    padding: "10px 18px"
    height: "48px"
  agent-tab-selected:
    backgroundColor: "{colors.copper}"
    textColor: "#151719"
  investigation-summary:
    backgroundColor: "{colors.evidence-surface}"
    textColor: "{colors.silver}"
    padding: "23px"
    rounded: "{rounded.sharp}"
---

# Hercules design system

Graphite reading surfaces, copper actions, Archivo headlines, and IBM Plex body type remain the visual foundation. The existing lion and wordmark anchor the identity. The procedural Canvas smoke/hatch/shimmer/halftone background stays unchanged. Native terminals retain their captured colors and typography.

## Product facts

Hercules is a host-side STDIO MCP server. Compatible agents, workers, and custom integrations can connect on Windows, macOS, and Linux. Connecting does not start the runtime. A session explicitly starts its owned Kali container; independent sessions have separate runtime ownership, working files, and allocated ports. Cleanup targets the owned runtime. Operators control networking, permissions, and target scope; Docker is not a complete security boundary.

Tool-specific filters remove known scanner noise while preserving important findings and diagnostics. Response-size bounding is a separate mechanism. Saved artifacts support follow-up but are not presented as a distinctive product feature. No numerical filter savings are claimed without a validated measurement. Reports and screenshots shown on the page are outcomes of the real local-lab recordings.

## Page sequence

Hero and native agent player → catalog summary → interactive architecture illustration → single-prompt installation. The architecture scene integrates Docker, browser control, concurrent tools, workspace management, and response filtering.

The hero and agent introduction are preserved. The technical catalog lives in GitHub documentation. Main-page explanations avoid raw MCP names, JSON payloads, hashes, byte counts, and recording mechanics.

## Visual language

Sharp corners, fine rules, generous chapter spacing, and readable silver text. Use copper to indicate actions, active stages, and meaningful connections. Keep labels opaque during animation. Do not introduce glass panels, decorative status dots, unverified counters, or a new type system.

One focused capability example is shown at a time in a four-tab walkthrough: network mapping, website verification, layered challenge solving, and a readable report. Use functional diagrams and real browser/report content. Illustrations must describe software relationships, not substitute physical machinery for Docker. The rejected chassis, blank paper, and generated architecture overview are not shown.

The architecture is a capability-first HTML/SVG software illustration. A compact agent/Hercules control column feeds a dominant Kali Docker enclosure. Six distinct software vignettes pair recognizable tools with plain-language purposes: CloakBrowser; Amass/DNS/Nmap; ffuf/Nuclei/SQLMap; Binwalk/ExifTool/Steghide; SearchSploit/Metasploit; Hydra/John. Shell and workspace tools connect the steps. Selected bundle availability is explicit; the scene does not promise every tool is installed.

Three rounded orthogonal routes connect real ports: Hercules to the runtime, runtime output to host-side filtering, and a narrow return rail from the filter to the agent. No paths cross text or cards. Parallel lanes show overlapping independent checks. The complete runtime unit departs and a new numbered runtime arrives; its mounted workspace becomes current while the previous numbered workspace remains inspectable. This is an illustrative, explicitly requested session transition, not Kubernetes reconciliation. A connection has one active workspace; separate clients may own independent runtimes.

Eleven real buttons expose capabilities and infrastructure. Hover and keyboard focus preview details, click/tap pins an explanation, and Escape or close clears it. Inspection pauses the loop, and the runtime is inert during its short replacement transition. Selected and keyboard explanations stick inside the scene at the viewport bottom; alignment leaves the selected card above them. Pointer focus never scrolls before the click completes. Detail space stays reserved. Keep lifecycle selectors, telemetry consoles, invented savings, and bot-evasion guarantees out of the scene. Authentic Docker artwork and the existing lion remain unchanged.

At 800px and below, agent/Hercules lead into the full-width runtime, followed by the filter and retained workspaces. Under 540px, tool modules become one readable column. DOM and visual order agree. Use shallow edges, one-pixel rules and restrained shadows; no WebGL, raster illustration, additional dependencies or altered global typography.

## Native player

One Canvas2D player, four agent tabs, and a compact investigation summary beside it on desktop and below it on phones. The prompt contains the objective once. The compact summary follows actual completed-call timestamps: current action, up to two observations, available browser evidence, and the verified report action. No findings or report appear before their underlying artifacts are available.

Play captured pixels at 2.5×. Switching agents restarts the same case and preserves explicit pause. Shuffled cycling retains the selected agent. Hold six recorded seconds at completion (2.4 wall seconds). Decode the opening before switching, crossfade for 200ms, and retain the last valid frame during loading, buffering, or failures. Reduced motion starts with a captured completed frame and swaps directly.

Load five source seconds at startup and maintain twelve ahead, with a shared verified compressed cache capped at 32MiB and decoded bitmaps capped at 64MiB. Native output timing remains separate from GSAP motion. A verified complete Hermes entrance frame avoids naturally scrolled startup artwork; no native pixels are replaced.

The only player buttons are pause/play, replay, and enlargement, each at least 44px. Enlargement fits and centers the existing complete frame; it does not choose a different geometry or reload the recording. Preserve proportions and never reflow terminal artwork.

Recorded-history navigation pauses playback and reviews previously presented screens. Desktop wheel/trackpad and Arrow/Page/Home/End keys provide access. Phone swipes scroll the page while playing; pause first to review history. Play resumes from the selected point. A horizontal history range sits below the image so it does not consume native-frame width. Navigation remains keyboard accessible, and page scrolling is released at history boundaries. Phones give the frame the full available page width; the complete transcript is available in a readable disclosure below it.

## Motion and accessibility

Use an unpinned fifteen-second software loop: dispatch, overlapping tool work, filtered response, stop the current runtime, and start a fresh one. Move the complete software enclosure, not a ghost outline. A visible state strip distinguishes running, completed, stopping, starting and ready states. The browser cursor and discovered-service branches participate in the work sequence. Labels remain opaque during work; replacement has a brief exit/arrival with an empty runtime holder beneath. Stop while inspected, hidden or offscreen; reduced motion presents all capabilities statically. Native terminal timing is independent.

Phones use ordinary document flow with meaningful positional motion. Reduced motion preserves every fact without pinning or continuous effects. The floating site-motion action has been removed at the user's request; native-player controls remain. Hidden/offscreen playback pauses without consuming unseen time. Focus outlines use copper; enlargement contains keyboard focus and closes with Escape. Loading errors retain a captured frame and expose retry guidance. If Canvas is unavailable, show an actual captured image.

Installation prominently presents “Install with one prompt,” a copy action, and copy → paste → connect/verify. The canonical prompt comes unchanged from the committed README. Prerequisites and explicit runtime startup remain clear; detailed setup stays in a disclosure and repository documentation.

## Review requirements

Review desktop, short laptop, and phones from 320px, including readable copy, relevance, contrast, keyboard access, reduced motion, DPR 1/2, asset failures, agent switching, history, and enlargement. Compare native reconstruction against independent captured pixels. Do not claim fresh capture or filter benchmarks when Docker is unavailable. Impeccable's React/Canvas adapter is unsupported; the user approved manual browser review. No automated visual receipt is asserted.

## Visual corrections — 2026-10-16

The browser proof uses a clearly labeled excerpt of the original capture, linked to the unchanged full image. Browser evidence remains actual pixels; no native interface is drawn by the website. The filter specimen is characterized input passed through the registered Hercules Nikto filter, with a regression requiring the finding and incomplete-scan warning to survive. It is not a live benchmark and carries no percentage claim.

Lower-section styles live in showcase.css. Remove superseded overrides rather than adding another layer. Mobile agent names and versions stack to prevent grid overflow. Enlargement uses its side insets with automatic width, preserving source geometry. Icon imports use the library’s individual public entrypoints, and Tailwind scans source files rather than recording archives.

## Illustration detail

Software diagrams share a graphite surface, copper routes, restrained one-pixel rules and consistent symbol frames. The Hercules process and Docker boundary have structural connection ports. On phones, the Docker route turns vertically and meets the container at the actual column center; it does not use a rotated horizontal fragment. Network branches share equal service rows so every route meets its endpoint center. Challenge symbols use a continuous three-stage route, with readable labels and the verified original flag. Native recording pixels and browser captures are unaffected.

## Capability gallery — 2026-10-17

Four separate demonstrations use an asymmetric grid: the real Juice Shop recording leads beside recon and background-job stories; an independent-workspace comparison spans the next row. Below 1040px the browser occupies a full row; below 760px all demonstrations stack. Small-phone diagrams turn into vertical lists rather than shrinking their labels. Keep Archivo headings, IBM Plex body/mono, graphite surfaces and copper connections.

The browser is actual CloakBrowser footage driven by Hercules in a private local Docker lab. It demonstrates the verified Login Admin and Score Board training challenges (2 of 186), not a complete Juice Shop assessment. The delivery loop is an edited highlight: it omits idle gaps and the payload entry while retaining original browser pixels. Keep its 1280×600 proportions, 2.5× delivery speed, captured poster and report. Pause the loop automatically when hidden or offscreen; reduced motion and video failure show the real completed capture. Do not add generated browser frames or claim guaranteed bot-detection bypass. Asset hashes and capture facts live beside the static assets and in CAPTURE.md.


## Architecture revision — 2026-10-19

The user rejected the prior scene despite its earlier subjective review score. That score is not evidence for this revision. This revision replaces generic categories and shell outlines with named capabilities, a complete runtime transition, a concise two-route circuit, and sequential workspace labels. Preserve raw recordings and public MCP APIs.

Review desktop, short laptop, tablet and 320/390px phones; exercise eleven feature explanations, keyboard focus/Escape, stable details, reduced motion, offscreen suspension and a full replacement loop. Browser iterations corrected pointer target movement, a phone inspector covering tall selections, and a runtime that could retain an invisible transform after reduced-motion changes. Runtime teardown explicitly clears animation styles; port positions use layout coordinates so resizing midtransition cannot strand connectors. Final independent review and unavailable checks are recorded separately from automated regressions.

Final independent review inspected actual browser renders and interactions at 1440×1000, 1280×720, 768×1024, 390×844 and 320×720. Its subjective rubric was 98/100: composition 24/25, craft 19/20, architectural clarity 20/20, motion 15/15, responsiveness 10/10, accessibility/theme 10/10. The remaining aesthetic deductions were uniform capability-cell weight and deliberately quiet metadata. No blocking functional or accuracy issues were found.

Verified: completed-to-fresh runtime stages, complete-unit replacement, resize recovery, reduced-motion restoration, eleven explanations, pointer selection, keyboard focus/Escape, selected cards clear of the inspector, 44px targets and no horizontal overflow or console errors. Screenshots were emitted by the browser tool; no saved files or automated visual receipts are claimed. Genuine 200% browser zoom, final DPR 2 rendering and screen-reader speech were unavailable; hidden-tab behavior was not independently verified. The full 41-test website suite passed, including native pixel reconstruction and background regressions; targeted component checks and TypeScript were rerun after the final scene changes.
