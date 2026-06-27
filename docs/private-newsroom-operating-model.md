# Private Newsroom Operating Model

Morning Paper is a way to own the algorithm that decides what reaches a
reader's attention. The reader keeps sources, preferences, memory, and delivery
rules in a private newsroom repo. Agents do the editorial work. The CLI gives
them deterministic tools for staging, estimating, rendering, reviewing, and
recording feedback.

The goal is not a feed reader. The goal is a daily paper that knows what is
going on in the reader's life and world, makes high-leverage connections, and
lands in the surface the reader will actually use.

## The Four Layers

1. **Skills** tell agents how to work: set up the newsroom, build an edition,
   revise the writing, and assign newsroom roles when a run needs separate
   context windows.
2. **The CLI** does repeatable work: install checks, source inventory,
   Assignment Board intake, page estimates, rendering, review, visual QA, final
   proof, run-ticket status, feedback routing, and local scheduling fallback.
3. **Dependencies** are local capabilities the reader or host agent can use:
   browser tools, scrape/export tools, `gh`, source CLIs, PDF/image tools,
   Telegram/GitHub delivery scripts, and any private collector dependencies.
4. **The private newsroom** is the owned algorithm: `EDITORIAL.md`,
   `VISUALS.md`, `SOURCES.md`, `DELIVERY.md`, `TASTELOG.md`, `preferences/`,
   `specs/`, `collectors/`, `memory/`, and `editions/`.

The public project ships the engine and skills. The private newsroom owns the
reader's taste and data.

## The Algorithm Loop

Morning Paper is inspired by feed algorithms, but it stays inspectable. Instead
of hiding ranking in a service, it names the loop in files:

1. **Candidate sourcing** - collectors, inboxes, staged URLs/files, exports,
   work systems, social scrapes, and agent research produce possible items.
2. **Source records** - collectors add enough context to judge an item: source,
   date, author, body text, thread/reply context, artifact links, sensitivity,
   and extraction limits.
3. **Memory filters** - ledgers and prior editions remove repeats, already-read
   articles, stale story angles, muted topics, and low-trust sources.
4. **Scoring** - the editor weighs candidates against `EDITORIAL.md`,
   `SOURCES.md`, section specs, the current day, the reader's recent feedback,
   and `preferences/interests.yaml` when the reader has added standing
   interests or dampeners there.
5. **Diversity and budget** - the edition balances source mix, novelty, page
   budget, visual budget, full-read budget, and business/world/personal lanes.
   Durable appetite changes belong in `preferences/source-budgets.yaml`.
6. **Selection and print** - the agent composes the finite paper; the CLI
   estimates, renders, reviews, and records artifacts.
7. **Feedback** - desk-sheet marks, chat notes, and delivery reactions update
   the smallest durable file and append `TASTELOG.md`.

The implementation can be simple: markdown files, YAML, JSON artifacts, shell
collectors, and a host agent. The important product standard is that a fresh
agent can inspect the loop and understand why the paper chose what it chose.

## One-Line Edition Run

A mature reader should be able to ask their host to run one edition:

```text
Use the Morning Paper skills in my private newsroom. Collect today's sources,
compose the edition from my settings, render and review it, deliver it according
to DELIVERY.md, then route any feedback I give into the smallest durable file.
```

Claude Code may call this a routine, Codex may call it an automation, another
host may call it a scheduled workflow. The cadence name is not important. The
edition run must have access to the newsroom, the installed CLI, and the host's
approved tools. It should stop with a real PDF, a clear status, and durable artifacts in
`editions/<date>/`.

The default completion promise is in
[edition-run-contract.md](edition-run-contract.md). Different readers may make the
contract stricter in their private `DELIVERY.md`, but source failures should
usually degrade into source-health notes instead of stopping the paper.

## Source Discovery

Setup should assume the first source list is incomplete. The reader may have
email, newsletters, chats, GitHub, Linear, local folders, notes, browser
history, social exports, saved reads, video history, and agent-produced files.
The right path is:

1. inventory likely sources;
2. inspect the shape of each source;
3. write an editorial source ledger/backlog entry in `SOURCES.md`;
4. test one small collector or converter;
5. stage markdown through `morning-paper stage`;
6. decide whether the source earns a recurring role.

Do not turn every possible input into an engine integration. `SOURCES.md`
records editorial judgment and backlog; it is not an executable source
registry. Source-specific scraping belongs in private collectors until a
pattern has been proven across readers.

Some readers want one or two articles every day. Others want a beat: what is
happening on X, YouTube, GitHub, a market, a community, or inside their own
work systems. A beat is not a pile of links. It is a recurring source desk with
purpose, trust, cadence, and page budget.

A broad source can contain multiple desks. X/social, for example, may have one
lane for frontier-agent workflows, one for commerce, one for creative tools,
and one for a reader's own project. The paper should budget the lanes that have
real evidence today instead of forcing every lane to appear every day.

