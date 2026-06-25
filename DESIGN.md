---
name: Morning Paper
description: A private pressroom that turns owned sources and taste into a finite daily paper.
colors:
  ink: "#1a1612"
  paper: "#ffffff"
  muted: "#6b6258"
  rule: "#1a1612"
  proof-red: "#a4231b"
  proof-wash: "#fdf3e7"
  card-paper: "#faf6ef"
  card-paper-soft: "#fcf9f4"
  track: "#e7dfd2"
  signal-blue: "#2b5d8c"
  passed-green: "#1e6b40"
typography:
  display:
    fontFamily: "MP Serif, Palatino, Georgia, serif"
    fontSize: "30pt"
    fontWeight: 700
    lineHeight: 1
    letterSpacing: "0.01em"
  headline:
    fontFamily: "MP Serif, Palatino, Georgia, serif"
    fontSize: "23pt"
    fontWeight: 700
    lineHeight: 1.15
    letterSpacing: "-0.01em"
  title:
    fontFamily: "MP Sans, Helvetica Neue, Helvetica, Arial, sans-serif"
    fontSize: "11pt"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "0.02em"
  body:
    fontFamily: "MP Serif, Palatino, Georgia, serif"
    fontSize: "10.5pt"
    fontWeight: 400
    lineHeight: 1.55
  label:
    fontFamily: "MP Sans, Helvetica Neue, Helvetica, Arial, sans-serif"
    fontSize: "7.5pt"
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: "0.12em"
  code:
    fontFamily: "Courier Prime, Courier New, Courier, monospace"
    fontSize: "8.5pt"
    fontWeight: 400
    lineHeight: 1.45
spacing:
  hairline: "0.5pt"
  rule: "2pt"
  page-margin-top: "0.8in"
  page-margin-side: "0.9in"
  paragraph-gap: "0.11in"
  section-gap: "0.2in"
  component-pad-sm: "0.06in"
  component-pad-md: "0.1in"
rounded:
  none: "0"
  tight: "2px"
components:
  proof-flag:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.proof-red}"
    typography: "{typography.label}"
    rounded: "{rounded.none}"
    padding: "0.5pt 3pt"
  paper-card:
    backgroundColor: "{colors.card-paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "0.09in 0.12in"
  source-note:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.muted}"
    typography: "{typography.label}"
    rounded: "{rounded.none}"
    padding: "0.07in 0.1in"
---

# Design System: Morning Paper

## 1. Overview

**Creative North Star: "The Private Pressroom"**

Morning Paper should feel like a serious personal machine for reading: tactile,
intelligent, independent. The system sits between algorithmic and analog. It
uses agents and source files to build a reader-owned algorithm, then lands the
result as a finite edition that can be read, marked up, and improved tomorrow.

The visual world borrows from proof sheets, old Mac software, small-run zines,
local files, editorial tools, and slow creative technology. Monologue by Every,
Sublime, Cosmos, Are.na, print rooms, and serious publications are useful
references. Vercel-style developer polish, Factory AI-style agent branding,
generic AI dashboards, cutesy roleplay, fake newspaper nostalgia, and beige
productivity apps are not.

The system should be concise, functional, and a little romantic about print.
Newsroom language is useful when it makes roles and proof clearer: desk, beat,
edition, final editor, pressroom, ledger. Plain language wins when the metaphor
gets in the way.

**Key Characteristics:**

- Print-first, with the PDF as the proof.
- Source-aware, finite, and skeptical of single-source truth.
- Nostalgic through utility, not decoration.
- Visual metaphors backed by durable newsroom files.
- Calm enough to read, distinct enough to remember.

## 2. Colors

The palette is black-ink-first with sparse proof and signal colors. Color
supports editorial state; it does not decorate the paper.

### Primary

- **Press Ink** (`#1a1612`): the main reading color, masthead rule, strong
  separators, and most high-confidence type.
- **Proof Red** (`#a4231b`): alerts, proof flags, action-required states, and
  genuine editorial friction. Use rarely so it keeps authority.

### Secondary

- **Signal Blue** (`#2b5d8c`): links, charts, source signals, and
  trust/skepticism surfaces where blue means evidence, not brand decoration.
- **Passed Green** (`#1e6b40`): reserved for genuinely positive state,
  completed proof, or successful delivery.

### Neutral

- **Paper** (`#ffffff`): the print surface.
- **Newsprint Muted** (`#6b6258`): secondary labels, folios, running headers,
  and source notes.
- **Card Paper** (`#faf6ef`): the warm inset for move boxes, proof slips, and
  rare highlighted blocks.
- **Soft Card Paper** (`#fcf9f4`): quieter inset surfaces.
- **Track Line** (`#e7dfd2`): hairlines, dotted writing areas, table dividers,
  and low-emphasis borders.
- **Proof Wash** (`#fdf3e7`): alert background only when the text itself cannot
  carry the warning.

### Named Rules

**The Ink First Rule.** Start with ink, rule, weight, and position. Add color
only when it clarifies status, source, or proof.

