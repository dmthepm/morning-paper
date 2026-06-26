<div align="center">
  <img src="docs/assets/hero.jpg" alt="Morning Paper wordmark with a terminal composing a printed edition" width="720">

  <h1>Morning Paper</h1>

  <p><strong>A real paper every morning, from your private newsroom.</strong></p>
</div>

---

Morning Paper turns sources and preferences you own into a finite daily edition:
calm, source-backed, print-ready, and easy to mark up.

An agent composes the paper. The `morning-paper` CLI renders it to PDF. Your
private newsroom is the folder where sources, taste, delivery rules, memory,
and feedback live as files.

It is not a summarizer for a fixed feed. It is an owned algorithm you can
inspect: collect candidates from many places, remember what you have already
seen, filter repeats and low-signal noise, judge what deserves attention
against your taste, then print an edition you can correct.

It gets better the way an editor gets better. You read the paper, give notes in
natural language, and the agent turns stable feedback into durable newsroom
files such as `EDITORIAL.md`, `VISUALS.md`, `SOURCES.md`, `DELIVERY.md`, and
`TASTELOG.md`.

## Set Up With An Agent

Use a strong reasoning model and paste this into Claude Code or Codex:

```text
Install Morning Paper on this machine.

Morning Paper is an owned algorithm: an agent composes a newspaper from sources
and preferences I keep as files, and the `morning-paper` CLI renders it to a
print-ready PDF. Success is a real demo PDF on disk and open on my screen, not
just a successful package install.

Do this end to end:
1. Install the latest `morning-paper[pretty]`.
2. Confirm `morning-paper --version` matches the latest version on PyPI.
3. Run `morning-paper doctor --strict` and fix what it flags until the
   typewriter renderer and render self-test pass.
4. Run `morning-paper demo --open`.
5. If install chose the wrong Python or an old package, prefer:
   `uv tool install --python 3.13 "morning-paper[pretty]"`.

Stop when the demo PDF exists and is open on my screen. Show me the exact
commands that worked, the installed version, and the PDF path.

Do not set up my private newsroom yet. First prove the engine prints.
```

After the demo PDF is open, install the plugin and say:
`set up my morning paper`.

- **Claude Code** — `/plugin marketplace add dmthepm/morning-paper`, then
  `/plugin install morning-paper@morning-paper`
- **Codex** — `codex plugin marketplace add dmthepm/morning-paper`, then
  `codex plugin add morning-paper@morning-paper`

The plugin carries the `setup`, `edition`, and `writing` skills. The engine
package alone renders papers; the plugin teaches the agent how to create and
operate your private newsroom.

## Manual Install

```bash
uv tool install --python 3.13 "morning-paper[pretty]"
morning-paper --version
morning-paper doctor --strict
morning-paper demo --open
```

`pipx install --python 3.13 "morning-paper[pretty]"` is the main fallback. Use
`pip` only inside a virtual environment. On macOS, the print stack may also need
`brew install pango gdk-pixbuf`.

## What It Does

- Renders a demo paper with no config or network.
- Scaffolds a private newsroom repo with durable preferences and setup state.
- Adds URLs or local files to a dated Assignment Board with page estimates.
- Builds daily editions from configured sources and Assignment Board material.
- Lets local collector scripts bring in anything else: folders, exports,
  Obsidian vaults, GitHub activity, business systems, research reports, or
  agent-produced files.
- Typesets markdown through print style packs and chart directives.
- Reviews a finished edition for editorial problems before delivery.
- Works without an LLM key; the agent experience comes from Claude Code or
  Codex.

No database. No Docker. No hosted account required. No fabricated filler: a
missing source prints "not configured" or "nothing today."

## Sources

Morning Paper should meet your sources where they already live: the work that
needs your attention, the people trying to reach you, the tabs you saved, the
feeds you chose, the repos and tickets that changed, and the exports or folders
your tools already produce. The source layer is intentionally plural: files,
URLs, folders, inboxes, APIs, local scrapes, and agent-generated reports all
become source markdown before the editor decides what deserves ink.

Because sources are infinite, the open-source project does not try to ship a
universal adapter for every platform. It ships the newsroom contract: source
ledgers, collector scripts, Assignment Board intake, memory, review, and feedback routing. A
reader's private repo decides which collectors matter.

Examples:

- email newsletters, Slack channels, Discord threads, or contributor notes;
- GitHub activity, Linear tickets, Main Branch updates, or other work systems;
- Twitter/X, YouTube, TikTok, Instagram, podcast, or browser-history exports;
- folders, synced files, Obsidian vaults, saved articles, and local reports;
- one-off URLs added to tomorrow's Assignment Board.

Article extraction is replaceable plumbing. The current engine has registered
extractors, but the product promise is not "use this scraper." Local extraction
keeps URL capture on your machine; remote readers or browser/API scrapes should
be explicit choices recorded in the source item. The promise is: add
source-backed material honestly, record when extraction was partial or remote,
and let the editor decide what earns space.

