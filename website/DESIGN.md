---
name: Hercules
description: A graphite and copper editorial system for an agent-owned Kali workspace.
colors:
  copper: "#ff6a2b"
  copper-hover: "#ff8652"
  copper-code: "#ffb48a"
  graphite: "#0e1014"
  raised-graphite: "#15181e"
  silver: "#f4efe9"
  muted-silver: "#cec5bc"
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

Hercules is a host-side STDIO MCP server. Compatible agents, workers, and custom integrations can connect on Windows, macOS, and Linux. Connecting does not start the runtime. A session explicitly starts its owned Kali container; independent sessions have separate runtime ownership, working files, and allocated ports. Cleanup targets the owned runtime. Operators control networking and permissions; Docker is not a complete security boundary.

Tool-specific filters remove known scanner noise while preserving important findings and diagnostics. Response-size bounding is a separate mechanism. Saved artifacts support follow-up but are not presented as a distinctive product feature. No numerical filter savings are claimed without a validated measurement. Reports and screenshots shown on the page are outcomes of the real local-lab recordings.

## Page sequence

Hero and native agent player → catalog summary → interactive architecture illustration → single-prompt installation. The architecture scene integrates Docker, browser control, concurrent tools, workspace management, and response filtering.

The hero and agent introduction are preserved. The technical catalog lives in GitHub documentation. Main-page explanations avoid raw MCP names, JSON payloads, hashes, byte counts, and recording mechanics.

## Visual language

Sharp corners, fine rules, generous chapter spacing, and readable silver text. Use copper to indicate actions, active stages, and meaningful connections. Keep labels opaque during animation. Do not introduce glass panels, decorative status dots, unverified counters, or a new type system.

One focused capability example is shown at a time in a four-tab walkthrough: network mapping, website verification, layered challenge solving, and a readable report. Use functional diagrams and real browser/report content. Illustrations must describe software relationships, not substitute physical machinery for Docker. The rejected chassis, blank paper, and generated architecture overview are not shown.

The architecture is a capability-first HTML/SVG software illustration. A horizontal agent/filter/Hercules chain feeds a dominant Kali Docker enclosure on the same centerline. Six distinct software vignettes pair recognizable tools with plain-language purposes: CloakBrowser; Amass/DNS/Nmap; ffuf/Nuclei/SQLMap; Binwalk/ExifTool/Steghide; SearchSploit/Metasploit; Hydra/John. Shell and workspace tools connect the steps. Selected bundle availability is explicit; the scene does not promise every tool is installed.

The user-directed topology is one horizontal line: Agent ↔ output filter ↔ Hercules ↔ Docker. Three short straight bidirectional links share a common centerline; there are no downward branches or return rails. The filter is a logical output-processing stage on the MCP channel, not a separate installed service. Only returned tool output is filtered.

The Docker enclosure contains six capability illustrations. Parallel lanes show overlapping independent checks. The complete runtime departs and a new numbered runtime arrives; its mounted workspace becomes current while the previous numbered workspace remains inspectable. This is an illustrative, explicitly requested session transition, not Kubernetes reconciliation. A connection has one active workspace; separate clients may own independent runtimes.

Eleven real buttons expose capabilities and infrastructure. Hover and keyboard focus preview details, click/tap pins an explanation, and Escape or close clears it. Inspection pauses the loop, and the runtime is inert during its short replacement transition. Selected and keyboard explanations stick inside the scene at the viewport bottom; alignment leaves the selected card above them. Pointer focus never scrolls before the click completes. Detail space stays reserved. Keep lifecycle selectors, telemetry consoles, invented savings, and bot-evasion guarantees out of the scene. Authentic Docker artwork and the existing lion remain unchanged.

The four-stage chain never stacks. On narrow screens a focusable, horizontally pannable diagram preserves its geometry with a visible navigation hint and native scrollbar. The page itself does not overflow. Selection brings the target into horizontal view before aligning it above the inspector. Workspace information sits below the three host-side stages inside the same pannable canvas. DOM and visual order agree. Use shallow edges, one-pixel rules and restrained shadows; no WebGL, raster illustration, additional dependencies or altered global typography.

