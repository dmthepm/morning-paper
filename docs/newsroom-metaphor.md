# Newsroom Metaphor

Morning Paper should make the reader feel they own a small, competent newsroom.
That is more than copy. It is a product model, a data model, and an agent
coordination model.

## The Core Mapping

| Newsroom word | Product object | Why it matters |
| --- | --- | --- |
| Reader / publisher | The human who owns the repo | The paper serves their attention, not a platform feed. |
| Newsroom | Private repo | The algorithm is inspectable as files. |
| Desk | Recurring source or section responsibility | A source family has purpose, trust, cadence, and budget. |
| Beat | Topic lane inside a desk | Broad sources like X can cover several distinct appetites. |
| Reporter | Collector, subagent, or source workflow | It gathers evidence but does not decide the whole paper. |
| Editor-in-chief | Main edition agent | It chooses the shape, cuts, order, and lead. |
| Art desk | Visual/layout pass | It makes data legible and tactile. |
| Copy desk | Writing skill and review | It tightens prose and catches labels, repetition, and bloat. |
| Final editor | Fresh proofing context plus CLI checks | It protects the reader from bad layout, stale artifacts, and source mistakes. |
| Pressroom | CLI renderer/reviewer | It does deterministic work and produces the PDF. |
| Edition | Rendered paper plus archived artifacts | The finite daily product. |
| Ledger | Memory files | Prevents repeats and preserves taste over time. |

## Data Structure Implications

The metaphor should be backed by files and artifacts:

- `SOURCES.md` names desks, beats, cadence, trust, and source health.
- `specs/*.md` defines section contracts and failure modes.
- `preferences/*.yaml` captures reader-owned knobs such as page budgets,
  desk-sheet behavior, review thresholds, and source-specific taste.
- `memory/*.md` and JSONL ledgers record what has already printed and what
  story angles are stale.
- `editions/<date>/data/<desk>/` holds reporter notebooks: raw pulls,
  hydration reports, media notes, source-health records, and cut lists.
- `editions/<date>/draft.md` is the editor's selected edition.
- `review.json`, `visual-qa.json`, and `final-editor.json` are proof slips.

If a future UI draws an org chart or newsroom map, it should read these files
instead of inventing a parallel model.

## Visual Concepts

### 1. Newsroom Map

Show desks as a map, not a dashboard grid. Each desk displays source health,
freshness, page budget, and whether a reporter has produced usable material.
Lines connect sources to desks and desks to printed sections. Missing
connections are useful: the reader can see when a source exists but has no
role.

### 2. Edition Board

Show today's finite paper before render. Candidates sit in lanes such as
collected, hydrated, selected, cut, and printed. Each card carries a source,
estimated pages, freshness status, route, and reason. The page budget makes the
editorial tradeoff visible.

### 3. Press Proof

Show the actual rendered pages with proof slips: review findings, visual QA,
final-editor status, and delivery status. This is where trust is earned before
the PDF lands.

## Voice Guidelines

Use newsroom language when it clarifies:

- "X Desk is thin today; printing source health only."
- "Art desk routed two screenshots to data artifacts and printed one crop."
- "Final editor flagged stale render output; rerender before delivery."
- "The Shopify beat earned one page; creative models stayed in source health."

Do not force theatrical speech:

- Avoid fake banter between agents.
- Avoid named characters unless the user deliberately creates them.
- Avoid status copy that hides failure behind charm.

## Where This Belongs

Public repo:

- README, operating model, skill-suite docs, collector docs, setup/edition
  skill language, and future UI docs.

Private newsroom:

- Reader-specific desks, beats, page budgets, source trust, visual taste,
  delivery rules, and feedback.

CLI:

- Deterministic nouns and verbs: `sources check`, `stage`, `queue`, `estimate`,
  `render`, `review`, `visual-qa`, `final-editor`, `apply-feedback`.
- Future possible verbs should expose proof and state, not invent editorial
  judgment.

Skills:

- Assign work to desks, read the right files, call the CLI for proof, and write
  the smallest durable update back to the newsroom.

## Risks To Avoid

- **Agent theater:** a cast of roles that produces worse papers.
- **Visual metaphor without data:** org charts or maps that cannot change the
  edition.
- **Dashboard drift:** many widgets, no finite paper.
- **Single-source branding:** the project should not become "X scraper to PDF"
  or "RSS newspaper."
- **Over-personalized defaults:** private newsroom taste must not leak into
  the public engine.
