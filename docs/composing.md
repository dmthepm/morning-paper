# Composing documents for `morning-paper render`

The render seam is the contract between *judgment* and *typesetting*: an agent
(or a human) writes plain markdown; the engine typesets it into a print-ready
PDF through a style pack and a palette. The composer never writes CSS.

```bash
morning-paper render brief.md --style flow --palette mono
morning-paper render call-card.md --style ops-card --palette color
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

| Style | Genre |
|---|---|
| `typewriter` | The newspaper: Courier Prime masthead, card sections, two-column HN-style cards. |
| `flow` | The continuous operator brief: dense, sections run together, no forced page breaks. |
| `ops-card` | The boxed reference one-pager: scripts, checklists, do/don't splits, dense tables. |
| `magazine` | The long-read essay page: serif body, kicker/dek/byline, pull quotes, wide margins. |
| `zine` | The pocket how-to guide: half-letter, marker display type, checkbox steps, command blocks. |
| `editorial` | The unified paper: one serif system for operator front + reading edition; duplex-mirrored folios, running section heads, ref-codes, desk-sheet writing furniture. |

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
style: flow        # overrides --style
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

- `flow`: `.masthead`, `.strip`/`.strip-item`, `.read`, `.sig`/`.sig-pair`,
  `.q-row` (queue items), `.bet` (deadline/momentum rows), `.cards2`/`.card`,
  `.ops`/`.ops-line`, `.action-required`, `.not-configured`, `.refs`
- `ops-card`: `.oc-title`, `.oc-banner`, `.oc-panel`, `.oc-table`,
  `.oc-split`/`.oc-col` (do/don't), `.oc-foot`
- `typewriter`: `.page-1-header`, `.info-row`, `.tweet`/`.tweet-pair`,
  `.hn-cards`/`.hn-card`, `.featured-reads`/`.full-read`, `.action-required`
- `magazine`: `.mg-kicker`, `.mg-title`, `.mg-dek`, `.mg-byline`, `.mg-lede`,
  `.mg-pull`/`.mg-pull-attr`, `.mg-note`, `.mg-end`
- `zine`: `.zn-cover`/`.zn-cover-title`/`.zn-cover-sub`/`.zn-cover-meta`,
  `.zn-step` (checkbox lines), `.zn-cmd`, `.zn-url`, `.zn-img`, `.zn-warn`
- `editorial`: `.masthead` (with `.masthead-title` for the nameplate,
  `.dateline` for the issue line, and an `.oxford` double rule),
  `.strip`/`.strip-item`, `.mg-kicker`/`.dept-kicker`
  (article heads; either may end with a `.ref-code`), `.mg-title`/`.dept-title`,
  `.mg-dek`, `.mg-byline`, `.q-row` (queue items), `.flag`, `.mp-stats`,
  `.mg-pull`, `.move`/`.dictation`, `.action-required`, `.not-configured`,
  `.trunc-notice` (the honesty box for clipped copy), `.page-break`,
  plus the `.ds-*` desk-sheet family below

### Ref-codes (`editorial`)

A kicker may carry a trailing short code:

```html
<span class="dept-kicker">The Queue <span class="ref-code">R2</span></span>
```

The code rides into the running page header alongside the section name and
prefixes the footer folio (`R2 · 7`), so a pen note keyed `R2` binds to a
place in the paper. Both are suppressed on the first page, like the running
header. Editions that skip codes keep plain folios — the separator only
prints when a code exists.

### Desk-sheet furniture (`editorial`)

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
editorial `@page` furniture in its own `<style>` block, across all three
page contexts (base, `:left`, `:right`).

### Forced page breaks and single sheets (`editorial`)

The editorial philosophy stands: separators flow, nothing forces a page.
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
**Staged for today** section (in both the editorial and typewriter build
templates), clipped items carry an on-page `.trunc-notice`, and the build
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
