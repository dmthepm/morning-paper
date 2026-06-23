# Agent contract — Morning Paper

You are setting up or running a personal newspaper for the human who summoned
you. Read this before you touch anything.

## What this is

Morning Paper is an owned algorithm. The reader's sources and preferences live
in files they keep, not a feed they rent. An agent — you — composes each day's
paper from those sources; the `morning-paper` CLI renders it to a print-ready
PDF. The product is the paper on the desk, not a successful install.

The division of labor never moves: **the agent composes, code renders, code
never writes the paper.** When a section has no data, it prints "not
configured" — never an invented headline, number, or quote.

## The two repos — never confuse them

- **This repo (`morning-paper`)** — the public engine and the plugin. The skill
  bodies under `plugins/morning-paper/skills/` are the single source both
  Claude Code and Codex load. You may read all of it.
- **The reader's newsroom repo** — private, created during setup, holds their
  preferences as files (the operating constitution, section specs, editorial
  taste, visual desk, source desk, delivery preferences, voice, collectors,
  memory, and taste log). The durable taste files are `EDITORIAL.md`,
  `VISUALS.md`, `SOURCES.md`, `DELIVERY.md`, and `TASTELOG.md`; update the
  smallest one that captures the reader's feedback. You write there freely on
  the reader's behalf. Nothing from a newsroom ever belongs in this public repo.

## Skills

Three skills, one body each, shared verbatim across hosts:

- **setup** — cold start. Installs the engine, interviews the reader, scaffolds
  their newsroom with working contracts (not empty folders), and offers
  host-native recurrence. The CLI routine is a local fallback, not the default.
- **edition** — composes, renders, reviews, and delivers today's paper.
- **writing** — the revision discipline for every word the paper prints.

## How to install the engine (verify, do not assume)

Setup touches local Python tooling and native print libraries. The package
manager can resolve an old version or the wrong interpreter and report success
anyway, so check each step against reality:

1. `uv tool install --python 3.13 "morning-paper[pretty]"` (pinning the
   interpreter avoids a beta Python with no print-stack wheels).
   `pipx install --python 3.13 "morning-paper[pretty]"` or a clean venv are
   equal fallbacks.
2. `morning-paper --version` — confirm it matches the latest on PyPI.
3. `morning-paper doctor --strict` — fix until it reports the typewriter
   renderer ready and the render self-test passed (macOS may need
   `brew install pango gdk-pixbuf`).
4. `morning-paper demo --open` — confirm the PDF exists on disk and opens on
   screen. That is the proof.

The CLI speaks JSON. `morning-paper doctor --json` reports install status;
`newsroom`, `edition`, `sources`, `stage`, `queue`, `estimate`, `render`,
`review`, and local-fallback `routine` are the verbs the edition skill drives. `newsroom init
<path>` scaffolds the private repo; `newsroom state <path> --set key=value`
keeps setup-state/SETUP current; `edition prepare <path>` creates the durable
files an agent can resume from; `edition final-editor <path>` writes the
pre-delivery ship rule after render/review; `sources check` inventories
configured sources and auto-detects a scaffolded newsroom when run from its root;
`sources check --newsroom <path>` explicitly inventories local collector scripts;
`queue list|show|remove` inspects and prunes staged material; `edition
apply-feedback <path> --route ROUTE --note ...` records stable reader feedback
into the smallest durable file, TASTELOG, and that edition's feedback plan.
Use `editorial`, `voice`, `visuals`, `sources`, `prior`, `delivery`, `checks`,
`the-read`, `front-page`, `reading`, or `taste`. `stage` takes a real file
path, never `/dev/stdin` — write a temp file first. Unsupported local-drop
files become private converter collectors from `collectors/CONVERTERS.md` or
`docs/source-conversion.md`; do not add a hosted scraper/OAuth registry to the
engine without an explicit scope change.

## The single-source rule (hold it forever)

Skill bodies live once, under `plugins/morning-paper/skills/<name>/SKILL.md`,
host-neutral and self-contained. Each host gets its own thin manifest pointing
at that one tree: `.claude-plugin/plugin.json` for Claude Code,
`plugins/morning-paper/.codex-plugin/plugin.json` for Codex (with `interface`,
no `hooks`). Every release bumps one strict-semver version across both
manifests together. Never fork a skill's prose between hosts.
