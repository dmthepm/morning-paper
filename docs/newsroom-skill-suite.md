# Morning Paper Skill Architecture

Status: current skill contract plus future split rules. Keep this aligned with
`ROLES.md`, the plugin manifests, and the setup/edition/writing skills.
The friend-ready newsroom contract lives in
[`docs/friend-ready-newsroom.md`](friend-ready-newsroom.md). Product/design
surface context lives separately in root `PRODUCT.md` and `DESIGN.md`.

## Principle

Morning Paper skills are newsroom desks, but not every desk should be a public
skill. The reader-facing path stays simple:

- "set up my morning paper"
- "make today's paper"
- "revise this like the paper"

The agent can still run a full newsroom behind those prompts. The richer
structure lives in role references, durable edition artifacts, and CLI checks.
That lets Codex, Claude Code, Hermes, or another host map the same work to
subagents, profiles, models, or a single sequential run.

The product split stays fixed:

- the agent composes and edits;
- the CLI renders, estimates, stages, validates, and offers a local scheduling
  fallback;
- the private newsroom stores memory and taste;
- the public repo ships reusable skills and engine code;
- code never fabricates the paper.

Do not copy generic `product.md` / `design.md` conventions. Morning Paper has
newsroom-native primitives already:

- `EDITORIAL.md` - what earns ink, what gets cut, what makes The Read.
- `VISUALS.md` - layout, charts, illustrations, image policy, PDF/email taste.
- `SOURCES.md` - source purpose, trust, cadence, health, backlog.
- `DELIVERY.md` - print, email, host-native recurrence/local fallback, page
  budget, opening behavior.
- `TASTELOG.md` - accepted/rejected feedback with dates and provenance.

## Current Shipping Contract

0.8.x ships exactly three plugin skills:

- `setup`
- `edition`
- `writing`

That exact set is intentional. `scripts/install_smoke.py`,
`scripts/host_plugin_smoke.py`, and `scripts/validate_codex_plugin.py` fail if
an unfinished desk skill leaks into the plugin surface. The names are plain
because the user path is plain. Do not rename them casually; compatibility
across hosts matters more than a neat taxonomy.

## Skill Roles

| Skill | Public job | Internal newsroom shape |
| --- | --- | --- |
| `setup` | Install the engine, prove the demo PDF, interview the reader, and scaffold a private newsroom with real contracts. | Front desk plus first operator interview. It writes durable taste/source/delivery files, not empty folders. |
| `edition` | Orchestrate today's paper end to end: prepare, collect, compose, render, review, prove, deliver, and route feedback. | Orchestrator. It may assign roles from `ROLES.md` into `editions/<date>/desks/`, then uses CLI artifacts as the run record. |
| `writing` | Revise prose the paper will print. | Copy desk. It is intentionally narrow and should stay narrow. |

`edition` is the main one-liner skill. It can call the role model without
forcing the user to think about roles. A serious run may create:

- `01-orchestrator.md`
- `02-assignment-editor.md`
- `03.N-<beat>-reporter.md`
- `04-editor.md`
- `05-copy-desk.md`
- `06-art-desk.md`
- `07-producer.md`
- `08-taste-editor.md`

Those are role artifacts, not public skills.

## When To Split A New Skill

This section is a design direction, not shipped surface. A role can graduate
into a first-class skill only when all of these are true:

1. It has repeated, distinct user prompts that should trigger it directly.
2. It needs enough procedure that keeping it inside `edition` hurts context
   economy or reliability.
3. It has realistic eval prompts comparing the new skill against the current
   three-skill baseline.
4. It ships with updated plugin manifests, smoke tests, README/setup guidance,
   and any required CLI support in the same release.

Until then, keep the public surface small and strengthen `ROLES.md`,
`docs/roles/`, CLI checks, and edition artifacts.

Likely future splits, if evals justify them:

- source onboarding and collector repair;
- feedback/taste digestion from Desk Sheet photos or chat notes;
- visual/layout review when it becomes too large for `edition`;
- install/pressroom repair separate from first-run setup.

## Skill Shape

Follow the skill-creator guidance:

- Keep SKILL.md bodies lean. Move long examples and variant-specific detail to
  references or docs that the skill points at.
- Put trigger behavior in the YAML `description`, not in a buried "when to use"
  section.
- Preserve the skill `name` unless making an intentional compatibility release.
- Bundle scripts only when agents would otherwise rewrite the same deterministic
  code repeatedly.
- Forward-test substantial revisions with fresh contexts and raw artifacts, not
  leaked diagnoses.

Current length pressure:

- `writing` is healthy and narrow.
- `edition` is acceptable but should keep pushing detail into `ROLES.md`,
  `docs/roles/`, and CLI artifacts.
- `setup` is too long. The next cleanup should move scaffold examples into
  references or deterministic CLI templates while preserving the friend path.

## Evaluation Before Expansion

Before shipping new skills or renaming existing ones, create realistic eval
prompts:

- "Install this for my nontechnical friend and stop when the demo PDF is open."
- "My paper feels too long and too tilted toward one source; tune tomorrow's
  edition."
- "Add my Obsidian project folder and a local Twitter export as sources."
- "The chart on page one wasted space; make visuals fit the surrounding copy."
- "I marked up today's desk sheet; update my paper's taste without
  overfitting."

Success means better artifacts, fewer wrong durable edits, fewer stops for
ordinary uncertainty, and a more honest paper. It does not mean more public
skills.

## Patterns To Keep

- Small public skill surface.
- Role references for separate contexts.
- One markdown role artifact with YAML frontmatter per role.
- Deterministic CLI checks for fragile proof work.
- Source-of-truth files edited in place.
- Evals that compare new behavior with the current baseline.

## Patterns To Avoid

- One giant skill that contains every adapter and every taste rule.
- A public skill per source before the source model is proven.
- Skills that bypass the CLI and reimplement rendering, staging, or scheduling.
- Skills that write public-repo docs with private newsroom facts.
- Cute internal names that leak into user-facing language.
