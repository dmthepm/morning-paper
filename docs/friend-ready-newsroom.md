# Friend-Ready Newsroom Contract

Status: current operating contract for the friend-ready Morning Paper workflow.
Current release: 0.8.9.

release: 0.8.9

Morning Paper should feel simple from the outside: install the engine, prove it
can render, set up a private newsroom, then make a real paper every morning.
The product is the print-ready paper the reader can hold, read, mark up, and
teach.

Product/design surface direction lives in root `PRODUCT.md` and `DESIGN.md`.
The role model lives in `ROLES.md` and `docs/roles/`. Historical release proof
notes live in `docs/archive/`.

## Current Truth

- `morning-paper` 0.8.9 is live on PyPI and tagged as `v0.8.9`.
- One shared skill tree ships to Claude Code and Codex.
- The public skill surface is intentionally small: `setup`, `edition`, and
  `writing`.
- Setup proves the engine before asking the reader to trust it:
  `morning-paper doctor --strict` and `morning-paper demo --open`.
- Setup scaffolds a private newsroom with durable files, not empty folders:
  `EDITORIAL.md`, `VISUALS.md`, `SOURCES.md`, `DELIVERY.md`, `TASTELOG.md`,
  `specs/`, `preferences/`, `collectors/`, `memory/`, `examples/`, and
  `editions/`.
- The edition workflow runs through durable artifacts: source inventory,
  collector report, Assignment Board, draft, estimate, render, review, visual
  QA, final editor, run ticket, operator answers, and feedback plan.
- Missing data prints as "not configured"; agents never invent a headline,
  number, quote, source, or delivery result.
- Local extraction is the default. Trafilatura is currently the local article
  parser behind `article_extractor: local`; it is pinned as `>=2.1,<3`.
  Remote extraction remains an explicit opt-in, not the default reader promise.

## Reader Promise

As a reader, I can set up Morning Paper with an agent and get:

- a demo PDF proving the print stack works;
- a private newsroom folder that owns my sources, taste, memory, and delivery
  rules as files;
- a first real edition from my sources, even if some sections say
  "not configured";
- a PDF path and, when configured, delivery through my saved delivery route;
- a clear way to give notes so tomorrow's paper improves.

## Skill Contract

0.8.x ships exactly three public skills:

- `setup` installs/proves the engine, interviews the reader, scaffolds the
  private newsroom, and offers host-native recurrence.
- `edition` makes today's paper: prepare, collect, compose, render, review,
  prove, deliver, and route feedback.
- `writing` is the copy-desk pass for words the reader will hold.

Newsroom roles are not public skills yet. They are references and handoff
contracts used inside the edition workflow. The orchestrator may assign
assignment editor, beat reporter, editor, copy desk, art desk, producer, and
taste editor work through files under `editions/<date>/desks/`.

## Daily Run Contract

The daily run is complete only when the agent has:

- run `morning-paper edition prepare . --date <edition-date>`;
- refreshed source inventory and collector notes;
- built or refreshed `assignment-board.json` and `assignment-board.md`;
- composed `draft.md` from real source material and newsroom preferences;
- run estimate, render, review, visual QA, and final editor;
- run `morning-paper edition status . --date <edition-date>`;
- delivered or handed back the PDF according to `DELIVERY.md`;
- updated ledgers and feedback artifacts when the paper ships.

The run may finish as:

- `complete` — readable PDF delivered or handed back, with clean proofs;
- `complete_with_notes` — readable PDF delivered or handed back, but source,
  review, visual, or delivery notes need attention;
- `blocked` — no honest readable paper can ship without repair or reader action.

## Assignment Board

The Assignment Board is the working surface for source material. It should show
what is ready, what needs source proof, what is held, what is cut, what printed,
and what source health problems matter. It replaces vague queue language in
reader-facing docs.

`morning-paper stage` may remain the compatibility command, but docs should
explain it as adding source material to the Assignment Board for an edition.

## Feedback Loop

After delivery, the agent asks for natural-language notes. Stable feedback is
routed with:

```bash
morning-paper edition apply-feedback . --date <edition-date> --route <route> --note "<reader note>" --why "<why it should change tomorrow>"
```

Supported routes include `editorial`, `voice`, `visuals`, `sources`, `prior`,
`delivery`, `checks`, `the-read`, `front-page`, `reading`, and `taste`.

The route should update the smallest durable newsroom file and append
`TASTELOG.md`. The reader should not have to think in YAML or repo structure.

## Source Conversion

Unsupported local files become private converter collectors, not hosted
scraper/OAuth registries in the public engine. Use `docs/source-conversion.md`
and the scaffolded `collectors/CONVERTERS.md`: convert to markdown, stage the
result for the target date, report skips honestly, and let the editor decide
what earns ink.

## Recurrence

Prefer the host's native recurring primitive:

- Claude Code routine / schedule trigger;
- Codex automation;
- ChatGPT scheduled task only when it has approved access to a runner, or as a
  reminder/check-in when it does not.

The CLI `morning-paper routine` path is a local fallback, not the default mental
model.

## Done

The friend-ready workflow is healthy when:

- README, `AGENTS.md`, the three skills, CLI help, and this contract agree;
- setup and edition resume from files after context loss;
- private newsroom facts never enter the public repo;
- the paper is readable before delivery;
- delivery truth is visible to the reader;
- feedback changes tomorrow's paper through durable files.
