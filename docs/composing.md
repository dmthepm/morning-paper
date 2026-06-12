# Composing documents for `morning-paper render`

The render seam is the contract between *judgment* and *typesetting*: an agent
(or a human) writes plain markdown; the engine typesets it into a print-ready
PDF through a style pack and a palette. The composer never writes CSS.

```bash
morning-paper render brief.md --style brief --palette mono
morning-paper render call-card.md --style field-card --palette color
morning-paper render brief.md --output ~/Desktop/brief.pdf   # copy the PDF where you want it
morning-paper styles   # list available styles + palettes
```

`--output PATH` (also on `demo`) copies the produced PDF to PATH after the
normal dated output directory is written; a trailing slash or an existing
directory keeps the PDF's own filename.

Body type for the whole paper scales with `outputs.font_scale` in config
(0.8 compact to 1.5 large print, default 1.0); every style pack's base body
size multiplies by it.

## Styles

The family is four packs, each a print genre with one job:

| Style | Genre | The job |
|---|---|---|
| `broadsheet` | The newspaper: one serif system for operator front + reading edition; duplex-mirrored folios, running section heads, ref-codes, desk-sheet writing furniture. | the morning paper you **read** |
| `brief` | The continuous operator brief: dense Courier, sections run together, queue rows, status cards, two-column link cards, no forced page breaks. | the page you **work through with a pen** |
| `field-card` | The boxed reference one-pager: scripts, checklists, do/don't splits, dense tables. | the card you **tape next to the phone** |
| `zine` | The pocket photocopier zine (v2): half-letter paste-up — marker title strips on an ink plate, halftone bands, checkbox steps, command blocks. | the guide you **hand to someone** |

The 0.4.x pack names still resolve for one release as deprecated aliases
(with a stderr warning): `editorial` and `magazine` → `broadsheet`, `flow`
and `typewriter` → `brief`, `ops-card` → `field-card`. Magazine was
broadsheet's article layer wearing a different kicker; typewriter's one
asset — the two-column boxed link-card grid — lives on as brief's
`.cards`/`.card` family.

## Palettes

Palettes are designed separately, not tinted from each other:

- `mono` — black-and-white for laser printers. Emphasis is weight and pattern.
- `color` — for color inkjets: warm ink, one working red for alerts, cool blue
  for data, green only for genuinely positive states.

Render the same document twice for both printers; the source never changes.

## Frontmatter (all optional)

```markdown
---
title: My Brief
style: brief       # overrides --style
palette: color     # overrides --palette
css: |             # bring-your-own stylesheet; replaces the style pack entirely
  body { … }
---
```

A `css:` block replaces the style pack *entirely* — `render` says so on
stderr and reports `"style": "custom-css"` in its JSON, never the name of a
pack the page is not actually wearing.

## Page footers

Set the running footer strings once, anywhere in the body:

```html
<span class="mp-footer-date">2026-06-11</span><span class="mp-footer-name">Morning Paper</span>
```

Page numbers (`Page N of M`) are automatic.

## Chart directives

Fenced blocks become print-quality inline SVG. Malformed data renders an
honest placeholder — never invented numbers.

````markdown
```mp-stats
Contacts | 14 | +2 / 24h
Paid 7d | $300 | 3 lifetime
```

```mp-bars
title: Yesterday's funnel
Link clicks | 10 | 10 | 10 - CPC $3.09
Landing views | 9 | 10 | LPV 90%
Pixel leads | 0 | 10 | 0
```

```mp-spark
title: Leads, last 14 days
3 5 2 8 9 4 6 7 2 1 5 9 12 11
```
````

- `mp-stats`: `label | value | delta` per line → big-number blocks.
- `mp-bars`: `label | value | max | annotation` per line → horizontal bars.
- `mp-spark`: whitespace/comma-separated numbers → a trend line with first/last labels.

Chart ink follows the palette automatically.

## Class vocabulary

Raw HTML is allowed in the markdown (the renderer runs markdown-it with
`html: true`). Each style pack documents its classes at the top of its CSS
file (`src/morning_paper/resources/styles/`). The most portable ones:

- `broadsheet`: `.masthead` (with `.masthead-title` for the nameplate,
  `.dateline` for the issue line, and an `.oxford` double rule),
  `.strip`/`.strip-item`, `.mg-kicker`/`.dept-kicker`
  (article heads; either may end with a `.ref-code`), `.mg-title`/`.dept-title`,
  `.mg-dek`, `.mg-byline`, `.q-row` (queue items), `.flag`, `.mp-stats`,
  `.mg-pull`, `.move`/`.dictation`, `.action-required`, `.not-configured`,
  `.trunc-notice` (the honesty box for clipped copy), `.page-break`,
  fenced code blocks (`pre`, merged from the retired magazine pack),
  plus the `.ds-*` desk-sheet family below
