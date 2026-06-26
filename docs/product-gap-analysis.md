# Product Gap Analysis

This document compares the current working product with the newer Morning
Paper vision:

1. a real paper every morning;
2. a private newsroom behind it;
3. an algorithm the reader owns.

The goal is to make the public engine, CLI, skills, setup flow, docs, and
rendered artifacts behave like one coherent private newsroom. The standard is
simple: a fresh agent with only the repo, plugin skills, CLI, and a reader's
newsroom should be able to produce an honest, good-looking paper without the
founder's chat history.

## What Already Works

- The engine renders markdown into print-ready PDFs and can run `doctor`,
  `demo`, `estimate`, `render`, `review`, `visual-qa`, and `final-editor`.
- `newsroom init` scaffolds a real private newsroom with `EDITORIAL.md`,
  `VISUALS.md`, `SOURCES.md`, `DELIVERY.md`, `TASTELOG.md`, specs,
  preferences, collectors, memory, and editions.
- `edition prepare` creates a resumable edition folder with source inventory,
  collector report, queue snapshot, draft, estimate, render, review, visual QA,
  final editor, operator answers, feedback plan, and optional Desk Sheet.
- The edition skill now points agents at the Daily Run Contract, source
  hydration, social cards, visual budgeting, ledgers, and feedback routing.
- The Desk Sheet exists as a reader-owned preference and a rendered one-page
  feedback surface.
- The public docs now name the right north star: paper first, private newsroom
  second, owned algorithm third.

## Main Gaps

### 1. Public Language And CLI Language Are Out Of Sync

The public product now leads with Morning Paper, edition, Desk Sheet, private
newsroom, sources, proof, and final editor. The working CLI and many docs still
lead with `stage`, `queue`, `slug`, `staged`, `candidate`, `brief`, and
`hydration`.

Those nouns are not harmless implementation detail. Agents repeat them to
readers, and the product starts to feel like a developer queue instead of a
private newsroom.

Improve:

- Keep existing command names for backward compatibility, but add reader-facing
  aliases or output labels: Source Slip, Assignment Board, held, cut, selected,
  printed, source health.
- Rewrite CLI help and agent-facing prose so "brief" becomes "paper" or
  "edition" unless the dense `brief` style pack is specifically meant.
- Preserve `slug` as an internal field, but avoid teaching readers to think in
  slugs.

### 2. The Assignment Board Is Described, But Not Yet A First-Class Artifact

Today, the staging queue is the closest thing to an Assignment Board. It has
titles, sources, word counts, estimates, truncation flags, and contributors.
That is useful plumbing, but it does not yet express editorial state.

The newer model needs a board that can show where an item is in the newsroom:
collected, needs hydration, ready to edit, selected, cut, held, printed, or
source-health only.

Improve:

- Add an edition artifact such as `assignment-board.json` and optionally
  `assignment-board.md`.
- Generate it from source inventory, collector output, staged items, ledgers,
  and the draft.
- Record cut reasons, hold reasons, repeat/staleness notes, sensitivity, trust,
  page estimate, route, and page budget impact.
- Make `queue list` able to feed the board, but do not make the queue the whole
  product model.

### 3. The Daily Run Contract Is Mostly Skill-Enforced, Not CLI-Enforced

The Daily Run Contract defines `complete`, `complete_with_notes`, and
`blocked`, but the engine does not yet emit one unified daily status.
`final-editor` returns proof status, and `review` returns editorial status, but
there is no single run ticket that says whether the whole daily promise was
met.

Improve:

- Add a `morning-paper edition status` or `morning-paper edition run-ticket`
  command.
- Write `run-ticket.json` and `run-ticket.md` into `editions/<date>/`.
- Include source check, collector report, assignment board, estimate freshness,
  render result, review, visual QA, final editor, ledgers, feedback route, and
  delivery attempt.
- Use the contract statuses exactly: `complete`, `complete_with_notes`,
  `blocked`.

### 4. The First-Run Demo Does Not Yet Prove The New Product

The current demo proves rendering, but it is still a fictional sample paper.
It does not yet show the strongest adoption story: one meaningful source
becomes a small honest paper, includes a Desk Sheet, and shows how feedback can
change tomorrow.

Improve:

- Keep the no-network demo as an engine proof.
- Add a "one-source first edition" setup path that stages one reader-provided
  URL/file and renders a small real paper from it.
- Include a Desk Sheet by default for the first private newsroom unless the
  reader disables it.
- Show the feedback route after the first edition: reader mark or chat note ->
  `edition apply-feedback` -> smallest durable file -> `TASTELOG.md`.

### 5. Desk Sheet Is Real, But Not Yet The Obvious Primary Loop Everywhere

The Desk Sheet is implemented and preferred in setup, but it is not yet the
dominant first impression in the README, demo, or daily handoff. Operator
answers and queue artifacts can still feel like the main interface.

Improve:

- Make the Desk Sheet the primary named feedback surface in README, setup
  output, delivery handoff, and first-run visuals.
- Keep `operator-answers.md` as the machine-readable fallback and chat bridge.
- Ensure Desk Sheet questions are compact, concrete, and tied to today's paper,
  not generic preferences or URL dumps.
- Add review checks for Desk Sheet overflow, uneven geometry, illegible labels,
  and missing writing space.

### 6. Source Records Need Stronger Newsroom Semantics

`SOURCES.md` captures purpose, cadence, trust, status, and backlog. `sources
check` inventories config, local drops, collectors, and next actions. But the
engine does not yet parse enough of the source ledger to help agents budget or
decide.

