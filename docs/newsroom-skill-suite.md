# Morning Paper Newsroom Skill Suite

Status: design contract for the next hardening pass. Do not implement the full
suite until the current `setup`/`edition`/`writing` skills have been evaluated
against real friend prompts.

## Principle

Morning Paper skills are newsroom desks. Each skill should help an agent decide
what to do, read the right durable files, call the CLI for deterministic work,
and write the smallest durable update back to the private newsroom.

The split stays fixed:

- the agent composes and edits;
- the CLI renders, estimates, stages, validates, and offers a local scheduling
  fallback;
- the private newsroom stores memory and taste;
- the public repo ships reusable skills and engine code;
- code never fabricates the paper.

Do not copy generic `product.md` / `design.md` conventions. Morning Paper has
newsroom-native primitives already:

- `EDITORIAL.md` — what earns ink, what gets cut, what makes The Read.
- `VISUALS.md` — layout, charts, illustrations, image policy, PDF/email taste.
- `SOURCES.md` — source purpose, trust, cadence, health, backlog.
- `DELIVERY.md` — print, email, routine, page budget, opening behavior.
- `TASTELOG.md` — accepted/rejected feedback with dates and provenance.

## Current Problem

The three shipped skills prove the product path, but they are too broad for the
next phase:

- `setup` is doing interview, install, scaffold, source onboarding, recurring
  setup guidance, and first-edition coaching in one very large body.
- `edition` is the right main loop, but visual editing, source triage, feedback
  digestion, and final proofing are becoming separate jobs.
- `writing` is correctly narrow and should remain the copy desk.
- The generic names (`setup`, `edition`, `writing`) are easy for humans but weak
  as a long-term cross-plugin namespace. Future additions should use explicit
  Morning Paper names unless host constraints require otherwise.

## Proposed Suite

Keep the friend-facing path simple: "set up my morning paper" and "build
today's edition" should still work. Internally, grow toward narrow desks:

| Skill | Role | Durable files read/write |
| --- | --- | --- |
| `morning-paper-setup` | Front desk. Install, interview, create private newsroom, open demo/first PDF. | `SETUP.md`, `setup-state.json`, all initial contracts |
| `morning-paper-status` | Triage. Inspect install, plugin state, newsroom state, host recurrence/local fallback, source health, latest edition. | reads state; writes no taste by default |
| `morning-paper-sources` | Assignment desk. Discover, inventory, connect, and debug local/RSS/inbox/collector sources. | `SOURCES.md`, collectors, source inventory |
| `morning-paper-edition` | Editor-in-chief. Compose, render, review, deliver, ask for feedback. | edition workspace, all taste files |
| `morning-paper-visuals` | Art/layout desk. Choose charts/images/illustrations, enforce visual fit, update style taste. | `VISUALS.md`, edition draft, render/review outputs |
| `morning-paper-feedback` | Taste desk. Turn natural-language notes or desk-sheet photos into durable rules. | `TASTELOG.md`, smallest matching taste file |
| `morning-paper-doctor` | Pressroom ops. Repair engine/plugin/install/native print stack/local fallback problems. | setup state, install logs; avoids editorial changes |
| `morning-paper-writing` | Copy desk. Revise prose for clarity, honesty, and reader fit. | `EDITORIAL.md`, voice/preferences, draft |

The existing `setup`, `edition`, and `writing` skills can either stay as aliases
or migrate to these explicit names in a compatibility release. Do not break the
current manifests casually; cross-host discoverability matters more than a neat
rename.

## Skill Shape

Each skill body should stay under roughly 500 lines and follow progressive
disclosure:

- `SKILL.md` holds trigger behavior, required reads, command sequence, and stop
  conditions.
- `references/` holds long examples: source adapters, visual patterns, feedback
  examples, delivery recipes.
- `scripts/` holds deterministic checks when agents would otherwise rewrite
  the same code: source inventory diffs, visual overflow audits, setup-state
  validation, style-guide linting.
- The skill should say which newsroom files it is allowed to modify and which
  ones it must only read.

## Visual Desk Contract

The visual skill exists because generated charts and illustrations can be
beautiful while still wasting measure, stranding lines, or breaking a printed
page. It should:

- inspect the edition draft and rendered review output before changing visuals;
- decide whether a visual should be full-width, two-column, inline, or cut;
- prefer semantic charts (`mp-bars`, `mp-spark`, `mp-stats`) when they explain
  data better than prose;
- use generated or searched imagery only when it adds reporting value, texture,
  or comprehension;
- check print density, label collision, image resolution, and page-break impact;
- update `VISUALS.md` when a reader accepts a stable visual preference.

## Source Desk Contract

The source skill should not force a user into Morning Paper's folder structure.
It should meet existing systems where they are:

- RSS feeds and newsletters;
- local folders, Obsidian vaults, synced folders, exports, and agent output;
- collector scripts owned by the private newsroom;
- browser/API/scrape tools chosen by the reader;
- optional business systems such as Main Branch.

It should record source purpose and trust before volume. A source is not
"configured" just because it can be scraped; it earns a role in the paper.

## Evaluation Before Expansion

Before shipping new skills, create realistic eval prompts:

- "Install this for my nontechnical friend and stop when the demo PDF is open."
- "My paper feels too long and too Hacker News heavy; tune tomorrow's edition."
- "Add my Obsidian project folder and a local Twitter export as sources."
- "The chart on page one wasted space; make visuals fit the surrounding copy."
- "I marked up today's desk sheet; update my paper's taste without overfitting."

Compare the new suite against the current three-skill baseline. Success means
better artifacts and fewer wrong durable edits, not more clever prose.

## Reference Patterns

Patterns worth copying:

- small composable skills with explicit triggers;
- router skills that send the agent to the right narrow workflow;
- deterministic scripts for fragile checks;
- source-of-truth files edited in place;
- evals that compare with-skill and baseline behavior.

Patterns to avoid:

- one giant skill that contains every adapter and every taste rule;
- empty scaffolds that look complete but carry no operating contract;
- dozens of source-specific skills before the source model is proven;
- skills that bypass the CLI and reimplement rendering, staging, or scheduling;
- skills that write public-repo docs with private newsroom facts.

Useful outside references for the pattern library:

- Matt Pocock skills: <https://github.com/mattpocock/skills>
- Garry Tan gstack skills: <https://github.com/garrytan/gstack/blob/main/docs/skills.md>
- Compound Engineering plugin: <https://github.com/everyinc/compound-engineering-plugin>
- Awesome Agent Skills index: <https://github.com/VoltAgent/awesome-agent-skills>
