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
  search-field:
    textColor: "{colors.silver}"
    rounded: "{rounded.sharp}"
    padding: "12px 16px"
    height: "52px"
    width: "510px"
  agent-tab:
    textColor: "{colors.muted-silver}"
    rounded: "{rounded.sharp}"
    padding: "10px 18px"
    height: "48px"
  agent-tab-selected:
    backgroundColor: "{colors.copper}"
    textColor: "#151719"
  evidence-tab:
    textColor: "{colors.muted-silver}"
    padding: "10px 14px"
    height: "48px"
  evidence-tab-selected:
    textColor: "{colors.copper-hover}"
  evidence-rail:
    backgroundColor: "{colors.evidence-surface}"
    textColor: "{colors.silver}"
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

# Design System: Hercules

## Overview

**Creative North Star: "Graphite/Copper Editorial World"**

Hercules pairs a dark technical workspace with clear editorial typography. Graphite reading surfaces, copper actions and thin rules make dense evidence understandable without disguising its provenance. The lion and Hercules wordmark remain the identity anchor.

The procedural Canvas smoke, hatch sampling, shimmer and halftone recipe is a binding material of this world. Keep the source renderer, adaptive frame rates, worker fallback, visibility pauses and reduced-motion still rendering. Dimensional graphite/copper illustrations support explanations; they are identified as illustrations. Actual native client interfaces retain their recorded geometry and ANSI colors.

**Key Characteristics:**

- Graphite surfaces, silver reading text and purposeful copper emphasis.
- Self-hosted Archivo display type with IBM Plex Sans and IBM Plex Mono.
- Sharp framing, restrained rules and generous separation around dense content.
- Native evidence, procedural atmosphere and clearly labeled supporting illustrations.
- Keyboard access, readable transcripts and complete static or reduced-motion presentations.

## Colors

The palette is warm copper against cool graphite, with silver carrying the reading hierarchy. The frontmatter owns canonical color values.

### Primary

- **Copper:** primary installation actions, selected agent tabs, emphasis and diagram connectors.
- **Copper Hover:** interactive link color, hover feedback and visible focus.
- **Copper Code:** recurring tool names, measured output emphasis and selected architecture stages.

### Neutral

- **Graphite:** the page ground and procedural-background scrim.
- **Raised Graphite:** subdued interactive surface feedback.
- **Silver:** primary reading text and identity.
- **Muted Silver:** supporting copy and inactive controls.
- **Rule:** translucent silver dividers separating evidence, controls and sections.
- **Action Ink:** dark text on filled copper actions.
- **Evidence Surface:** an almost opaque reading enclosure for the synchronized rail.

Section surfaces use nearby solid graphite tones: architecture is slightly deeper than setup, and expanded tool chains use a raised graphite field. These remain contextual material variations rather than additional accent families.

### Named Rules

**The Copper Has a Job Rule.** Copper identifies an action, selected state, tool or explanatory connection; do not distribute it as unrelated decoration.

**The Native Color Rule.** Recorded client colors belong to their capture. Surrounding controls use the house palette without recoloring terminal evidence.

## Typography

**Display Font:** Archivo with a sans-serif fallback, self-hosted and condensed through the observed font stretch (87.5%).
**Body Font:** IBM Plex Sans with a sans-serif fallback, self-hosted.
**Label/Mono Font:** IBM Plex Mono with a monospace fallback, self-hosted.

**Character:** Archivo gives wide, balanced headings a firm editorial voice. IBM Plex Sans keeps the surrounding interface readable; Mono identifies code, tool calls, filenames and measured detail.

### Hierarchy

