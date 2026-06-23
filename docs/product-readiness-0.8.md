# Morning Paper 0.8 Product Readiness

Status: shipped source of truth for the 0.8 hardening pass. Current release: 0.8.3.

## Mission

Morning Paper 0.8 is the friend-ready personal newsroom release. A
nontechnical reader should be able to hand the job to Claude Code or Codex and
get a real first paper: engine installed, print stack proved, private newsroom
created, sources explained in normal language, first PDF opened, and a clear
feedback loop for tomorrow.

The product promise stays narrow:

- the reader owns the algorithm as files;
- the agent edits and composes the paper;
- the CLI renders, verifies, manages durable source queues, and offers a local
  scheduling fallback;
- a section with no data says "not configured";
- the paper lands once and ends.

## Current Truth

- `morning-paper` 0.8.3 is live on PyPI and tagged as `v0.8.3`; the repo
  carries one skill tree for Claude Code and Codex.
- The plugin surface is structurally healthy: Claude validation, Codex
  validation, install-smoke, and isolated host install checks exist, and both
  host manifests carry the same 0.8.3 semver.
- The public README now has the owned-algorithm mission and a copyable agent
  install prompt.
- The setup skill writes a real newsroom scaffold instead of empty folders and
  records setup state in `setup-state.json` plus `SETUP.md`.
- The private newsroom now has durable taste primitives:
  `EDITORIAL.md`, `VISUALS.md`, `SOURCES.md`, `DELIVERY.md`, and
  `TASTELOG.md`. These are newsroom-native, not copied product/design docs:
  they tell the agent what earns ink, how visuals should work in PDF/email,
  why sources exist, how the paper lands, and which taste changes were accepted
  or rejected over time.
- The edition skill has the editor model, source collection, review, return
  path, and durable intermediate files for interruption recovery.
- The source model is reader-stack-first: work streams, personal feeds, local
  knowledge, exports, folders, and agent/tool outputs can all arrive through
  feeds, collectors, host-agent workflows, or staged markdown for a specific
  edition date.
- Source inventory is honest about starter collector limits: the local drop
  reports supported staging candidates separately from unsupported files that
  need a converter collector.
- The scaffolded local-drop collector reports unsupported files at runtime too,
  so a collector transcript cannot say "ok" while silently skipping a PDF, CSV,
  JSON export, browser dump, or app-specific file.
- `doctor --strict` proves actual layout for the production print path.
- The chart furniture now has renderer-level guardrails: built-in `mp-bars`,
  `mp-spark`, and `mp-stats` align with the available measure, cap print
  density, clip labels, and add honest overflow notes instead of colliding or
  floating as narrow inserts.
- The review desk now has a deterministic visual-provenance check: standalone
  images, missing captions/source notes, explicit narrow widths, and one-item
  visual grids produce advisory findings before delivery.
- The print stack is deterministic across machines: broadsheet serif/sans
  faces now lead with vendored MP Serif (TeX Gyre Pagella) and MP Sans (Arimo),
  charts lead with vendored Courier Prime, and `@font-face` emits the correct
  format hint for OTF vs TTF files.
- The next skill architecture is drafted in `docs/newsroom-skill-suite.md`.
  It treats skills as newsroom desks over durable files, not as a pile of
  source adapters or a clone of generic product/design docs. It is explicitly
  future-facing: 0.8.x ships exactly `setup`, `edition`, and `writing`, and
  plugin smoke tests fail if an unfinished desk skill leaks into the surface.

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
- setup writes `EDITORIAL.md`, `VISUALS.md`, `SOURCES.md`, `DELIVERY.md`, and
  `TASTELOG.md` so the reader's taste can evolve in durable files;
- rerunning setup reads these files before asking questions.

### 3. Sources Start From What The Reader Already Has

As a reader, I can name the places my attention and work already live — email,
Slack, GitHub, Linear, saved articles, social or video exports, local folders,
newsletters, feeds, or tools — without learning Morning Paper's internals.

Acceptance:

- setup records source candidates in the newsroom;
- the agent validates feeds when possible and labels full-text versus summary;
- source inventory includes local newsroom collectors when a newsroom path is
  provided;
- source guidance covers work streams, personal feeds, local folders, exports,
  and tools the reader already uses;
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
  `draft.md`, `render-result.json`, `review.json`, `final-editor.json`,
  `final-editor.md`, `operator-answers.md`, and `feedback-plan.md`;