For social or fast-moving sources, setup should capture the distinction between
standing taste and daily discovery. A reader may care about "AI agents" every
day, but the actual item worth printing could be a product release, a long
thread, a reply-chain backlash, a demo, a new model, or a small operator's
specific workflow. The source desk should preserve specific evidence, not
flatten it into generic summaries.

Social discovery is not the same as social print. A search scraper may be good
at finding candidates while still returning truncated snippets. Before a post
prints, the source desk should complete finalists into records with full text,
author/date, canonical URL, engagement metrics when available, media/artifact
links, thread/reply/quote context, article body for long native posts, and a
route: compact card, thread card, long read, source health, or cut.

Media and long-native posts need an editorial pass. Images, screenshots, demo
videos, and X Articles can be the actual source of value. A source desk should
inspect them, decide whether they clarify the story, and then route them to a
small figure, annotated crop, mini-read, full-read page, data artifact, or cut.
Printer-friendly reading stays the default; visuals earn space by making the
source easier to judge.

## Multi-Agent Edition Desk

A high-quality edition can use multiple context windows when the host supports
them:

- **Assignment desk:** inspect source inventory, collector output, local drops,
  and data folders; report what is fresh, missing, stale, or worth assigning.
- **Beat reporters:** investigate one source family each, such as X/social,
  work systems, saved reads, or local notes. They write source-backed markdown
  or collector notes, not final prose.
- **Editor-in-chief:** chooses the day's shape, page budget, order, The Read,
  and cuts.
- **Art desk:** after the editorial shape is stable, proposes charts, diagrams,
  pull quotes, screenshots, or small visuals that clarify instead of decorating.
- **Copy desk:** runs the writing skill and removes bloat without losing
  evidence.
- **Fresh final editor:** reads the rendered artifacts with less context and
  catches layout, source, budget, and delivery failures before the reader sees
  them.

Subagents should write role handoffs and source notes into the edition folder;
source material belongs on the Assignment Board. The main editor remains
responsible for the final paper.

## Budget

The edition skill should reason in budgets:

- page budget: target pages, acceptable range, and what to cut first;
- source budget: which sections get room today and which are only health lines;
- full-read budget: how many articles are printed in full, if any;
- visual budget: how often visuals appear and how much page real estate they
  consume;
- beat/topic budget: how many pages each recurring lane gets today, and what
  becomes only a source-health line;
- research budget: how much time/tooling to spend before composing.

`morning-paper edition estimate`, `morning-paper edition assignment-board`,
`morning-paper edition status`, render output, review, and visual QA are the
current tools. `morning-paper queue` remains the compatibility view of staged
Assignment Board material. Future CLI work should make rendered visual and
page-budget feedback easier for agents to use before the final render.

## Memory And Feedback

The newsroom should remember what matters:

- `memory/reads-ledger.md` prevents repeated reads.
- Source-specific ledgers, such as a social/story ledger, prevent repeated
  posts, releases, threads, and story angles.
- `memory/MEMORY.md` and `memory/threads/` hold running storylines.
- `editions/<date>/` is the run state. Pending JSON means unfinished work.
- `operator-answers.md`, desk-sheet notes, chat replies, and dictated feedback
  should route through `morning-paper edition apply-feedback`.
- Durable feedback changes the smallest right file, then appends `TASTELOG.md`.

The feedback skill should not blindly save every reaction. It should preserve
stable taste and leave one-off notes in the edition handoff.

## Delivery

The default artifact is a print-ready PDF. A reader may also want:

- a direct GitHub artifact link or committed markdown archive;
- Telegram delivery of the PDF;
- an email/article view;
- a mobile-friendly reading version;
- "article later" staging for links that should become future reads.

Delivery preferences live in `DELIVERY.md`. Credentials and tokens live outside
the repo. Delivery scripts belong in the private newsroom until the pattern is
general enough for public docs.

## Dogfood Release Gate

When the project claims a workflow is fixed, test it with a fresh agent:

1. give the agent the public skills, CLI, and a newsroom;
2. withhold chat history;
3. ask it to create or audit the thing that was fixed;
4. record what it could infer from files and what it only knew because a human
   happened to say it;
5. promote missing durable context into the right layer: skill, CLI, scaffolded
   preference, private newsroom file, or docs.

This is the core open-source standard: a new user should not need the original
developer's context to get an impressive first paper.

## Known Gaps To Explore

- Source-shape experiments for X/social, YouTube, browser history, chats, and
  newsletter exports.
- A clearer source-desk skill or CLI verb for testing local tools and writing
  source ledgers.
- Better pre-render budgeting for visuals and long full reads.
- A feedback/taste skill that digests desk-sheet photos, chat notes, and
  delivery comments into surgical durable updates.
- Delivery recipes for Telegram, GitHub artifact links, email/article views,
  and mobile-friendly reading.
- Evals that compare a single-agent run with a multi-agent newsroom run.
