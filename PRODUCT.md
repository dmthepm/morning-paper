# Product

## Register

brand

## Users

Morning Paper is for people who no longer want their attention shaped only by
platform feeds. The primary users are builders, operators, researchers,
founders, writers, and serious readers who already have scattered sources:
newsletters, feeds, repos, notes, social exports, local folders, articles,
voice notes, and agent-produced files.

They are comfortable working with AI agents, but they do not want a black-box
feed, a generic dashboard, or a new source marketplace. They want a finite
daily edition they can read, mark up, and improve over time. The product should
make them feel like they have a private newsroom working from their material,
not like they are supervising an AI workflow chart.

## Product Purpose

Morning Paper helps a reader turn their own sources, data, patterns, and taste
into a finite daily paper. The reader owns the private newsroom as files:
sources, preferences, memory, delivery rules, and feedback. The host agent is
the orchestrator. It prepares the edition, assigns newsroom roles when useful,
collects, composes, renders, reviews, proves, delivers, and routes feedback.
The CLI renders, estimates, reviews, validates, stages, and records
deterministic artifacts.

The project sits between algorithmic and analog: it uses agents and durable
files to build a reader-owned algorithm, then lands that intelligence as a real
paper. The public promise should read in this order: a real paper every
morning, a private newsroom behind it, and an algorithm the reader owns.

Success is not a clever automation or a populated dashboard. Success is a
readable edition on the desk, with a Desk Sheet or natural-language reply that
lets the reader's notes become better taste tomorrow.

PRODUCT.md and DESIGN.md are internal design/product context for surfaces,
prototypes, and brand decisions. They are not operating contracts for an edition
run. `docs/edition-run-contract.md`, `docs/private-newsroom-operating-model.md`,
and `ROLES.md` define how agents actually run the paper; these files define how
the product should feel, speak, and present that work.

## Brand Personality

Tactile, intelligent, independent.

The brand should feel like AI meets editorial judgment: thoughtful, source-aware,
and alive to the romance of a morning reading ritual. It can carry nostalgia,
especially old Mac software, print tools, proof sheets, local files, and the
feeling of a serious personal machine. It should also feel current: agents,
sources, private data, and adaptive preferences are part of the product, not
retro decoration.

The ambition is not just trust; it is memorability. Morning Paper should feel
like an object and a world people want to show other serious readers, while
staying restrained enough to actually read and print.

The tone is concise and grounded. Use newsroom language when it helps the user
understand the system: newsroom, desk, beat, orchestrator, assignment editor,
beat reporter, editor, copy desk, art desk, producer, taste editor, pressroom,
edition, ledger. Do not turn every interaction into lingo or character play.
Plain language wins when the metaphor gets in the way.

Useful reference direction:

- Monologue by Every: AI meets editorial, with a thoughtful reader/writer feel.
- Every as a broader sensibility: agents and editorial craft in the same room.
- Sublime: mindful collection and slow creative technology, including the
  sensibility of small-run publishing, labels, and zines.
- Cosmos and Are.na: personal taste, creative collecting, and networked
  knowledge without the pressure of an infinite productivity feed.
- Old Mac software: personal, capable, local, a little nostalgic, and practical.
- Serious publications and print rooms: edited, proofed, finite, tactile.
- Ground News as a conceptual reference for source skepticism, not as a visual
  template.

## Anti-references

Morning Paper should not feel like:

- a generic AI dashboard;
- Vercel-style developer polish as a default aesthetic;
- Factory AI or similar agent-workflow branding that foregrounds AI machinery
  more than the user's reading ritual;
- productivity-maximalist software that treats more throughput as the whole
  point;
- cutesy agent roleplay;
- a fake newspaper costume;
- a beige productivity app;
- an infinite feed reader;
- a social screenshot wall;
- a source scraper marketplace.

Avoid over-fluffing the message. "Own your algorithm," "private newsroom," and
"real paper every morning" are useful ideas, but the brand does not need to
force one final tagline yet. Morning Paper itself is the anchor; the first
public impression leads with the paper.

## Design Principles

1. **The paper is the proof.** Every setup, collector, skill, and CLI command
   should point toward a real edition the reader can inspect.
2. **The Desk Sheet is the loop.** The primary human interaction is reading the
   paper, marking the Desk Sheet or replying naturally, and letting tomorrow's
   paper improve. Agent tuning is a superuser layer, not the morning ritual.
3. **Own the algorithm, then make it finite.** The product turns many sources
   and adaptive preferences into one readable paper, not another stream.
4. **Use metaphor as structure.** Newsroom language should clarify roles,
   files, source health, proofing, and feedback routing. It should not become
   theatrical.
5. **Treat internal language as product language.** CLI nouns, file names, docs,
   and skills become the words agents use with readers. Prefer plain newsroom
   words: sources, desks, beats, candidates, assignment board, edition, proof.
6. **The orchestrator is a backstage role.** The host agent may assign desks,
   read handoffs, and prove the run, but the reader should mostly see a paper,
   a path for notes, and clear status when something is blocked.
7. **Show the work without making work.** Sources, desks, ledgers, assignment
   boards, run tickets, and proof views should make the system more trustworthy
   and easier to steer.
8. **Nostalgia earns its place through utility.** Old software and print
   references should make the product feel personal and tangible, never merely
   decorative.

## Accessibility & Inclusion

Default to WCAG AA for digital surfaces. Support reduced motion. Do not rely on
color alone for status or meaning. Keep print and PDF outputs readable in
monochrome. Treat private source analysis carefully: personal data, work data,
and scraped material should be clearly sourced, honestly limited, and easy for
the reader to exclude.
