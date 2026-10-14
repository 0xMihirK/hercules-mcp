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
  phase-button:
    textColor: "{colors.muted-silver}"
    rounded: "{rounded.sharp}"
    padding: "8px 12px"
    height: "44px"
  phase-button-selected:
    backgroundColor: "#2b2522"
    textColor: "{colors.copper-code}"
---

# Hercules design system

Graphite reading surfaces, copper actions, Archivo headlines, and IBM Plex body type remain the visual foundation. The existing lion and wordmark anchor the identity. The procedural Canvas smoke/hatch/shimmer/halftone background stays unchanged. Native terminals retain their captured colors and typography.

## Product facts

Hercules is a host-side STDIO MCP server. Compatible agents, workers, and custom integrations can connect on Windows, macOS, and Linux. Connecting does not start the runtime. A session explicitly starts its owned Kali container; independent sessions have separate runtime ownership, working files, and allocated ports. Cleanup targets the owned runtime. Operators control networking, permissions, and target scope; Docker is not a complete security boundary.

Tool-specific filters remove known scanner noise while preserving important findings and diagnostics. Response-size bounding is a separate mechanism. Saved artifacts support follow-up but are not presented as a distinctive product feature. No numerical filter savings are claimed without a validated measurement. Reports and screenshots shown on the page are outcomes of the real local-lab recordings.

## Page sequence

Hero → native agent player and investigation summary → four capability examples → sandbox lifecycle → portability → output filters → single-prompt installation.

The hero and agent introduction are preserved. The technical catalog lives in GitHub documentation. Main-page explanations avoid raw MCP names, JSON payloads, hashes, byte counts, and recording mechanics.

## Visual language

Sharp corners, fine rules, generous chapter spacing, and readable silver text. Use copper to indicate actions, active stages, and meaningful connections. Keep labels opaque during animation. Do not introduce glass panels, decorative status dots, unverified counters, or a new type system.

The four capability examples form an asymmetric gallery: network mapping, website verification, layered challenge solving, and a readable report. Use functional diagrams and real browser/report content. Illustrations must describe software relationships, not substitute physical machinery for Docker. The rejected chassis, blank paper, and generated architecture overview are not shown.

The sandbox is a large HTML software-workspace scene. Its agent requests connect through Hercules to two separately owned Docker runtimes. Lifecycle controls explain connection, explicit startup, independent sessions, and cleanup. The lion uses the existing vector paths with tighter intrinsic framing; authentic Docker artwork is from Devicon v2.17.0. OS and interface glyphs use the existing Phosphor library. Labels and controls remain accessible HTML.

## Native player

One Canvas2D player, four agent tabs, and a compact investigation summary beside it on desktop and below it on phones. The summary follows actual completed-call timestamps: objective, action, discoveries, rejected leads, visual evidence, and verified report. No findings or report appear before their underlying artifacts are available.

Play captured pixels at 2.5×. Switching agents restarts the same case and preserves explicit pause. Shuffled cycling retains the selected agent. Hold six recorded seconds at completion (2.4 wall seconds). Decode the opening before switching, crossfade for 200ms, and retain the last valid frame during loading, buffering, or failures. Reduced motion starts with a captured completed frame and swaps directly.

Load five source seconds at startup and maintain twelve ahead, with a shared verified compressed cache capped at 32MiB and decoded bitmaps capped at 64MiB. Native output timing remains separate from GSAP motion. A verified complete Hermes entrance frame avoids naturally scrolled startup artwork; no native pixels are replaced.

The only player buttons are pause/play, replay, and enlargement, each at least 44px. Enlargement fits and centers the existing complete frame; it does not choose a different geometry or reload the recording. Preserve proportions and never reflow terminal artwork.

Recorded-history navigation pauses playback and reviews previously presented screens. Desktop wheel/trackpad and Arrow/Page/Home/End keys provide access. Phone swipes scroll the page while playing; pause first to review history. Play resumes from the selected point. Range navigation remains keyboard accessible, and page scrolling is released at history boundaries.

## Motion and accessibility

Use one scoped desktop sandbox pin at minimum 1024px width and 700px height. The four lifecycle stages advance with scroll; buttons also work independently. Connections, positional reveals, and noise-bar transformations explain the product. Avoid fading readable text below contrast requirements.

Phones use ordinary document flow with meaningful positional motion. Reduced motion and the site motion control preserve every fact without pinning or continuous effects. Hidden/offscreen playback pauses without consuming unseen time. Focus outlines use copper; enlargement contains keyboard focus and closes with Escape. Loading errors retain a captured frame and expose retry guidance. If Canvas is unavailable, show an actual captured image.

Installation prominently presents “Install with one prompt,” a copy action, and copy → paste → connect/verify. The canonical prompt comes unchanged from the committed README. Prerequisites and explicit runtime startup remain clear; detailed setup stays in a disclosure and repository documentation.

## Review requirements

Review desktop, short laptop, and phones from 320px, including readable copy, relevance, contrast, keyboard access, reduced motion, DPR 1/2, asset failures, agent switching, history, and enlargement. Compare native reconstruction against independent captured pixels. Do not claim fresh capture or filter benchmarks when Docker is unavailable. Impeccable's React/Canvas adapter is unsupported; the user approved manual browser review. No automated visual receipt is asserted.
