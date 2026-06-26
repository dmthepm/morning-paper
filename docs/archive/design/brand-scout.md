# Brand Scout

Status: exploratory. This is not canonical project context. The durable public
design context lives in root `PRODUCT.md` and `DESIGN.md`. The daily paper's
operating contract lives in `docs/friend-ready-newsroom.md`, `ROLES.md`, and
the active setup/edition/writing skills.

## Product-Design Workflow

Use this order when evolving the brand or a new surface:

1. Load root `PRODUCT.md` and `DESIGN.md`.
2. Read the friend-ready newsroom contract and role model for operating truth.
3. Shape a specific surface as a confirmed brief.
4. Build only after the shape is clear.
5. Critique, audit, polish, layout, delight, typeset, and iterate from the
   rendered surface rather than from abstract taste.

For this project, brand work may use subagents for scouting, but the stable
product/design context belongs in `PRODUCT.md` and `DESIGN.md`, not in chat.

## Working Product Frame

Morning Paper is a private newsroom for the reader's attention. The reader owns
the sources, taste, memory, and delivery rules as files. Agents do editorial
work. The CLI is the pressroom: deterministic proof, render, review, delivery,
and feedback routing.

The public frame should keep these ideas in tension without forcing a premature
tagline: the reader owns the algorithm, the newsroom is private, and the output
is a real paper every morning.

## Current Confirmed Direction

The first canonical brand context now starts with:

- brand feel: tactile, intelligent, independent;
- references: Monologue by Every, Every's broader AI/editorial sensibility,
  Sublime, Cosmos, Are.na, old Mac software, serious publications, print
  rooms, and Ground News as a conceptual trust reference;
- anti-references: Vercel-style developer polish as the default lane, Factory
  AI-style agent branding, cutesy roleplay, generic AI dashboards, fake
  newspaper nostalgia, productivity-maximalist software, and beige
  productivity apps;
- framing centers Morning Paper itself, with "own your algorithm", "private
  newsroom", and "real paper every morning" as supporting ideas.

The slow creative technology references matter: Sublime, Cosmos, and Are.na
suggest collecting, taste, reflection, and cultural texture without becoming an
infinite stream. Morning Paper should feel adjacent to that world, but more
pressroom and edition-oriented.

## Brand Lanes To Explore

### 1. Pressroom Proof

References:

- proof slips
- red-pencil markup
- newspaper dummy sheets
- plate-registration marks
- print-shop job tickets
- page-budget boards

Why it fits:

- Strongest match to "the paper is the product."
- Makes CLI proof, render, review, and final editor feel trustworthy.
- Gives adoption a concrete artifact: the PDF and the proof around it.

Risk:

- Can collapse into saturated editorial-typographic slop: display serif, rules,
  mono labels, and no real idea.

Color:

- restrained but tactile;
- warm paper or neutral base, near-black ink, proof red, blue-pencil annotation,
  maybe one utility green for passed checks;
- must survive monochrome.

Typography:

- sturdy grotesk plus a workhorse text face;
- avoid Newsreader, Fraunces, IBM Plex, Inter, Space Mono, Cormorant, and other
  saturated default type choices;
- look toward job-ticket, pressroom, civic-print, or field-proof specimens.

Imagery:

- rendered pages;
- proof stamps;
- page thumbnails;
- source slips;
- marginalia;
- crop and registration marks.

Anti-references:

- Substack editorial minimalism;
- Notion-style rule-separated columns;
- fake newspaper nostalgia;
- agent-role cartoons.

### 2. Private Library Ledger

References:

- index cards
- library catalog drawers
- accession records
- field notebooks
- folder tabs
- reading ledgers
- zettelkasten cabinets

Why it fits:

- Emphasizes ownership, memory, source ledgers, and editable taste.
- Good for open-source trust because it makes the data model legible.

Risk:

- Could feel like a notes app or personal knowledge base instead of a daily
  paper engine.

Color:

- archival accents: folder buff, catalog green, date-stamp red, graphite,
  muted blue;
- avoid becoming another beige productivity app.

Typography:

- readable literary text face paired with an unfussy admin sans;
- type should feel like durable record labels, not magazine luxury.

Imagery:

- source ledger;
- beat cards;
- drawer labels;
- filed clippings;
- memory trails.

Anti-references:

- Obsidian clone;
- academic archive;
- sentimental stationery brand.

### 3. Wire Desk Signal

References:

- AP/Reuters wire copy
- radio logs
- shipping manifests
- aviation/weather charts
- signal maps
- newsroom assignment boards

Why it fits:

- Captures the algorithmic side: many sources, finite attention, source health,
  routing, freshness, scoring, and selection.

Risk:

- Could become a dashboard, surveillance wall, or ops-console product, losing
  the calm paper-on-desk romance.

Color:

- more committed and semantic;
- white/black or pale grid base with sharp signal accents;
- color shows state, not decoration.

Typography:

- condensed utility sans for labels plus a highly legible body face;
- mono only for literal logs or code output, not the whole identity.

Imagery:

- source desks;
- assignment lanes;
- freshness bands;
- route stamps;
- candidate-to-print flow.

Anti-references:

- Bloomberg-terminal cosplay;
- generic AI dashboard;
- neon hacker UI;
- infinite feed analytics.

## Prototype Surfaces

### Assignment Board

Show desks, beats, collectors, source trust, cadence, freshness, page budgets,
and which candidates may earn space in today's paper. This makes the owned
algorithm inspectable without making the reader learn technical language.

Existing inputs:

- `SOURCES.md`
- `specs/*`
- `source-inventory.json`
- `collector-report.md`
- `morning-paper sources check --newsroom .`

Potential future CLI:

- `morning-paper sources health --json`
- `assignment-board.json` from `edition prepare`

### Skepticism Desk

Ground News-style trust surface. For a candidate story, show who is saying it,
what is missing, source diversity, extraction limits, repeats/staleness, and
whether it should print, cut, or become source health.

Existing inputs:

- `queue list/show`
- `queue-snapshot.json`
- `memory/reads-ledger.md`
- source-specific ledgers
- `review.json`
- `final-editor.md`

Potential future CLI:

- `morning-paper candidates hydrate --json`
- `morning-paper evidence compare --json`
- `claim-ledger.json`
- `source-diversity.json`

### Assignment Board / Proof Pages

The daily work surface. Lanes: collected, hydrated, selected, cut, printed,
proofed, delivered. Cards carry page estimate, source, route, freshness, reason,
and review flags.

Existing inputs:

- `editions/<date>/`
- `draft.md`
- `estimate-result.json`
- `render-result.json`
- `review.json`
- `visual-qa.json`
- `final-editor.json`
- `operator-answers.md`
- `feedback-plan.md`

Potential future CLI:

- `morning-paper edition assignment-board --json`
- `cut-list.json`
- `selection-rationale.json`
- `section-budget.json`
- `delivery-status.json`