## Native player

Loading refinements retain this presentation: a compact, content-addressed JSON
catalog supplies playback fields only; full provenance stays in the original
manifest. Verify the selected poster before fetching its pixel index. Hermes'
verified entrance is included in the catalog. Do not warm unused agents'
indexes or posters. Reserve the captured ratio with container queries before
JavaScript measures the player, then use the selected capture's exact ratio.
Autoplay still waits for visibility and preserves explicit pause.

The architecture module loads near the viewport with its heading and space
reserved. Decorative workers leave headroom after expensive frames and park
their timer while hidden/reduced; the procedural recipe and captured pixels
are unchanged. Shared cards use the same lion, graphite/copper palette and
Archivo headline at 1200×630, with readable crop-safe type and no tiny counters.

One Canvas2D player, four agent tabs, and one Scenarios picker beside it on desktop and below it on phones. The picker replaces the workflow summary; the former horizontal scenario row is removed. Choosing a scenario restarts that investigation while retaining the selected agent. Keep native playback, history, pause, replay and enlargement unchanged. The prompt contains the objective once. The disclosure/link strip beneath the player is removed; capture provenance remains in the recording documentation.

Play captured pixels at 2.5×. Switching agents restarts the same case and preserves explicit pause. Shuffled cycling retains the selected agent. Hold six recorded seconds at completion (2.4 wall seconds). Decode the opening before switching, crossfade for 200ms, and retain the last valid frame during loading, buffering, or failures. Reduced motion starts with a captured completed frame and swaps directly.

Load five source seconds at startup and maintain twelve ahead, with a shared verified compressed cache capped at 32MiB and decoded bitmaps capped at 64MiB. Native output timing remains separate from GSAP motion. A verified complete Hermes entrance frame avoids naturally scrolled startup artwork; no native pixels are replaced.

The only player buttons are pause/play, replay, and enlargement, each at least 44px. Enlargement fits and centers the existing complete frame; it does not choose a different geometry or reload the recording. Preserve proportions and never reflow terminal artwork.

Recorded-history navigation pauses playback and reviews previously presented screens. Desktop wheel/trackpad and Arrow/Page/Home/End keys provide access. Phone swipes scroll the page while playing; pause first to review history. Play resumes from the selected point. A horizontal history range sits below the image so it does not consume native-frame width. Navigation remains keyboard accessible, and page scrolling is released at history boundaries. Phones give the frame the full available page width; raw transcripts remain in the recording assets and repository documentation. The session banner and transcript disclosure are omitted from the player at the user’s request.

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

Software diagrams share a graphite surface, copper routes, restrained one-pixel rules and consistent symbol frames. The Hercules process and Docker boundary have structural connection ports. The architecture keeps all four connection stages horizontal, including on phones; its bounded canvas pans independently of the page. Network branches share equal service rows so every route meets its endpoint center. Challenge symbols use a continuous three-stage route, with readable labels and the verified original flag. Native recording pixels and browser captures are unaffected.

## Capability gallery — 2026-10-17

Four separate demonstrations use an asymmetric grid: the real Juice Shop recording leads beside recon and background-job stories; an independent-workspace comparison spans the next row. Below 1040px the browser occupies a full row; below 760px all demonstrations stack. Small-phone diagrams turn into vertical lists rather than shrinking their labels. Keep Archivo headings, IBM Plex body/mono, graphite surfaces and copper connections.

The browser is actual CloakBrowser footage driven by Hercules in a private local Docker lab. It demonstrates the verified Login Admin and Score Board training challenges (2 of 186), not a complete Juice Shop assessment. The delivery loop is an edited highlight: it omits idle gaps and the payload entry while retaining original browser pixels. Keep its 1280×600 proportions, 2.5× delivery speed, captured poster and report. Pause the loop automatically when hidden or offscreen; reduced motion and video failure show the real completed capture. Do not add generated browser frames or claim guaranteed bot-detection bypass. Asset hashes and capture facts live beside the static assets and in CAPTURE.md.


## Architecture revision — 2026-10-19