See [docs/collectors.md](docs/collectors.md) for the Assignment Board intake contract.
See [docs/source-conversion.md](docs/source-conversion.md) for small converter
recipes when the local drop folder contains CSV, JSON, PDFs, vaults, work
exports, or social/video history.

## Recurring Editions

Prefer the native recurring primitive of the agent host you already use.
Morning Paper should not invent a second scheduling system unless you ask for a
local fallback.

Copy one of these into the host:

```text
Set up a Claude Code routine that builds my Morning Paper on my chosen cadence
(weekday mornings by default unless I say otherwise). Use my private newsroom
to make the next edition and follow the Edition Run Contract: check sources,
compose, render the PDF, review, run final-editor, update memory, open or
deliver it the way my DELIVERY.md says, and tell me only if the run failed or
needs my attention. If you are in the Claude Code CLI, use /schedule to create
the routine.
```

```text
Set up a Codex automation that builds my Morning Paper on my chosen cadence
(weekday mornings by default unless I say otherwise). Use this project/newsroom
to build the next edition through the Edition Run Contract, render the PDF,
update memory, and report the PDF path plus anything that needs my attention.
```

```text
Set up a scheduled task for my Morning Paper. On my chosen cadence, check
whether the next edition was produced or remind me to make the paper in my
newsroom. If you have an approved way to access the newsroom runner, use it;
otherwise do not pretend you rendered the PDF.
```

Claude Code calls this a **routine**. Codex calls it an **automation**. ChatGPT
calls it a **scheduled task**. The important distinction: Codex and Claude can
run inside the project/newsroom; ChatGPT tasks are useful for reminders or
connected workflows, but may not have access to project files and should not
claim local PDF work unless the local runner is actually available. If those are
not available or you specifically want a machine-local fallback, the CLI still
has `morning-paper routine install|status|uninstall`; use it deliberately, not
by default. Verify the host's current recurrence command before saving the
schedule; the Edition Run Contract is stable, host scheduling commands can
change.

## Styles

`morning-paper styles` lists the print family:

| Style | What it is |
| --- | --- |
| `broadsheet` | The newspaper you read |
| `brief` | A compact paper you work through with a pen |
| `field-card` | A boxed reference card |
| `zine` | A half-letter photocopier handout |

```bash
morning-paper render draft.md --style broadsheet --palette color
```

## For Agents

Read [AGENTS.md](AGENTS.md) first. The short version:

- agent composes, code renders;
- use `doctor --strict` as proof, not vibes;
- write setup and edition state to files before long work;
- use `edition apply-feedback` to record durable reader feedback;
- never put private newsroom facts in this public repo.

Useful CLI verbs: `newsroom`, `sources`, `stage`, `queue`, `edition`,
`estimate`, `render`, `review`, local-fallback `routine`, `doctor`.
`sources check` auto-detects a scaffolded newsroom when run from its root;
use `--newsroom <path>` when checking from somewhere else.

## Docs

- [PRODUCT.md](PRODUCT.md) and [DESIGN.md](DESIGN.md) — product and visual context for shaping public/product surfaces
- [ROLES.md](ROLES.md) — the newsroom role model and handoff contract
- [docs/roles/](docs/roles/) — role references for orchestrator, assignment editor, beat reporters, editor, copy desk, art desk, producer, and taste editor
- [docs/private-newsroom-operating-model.md](docs/private-newsroom-operating-model.md) — the owned-algorithm routine, multi-agent desk, budgets, memory, and delivery model
- [docs/edition-run-contract.md](docs/edition-run-contract.md) — the unattended completion promise for routines and automations
- [docs/newsroom-skill-suite.md](docs/newsroom-skill-suite.md) — current skill architecture and future split rules
- [docs/collectors.md](docs/collectors.md) — bring your own sources
- [docs/source-conversion.md](docs/source-conversion.md) — turn exports into Assignment Board material
- [docs/feedback-loop.md](docs/feedback-loop.md) — turn notes into durable taste
- [docs/composing.md](docs/composing.md) — layout, chart, and review vocabulary
- [docs/inbox.md](docs/inbox.md) — trusted contributor email intake
- [ROADMAP.md](ROADMAP.md) — what shipped, what's next
- [CHANGELOG.md](CHANGELOG.md) — release history

## Development

```bash
git clone https://github.com/dmthepm/morning-paper.git
cd morning-paper
pip install -e ".[dev,pretty]"
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src python -m pytest tests/
python scripts/setup_scaffold_smoke.py --isolated
python scripts/new_user_smoke.py
python scripts/dogfood_newsroom_smoke.py
python scripts/five_edition_loop_smoke.py
python scripts/source_shape_intake_smoke.py
python scripts/host_plugin_smoke.py
python3 scripts/release_candidate_check.py --outdir /tmp/morning-paper-dist --install-check
```

## License

MIT