- **Display:** the frontmatter display role governs the large opening statement. Narrow screens use the observed responsive size (`clamp(36px, 7.3vw, 56px)`).
- **Headline:** the frontmatter headline role governs chapter headings. The player introduction uses a smaller responsive heading (`clamp(30px, 2.9vw, 44px)`) with a more open line-height (1.12).
- **Title:** the frontmatter title role is the default subsection heading. Story and evidence titles can grow to the observed larger size (36px); compact architecture titles use a smaller size (23px).
- **Body:** the frontmatter body role sets the page baseline. Explanatory copy commonly uses the observed supporting range (15–17px) and line-height (1.55–1.65), with reading widths around 54–66ch.
- **Label:** use the frontmatter label role for general navigation and supporting controls. Preserve sentence case rather than adding uppercase ornamental text.
- **Code:** the frontmatter code role serves tool calls and preformatted lifecycle examples. Native replay uses its captured cell grid and independent IBM Plex Mono rendering.

### Named Rules

**The Wide Heading Rule.** Keep headings balanced with deliberate breaks and clear line-height; display tracking must remain at or above the incumbent lower bound (-0.04em).

**The Mono Means Evidence Rule.** Use Mono for code or measured detail, with Sans carrying explanations and Archivo carrying hierarchy.

## Layout

A centered container has the observed maximum width (1536px) and fluid page gutter from the frontmatter. Main chapters use the recorded desktop, tablet and mobile spacing steps. Tight control groups and evidence rows sit inside this generous section rhythm.

Use purposeful adjacent regions: a broad primary stage with a narrower evidence rail, paired headline and explanation, or illustration beside a readable story. Desktop player proportions are 3:1 with a minimum rail width (270px) and gap (24px). At the intermediate breakpoint (1100px), the player becomes 2.4:1, the rail minimum shrinks (245px), and the gap tightens (18px). At the narrow breakpoint (760px), regions stack, agent controls form two columns, the rail expands to content height, and catalog items become two columns.

Chapter headings use a 1.1:1 split and gap (60px); their gap tightens on tablets and their content stacks on phones. Chains use four columns for sequential evidence, then one column on phones. Keep the native recording's grid intact and scale the whole captured geometry. Enlargement provides a readable alternative to a small scaled preview.

The current showcase follows Hero → native player → tool chains → architecture and isolation → filters and evidence → installation. Its selected editorial composition belongs to `.impeccable/surface-brief.md`; future surfaces should inherit the spatial grammar rather than duplicate this page order.

### Named Rules

**The Group Before Gap Rule.** Keep related controls and facts close, then give the next section room. Do not flatten the chapter rhythm into equally spaced small cards.

**The Fixed Grid Rule.** Native terminal artwork scales as a whole; do not reflow its captured cells to fit a layout.

## Elevation & Depth

Depth primarily comes from solid tonal layering, sharp rules and dimensional supporting illustrations. Reading surfaces stay quiet over the procedural Canvas field, whose final observed opacity is restrained (0.25). The directional background scrim is native to this world and remains behind content.

The enlarged recording uses a diffuse overlay shadow (`0 24px 80px rgba(0,0,0,.75)`). The selected evidence tab uses an inset copper underline (`inset 0 -2px var(--copper)`), a state indicator rather than lifted depth.

### Named Rules

**The Quiet Surface Rule.** Use graphite tone and thin rules for ordinary grouping. Reserve the observed diffuse shadow for the enlarged recording overlay.

## Shapes

Page frames, buttons, inputs, evidence containers and diagrams use sharp corners from the frontmatter. Thin borders establish edges without pill forms or heavy decorative outlines. Icons are real inline SVG controls and explanatory symbols, with copper identifying diagram connections.

The lion image and wordmark are preserved. The procedural smoke/hatch Canvas and graphite/copper illustrations supply organic and dimensional material within the otherwise precise geometry.

## Components

### Buttons

Direct, quiet actions with enough room to operate.

- **Primary:** filled Copper with Action Ink; the frontmatter records its padding and minimum target height. Hover uses Copper Hover.
- **Secondary:** transparent with a Rule border; hover shifts the border toward Copper.
- **Focus:** Copper Hover outline (2px) offset from the control (4px).
- **Responsive:** narrow-screen buttons use the observed tighter padding (12px 15px) and size (13px). Icon actions retain at least a 44px target.

