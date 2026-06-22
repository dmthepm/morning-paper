# Morning Paper 0.8 Product Readiness

Status: release-candidate source of truth for the 0.8 hardening pass.

## Mission

Morning Paper 0.8 is the friend-ready personal newsroom release. A
nontechnical reader should be able to hand the job to Claude Code or Codex and
get a real first paper: engine installed, print stack proved, private newsroom
created, sources explained in normal language, first PDF opened, and a clear
feedback loop for tomorrow.

The product promise stays narrow:

- the reader owns the algorithm as files;
- the agent edits and composes the paper;
- the CLI renders, verifies, schedules, and manages durable source queues;
- a section with no data says "not configured";
- the paper lands once and ends.

## Current Truth

- `morning-paper` 0.7.1 is live on PyPI; the current repo is prepared as the
  0.8.0 release candidate and carries one skill tree for Claude Code and Codex.
- The plugin surface is structurally healthy: Claude validation, Codex
  validation, install-smoke, and isolated host install checks exist, and both
  host manifests carry the same 0.8.0 semver.
- The public README now has the owned-algorithm mission and a copyable agent
  install prompt.
- The setup skill writes a real newsroom scaffold instead of empty folders and
  records setup state in `setup-state.json` plus `SETUP.md`.
- The edition skill has the editor model, source collection, review, return
  path, and durable intermediate files for interruption recovery.
- The source model is local-folder-first: HN and RSS are optional starter
  sources, and everything else can arrive through collectors that stage
  markdown for a specific edition date.
- `doctor --strict` proves actual layout for the production print path.
- The demo's chart furniture now has a renderer-level guardrail: built-in
  `mp-bars` and `mp-spark` visuals use the full available measure instead of
  floating as narrow inserts.

## User Stories

### 1. First Paper, No Terminal Expertise

As a nontechnical reader, I can paste one setup prompt into Claude Code or Codex
and receive a real demo PDF, then a real first edition from my private newsroom.

Acceptance:

- the agent confirms the latest package version;
- `doctor --strict` passes;
- `demo --open` writes a PDF and opens it;
- the Morning Paper plugin is installed for the host in use;
- the private newsroom exists with setup state, specs, preferences,
  collectors, memory, and edition folders;
- the first edition PDF exists and the agent reports its path.

### 2. Setup Can Resume

As a reader whose setup is interrupted, I can ask another agent to continue
without repeating every answer.

Acceptance:

- setup writes `setup-state.json` and `SETUP.md`;
- both record installed version, demo proof path, plugin state, newsroom path,
  source choices, printer choice, pending questions, and next action;
- rerunning setup reads these files before asking questions.

### 3. Sources Start From What The Reader Already Has

As a reader, I can name sites, newsletters, folders, exports, feeds, or tools
without knowing what RSS is.

Acceptance:

- setup records source candidates in the newsroom;
- the agent validates feeds when possible and labels full-text versus summary;
- source inventory includes local newsroom collectors when a newsroom path is
  provided;
- HN is presented as an optional starter source, not the product identity;
- skipped or credentialed sources have a clear next action;
- local folder/drop-folder ingestion is available as a collector recipe.

### 4. The Editor Reads The Right Date

As the editor, I can tell whether I am collecting for today's paper or staging
something for tomorrow.

Acceptance:

- edition collectors target the edition date explicitly;
- ad hoc `stage` keeps its "read this tomorrow" default;
- `queue` and future queue commands expose the date they are reading;
- tests cover today/tomorrow behavior.

### 5. Edition Work Survives Compaction

As an agent composing a long edition, I can resume from files after context
compaction or a process interruption.

Acceptance:

- edition work writes durable intermediate files early:
  `source-inventory.json`, `collector-report.md`, `queue-snapshot.json`,
  `draft.md`, `render-result.json`, `review.json`, and
  `operator-answers.md`;
- the edition skill reads those files before restarting work;
- delivery ends by asking for natural-language feedback.

## Print Stack Policy

