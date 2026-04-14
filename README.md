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
  - `x-article-print` as the canonical article-print reference
  - `x-article-to-print` as legacy migration material only
  - `morning-brief-print`
  - `templates/typewriter.md`
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
- `typewriter` as the default renderer
- markdown/HTML/JSON artifacts
- no LLM required
- `portable` PDF fallback when the premium renderer is unavailable

Quick start:

```bash
morning-paper init
morning-paper build
morning-paper print https://example.com
```

That creates a config at `~/.config/morning-paper/config.yaml` and outputs a
paper under `~/.local/share/morning-paper/<date>/`.

## CLI

```bash
morning-paper init
morning-paper build
morning-paper doctor
```

There are now two lanes:

- public product lane:
  - `init`
  - `build`
  - `print`
- legacy compatibility lane for the private Thoth deployment:
  - `pass1`
  - `pass2`
  - `pass3`
  - `assemble`
  - `render`
  - `digest`
  - `smoke`

Important:

- the extracted seed scripts still contain Thoth-specific paths
- those remain for the private deployment only
- the public `init/build` path is the portable product surface
- if you invoke a legacy command from a normal package install, Morning Paper
  will tell you to use `init` and `build` instead of failing with a traceback
- the canonical public renderer is now `typewriter`
- `portable` remains only as the fallback path when the richer renderer is unavailable

## Renderer Dependencies

Morning Paper now has two renderer modes:

- `typewriter` (default)
  - the actual product look
  - uses package-owned `typewriter`
  - prefers optional `WeasyPrint`
- `portable`
  - pure Python fallback
  - lower visual quality

The default config uses:

```yaml
outputs:
  renderer: typewriter
```

If `WeasyPrint` is not installed or its native libraries are unavailable, Morning Paper falls back cleanly and reports that in the build output.

For the richer renderer:

```bash
pip install "morning-paper[pretty]"
```

On macOS, the richer renderer may also need:

```bash
brew install pango gdk-pixbuf
```

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

1. Replace the remaining fallback article-print behavior with the full package-owned premium render path.
2. Add queueing commands for agent systems to stage tomorrow's paper without private harness assumptions.
3. Add optional LLM scoring as an extra, not a requirement.
4. Harden `print <url...>` for X article extraction and multi-article composition.
5. Keep the Thoth harness thin and private.
6. Reduce the legacy script lane over time.

## License

MIT
