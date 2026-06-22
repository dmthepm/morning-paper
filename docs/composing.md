# Composing documents for `morning-paper render`

The render seam is the contract between *judgment* and *typesetting*: an agent
(or a human) writes plain markdown; the engine typesets it into a print-ready
PDF through a style pack and a palette. The composer never writes CSS.

Prose quality has its own contract: `plugins/morning-paper/skills/writing/SKILL.md`
carries the revision discipline (Strunk per-sentence checks, the AI-tells kill
list) that every composed document should pass before it reaches `render`.

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

## The taste layer (free, every pack, zero markup)

A well-composed document — headline, byline, prose, a chart — typesets cleanly
in any of the four packs with **no layout markup**. A shared base stylesheet
(`resources/styles/_base.css`), composed before each pack, gives all four the
same keep-together craft:

- **Heads never strand at a page foot.** The kicker → title → deck → byline
  chain glues to the body that follows (`break-after: avoid`), and the head box
  stays whole (`break-inside: avoid`). These attach to the classes the renderer
  already emits (`.article-head`, `.mg-title`/`.dept-title`, `h1`–`h3`), so you
  get it for free — there is nothing to turn on.
- **No single dangling line.** `orphans: 3; widows: 3` keeps at least three
  lines together across any break, so a headline carries its first sentences
  onto the new page and no lone line sits at a page top.
- **Atomic furniture never tears.** Charts, stat blocks, callouts, pull-quotes,
  and table rows stay whole (`break-inside: avoid`).
- **Split blocks look finished.** When a bordered callout or quote is genuinely
  too tall to keep whole, both fragments redraw their border and padding
  (`box-decoration-break: clone`) instead of one edge being amputated.

**Fail-soft is the contract.** Every keep is a *preference*, not an impossible
guarantee. If honoring a keep would be worse than breaking — a block taller
than the text column — WeasyPrint flows it normally rather than shoving a chain
to the next page and stranding a half-empty one. You never get a clipped or
blank page from the taste layer; over-tall content degrades to a clean break at
the least-bad internal seam.

Because the base is composed first, each pack's own rules still win by source
order — the four packs keep their exact look. The base only adds the
keep-together behavior brief/field-card/zine previously lacked; broadsheet's
default look is unchanged.

## Reviewing a finished edition

`morning-paper review <edition>` reads a composed edition and emits **editorial
warnings, never hard fails** — the copy desk's last read before it prints. It
is the editorial twin of `doctor`: `doctor` answers "does it render", `review`
answers "is it good enough to run".

```bash
morning-paper review ~/.local/share/morning-paper/2026-06-21   # a date dir
morning-paper review draft-edition.md --json                   # one file
morning-paper review --strict                                  # latest edition, CI gate
morning-paper review 2026-06-21 --explain headline-line-count  # the threshold math
```

- Pass an edition directory, the composed markdown (or JSON) file, or a date;
  with no argument it reviews the latest edition under `outputs.directory`.
- Exit code is **0 by default, always.** `--strict` makes a `flag` (and only a
  `flag`) exit 1 — for CI. `info`/`nudge` never affect exit.
- `--json` prints the full report; the default human output leads with flags
  and is one quiet line when clean. `--verbose` shows info; `--explain CHECK`
  prints the numbers and their provenance.

The eight checks, all text-only (they run even on a fallback-only install):

| Check | Severity | Flags |
|---|---|---|
| `headline-line-count` | flag | a TRUE headline estimated to wrap 3+ lines at the pack's measure |
| `headline-length` | nudge | a TRUE headline over ~60 characters |
| `headline-verb-presence` | flag | a label head with no finite verb |
| `hed-dek-redundancy` | nudge | a deck that echoes ≥50% of the head's words |
| `section-balance` | nudge | a section >2.5× the median, or one lonely item next to fat ones |
| `empty-or-sparse-section` | nudge | a heading over no real content |
| `duplicate-headline` | nudge | the same story twice (URL or near-identical title) |
| `stale-dateline` | info | a lead item materially older than the edition date |

`review` complements the taste layer — it never re-checks what the CSS already
prevents (orphan/widow *lines*, stranded heads). It catches the residue CSS
cannot fix: a head that still wraps because the *words* are long, a starved or
dead section, a stale or duplicate story.

The two LENGTH checks (`headline-line-count`, `headline-length`) measure only
**true headlines** — the lead/front head (`.mg-title`), a printed article's
headline (`.article-title`), the field-card title (`.oc-title`), and markdown
`#`/`##` heads in the simpler packs. They **exempt** deck/department/section
labels (`.dept-title`, `.mg-dek`, kickers), which are multi-sentence summaries
long by design — flagging them was the 0.6.0 false positive. The other
headline checks (`headline-verb-presence`, `hed-dek-redundancy`,
`duplicate-headline`) still read every head, so a label-style department title
with no verb still flags.

A newsroom's `preferences/checks.yaml` (when present) tunes the checks — the
file is read automatically, never written by `review`:

