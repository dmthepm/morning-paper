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
pip install git+https://github.com/dmthepm/morning-paper.git
```

For local development:

```bash
pip install -e .
```

## Portable v0.1

The product cut for `v0.1` is:

- no Thoth path assumptions
- HN + RSS only
- print-ready PDF output
- markdown/HTML/JSON artifacts
- no LLM required

Quick start:

```bash
morning-paper init
morning-paper build
```

That creates a config at `~/.config/morning-paper/config.yaml` and outputs a
paper under `~/.local/share/morning-paper/<date>/`.

## CLI

```bash
morning-paper init
morning-paper build
morning-paper pass1 --help
morning-paper pass2 --help
morning-paper pass3 --help
morning-paper assemble --help
morning-paper render --help
morning-paper doctor
morning-paper smoke
```

There are now two lanes:

- public product lane:
  - `init`
  - `build`
- legacy compatibility lane for the private Thoth deployment:
  - `pass1`
  - `pass2`
  - `pass3`
  - `assemble`
  - `render`
  - `digest`

Important:

- the extracted seed scripts still contain Thoth-specific paths
- those remain for the private deployment only
- the public `init/build` path is the portable product surface

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

1. Harden the portable `init/build` path with fixtures and golden tests.
2. Add optional LLM scoring as an extra, not a requirement.
3. Add source plugin interfaces for X and YouTube.
4. Keep the Thoth harness thin and private.
5. Reduce the legacy script lane over time.

## License

MIT