- `brief`: `.masthead`, `.strip`/`.strip-item`, `.read`, `.sig`/`.sig-pair`,
  `.q-row` (queue items), `.bet` (deadline/momentum rows), `.cards`/`.card`
  (the two-column boxed link-card grid; `.cards2` is the deprecated 0.4.x
  name), `.ops`/`.ops-line`, `.action-required`, `.not-configured`, `.refs`
- `field-card`: `.oc-title`, `.oc-banner`, `.oc-panel`, `.oc-table`,
  `.oc-split`/`.oc-col` (do/don't), `.oc-foot`
- `zine` (v2): see the dedicated section below

### Zine v2 vocabulary

The zine is a half-letter photocopier paste-up: typewriter body
(Courier Prime), felt-marker display (Permanent Marker), max two inks per
page (`--mp-ink` + `--mp-accent` — the mono palette is pure photocopier, the
color palette adds a riso-red second ink). Display elements tilt 1–3°; body
text and command blocks stay dead straight. Prints 2-up on Letter
(`pdfbook2` / `lp -o number-up=2`).

| Class | Furniture |
|---|---|
| `.z2-masthead` | letterspaced mono series line at the very top |
| `.z2-plate` + `.z2-strip` (`.alt`, `.accent`) + `.z2-plate-sub` | cover ink plate with rotated cut-paper title strips |
| `.z2-plate-dots`, `.z2-dots-exit`, `.z2-dots` | halftone dot bands (cover exit fade; section divider) |
| `.z2-stamp` (in a `.z2-stamp-row`) | tilted double-border rubber stamp — riso-red on the color palette |
| `.z2-specs` (`.row` > `.k` + `.v`) | Field Notes dotted-leader spec rows |
| `.z2-toc-title`, `.z2-toc-row` (with `.pg`) | cover lines with dot leaders to folios |
| `.z2-step` | checkbox instruction line — the zine's job |
| `.z2-cmd` | inverted-xerox command bar with a `$` prompt (`.dim` for muted spans) |
| `.z2-warn` (`.z2-warn-head` + `.z2-warn-body`) | alert band + bordered body |
| `.z2-cut`/`.z2-cut-in` (`.say` + `.who`; `.tilt-r`) | pasted-on quote scrap with a hard offset shadow |
| `.z2-sticker` | accent pill slapped on at an angle |
| `.z2-note` | marginal marker scrawl |
| `.z2-cutout` (`.z2-cutout-label`, `.t`, `.r`) | dashed "cut here" reference card |
| `.z2-colophon`/`.z2-colophon-in` (`.big` + `.small`) | back-cover colophon scrap |

The scraps use a **two-wrapper markup** — WeasyPrint has no `box-shadow`, so
the hard offset shadow is an ink-plate wrapper with the content box
translated up-left:

```html
<div class="z2-cut"><div class="z2-cut-in">
  <div class="say">"The queue remembers everything you ever asked it to do."</div>
  <div class="who">ops wisdom, June 2026</div>
</div></div>
```

A typical cover, straight from the pack's reference sample:

```html
<div class="z2-masthead">Morning Paper · Pocket Series · Nº 2</div>

<div class="z2-plate">
  <div><span class="z2-strip">WAKE THE</span></div>
  <div><span class="z2-strip alt">PRINTER!</span></div>
  <div class="z2-plate-sub">the thoth LaserJet revival guide</div>
</div>
<div class="z2-plate-dots"></div>
<div class="z2-dots-exit"></div>

<div class="z2-stamp-row"><span class="z2-stamp">Free · Fold · Staple · Hand to a friend</span></div>

<div class="z2-specs">
  <div class="row"><span class="k">Subject</span><span class="v">HP LaserJet M15w, jammed since May</span></div>
  <div class="row"><span class="k">Time needed</span><span class="v">about five minutes</span></div>
</div>
```

…and a step with its command:

```html
<div class="z2-step"><strong>Cancel everything stale:</strong></div>
<div class="z2-cmd">cancel -a HP-LaserJet-M15w</div>
```

### Ref-codes (`broadsheet`)

A kicker may carry a trailing short code:

```html
<span class="dept-kicker">The Queue <span class="ref-code">R2</span></span>
```

The code rides into the running page header alongside the section name and
prefixes the footer folio (`R2 · 7`), so a pen note keyed `R2` binds to a
place in the paper. Both are suppressed on the first page, like the running
header. Editions that skip codes keep plain folios — the separator only
prints when a code exists.

### Desk-sheet furniture (`broadsheet`)

The `.ds-*` classes set ruled *writing* furniture: dotted rules mean "write
here", solid rules are the paper talking. They are components, not a page
mandate — compose whichever zones a document needs. Everything is built on a
0.34in writing unit (pen-real line pitch).

- `.ds-zone` with a `.ds-zone-head` (`.ds-kicker` left, `.ds-zone-code`
  machine token right)
- `.ds-line` — one dotted writing rule per unit; `.ds-ghost` for a whisper
  italic prompt; `.ds-line-inset` for a rule inset clear of corner marks
- `.ds-react` rows — a dotted `.ds-code-box` for a written code plus a
  `.ds-write` note rule
- checkbox rows — `.ds-q` (`.ds-q-code`, `.ds-q-text`, `.ds-q-opts` with
  `.ds-opt`/`.ds-opt-label`), pen-scale `.cbx` boxes, `.ds-q-writein` for a
  written answer line; `.ds-menu`/`.ds-menu-opt` and `.ds-tom-write` for
  pick-one strips
- `.ds-sheet` — a 10in frame anchoring corner registration marks
  (`.ds-reg ds-reg-tl|tr|bl|br`) for scan orientation
- `.ds-masthead`/`.ds-title`/`.ds-dateline`/`.ds-howto` — a quieter masthead

A full single-sheet layout (no folio, no running heads) must null the
broadsheet `@page` furniture in its own `<style>` block, across all three
page contexts (base, `:left`, `:right`).

### Forced page breaks and single sheets (`broadsheet`)

The broadsheet philosophy stands: separators flow, nothing forces a page.
The one documented escape hatch is sheet furniture that must land on its own
page — a desk sheet printed duplex as a tear-off back page, a form that a
scanner expects alone. Opt in with:

```html
<div class="page-break"></div>
```

Place it immediately before the sheet's wrapper. Use it for whole-sheet
furniture only; if prose needs a forced break, the composition is fighting
the style — recompose instead.

## Staged copy into composed editions

`morning-paper stage <url|file>` queues material under
`{outputs.directory}/staging/{date}/` — `queue.json` holds the metadata
(title, source, `est_pages`, and the honesty flags `truncated`,
`words_extracted`, `warning`), and each item's markdown sits next to it as
`{slug}.md`.

The daily `build` consumes that queue itself: staged items are appended as a
**Staged for today** section (the broadsheet-native build template serves
every style), clipped items carry an on-page `.trunc-notice`, and the build
JSON reports the included slugs under `staged_included`. If a queue exists
but cannot be included — unreadable file, or the portable fallback renderer —
the build warns loudly instead of letting the material vanish.

When composing a custom edition by hand (an agent writing tomorrow's brief
through `render`), read the same seam:

1. `morning-paper queue --date YYYY-MM-DD` for the metadata and page budget.
2. Pull each `{slug}.md`, strip its frontmatter (article prints carry their
   own `css:` block that would override your style pack), and weave the body
   into your document.
3. Carry the honesty through: if the queue says `truncated: true`, put the
   item's `warning` in a `.trunc-notice` on the page — the reader holding
   the paper deserves the same truth the JSON had.

## Article extraction (`print` / `stage`) and privacy

When you hand the engine a URL (`morning-paper print <url>`,
`morning-paper stage <url>`), an extractor turns the page into printable
blocks. Two are registered:

- `local` (default) — fetches the page directly from this machine and parses
  it with trafilatura. **The URLs your reader cares about never leave their
  computer.** No key, no rate limits, works offline-adjacent (only the
  article's own host is contacted).
- `jina` — sends the URL to the third-party `r.jina.ai` reader service
  (anonymous tier: shared rate limits, 40-second timeout). Stronger on
  JavaScript-heavy pages and X posts.

The chain is `local -> jina`: when local extraction recovers too little
content, the engine retries through jina and the result carries an honest
note (`extraction_note` on the article, an `extractor_note` field in the
stage JSON, and a warning line in `print` output) saying the URL was sent to
the third-party service. It never falls back silently — if your reader's
threat model forbids the remote reader entirely, respect the note and skip
the article instead of staging it. Pin a backend with `article_extractor:
local` or `article_extractor: jina` in config.

Both paths feed the same validation gate (shell pages and too-short
extractions are rejected, never printed) and the same truncation reporting
(`truncated`, `words_extracted`, plain-language `warning`).