- the edition skill reads those files before restarting work;
- `morning-paper edition final-editor` performs an independent pre-delivery
  proof over the newsroom contracts, render result, review result, source
  warnings, visual warnings, page budget, and feedback route;
- delivery ends by asking for natural-language feedback;
- `feedback-plan.md` gives the agent a compaction-safe route from notes to the
  smallest durable newsroom file;
- `morning-paper edition apply-feedback` records stable reader notes into the
  selected durable file, `TASTELOG.md`, and the edition's `feedback-plan.md`;
- accepted feedback is routed to the smallest durable file:
  `EDITORIAL.md`, `VISUALS.md`, `SOURCES.md`, `DELIVERY.md`, `specs/`,
  `preferences/`, or `TASTELOG.md`. The supported routes include `editorial`,
  `voice`, `visuals`, `sources`, `prior`, `delivery`, `checks`, `the-read`,
  `front-page`, `reading`, and `taste`.

### Source Conversion UX

Unsupported local-drop files should become small private converter collectors,
not engine integrations. The public source conversion playbook
(`docs/source-conversion.md`) and scaffolded private playbook
(`collectors/CONVERTERS.md`) cover CSV, JSON, PDFs, Obsidian/folders, GitHub /
Main Branch/work systems, and social/video/browser exports. The invariant is
stable: convert to markdown, stage with `morning-paper stage --date`, report
skips/truncation/remote extraction honestly, and let the editor decide what
earns ink.

### Feedback Loop Quality

The feedback loop is explicit rather than magical. Agents use
`morning-paper edition apply-feedback` to route stable reader notes to the
smallest durable file, append `TASTELOG.md`, and update that edition's
`feedback-plan.md`. `docs/feedback-loop.md` gives route examples for editorial,
voice, visuals, sources, delivery, `prior`, `checks`, section specs, and
rejected taste. YAML targets receive comments first so they remain parseable.

## Dogfood Smoke

`scripts/dogfood_newsroom_smoke.py` is the current private-newsroom proxy. It
uses synthetic fixtures only, but exercises the user-shaped path: work pulse,
saved reading, local note, CSV/JSON export files, converter digest, staged
queue, rendered PDF, review, final-editor, feedback applied to `SOURCES.md`,
and a private-term scan over temp markdown/JSON/YAML/text artifacts. A passing
run may ship with `notes` when unsupported exports are visible; that is
intentional source honesty, not a failure.

## Native Recurrence Policy

The daily paper should lean into the recurring primitive of the host the reader
already uses:

- Codex: **automations**;
- Claude Code: **routines** with schedule triggers, including `/schedule` in
  the Claude Code CLI;
- ChatGPT: **scheduled tasks**.

Morning Paper should provide short prompts that ask the host agent to set up the
recurring run using the reader's newsroom and the `edition` workflow. Codex and
Claude paths should run where the private newsroom is visible. ChatGPT scheduled
tasks are a reminder/check-in path unless the reader has explicitly connected a
runner that can access the newsroom and render the PDF; they must not assume
project-file or local-newsroom access. The CLI's `routine` command remains a
deliberate local fallback for users who want
launchd/systemd/cron, not the default onboarding path.

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
- `doctor --json` reports Python, core source/parser dependencies
  (`feedparser`, `trafilatura`, `requests`), markdown/PDF dependencies
  (`markdown-it-py`, `fpdf2`, `Pillow`, `PyYAML`), WeasyPrint and its print
  stack (`tinycss2`, `cssselect2`, `pydyf`, `cffi`, `fontTools`), the enforced
  WeasyPrint support range, and native dependency status where detectable;
- CI exercises the pretty renderer path on supported platforms;
- docs and skills agree on Python, uv/pipx, native libraries, and fail-loud
  behavior.

The maintenance stance is deliberate: readers should not need to know what
WeasyPrint or trafilatura are, but Morning Paper does. WeasyPrint is bounded by
major version because it owns the print layout. Trafilatura is currently the
local article parser behind `article_extractor: local`; it is also bounded to
the current major line (`>=2.1,<3`). It stays an internal implementation
detail, but every release candidate must prove the installed artifact reports
and exercises it.

## Source Model

Entry points:

- local drop folder for files the reader or an agent already has;
- `stage` for one URL, file, or saved item;
- feed URLs when the reader already has them, including full-text feeds when
  `content:encoded` is present;
- contributor inbox;
- queue/status for budget-aware inspection;
- private collectors for work tools, personal feeds, local exports, and
  reader-owned data stores.

Private newsroom collectors and host-agent workflows:

- local drop folder for `.md`, `.txt`, `.url`, and synced-folder files;
- GitHub/`gh` activity;
- Main Branch business facts;
- browser/API/scrape outputs the reader already trusts;
- exports from YouTube, Instagram, TikTok, email, Slack, Obsidian, or other
  tools.

0.8 should not build hosted sync, OAuth connectors, a scraper registry, a
platform-specific scheduling layer, or a dashboard. The engine should expose
durable seams; the reader's newsroom and chosen host agent own private source
logic.
`morning-paper sources list|check --newsroom <path>` is the bridge between the
engine and that private logic: it inventories built-in feeds plus local
collector scripts, and `check` validates RSS reachability/full-text mode plus
collector shell syntax. When run from a scaffolded newsroom root, `sources
check` auto-detects that newsroom so a fresh agent does not miss the local drop
folder or collector scripts.

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
- `scripts/setup_scaffold_smoke.py --isolated` passes from a temporary venv and
  `HOME`, proving the CLI scaffold, `setup-state.json`/`SETUP.md` refresh,
  local-drop collector, edition workspace, render, review, and feedback
  artifact without touching the user's real config or routine;
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

0.8.2 candidate hardening: `doctor --strict` now checks the installed
WeasyPrint version against that supported range before running the render
self-test. An older renderer that imports is still not enough proof.

2026-06-22 release-candidate artifact proof for `0.8.2`: build from a clean
source copy, verify one semver across `pyproject.toml`, `__version__`, the
Claude Code manifest, and the Codex manifest, inspect the wheel/sdist for the
new feedback-plan/source-framing code, then install both wheel and sdist with
`[pretty]`. Both artifacts printed `morning-paper --version` as `0.8.2`,
resolved WeasyPrint `69.0`, passed `doctor --strict --json`, and rendered
`demo --output <tmp>/demo.pdf` as a real two-page PDF with JSON-only stdout.

2026-06-22 release-candidate artifact proof: build `0.8.1` from a clean source
copy, not an in-place tree with ignored `build/` residue. A dirty in-place
build can copy stale generated files into the wheel because setuptools reuses
`build/lib`; the clean-source build produced `morning_paper-0.8.1.tar.gz` and
`morning_paper-0.8.1-py3-none-any.whl` with no stale `typewriter` resources.
Both the wheel and sdist installed in fresh virtualenvs with `[pretty]`, printed
`morning-paper --version` as `0.8.1`, resolved WeasyPrint `69.0`, passed
`doctor --strict --json`, and rendered `demo --output <tmp>/demo.pdf` as a
real two-page PDF with JSON-only stdout.
This proof is now executable as
`python3 scripts/release_candidate_check.py --outdir dist --install-check`, and
the PyPI publish workflow runs that command before upload.

2026-06-22 typography proof: `0.8.1` vendors MP Serif and MP Sans so the
product no longer depends on Palatino, Helvetica, or Courier New being present
on the reader's machine. The front-page visual snapshot was regenerated against
the bundled fonts, and release checks confirm the font files and licenses ship
inside the wheel.

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
- `scripts/setup_scaffold_smoke.py --isolated` passes from a temporary venv and
  sandboxed home on the current tree: it runs `doctor --strict --json`, renders
  a demo PDF, scaffolds `Friend-Newsroom`, updates setup state, stages a local
  source via the scaffolded `collectors/local-drop.sh`, runs `edition prepare`,
  renders a PDF, saves all durable edition artifacts, and gets a clean review;
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

2026-06-22 Claude Code live check: an authenticated Claude session proved the
demo path by producing a real two-page PDF and opening it on screen. Treat this
as historical live-host evidence, not as the current release proof: the 0.8.2
release gate is the clean artifact check, strict Claude plugin validation,
host-plugin smoke, and sandbox setup smoke. Full interactive setup against the
user's real home/config remains deliberately unforced because it can install a
routine and write `~/.config`; any future live-agent setup-skill run should use
a temp home/config or explicit user approval.