**The No Feed Chrome Rule.** Never import social-platform color systems into
the paper. X, RSS, GitHub, and inbox material become Morning Paper material.

## 3. Typography

**Display Font:** MP Serif, with Palatino and Georgia fallbacks.  
**Body Font:** MP Serif, with Palatino and Georgia fallbacks.  
**Label Font:** MP Sans, with Helvetica Neue and Arial fallbacks.  
**Code Font:** Courier Prime, with Courier fallbacks.

**Character:** The pairing is newspaper-readable but not faux antique. MP Serif
does the quiet reading work. MP Sans handles proof labels, running furniture,
and operational clarity. Courier Prime is only for code, logs, and literal
machine output.

### Hierarchy

- **Display** (700, 30pt, 1 line-height): masthead and only the largest brand
  moments.
- **Headline** (700, 23pt, 1.15 line-height): full-read and major section
  titles.
- **Title** (700, 11pt, 1.2 line-height): operational section headings and
  compact proof surfaces.
- **Body** (400, 10.5pt, 1.55 line-height): edition reading text. Keep line
  length calm and finite.
- **Label** (700, 7.5pt, 0.12em letter-spacing): short labels, datelines,
  source notes, and proof marks. Do not use label styling as repeated
  decorative eyebrows.
- **Code** (400, 8.5pt, 1.45 line-height): fenced code, logs, and commands
  only.

### Named Rules

**The No Costume Mono Rule.** Monospace appears when the content is literally a
command, code block, or log. It is not the brand voice.

**The Label Restraint Rule.** Labels are functional proof marks. Repeated tiny
uppercase headings are forbidden unless the page is a true ledger or proof
surface.

## 4. Elevation

Morning Paper is flat by default. Depth comes from page geometry, rules,
insets, source hierarchy, and proof marks rather than shadows. The printed
edition should survive home printers, PDF preview, and monochrome output.

### Shadow Vocabulary

No default shadow vocabulary. If a future web surface needs elevation, use it
as interaction feedback only, and keep it tight enough to avoid soft SaaS card
glow.

### Named Rules

**The Flat Proof Rule.** A proof surface earns trust through hierarchy, source
notes, and status, not floating cards.

## 5. Components

### Proof Flags

- **Shape:** square-corner outlined label (`0` radius).
- **Color:** proof red for warning, muted ink for informational state, passed
  green only when completion is real.
- **Use:** review notes, source warnings, final-editor status, and explicit
  proof states.

### Paper Cards

- **Shape:** square-corner inset block (`0` radius).
- **Background:** Card Paper (`#faf6ef`) or Soft Card Paper (`#fcf9f4`).
- **Border:** top rule or thin full border, never a decorative side stripe.
- **Use:** move boxes, proof slips, source-health notes, and routed material
  that needs to stand apart from reading prose.

### Source Notes

- **Style:** muted label text with thin rule or dashed border.
- **Use:** source health, extraction limits, remote tool notes, and "not
  configured" states.
- **Rule:** source notes must be honest and short. They do not replace the
  actual source material.

### Tweet / Social Cards

- **Style:** tweet-first, variable-height, paper-native cards.
- **Content:** handle, date, full hydrated text when it fits, quiet engagement
  tokens, and small context tags.
- **Rule:** do not translate every post into agent-written claim/context copy.
  Selection is the editorial act.

### Assignment Board Cards

- **Style:** compact candidate cards for a future digital or CLI-rich surface.
- **Content:** source, freshness, estimated pages, route, reason, and proof
  status.
- **Rule:** cards must change the editorial decision. If they only decorate the
  process, cut them.

## 6. Do's and Don'ts

### Do:

- **Do** make the rendered paper or proof artifact the center of every brand
  and product surface.
- **Do** use newsroom language when it clarifies a real role, file, source
  state, or proof step.
- **Do** keep color sparse, semantic, and monochrome-safe.
- **Do** let old Mac software, small-run zines, Monologue, Sublime, Cosmos, and
  Are.na inform the atmosphere without copying their surfaces.
- **Do** show source diversity, missing perspectives, prior mentions, and
  extraction limits when trust is the point.
- **Do** use actual rendered pages, proof slips, ledgers, source desks, and
  assignment boards as imagery before invented decoration.

### Don't:

- **Don't** make this a generic AI dashboard.
- **Don't** default to Vercel-style developer polish or Factory AI-style agent
  machinery.
- **Don't** create cutesy agent roleplay unless the user explicitly asks for an
  optional experimental surface.
- **Don't** use fake newspaper nostalgia: distressed paper, fake ink smudges,
  costume mastheads, or theatrical newsroom copy.
- **Don't** build another beige productivity app.
- **Don't** turn Morning Paper into an infinite feed reader, social screenshot
  wall, or source scraper marketplace.
- **Don't** use gradients, glassmorphism, ghost-card shadows, oversized rounded
  cards, or repeated decorative eyebrows.