WeasyPrint is the production renderer. Morning Paper should understand and
lean on it, not rebuild it. WeasyPrint owns:

- HTML/CSS layout;
- paged media;
- page counters and margin boxes;
- page-break, orphan, widow, and keep-together behavior;
- font loading through CSS and `@font-face`;
- PDF writing;
- page count via rendered document pages;
- URL/resource fetching hooks where needed.

Morning Paper owns:

- install guidance;
- dependency verification;
- the supported WeasyPrint major-version bound;
- print-specific style packs;
- source honesty;
- agent/editor workflow;
- durable newsroom state;
- friend-ready error messages.

0.8 acceptance:

- the `[pretty]` extra stays on the current supported WeasyPrint major line
  and is advanced deliberately after a clean install/render smoke;
- `doctor --strict` performs a real layout pass, not just import checks;
- `doctor --json` reports Python, WeasyPrint, tinycss2, cssselect2, pydyf,
  cffi, Pillow, and native dependency status where detectable;
- CI exercises the pretty renderer path on supported platforms;
- docs and skills agree on Python, uv/pipx, native libraries, and fail-loud
  behavior.

## Source Model

Built in:

- RSS feeds, including full-text feeds when `content:encoded` is present;
- optional Hacker News starter source;
- `stage` for one URL or file;
- contributor inbox;
- queue/status.

Private newsroom collectors:

- local drop folder for `.md`, `.txt`, `.url`, and synced-folder files;
- GitHub/`gh` activity;
- Main Branch business facts;
- Apify or browser-driven scrapes;
- exports from YouTube, Instagram, TikTok, email, Slack, Obsidian, or other
  tools.

0.8 should not build hosted sync, OAuth connectors, a scraper registry, or a
dashboard. The engine should expose durable seams; the reader's newsroom owns
private source logic.
`morning-paper sources list|check --newsroom <path>` is the bridge between the
engine and that private logic: it inventories built-in feeds plus local
collector scripts, and `check` validates RSS reachability/full-text mode plus
collector shell syntax.

## Out Of Scope For 0.8

- hosted SaaS;
- built-in Dropbox/iCloud/Google Drive OAuth;
- built-in X/Twitter, YouTube, Slack, or email search connectors beyond the
  existing contributor inbox;
- automatic LLM ranking inside the CLI;
- a full interactive config TUI;
- replacing WeasyPrint.

## Verification Plan

Before 0.8 is complete:

- unit tests pass;
- plugin validators pass;
- install-smoke passes;
- `scripts/host_plugin_smoke.py` passes, proving isolated Claude Code and
  Codex homes can discover, install, and load the shared setup/edition/writing
  skills from a clean local marketplace copy;
- `doctor --strict` proves rendering;
- `demo --open` renders and opens a PDF in the first-run flow;
- `scripts/setup_scaffold_smoke.py` passes from a temporary `HOME`, proving
  the CLI scaffold, `setup-state.json`/`SETUP.md` refresh, local-drop
  collector, edition workspace, render, review, and feedback artifact without
  touching the user's real config or routine;
- `scripts/fresh_friend_smoke.py` passes the five local persona simulations:
  creator/news reader, business owner/Main Branch, technical agent,
  nontechnical RSS/newsletter, and local-folder/source-dump;
- a live Codex agent run uses the installed plugin path to produce a first PDF
  from a temp home/config and clean local source;
- a live Claude Code agent run uses the installed plugin path to produce a
  first PDF;
- setup and edition resume from files;
- source/date behavior is explicit and tested;
- README, AGENTS.md, setup skill, edition skill, CLI help, and Roadmap agree.

2026-06-22 dependency proof: a clean virtualenv installed the current
`.[pretty]` extra, resolved WeasyPrint `69.0`, passed
`morning-paper doctor --strict --json` with a one-page render self-test, and
rendered `morning-paper demo --output <tmp>/demo.pdf`. This is the maintenance
contract: readers should not need to know WeasyPrint exists, but Morning Paper
must track its releases, constrain the supported major line, and prove the
print path in CI before shipping.