The user rejected the prior scene despite its earlier subjective review score. That score is not evidence for this revision. This revision replaces generic categories and shell outlines with named capabilities, a complete runtime transition, a concise two-route circuit, and sequential workspace labels. Preserve raw recordings and public MCP APIs.

Review desktop, short laptop, tablet and 320/390px phones; exercise eleven feature explanations, keyboard focus/Escape, stable details, reduced motion, offscreen suspension and a full replacement loop. Browser iterations corrected pointer target movement, a phone inspector covering tall selections, and a runtime that could retain an invisible transform after reduced-motion changes. Runtime teardown explicitly clears animation styles; port positions use layout coordinates so resizing midtransition cannot strand connectors. Final independent review and unavailable checks are recorded separately from automated regressions.

The previous composition’s independent review inspected actual browser renders and interactions at 1440×1000, 1280×720, 768×1024, 390×844 and 320×720. Its subjective rubric was 98/100: composition 24/25, craft 19/20, architectural clarity 20/20, motion 15/15, responsiveness 10/10, accessibility/theme 10/10. The remaining aesthetic deductions were uniform capability-cell weight and deliberately quiet metadata. No blocking functional or accuracy issues were found.

Verified: completed-to-fresh runtime stages, complete-unit replacement, resize recovery, reduced-motion restoration, eleven explanations, pointer selection, keyboard focus/Escape, selected cards clear of the inspector, 44px targets and no horizontal overflow or console errors. Screenshots were emitted by the browser tool; no saved files or automated visual receipts are claimed. Genuine 200% browser zoom, final DPR 2 rendering and screen-reader speech were unavailable; hidden-tab behavior was not independently verified. The full 41-test website suite passed, including native pixel reconstruction and background regressions; targeted component checks and TypeScript were rerun after the final scene changes.

## Linear connection correction

The latest user instruction explicitly requires left-to-right flow, not an up/down layout. All four stages now share one centerline at every viewport size. The earlier sidebar and three-node/downward-Docker compositions are superseded. Preserve the line on phones with horizontal panning rather than vertical reflow, while keeping page scrolling and keyboard access available.

The source-order regression requires agent → filter → Hercules → Docker, an output-only filter label and a named horizontal diagram region. The 98/100 and 96/100 review records above describe earlier compositions; no score is transferred to this linear version. Raw recordings, public APIs and the installation contract remain unchanged.

## Linear layout spacing refinement

The Docker enclosure spans two grid rows. The three host-side stages share the upper row, with managed workspaces directly beneath them. This fills the former empty lower-left area without adding a downward connection. The Docker docking port aligns with the host-stage centerline independently of the enclosure height. Capability cells are compact while their labels retain readable type. On phones, the focusable explanation panel has a bounded viewport-relative height and scrolls long descriptions; selecting another feature resets its internal scroll. No prior subjective score applies to this refinement.

The independent review inspected current desktop, short-laptop, tablet and 320/390px browser renders and interactions. Its final design judgment was 95/100 (23 composition, 18 craft, 20 clarity, 14 motion, 10 responsive, 10 accessibility), with no functional or accuracy blocker; it was satisfied with this spacing correction. Remaining aesthetic opportunities are uniform tool-subtitle heights and a quieter replacement fade. This is not the previously requested 98 score. Genuine zoom, DPR 2, screen-reader speech and hidden-tab behavior were not independently checked. Final phone refinements constrain the workspace card to a readable width inside the horizontal canvas.

## Request / response clarification — current architecture

This revision supersedes the shared bidirectional centerline and blue-gray schematic surfaces above. The four stages remain left-to-right. Separate directional rails show requests leaving the agent through Hercules for Docker, and results returning through Hercules and its logical noise-filter stage. Distinct input/output ports prevent ambiguous T junctions; the filter is part of Hercules output handling, not an extra installed service. A dashed mount relation connects the Docker runtime to explicitly labeled host storage. Current and previous sessions replace unexplained runtime/workspace numbers. All three host-stage cards share aligned top/bottom edges.