### Cards / Containers

Evidence-first enclosures use sharp corners, near-opaque graphite and a single Rule border. The rail's desktop content inset is observed at 22px, tightening to 18px on smaller screens. Rail content scrolls within a desktop limit (440px), then expands naturally on phones. Rows use fine dividers; ordinary containers do not acquire a raised shadow.

### Inputs / Fields

The catalog search is a transparent field inside a sharp Rule frame. It uses the recorded inset and minimum height from the frontmatter, muted placeholder text and a Copper Hover caret. Focus moves to the whole search enclosure with a Copper Hover outline (2px) and offset (3px).

### Navigation

The header is a compact ruled strip (64px high). Its lion wordmark uses Archivo, while section links use muted Sans and brighten on hover. Links have at least a 44px target. The observed narrow layout hides the section link row at 760px and retains the brand and source action.

### Tabs and Stage Controls

Agent tabs are filled only when selected; inactive tabs stay muted and use Raised Graphite on hover. Evidence tabs remain quiet, marking selection with Copper Hover text and an inset copper underline. Both groups use real tab semantics with Arrow, Home and End keyboard navigation.

Architecture stage controls are sharp bordered buttons. Selected stages use a warm graphite fill, Copper border and Copper Code text. Preserve `aria-pressed` state.

### Tool Chains

Expandable ruled rows pair an Archivo title, a Sans explanation and a copper chevron. The open state brightens the title and rotates the chevron. The revealed sequence uses code names above evidence descriptions, connecting actual steps with SVG arrows; phones place the sequence vertically.

### Native Player and Evidence Rail

Keep captured native bytes, fixed cell geometry, original 1× timing, captured stills and recorded client colors. Visible surrounding controls provide pause, replay, enlargement, transcript and evidence access. Preserve an actual frame through loading and render preparation; loading or failure recovery is readable and directs visitors to Replay or the captured transcript.

Enlargement uses the observed fixed inset (24px desktop, 10px phone), a diffuse shadow, Escape dismissal and contained keyboard focus. Synchronized findings and files become available according to the capture; the report appears after evidence verification. Capture provenance is factual supporting content, not an ornamental eyebrow.

### Motion and Static Explanations

Preserve the independent procedural background and native recording clocks. The runtime ownership sequence uses scoped GSAP pinning only on suitable desktops (minimum width 1000px and height 900px), with scrub (0.7). The evidence illustration and pipeline use a separate reveal sequence on desktops (minimum width 1000px). Native playback stays independent at 1×.

Reduced motion removes smooth scrolling and shortens transitions; the background renders still, the recording presents a completed captured frame until explicitly played, and the complete architecture explanation appears in ordinary document flow. A fixed 44px motion control pauses site motion. Hidden or offscreen recording playback pauses without consuming unseen time.

## Do's and Don'ts

### Do:

- **Do** preserve graphite/copper, the lion wordmark and the self-hosted Archivo / IBM Plex pairing.
- **Do** preserve the source Canvas smoke, hatch and halftone material, including worker fallback and reduced-motion still rendering.
- **Do** use thin rules and solid graphite reading surfaces to make evidence and controls legible.
- **Do** keep native recordings at original timing and fixed geometry, with captured stills and readable transcripts.
- **Do** provide at least 44px interactive targets and visible focus.
- **Do** retain every explanatory fact on phones and under reduced motion.
- **Do** label supporting illustrations and scripted model decisions explicitly.

### Don't:

- **Don't** replace the procedural background with generated raster artwork.
- **Don't** recolor, fabricate or reflow the native client interface.
- **Don't** add decorative status dots, generic glass cards or invented metrics.
- **Don't** use ornamental kickers to manufacture hierarchy.
- **Don't** apply the overlay shadow to ordinary reading surfaces.
- **Don't** tighten display tracking beyond the confirmed lower bound (-0.04em).