2026-06-22 release-candidate artifact proof: build `0.8.0` from a clean source
copy, not an in-place tree with ignored `build/` residue. A dirty in-place
build can copy stale generated files into the wheel because setuptools reuses
`build/lib`; the clean-source build produced `morning_paper-0.8.0.tar.gz` and
`morning_paper-0.8.0-py3-none-any.whl` with no stale `typewriter` resources.
Both the wheel and sdist installed in fresh virtualenvs with `[pretty]`, printed
`morning-paper --version` as `0.8.0`, resolved WeasyPrint `69.0`, passed
`doctor --strict --json`, and rendered `demo --output <tmp>/demo.pdf` as a
real two-page PDF with JSON-only stdout.

## Live Acceptance Notes

2026-06-22 Codex live setup-skill check: passed against the current local
worktree from a temporary `CODEX_HOME`, `HOME`, and `XDG_CONFIG_HOME` with the
Morning Paper plugin installed from a local marketplace copy. The live Codex
session loaded the plugin's setup, edition, and writing skills; created a fresh
temp workspace; ran the local engine; ran `doctor --strict`; created
`Friend-Newsroom`; refreshed setup state; staged one safe synthetic markdown
source through the scaffolded `collectors/local-drop.sh`; ran
`edition prepare`; refreshed the collector report and queue snapshot; composed
`draft.md`; rendered a one-page broadsheet PDF; ran review to `clean`; and
wrote `LIVE-CODEX-SETUP-RESULT.json`.

Independent proof from that run:

- result JSON parsed with `ok: true`;
- rendered PDF existed, was non-empty, and began with `%PDF-`;
- `render-result.json` reported 1 page and 0 warnings;
- `review.json` reported `status: clean` after an initial reviewer nudge led
  the agent to revise the draft headline and section structure;
- reviewer artifact resolution now follows `render-result.json` to the
  rendered `edition/edition.md`/`edition/edition.json` pair instead of
  accidentally reviewing workspace metadata;
- after updating the deterministic smoke fixture to use real claim headlines,
  `scripts/fresh_friend_smoke.py` now produces five PDFs and five clean
  reviews on the current tree;
- `scripts/setup_scaffold_smoke.py` passes from a sandboxed home on the current
  tree: it runs `doctor --strict --json`, renders a demo PDF, scaffolds
  `Friend-Newsroom`, updates setup state, stages a local source via the
  scaffolded `collectors/local-drop.sh`, runs `edition prepare`, renders a PDF,
  saves all durable edition artifacts, and gets a clean review;
- the edition workspace contained source inventory, collector report,
  queue snapshot, draft, render result, review JSON, operator answers, and
  rendered PDF/HTML/Markdown/JSON artifacts.

Two useful catches from the live run:

- a fully isolated editable `pip install` failed when network name resolution
  was unavailable because build dependencies could not be fetched; the run
  recovered with a workspace venv using system site packages and
  `--no-build-isolation --no-deps`;
- `morning-paper render <draft.md>` renders the draft as written; it does not
  expand the build-pipeline `<!-- Staged for today -->` placeholder. The
  edition agent should compose staged content into `draft.md` before rendering.
- `morning-paper review <prepared-edition-dir>` must review the rendered
  artifacts, not the workspace metadata; this is now covered by tests.
- scaffolded collector scripts call `morning-paper` from `PATH`; in a source
  checkout simulation, a workspace-local shim is useful so collectors exercise
  the current worktree instead of any globally installed package.

2026-06-22 Claude Code live check: passed from an authenticated Claude session.
The session ran the live 0.7.1 demo, produced a real two-page PDF, and opened it
on screen. The deliberately unforced piece is full interactive setup against
the user's real home/config because it can install a routine and write
`~/.config`; deterministic sandbox setup is now covered by
`scripts/setup_scaffold_smoke.py`, while a true live-agent setup-skill run
should still use a temp home/config or explicit user approval.