Use the page’s existing graphite, orange, cream text, Archivo and IBM Plex tokens. Eight compact capability headers reveal one tool list in a reserved preview on hover, keyboard focus or touch selection. Stronger resting borders and visible information symbols invite interaction. Known findings/diagnostics are distinguished from noise, while large responses retain separately disclosed size limits; never promise no truncation. Secondary labels use the established higher-contrast ink variables. The selected detail remains keyboard accessible and stable, and reduced motion keeps all routes and categories visible. Native recordings and public APIs are unchanged.

Final browser correction: host stages stretch to match the runtime height, so their top and bottom baselines align and the return rail sits only 32px below them. The runtime replacement holder has no text behind fading tool labels. The native player reserves the requested capture’s actual pixel ratio before its first decoded frame, preventing initial loading from moving the architecture beneath it. Independent desktop/320/390 review covered theme, directed routes, workspace relation, capability selection, keyboard and reduced motion; genuine zoom, DPR 2 and screen-reader speech were not checked. The mechanical detector reported three existing warnings in the session-summary/install styles outside the changed architecture block; no new architecture finding was reported.

## Compact return-channel revision — current

This revision supersedes the stretched four-stage row. The upper request row is Agent → Hercules → Docker with aligned 84px header bands and content-sized host cards. The filter sits below Hercules directly in one continuous right-to-left return route. Rounded orthogonal bends and horizontal left-facing arrowheads replace the upward taps. A separate solid neutral route labeled “Workspace mount” connects the runtime to host storage. Keep all three upper nodes horizontal on phones within the existing focusable pannable canvas.

Frame the scene with “Follow a request from your agent to Kali—and back.” Group “Output filtering,” its relationship to Hercules, removed scanner noise, the retained finding and important diagnostic in one compact body. Response-size bounds appear only in the interactive explanation; never imply filtering prevents truncation. Default details explain the complete investigation. Keep eight category headers, stable tool previews, current/previous workspace labels and existing graphite/orange/cream tokens.

The phase status is visually inside the Kali header but outside the animated runtime, so it remains readable during teardown and the empty slot. The former “Example job progress” block and its animated bars are removed. The 15-second illustrative loop is request 0–0.8, tool execution 0.8–4.2, filtered return 4.2–5.4, completed hold 5.4–7, new-session request/stopping 7–8.4, completely empty runtime 8.4–9.1, starting 9.1–10.8, ready 10.8–15. Teardown rows fade top-to-bottom 40ms apart; fresh rows arrive bottom-to-top 40ms apart with restrained container scale/opacity easing. No overlapping runtimes, Kubernetes scheduling or replacement per tool request is implied. Preserve layout dimensions, pause hidden/offscreen and during inspection, finish an underway replacement before honoring inspection pause, and show a complete static scene under reduced motion. Decorative status/motion is hidden from assistive technology; real capability controls remain accessible outside their brief inert replacement interval.

New regressions exercise the actual GSAP timeline using object targets: exact 15-second duration, full opacity-zero 0.7-second stopped interval, reversed row arrival, ready/reset state and loop restart. Pure geometry tests require one rounded return channel, bounded corner radius and no invalid coordinates. Existing component checks retain truthful copy and named controls. Root browser checks confirmed DPR 2 crisp geometry and reduced-motion restoration, plus offscreen pause/resume. Genuine browser zoom and screen-reader speech are unavailable and must not be claimed.

The final independent browser review passed at desktop, short-laptop, tablet and 320/390px phone sizes after correcting a resize-selection race. Explicit selections now remain visible through late page reflow; wheel, touch, pointer and keyboard input immediately release that alignment, avoiding scroll traps. The reviewer exercised focus/Escape, touch-sized selections, horizontal panning and reduced motion, and found no remaining blocking issue. Screenshots were emitted in the browser review; no saved screenshot files or inherited design score are asserted. Exact empty-slot timing is covered by the actual GSAP regression rather than a frame-timed browser recording. Genuine 200% browser zoom and screen-reader speech remain unverified.

The next layout pass widens the two request gutters, groups Hercules and its return filter with a quiet dashed enclosure, aligns workspace cards to the three main columns, and centers a dashed mount on the current workspace. Request and return routes now meet their visible card edges without short jogs; the return label sits alongside its upward turn. Small chevrons identify parent explanations while the eight capability controls rely on their existing hover and focus states.
