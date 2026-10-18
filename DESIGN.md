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

The architecture is one lightly dimensional HTML/SVG software scene. An agent connects through Hercules to a bounded Kali Docker runtime containing browser control and security tools. Actual element bounds determine the SVG routes: request, tool dispatch, workspace mount, raw output, and concise return response. Connections meet their endpoints and remeasure on resize; labels remain readable HTML or SVG text.

Workspace A is the current mounted workspace; Workspace B is retained on the host. A connection has one active workspace. Creating a fresh session stops that connection's current runtime; separate connections can own independent runtimes. Do not imply one connection has multiple simultaneously active containers.

Six real buttons expose Hercules, Docker, browser control, parallel execution, workspaces, and filtering. Hover and keyboard focus preview a compact explanation, click/tap pins it, Escape or the close action clears it. Reserve explanation space to prevent layout shifts. Remove lifecycle selectors, telemetry consoles, invented metrics, and unverified bot-evasion claims. Authentic Docker artwork and the existing lion remain unchanged.

On desktop the scene reads across; at 960px and below, agent/Hercules sit above the full-width Docker enclosure, followed by workspaces and filtering. Depth comes from shallow edges and restrained shadows, not tilted text or a physical appliance. The scene uses existing GSAP and Phosphor dependencies without WebGL or generated raster artwork.

## Native player

One Canvas2D player, four agent tabs, and a compact investigation summary beside it on desktop and below it on phones. The prompt contains the objective once. The compact summary follows actual completed-call timestamps: current action, up to two observations, available browser evidence, and the verified report action. No findings or report appear before their underlying artifacts are available.

Play captured pixels at 2.5×. Switching agents restarts the same case and preserves explicit pause. Shuffled cycling retains the selected agent. Hold six recorded seconds at completion (2.4 wall seconds). Decode the opening before switching, crossfade for 200ms, and retain the last valid frame during loading, buffering, or failures. Reduced motion starts with a captured completed frame and swaps directly.

Load five source seconds at startup and maintain twelve ahead, with a shared verified compressed cache capped at 32MiB and decoded bitmaps capped at 64MiB. Native output timing remains separate from GSAP motion. A verified complete Hermes entrance frame avoids naturally scrolled startup artwork; no native pixels are replaced.

The only player buttons are pause/play, replay, and enlargement, each at least 44px. Enlargement fits and centers the existing complete frame; it does not choose a different geometry or reload the recording. Preserve proportions and never reflow terminal artwork.

Recorded-history navigation pauses playback and reviews previously presented screens. Desktop wheel/trackpad and Arrow/Page/Home/End keys provide access. Phone swipes scroll the page while playing; pause first to review history. Play resumes from the selected point. A horizontal history range sits below the image so it does not consume native-frame width. Navigation remains keyboard accessible, and page scrolling is released at history boundaries. Phones give the frame the full available page width; the complete transcript is available in a readable disclosure below it.

## Motion and accessibility

Use an unpinned software scene with a twelve-second explanatory loop: explicit startup, agent coordination, overlapping checks, filtered response, and on-request replacement with a fresh runtime. It is an illustration, not live telemetry or Kubernetes orchestration. A departing shell and arriving shell depict replacement while labels stay legible. Pause the loop when the section is offscreen or the document is hidden; reduced motion shows every fact without playing the cycle. Native terminal timing is independent.

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


## Architecture review — 2026-10-19

Validate six feature interactions, focus visibility, pinned details, Escape, resize geometry, reduced motion, and offscreen/hidden suspension. Review the rendered scene at 1440px, 1280px short laptops, 768px tablets, and 320/390px phones, including genuine browser zoom. An independent reviewer scores composition (25), craft (20), clarity/accuracy (20), motion (15), responsiveness (10), and accessibility/theme (10). Scores are subjective assessments supported by browser screenshots and concrete findings, never a substituted automated visual proof.

Independent browser review completed at desktop 1440px, laptop 1280×720, tablet 768px, and phones 390/320px. Iterations corrected disconnected routes, a stacked connector crossing Hercules text, narrow-phone detail height changes, and visible-scene animation suspension. The final subjective assessment was 98/100: composition 24/25, craft 19/20, clarity 20/20, motion 15/15, responsiveness 10/10, accessibility/theme 10/10. Incoming replacement carries a transient “Fresh runtime” label. Explanations reserve 235px at 390px and 280px at 320px, with no observed layout shift across the six features.

Reduced motion and actual offscreen pausing were verified. Genuine 200% browser zoom and hidden-tab simulation could not be exercised through the review browser and are not claimed as passed checks. Screenshot evidence was emitted by CUA during review; no saved screenshot files or automated visual receipts are asserted.
