# Morning Paper

Morning Paper is a Python CLI for building a daily intelligence paper from
configurable sources.

It is the public engine.

`Morning Brief` is one private deployment of that engine on Thoth.

## Positioning

Most news tools do not know the operator.
Most personal assistants do not read the world well.

Morning Paper is meant to combine:

- personal context
- curated world signal
- deterministic staging artifacts
- print-ready output

without requiring a full second-brain platform or database-heavy stack.

## Current State

This repo starts from the live Thoth Morning Brief seed.

Right now it contains:

- extracted pass scripts
- assembly and render helpers
- templates
- fixture data
- validation helpers
- a first CLI wrapper

Important:

- the initial extraction commit was a repo split, not final render authority
- the current approved render family is grounded in the 2026-04-12 style audit:
  - tuned Morning Paper / Morning Brief PDFs on Thoth
  - `x-article-print`
  - `x-article-to-print`
  - `morning-brief-print`
  - `templates/typewriter-v5.md`
- public render changes should follow that canon, not improvise from the seed scripts alone

The boundary is deliberate:

- public repo: generic engine, CLI, templates, tests, plugin surface
- private harness: cron, credentials, Telegram delivery, printer target,
  Devon-specific weighting, machine paths

## Design Principles

- code for data, LLMs for judgment
- thin harness, fat passes
- markdown/file artifacts as durable truth
- zero infrastructure to start
- first-class `doctor` and `smoke`

## Install

```bash
pip install -e .
```

## CLI

```bash
morning-paper pass1 --help
morning-paper pass2 --help
morning-paper pass3 --help
morning-paper assemble --help
morning-paper render --help
morning-paper doctor
morning-paper smoke
```

This initial CLI is a compatibility wrapper around the extracted seed scripts.
The next step is to move the useful logic into importable package modules and
shrink the script layer.

Important:

- some extracted seed scripts still contain Thoth-specific paths
- that is intentional for the first extraction commit
- the migration plan is to move those assumptions behind config and private
  harness adapters, not keep them in the public engine forever

## Repo Layout

- `src/morning_paper/`
  - package and CLI
- `scripts/`
  - extracted seed entrypoints from the live Thoth deployment
- `templates/`
  - render templates
- `tests/`
  - fixtures and golden outputs
- `docs/`
  - product and runtime extraction notes

## Render Authority

The public repo should treat these as the current best evidence for print style:

- tuned artifacts from `2026-04-12`
- the X article print skill family on Thoth
- the Morning Brief print template family on Thoth

The main failure mode discovered in the style audit was not typography. It was
structure:

- concatenated article markdown leaked orphaned `---` markers into the body
- combined outputs used broken relative image paths
- a seed extraction was mistaken for the full render canon

See:

- `docs/style-forensics-2026-04-12.md`
- `docs/layout-contract.md`
- `templates/morning-paper-v1.md`

## What This Is Not

- not a general second brain
- not a wiki
- not a PKM platform
- not Postgres-first
- not Docker-required

## Roadmap

1. Extract generic logic from the seed scripts into package modules.
2. Add a real config schema and example configs.
3. Add source plugin interfaces.
4. Keep the Thoth harness thin and private.
5. Repoint Thoth cron to the public CLI plus private config.

## License

MIT