Improve:

- Define a structured source ledger shape for desks, beats, cadence, trust,
  sensitivity, active/paused status, and page budget.
- Let `sources check --newsroom` report those fields where available.
- Distinguish source discovery from print-ready source records.
- Keep source-specific scraping in private collectors until patterns are proven
  across readers.

### 7. Memory Exists, But Repeat Prevention Is Not Yet Universal

The scaffold creates reads and memory ledgers, and the edition skill tells
agents not to repeat reads, posts, releases, threads, or stale story angles.
The CLI does not yet provide a general "seen before" check across URLs,
canonical IDs, social posts, source artifacts, and story angles.

Improve:

- Add a reader-owned seen ledger with canonical URL, normalized URL, source ID,
  title, author, date, edition date, route, and story key.
- Add commands or helpers for `seen check`, `seen add`, and `seen explain`.
- Make stage, assignment board, and review able to warn about likely repeats.
- Treat URL matching as one signal, not the whole memory system.

### 8. Rendered Visual Motifs Are Mostly Design Intent, Not Components

The design system names proof flags, source notes, tweet/social cards, paper
cards, charts, Desk Sheet marks, earned ink slips, source slips, taste ledger,
and run tickets. The current renderer has some primitives, but the newer
motifs are not yet consistently available as reusable print furniture.

Improve:

- Add print-native components for earned ink slips, source slips, run tickets,
  and taste ledger entries.
- Make social cards variable-height, tweet-first, and full-text by default
  after hydration.
- Keep visuals printer-friendly: monochrome-safe, sparse, high contrast, no
  gradients, no feed chrome.
- Add layout fixtures that render lots of short, medium, and long social posts
  to test density before shipping a new card pattern.

### 9. Visual QA Needs To Catch The Failures We Have Seen

The current checks prove that a PDF exists and can be inspected, but the system
has produced ugly artifacts: literal markdown tables, too many rules around
metadata, long title lines, weak first-page flow, missing glyphs, raw URL
lists, cramped Desk Sheet questions, and missing visuals.

Improve:

- Add fixture PDFs for Desk Sheet, one-source first edition, social page,
  full-read page, reading menu, source health, and long-title page.
- Add review checks for raw table pipes, repeated horizontal rules, bracketed
  debug tags, long raw URL lists, missing glyph/tofu patterns, and title line
  count.
- Add visual QA guidance that requires opening the PDF or rendered page images
  before delivery when the host can do it.
- Treat an unreadable but technically rendered PDF as `blocked` or
  `complete_with_notes`, never `complete`.

### 10. The README Still Leads With The Old Order

The current README says "Own your algorithm. Your personal newsroom." That is
true, but the latest product order is paper first. The README should make the
reader want the object before explaining the machine.

Improve:

- Lead with the real paper and Desk Sheet ritual.
- Move "own your algorithm" into the explanation of why the private newsroom
  matters.
- Replace the current hero with a visual that proves one of the approved public
  visual territories.
- Add a small proof path: install, doctor, demo, setup, edition, final editor.

### 11. Skill Architecture Is Still Too Monolithic

The edition skill has absorbed a lot of the new standard: source desks,
hydration, social routes, visuals, budgets, copy desk, final editor, delivery,
and feedback. That works for dogfooding, but it is heavy for fresh agents and
hard to evaluate.

Improve:

- Split future narrow skills around actual newsroom jobs: source desk, social
  desk, art desk, feedback/taste desk, delivery desk, final editor.
- Keep the edition skill as orchestrator.
- Require subagents to write into edition artifacts, not chat memory.
- Add fresh-agent smoke tests that withhold context and grade whether the
  artifact could be produced from repo instructions alone.

### 12. Delivery Preferences Are Scaffolded, But Recipes Are Thin

`DELIVERY.md` correctly keeps delivery preferences in the private newsroom and
credentials outside the repo. The public project does not yet have strong
recipes for Telegram, GitHub artifact links, email/article views, mobile
reading, or read-later staging.

Improve:

- Add private-newsroom delivery recipes, not engine-level integrations, until
  patterns are proven.
- Make delivery attempts visible in the run ticket.
- Keep "no action outside the paper" as the default core contract.
- Treat delivery failure as `complete_with_notes` when the PDF exists and as
  `blocked` only when the reader's private contract requires that delivery.

## Release Backlog

### P0: Make The New Language Operational

- Update CLI help and skill language so paper/edition/Desk Sheet/source/proof
  lead, while queue/stage remain compatible plumbing.
- Add run-ticket artifacts and a unified daily status.
- Add assignment-board artifacts with editorial lanes and cut/hold reasons.
- Update README lead and hero order to paper first.

### P1: Make The First Experience Feel Like The Product

- Add a one-source first edition path.
- Include Desk Sheet as the default feedback loop.
- Add fixture renders for the first-run paper and Desk Sheet.
- Add review checks for the concrete artifacts already observed in dogfood
  editions.

### P2: Make The Newsroom Smarter Without Becoming A Dashboard

- Add structured source ledger parsing.
- Add seen-ledger helpers for URLs, source IDs, posts, reads, and story angles.
- Add print-native motifs: earned ink slips, source slips, run ticket, taste
  ledger snippets.
- Split source, art, feedback, and delivery work into smaller skills once the
  artifacts are stable.

## Product Standard

Do not judge progress by whether the engine can technically render a PDF. Judge
it by whether a fresh agent can produce a finite, source-backed, good-looking
paper from the reader's own newsroom, hand back a clear status, and leave
enough durable state that tomorrow is better.
