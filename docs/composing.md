# Composing documents for `morning-paper render`

The render seam is the contract between *judgment* and *typesetting*: an agent
(or a human) writes plain markdown; the engine typesets it into a print-ready
PDF through a style pack and a palette. The composer never writes CSS.

```bash
morning-paper render brief.md --style flow --palette mono
morning-paper render call-card.md --style ops-card --palette color
morning-paper styles   # list available styles + palettes
```

## Styles

| Style | Genre |
|---|---|
| `typewriter` | The newspaper: Courier Prime masthead, card sections, two-column HN-style cards. |
| `flow` | The continuous operator brief: dense, sections run together, no forced page breaks. |
| `ops-card` | The boxed reference one-pager: scripts, checklists, do/don't splits, dense tables. |

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

Honesty rule (engine doctrine): a section with no data says so
(`.not-configured`) — composition degrades, it never fabricates.