```yaml
version: 1
thresholds:
  headline-line-count:
    warn_at_lines: 2            # run tighter than the default 3
    per_pack: { zine: 3 }       # a zine tolerates a louder, longer head
  headline-length:
    nudge_at: 50
mute:
  - check: headline-length
    when: { section: "Field Notes" }   # field notes run long on purpose
  - check: stale-dateline
    scope: global                       # I read evergreens; age is fine
```

Every finding reports `threshold.source` (`default` or `user`) so a tuned rule
is transparent in origin. The learned-feedback loop (`--learn`) and the
geometry checks (a render pass) are deferred to later phases.

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
Charts are guarded print furniture: each directive renders as one atomic block,
and the built-in bar/spark primitives use the full available measure so visuals
align with the section above and below instead of floating as narrow inserts.
They also have print-density bounds: `mp-bars` shows up to 12 rows, `mp-stats`
shows up to 6 primary blocks plus an honest "not shown" note, and `mp-spark`
uses the most recent 90 values with an honest title note when older values are
omitted. Labels and annotations are clipped rather than allowed to collide. If
a chart needs more than that, split it or summarize.

## Visual and figure primitives

Images should earn ink. Use a visual when it explains something prose cannot:
a map, annotated screenshot, object photo, chart, diagram, or generated
illustration that adds editorial texture. Cut decorative visuals before they
steal space from the read.

Markdown images and explicit figures default to the full available measure so
they align with the section above and below:

```html
<figure class="mp-figure">
  <img src="images/harbor-seals.png" alt="Harbor seal count over 14 days">
  <figcaption>Harbor seals counted at the breakwater, last 14 days.</figcaption>
  <span class="mp-source-note">Source: reader collector, 2026-06-22.</span>
</figure>
```

For two related visuals, use a shared block so the pair moves together:

```html
<div class="mp-visual-grid">
  <figure class="mp-figure">...</figure>
  <figure class="mp-figure">...</figure>
</div>
```

Avoid narrow orphan images. If a visual cannot fill the measure or pair with a
neighbor, rewrite it as a chart/table, make it full-width, or cut it.

## Class vocabulary

Raw HTML is allowed in the markdown (the renderer runs markdown-it with
`html: true`). Each style pack documents its classes at the top of its CSS
file (`src/morning_paper/resources/styles/`). The most portable ones:

- `broadsheet`: `.masthead` (with `.masthead-title` for the nameplate,
  `.dateline` for the issue line, and an `.oxford` double rule),
  `.strip`/`.strip-item`, `.mg-kicker`/`.dept-kicker`
  (article heads; either may end with a `.ref-code`), `.mg-title`/`.dept-title`,
  `.mg-dek`, `.mg-byline`, `.q-row` (queue items), `.flag`, `.mp-stats`,
  `.mp-chart`, `.mp-figure`, `.mp-visual-grid`, `.mp-source-note`, `.mg-pull`,
  `.move`/`.dictation`, `.action-required`, `.not-configured`, `.trunc-notice`
  (the honesty box for clipped copy), `.page-break`,
  fenced code blocks (`pre`, merged from the retired magazine pack),
  plus the `.ds-*` desk-sheet family below
- `brief`: `.masthead`, `.strip`/`.strip-item`, `.read`, `.sig`/`.sig-pair`,
  `.q-row` (queue items), `.bet` (deadline/momentum rows), `.cards`/`.card`
  (the two-column boxed link-card grid; `.cards2` is the deprecated 0.4.x
  name), `.ops`/`.ops-line`, `.action-required`, `.not-configured`, `.refs`
- `field-card`: `.oc-title`, `.oc-banner`, `.oc-panel`, `.oc-table`,
  `.oc-split`/`.oc-col` (do/don't), `.oc-foot`
- `zine` (v2): see the dedicated section below

### Zine vocabulary

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
  <div class="z2-plate-sub">the neighborhood press revival guide</div>
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
blocks. Treat this as replaceable plumbing, not editorial truth.

The contract is stable even if the backend changes:

- if extraction is partial, the staged item carries `truncated`,
  `words_extracted`, and a plain-language `warning`;
- if a URL leaves the machine through a remote reader service, the staged item
  carries an `extractor_note`;
- shell pages, too-short extractions, and obvious garbage are rejected instead
  of printed;
- the editor must surface those notes or skip the item. Never print a clipped
  or remote-fetched article as if it were complete and local.

Backend names and configuration live in the architecture/reference docs. The
composition skill should care about source honesty and page fit.

## Scheduling the daily compose

The composition pass can run manually or through the host's native recurring
primitive:

- Codex automation: can run the `edition` skill in the project/newsroom and
  choose a local project or background worktree environment;
- Claude Code routine: use a schedule trigger and run the edition workflow from
  the private newsroom;
- ChatGPT scheduled task: good for reminders, check-ins, or connected workflows;
  it should not claim it rendered a local PDF unless it has approved access to
  the newsroom runner.

The CLI's `morning-paper routine install|status|uninstall` remains an advanced
local fallback for users who explicitly want launchd/systemd/cron. It should
not be the default setup path for readers already living in an agent host.
