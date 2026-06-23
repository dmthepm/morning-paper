# Changelog

All notable changes to Morning Paper will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added
- `morning-paper edition final-editor` now writes `final-editor.json` and
  `final-editor.md`, giving agents a separate pre-delivery ship rule after
  render and review. It checks required edition artifacts, the PDF path, page
  budget, review status, visual/source warnings, and the feedback route before
  the reader sees the paper.
- Source conversion guidance now lives in both the public
  `docs/source-conversion.md` playbook and each scaffolded newsroom's
  `collectors/CONVERTERS.md`, giving agents practical local-first recipes for
  CSV, JSON, PDF, Obsidian/folder, GitHub/Main Branch/work, and social/video
  exports without expanding the engine into a scraper registry.
- `docs/feedback-loop.md` now documents how natural-language and desk-sheet
  feedback should become the smallest durable newsroom change, including
  rejected taste and YAML-safe preference updates.
- `scripts/dogfood_newsroom_smoke.py` now exercises a synthetic but
  user-shaped private newsroom path: work pulse, saved reading, local note,
  CSV/JSON exports, converter digest, render, review, final-editor, feedback
  routing, and private-term scan.

## [0.8.2] - 2026-06-22

### Added
- **Durable feedback plans.** `morning-paper edition prepare` now writes
  `feedback-plan.md` beside `operator-answers.md`, giving agents a
  compaction-safe route from reader notes to the smallest durable newsroom file
  (`EDITORIAL.md`, `VISUALS.md`, `SOURCES.md`, `DELIVERY.md`, `specs/`,
  `preferences/`, collectors, staging, or `TASTELOG.md`). The edition skill and
  scaffolded newsroom constitution now require the agent to record Applied
  Feedback with paths changed.
- **Source-stack-first onboarding.** Current-facing setup/source guidance now
  frames sources as work streams, personal feeds, local knowledge, exports,
  folders, and tool/agent outputs instead of centering any one public feed.
- **Visual integration guardrails.** Shared figure/image CSS, source-note
  primitives, visual-grid support, field-card chart styling, and visual QA
  instructions make agent-created charts and illustrations fit the surrounding
  page instead of floating awkwardly.

### Changed
- `sources list` / `sources check` now suggest concrete reader-owned source
  classes such as email/newsletters, Slack, GitHub, Linear, local folders,
  social exports, video feeds, RSS/feed URLs, and saved files when no source is
  configured.
- `sources list` / `sources check` now auto-detect a scaffolded newsroom when
  run from its root, so the local drop folder and collector scripts appear even
  when a fresh agent forgets `--newsroom .`.
- `sources list` / `sources check` now separate supported local-drop candidates
  from unsupported files. The starter collector stages `.md`, `.markdown`,
  `.txt`, and `.url`; PDFs, CSVs, JSON exports, browser dumps, and other files
  are reported by both source inventory and the scaffolded local-drop collector
  as needing a converter collector instead of being implied as ready-to-stage.
- Package/plugin metadata, README, collector docs, scaffolded newsroom files,
  and smoke tests now use the broader personal-newsroom source model.
- Active setup, edition, collector, roadmap, and readiness docs now describe a
  newsroom intake layer for work systems, people, saved reading, exports,
  folders, and agent outputs instead of centering public feed examples.
- `scripts/fresh_friend_smoke.py` now checks first-edition quality, not just
  PDF existence: The Read, source inventory, page budget, feedback route,
  durable feedback file routing, clean review status, and reader-owned next
  source candidates must all be present.
- `scripts/setup_scaffold_smoke.py --isolated` now creates a temporary
  `[dev,pretty]` install before running setup smoke, so release verification is
  not confused by a developer machine with stale WeasyPrint/trafilatura.
- Remote article fallback is now explicit. `article_extractor: local` keeps URL
  capture on the reader's machine; it no longer escalates to the Jina remote
  reader unless `remote_extractor_fallback: true` is set. Direct
  `article_extractor: jina` remains available for readers who choose it.
- **Executable feedback loop.** `morning-paper edition apply-feedback` records
  stable reader notes into the selected durable newsroom file, appends
  `TASTELOG.md`, and updates the edition's `feedback-plan.md` so feedback
  survives compaction as an auditable change.
- `edition apply-feedback` now supports narrower scaffolded routes:
  `voice`, `prior`, `checks`, `the-read`, `front-page`, and `reading`, so
  stable notes can land in `preferences/` and `specs/` instead of being forced
  into broad desk files.
- Feedback recorded to YAML targets (`prior` and `checks`) is appended as YAML
  comments, keeping `preferences/algorithm-prior.yaml` and
  `preferences/checks.yaml` parseable until an agent promotes the note into a
  concrete setting.
- **Source vocabulary cleanup.** CLI help, generated config comments, source
  inventory JSON, setup guidance, roadmap, and demo copy now say source stack,
  entry points, and reader-owned sources instead of teaching a feed-first
  mental model.
- **Dependency visibility for maintenance.** `doctor --json` now reports the
  core source/parser dependency versions (`feedparser`, `trafilatura`,
  `requests`) and markdown/PDF dependency versions alongside the WeasyPrint
  print stack, `trafilatura` is bounded to the current supported major line
  (`>=2.1,<3`), and the release-candidate checker fails if a clean install does
  not expose those versions.
- **Exact shipped skill contract.** Plugin validation and host smoke tests now
  fail if the 0.8.x plugin exposes anything other than the shipped
  `setup`/`edition`/`writing` skill set. Future newsroom desk skills must land
  deliberately with updated manifests, evals, and docs.
- **Host-native recurrence wording.** Setup/readme guidance now names Claude
  Code `/schedule` for routines and warns that ChatGPT scheduled tasks must not
  assume project-file or local-newsroom access.
- `morning-paper review` now includes an advisory `visual-provenance` check for
  standalone images, missing captions/source notes, explicit narrow visual
  widths, and one-item visual grids.

### Fixed
- `doctor --strict` now refuses to certify an imported WeasyPrint renderer when
  the installed version is outside Morning Paper's supported range
  (`>=69.0,<70`). Casual `doctor` still reports the situation with install
  guidance, but the strict proof gate no longer treats an old native print
  stack as production-ready.

### Verified
- Current local release-candidate checks pass: unit tests, Codex plugin
  validation, Claude Code plugin validation, host plugin smoke, setup scaffold
  smoke, fresh-friend persona simulations, and clean wheel/sdist install checks
  with WeasyPrint 69.0 and a rendered demo PDF.

## [0.8.1] - 2026-06-22

### Fixed
- **Deterministic typography — the paper renders identically on every machine.**
  The broadsheet body previously leaned on system fonts (Palatino, Helvetica
  Neue) and chart labels on Courier New, so a paper that looked right on macOS
  fell back to substitute fonts on Linux (and any machine without those faces
  installed). Two metric-compatible libre families are now vendored and wired
  via `@font-face` over absolute `file://` URLs: **MP Serif** (TeX Gyre
  Pagella, a Palatino-metric serif, GUST Font License) and **MP Sans** (Arimo,
  a Helvetica/Arial-metric sans, SIL OFL 1.1). Every pack leads its serif/sans
  with the bundled face and keeps the legacy system names only as fallback;
  chart labels lead with the vendored Courier Prime. The cross-platform
  front-page visual snapshot now renders the same glyphs everywhere instead of
  diverging by ~11 mean pixel levels on Linux.
- `_font_face_css` now emits the correct `format()` hint per file
  (`opentype` for `.otf`, `truetype` for `.ttf`) so WeasyPrint loads the OTF
  serif instead of skipping it.
- `tests/test_friend_contract.py` reads `pyproject.toml` with a tolerant regex
  instead of `tomllib`, so the friend-contract guardrail runs on Python 3.10
  (the package's floor) instead of erroring at import.

## [0.8.0] - 2026-06-22

### Added
- **Friend-ready personal newsroom setup.** `morning-paper newsroom init
  <path>` now scaffolds a private newsroom repo with resumable setup state
  (`setup-state.json` + `SETUP.md`), the operating constitution (`CLAUDE.md`),
  section specs, source collectors, edition templates, memory files, and
  newsroom-native taste files: `EDITORIAL.md`, `VISUALS.md`, `SOURCES.md`,
  `DELIVERY.md`, and `TASTELOG.md`. These are the durable files an agent edits
  when the reader gives natural-language feedback.
- **Resumable setup state.** `morning-paper newsroom state <path> --set
  key=value` updates `setup-state.json` and refreshes `SETUP.md`, recording the
  installed version, strict doctor proof, demo PDF path/open status, Claude
  Code/Codex plugin state, source choices, printer choice, pending questions,
  and next action.
- **Source inventory and local collector bridge.** `morning-paper sources
  list|check --newsroom <path>` inventories built-in feeds plus local newsroom
  collector scripts, checks RSS reachability/full-text mode, and validates
  collector shell syntax. The scaffold includes a local drop-folder collector
  for `.md`, `.txt`, `.url`, synced-folder files, and agent-produced files.
- **Queue inspection verbs.** `morning-paper queue list|show|remove` gives
  agents a durable, file-backed way to inspect and prune staged material
  against the page budget.
- **Compaction-safe edition workspaces.** `morning-paper edition prepare
  <newsroom>` writes the files a compacted or fresh agent needs before
  composing: `source-inventory.json`, `collector-report.md`,
  `queue-snapshot.json`, `draft.md`, `render-result.json`, `review.json`, and
  `operator-answers.md`.
- **First-run PDF opening.** `morning-paper demo --open` now renders the
  synthetic paper, reports an `opened` JSON payload, and asks the platform to
  open the PDF (`open`, `start`, or `xdg-open`) so setup ends with the product
  on screen.
- **Release verification machinery.** New smoke scripts cover setup scaffold,
  fresh-friend personas, host plugin installs, install-smoke, and clean release
  artifact builds. `scripts/release_candidate_check.py` builds from a clean
  source copy, rejects stale build debris, and can install both wheel and sdist
  with `[pretty]` to prove `doctor --strict` and demo rendering before publish.

### Changed
- **WeasyPrint is the production print stack.** The `[pretty]` extra is bounded
  to the supported WeasyPrint major line (`>=69,<70`), CI exercises the pretty
  renderer path, and `doctor --strict` now runs a real layout self-test instead
  of only checking imports. `doctor --json` reports Python, WeasyPrint,
  tinycss2, cssselect2, pydyf, cffi, Pillow, fontTools, and detectable native
  Pango status.
- **One canonical friend path.** README, `AGENTS.md`, the setup skill, CLI help,
  roadmap, and tests now agree: install with a pinned Python, run
  `morning-paper doctor --strict`, run `morning-paper demo --open`, then install
  the Claude Code or Codex plugin and let the `setup` skill create the private
  newsroom.
- **Sources are reader-stack-first.** Source docs and scaffolded `SOURCES.md`
  now frame the paper around work streams, personal feeds, local knowledge,
  exports, folders, and collector-backed tools the reader already uses.
- **Date semantics are explicit.** Edition collectors target the edition date;
  ad hoc `stage` remains "read this later" and defaults to tomorrow.
- **Visuals gained print guardrails.** Built-in `mp-bars`, `mp-spark`, and
  `mp-stats` use the available measure, cap density, clip labels, and add
  honest overflow notes instead of colliding or floating as narrow inserts.
- **Package and plugin copy now match the mission.** Project metadata and both
  plugin manifests describe Morning Paper as a personal newsroom / owned
  algorithm, not a generic PDF builder.

### Fixed
- The demo's "make it yours" hint now uses the pinned `uv tool install
  --python 3.13 "morning-paper[pretty]"` path.
- `morning-paper review <prepared-edition-dir>` now follows `render-result.json`
  to the rendered artifacts instead of accidentally reviewing workspace
  metadata.
- Release builds now run from a clean source copy so stale `build/` artifacts
  cannot leak removed resources into the wheel.

### Verified
- Current local release-candidate checks pass: unit tests, Codex plugin
  validation, Claude Code plugin validation, install-smoke, host plugin smoke,
  setup scaffold smoke, fresh-friend persona simulations, `doctor --strict`,
  and clean wheel/sdist install checks with WeasyPrint 69.0 and a rendered demo
  PDF.

## [0.7.1] - 2026-06-22

### Added
- **Codex support — the plugin now installs on Claude Code and Codex from one repo.** The skill bodies moved to `plugins/morning-paper/skills/<name>/SKILL.md` and are the single source both hosts load. The Claude Code manifest (`.claude-plugin/plugin.json`) points at them with `"skills": "./plugins/morning-paper/skills/"`; a new Codex manifest (`plugins/morning-paper/.codex-plugin/plugin.json`) points at the same tree with `"skills": "./skills/"` relative to its own plugin root, carries the required `interface` block, omits `hooks` (Codex validation rejects it), and pins the same strict-semver version. A new Codex marketplace (`.agents/plugins/marketplace.json`) lists the plugin at `./plugins/morning-paper`. No skill prose is duplicated and no skill body differs between hosts. Verified end to end on this machine: `claude plugin validate ./ --strict` passes, the official Codex `validate_plugin.py` passes, and a live `codex plugin add morning-paper@morning-paper` installs with all three skills (`setup`, `edition`, `writing`) present
- **`AGENTS.md`** — the repo-level cross-agent contract Codex and other agents read: the owned-algorithm product shape, the public-engine / private-newsroom boundary (never write the public repo), the verify-each-step install discipline, and the single-source rule
- **CI gates for the plugin surface and a Codex structural validator.** A new `plugins` CI job runs `claude plugin validate ./ --strict`, the new `scripts/validate_codex_plugin.py` (mirrors the official Codex validator's rules — strict semver, required `interface`, no `hooks`, `skills` resolves to `skills`, the marketplace source is a real subdirectory), and `scripts/install_smoke.py` (proves both manifests resolve to the same real skills tree carrying all three skills, and that the two manifest versions match)

### Changed
- **Install guidance pins the interpreter.** The README, the `setup` skill, and `AGENTS.md` now recommend `uv tool install --python 3.13 "morning-paper[pretty]"` (and `pipx install --python 3.13 …`). A bare `uv tool install` can pick a Python beta with no WeasyPrint wheels and resolve an older release or fail; the pin avoids it. Each path now also says to confirm `morning-paper --version` against PyPI before trusting the install
- **README mission rewrite + a "Set Up With An Agent" section.** The opening states the product as an owned algorithm — an agent composes from sources and preferences you keep as files, code renders the PDF; print-first, anti-feed, optional connections that make it richer. The agent-setup section carries a copyable prompt that teaches the agent how to think (success is a demo PDF on disk, not a package install; verify each step) and routes friends to the plugin on both hosts; a smaller manual fast-path follows
- The `setup` skill's two deepening links (`docs/collectors.md`, `examples/brief.example.md`) became absolute GitHub URLs, so they resolve from an installed plugin that ships only the skill bodies; `docs/architecture-decisions.md` §16 and `docs/composing.md` were updated to the dual-host skill-distribution layout

## [0.7.0] - 2026-06-22

### Added
- **Full-text RSS — feeds that ship the whole article now print as real reads.** `fetch_rss_feeds` reads `content:encoded` (feedparser's `entry.content`) into a new `SourceItem.body` field, kept whole (never truncated). `summary` stays the short blurb, still capped at 280 chars. The broadsheet build reads (`_render_broadsheet_reads`) and the markdown render print the full `body` when present, falling back to the capped summary for summary-only feeds — so a full-text feed (Substack/Atom full, paid full-text feeds) prints the essay, not a 280-char clip, while summary feeds are unchanged. The build JSON carries `body` automatically. The engine learns nothing about any specific feed: it just stops mangling full-text RSS
- **The setup scaffold — `setup` writes the newsroom's working contracts, not empty folders.** The `setup` skill's §5 now generates a genericized, fully working newsroom: an operating constitution (`CLAUDE.md`) with the ordered LAW input list and the honesty rule; section specs led by `specs/the-read.md` (the four moves: GAPS / CONNECTIONS / ALIGNMENT-DRIFT / NEXT MOVE; the NO-MIRRORING / OUTSIDE-IN / SURPRISE-ONCE rules) plus `front-page.md`, `reading.md`, and a five-field `_template.md`; `preferences/` (voice template, commented `algorithm-prior.yaml` — the installable artifact behind "own your algorithm" — and a commented `checks.yaml`); `memory/` (an EMPTY `reads-ledger.md`, an empty `MEMORY.md` index, a `threads/` README); an `editions/` dir with a `*.pdf` gitignore; and a `collectors/` contract (`_lib.sh`, `run_all.sh`, and two worked examples) that follows the public `morning-paper stage`/`queue.json` contract — never the old `editions/<date>/data/` path. The result is a paper a fresh friend gets end-to-end, with zero operator-specific content
- The `examples/brief.example.md` skeleton is now the edition skeleton the scaffold copies into the newsroom and the `edition` skill references

### Changed
- `setup` install line is uv-first (`uv tool install "morning-paper[pretty]"`), matching the README, and documents `uv tool upgrade morning-paper` as the separate engine-update step; the `edition` skill's Collect step names `collectors/run_all.sh` and the staging contract explicitly; the in-CLI update notice points at `uv tool upgrade` / `pipx upgrade` instead of bare pip
- Docs tightened and re-baselined: `architecture-decisions.md` §8 (CLI surface refreshed to the real stable verbs), §11/§12 (the 0.4.2 Jina-to-local amendments folded into the base text so the doc stops contradicting itself — local is the default), §16 (skill-distribution path corrected to `skills/`); `docs/collectors.md` fixed the broken `/dev/stdin` collector example (the CLI requires a real file) and points at the scaffolded example collectors; ROADMAP re-baselined through 0.7.0 with the stale `v0.4` "Next" regression removed; the duplicate `### Added` block under 0.4.0 merged

### Removed
- The thin shadowing skill stub `.claude/skills/morning-paper/SKILL.md` (no frontmatter, never shipped through the plugin loader, claimed jina was the default, and shadowed the real `setup`/`edition`/`writing` skills during local dev) and the now-cut `docs/product-spec.md` (Devon's private brief spec) and `docs/qa-contract.md` (superseded by the `review` verb)

## [0.6.1] - 2026-06-22

### Fixed
- **`review` headline length checks no longer cry wolf on deck/department titles.** The `headline-line-count` and `headline-length` checks (shipped in 0.6.0) treated EVERY composed head the same — `.mg-title`, `.dept-title`, and `.oc-title` alike — and flagged each one that ran past the line/character budget. But `.dept-title` is a broadsheet DEPARTMENT title: a multi-sentence summary that the renderer emits for every read/department/staged item, long BY DESIGN. The result was ~90% false positives on a normal edition (a known-good delivered edition trips them too), which trained the editor to ignore the one QC gate the `edition` skill says to act on. The two LENGTH checks now flag only TRUE headlines — the lead/front head (`.mg-title`), a printed article's headline (`.article-title`), the field-card title (`.oc-title`), and markdown `#`/`##` heads in the simpler packs — and EXEMPT deck/department/section-label elements (`.dept-title`, `.mg-dek`, kickers). The class → role map is explicit and documented in `reviewers.py` (`_TRUE_HEAD_CLASSES` / `_DECK_HEAD_CLASSES`, `Headline.role`). The other headline checks are unchanged: `headline-verb-presence`, `hed-dek-redundancy`, and `duplicate-headline` still read every head regardless of role, so a label-style department title with no verb still flags. A genuinely-overlong real headline still flags exactly as before — only the deck false positives drop out
- Tests: a long `.dept-title` deck does NOT trip `headline-line-count` or `headline-length`; a real `.mg-title` headline over the line/char limit still flags (both the line-count flag and the length nudge); the existing length-check fixtures were retargeted from `.dept-title` (now a deck) to `.mg-title` (a true headline)

## [0.6.0] - 2026-06-21

### Added
- **The layout taste layer — keep-together craft, free in every pack.** A new shared base stylesheet (`resources/styles/_base.css`) is composed BEFORE each style pack, so the keep-together behavior that until now lived only (and only partially) in broadsheet is promoted to all four packs at one definition site. `compose_css` now lays down three sheets in cascade order — `_base.css` + palette + pack — and because the base is first, every pack rule still wins on equal specificity by source order, so the four packs keep their exact current look. The default tier ships: heads never strand at a page foot (head-chain `break-after: avoid` glues kicker → title → dek → byline → body, on the `.article-head`/`.mg-title`/`.dept-title`/`h1`–`h3` classes the renderer already emits, so no renderer change is needed); the head box stays whole (`break-inside: avoid`); `p { orphans: 3; widows: 3 }` so at least three lines ride together across any break (promoted to brief/field-card/zine, which set neither before); atomic furniture never tears (`.mp-chart`, `.mp-stat`, `.move`, `.action-required`, `table.data tr`, `.trunc-notice`, `blockquote`); and split blocks look finished (`box-decoration-break: clone` on bordered callouts/quotes). Everything is CSS the shipped WeasyPrint path already supports — no new dependency, no agent-facing surface. **The broadsheet default look is unchanged** (verified: the demo edition lays out byte-identically — same page count, same content placement per page). This is the layout-primitives spec's Phase 1 only; the block primitives (`keep`/`keep-next`/`fresh-page`) and the per-edition `margins`/`density` knobs are deferred to later phases
- **`morning-paper review <edition>` — the copy desk's last read.** A new verb, the editorial twin of `doctor`: where `doctor` answers "does it render", `review` answers "is it good enough to run". It reads a FINISHED edition's artifacts (the composed markdown, and the edition JSON when present) and emits editorial WARNINGS — never hard fails. The severity ladder is three advisory rungs (`info` / `nudge` / `flag`) and tops out at `flag`; exit code is 0 by default, and `--strict` is the only way a `flag` (and only a `flag`) becomes a nonzero exit — a cron edition never breaks because a headline ran long. `--json` carries the full report (envelope: `edition`, `checks_run`, `checks_skipped`, `findings`, `summary`, `status` ∈ `clean`/`notes`/`review`); the default human output is desk-sheet voice, flags first, quiet when clean; `--verbose` surfaces info, `--explain CHECK` prints the threshold math and provenance. `checks_skipped` is first-class and honest — a check that can't run (no JSON for the dateline) says so, never silently passes
- **The eight text-only checks** (Phase 1): `headline-line-count` (the seed — flags a head estimated to wrap 3+ lines at the pack's measure; width-aware, not raw chars), `headline-length` (nudge over ~60 chars), `headline-verb-presence` (flags a label head with no finite verb, stdlib POS-lite, no ML), `hed-dek-redundancy` (nudge when a deck echoes ≥50% of the head's words), `section-balance` (nudge for a section >2.5× the median, or one lonely item next to fat siblings), `empty-or-sparse-section` (nudge for a heading over dead air), `duplicate-headline` (nudge for the same story twice, by URL or near-identical title via stdlib `difflib`), and `stale-dateline` (info when the lead item is materially older than the edition date). This complements the layout layer rather than duplicating it — layout PREVENTS structurally (orphans/widows, head-glue, fail-soft keeps), `review` CATCHES the residue CSS cannot fix (a head that wraps because the WORDS are long, a starved section, a stale or duplicate story)
- **`preferences/checks.yaml` is read** (when present, searched up the edition's directory tree and the cwd) for tuned thresholds (optionally per-pack) and mutes (global or scoped to a section) — each finding reports `threshold.source` (`default`/`user`) so a tuned rule is transparent. The learned `--learn` proposal loop and the geometry checks are deferred; this release reads an existing file, it never writes one
- The `edition` skill now runs `review --json` after compose/render and before delivery, and revises on `flag` findings using each finding's `hint` (guidance, not a gate)
- Tests: `_base.css` present and composed first in the three-sheet order; the broadsheet default look unchanged (the demo stays a stable 2-page render); all four packs now carry orphans/widows + head-glue + atomic-furniture keeps; the base uses only soft breaks (no forced page break, no box-shadow, no float); an over-tall kept block fails soft (flows, finite page count). The review verb exits 0 with findings JSON and 1 only under `--strict` on a flag; each of the eight checks fires on a crafted bad input and is silent on clean input; `checks.yaml` threshold override (with provenance) and section/global mutes are respected; same edition + same prefs → byte-identical report

## [0.5.2] - 2026-06-12

### Fixed
- **The scheduled edition now runs IN your newsroom directory.** `routine install` wrote scheduler jobs with no working directory, so the headless `claude -p` edition run started in `$HOME` and could not find the newsroom — `specs/`, `collectors/`, `editions/` were simply not there, and every scheduled paper composed blind. Install now captures the directory you install from (the contract: you install from your newsroom) and pins the job to it: launchd gets a `WorkingDirectory` plist key, the systemd service a `WorkingDirectory=` line, and the cron job a quote-safe `cd` into the newsroom inside its `sh -c` wrapper. `--workdir PATH` overrides the default (validated: must be an existing directory); the install JSON reports the resolved `workdir`, and `routine status` / `doctor` surface it where the artifact makes it cheap (the launchd plist). **Upgrading from 0.5.1: re-run `morning-paper routine install` from your newsroom** (or pass `--workdir`) — existing installs keep the old directory-less job until reinstalled

### Changed
- Edition skill, "Read the newsroom": the editor now also reads, when present, `memory/reads-ledger.md` (the cumulative record of everything already printed — repeating a read the owner already got is a hard fail; today's reads are appended when the paper ships), the most recent `editions/<date>/operator-answers.md` (triaged owner ink: deep-read picks, queue answers, steers — honored exactly), and checks an `inbox/scans/` directory for untriaged captures before composing

## [0.5.1] - 2026-06-12

### Added
- **`morning-paper routine` — the paper without the chat.** The editor is an agent, so the scheduled job is just `claude -p` run headless against the user's existing subscription: `routine install` schedules a daily run of the edition skill (default 05:00, `--time HH:MM` to change, `--command CMD` to replace the job; if `claude` is not on PATH the install refuses, warns, and prints the exact command to wire into your own scheduler). Platform ladder: macOS gets a launchd LaunchAgent (`~/Library/LaunchAgents/com.morning-paper.edition.plist`) using `StartCalendarInterval` — chosen because launchd coalesces runs missed during sleep into one run on wake, so the paper is ready when the laptop opens; `RunAtLoad` stays false (install never triggers an immediate run) and the installing user's `PATH` is frozen into the job so launchd's minimal environment can still find `claude`. Linux gets a systemd user timer with `Persistent=true` (the same catch-up behavior), falling back to a crontab line with the honest note that cron has no coalescing. Loading prefers `launchctl bootstrap gui/$UID` with a legacy `launchctl load` fallback
- `routine status` — JSON: installed?, scheduler, schedule (time + plain-language semantics), the raw command, last run (parsed from timestamped run markers the routine wraps around every invocation in `~/.local/share/morning-paper/routine.log`, plus `launchctl print` state on macOS), computed next fire, and the log path. `routine uninstall` removes the job cleanly and is idempotent — uninstalling an absent routine is a no-op, not an error
- `doctor` now reports the routine (installed/not, scheduler, time) — in `--json` under `"routine"` and as a human line; absence is informational, never an error
- The scheduling ladder documented in the README ("The morning routine"): Tier 0 say-"paper"-each-morning, Tier 1 `routine install` laptop-wake magic, Tier 2 always-on (+ the `pmset repeat wakeorpoweron` note for self-waking Macs), Tier 3 cloud-compose split. docs/composing.md points at the seam; the setup skill's routine section now offers the real command and the ladder
- 27 new tests: plist/systemd/cron unit generation (content, quoting, `%`-escaping per scheduler), install flows with subprocess mocked (no real launchctl/systemctl/crontab in CI), the bootstrap→load fallback, run-marker log parsing, status JSON, uninstall idempotence, the no-claude-binary warning path, and doctor's routine report

## [0.5.0] - 2026-06-11

### Changed
- **The style family** (per the 2026-06-11 style-system audit): six packs become four, each named for the print genre it is — a name a stranger could sketch, never a font or a CSS property:

  | 0.4.x name | 0.5.0 name | What happened |
  | --- | --- | --- |
  | `editorial` | `broadsheet` | renamed — it is the paper itself, not a column genre |
  | `flow` | `brief` | renamed — it literally renders the operator brief; name the artifact |
  | `ops-card` | `field-card` | renamed — keeps the card job, loses the jargon |
  | `magazine` | `broadsheet` | merged — it was broadsheet's article layer in a different kicker; its one real asset (the fenced-code-block `pre` treatment from 0.4.3) is folded into broadsheet |
  | `typewriter` | `brief` | retired — its newspaper job went to broadsheet, its Courier voice was already brief's; its one asset, the two-column boxed link-card grid, is now brief's canonical `.cards`/`.card` family (`.cards2` stays as a deprecated alias selector) |
  | `zine` | `zine` | right name, wrong execution — replaced by v2 (below) |

- The old names keep working for **one release of grace** as deprecated aliases: config validation, `--style`, and frontmatter `style:` all accept them, resolve them to the canonical pack, and print a one-time stderr warning. `morning-paper styles` lists the alias table under `deprecated_aliases`. The default style is now `broadsheet` (the same look `editorial` configs were already getting)
- One build template: the broadsheet-native front page (`resources/broadsheet-build.md`, formerly `editorial-build.md`) serves every style. The typewriter build template is retired; builds configured with the `typewriter` alias route to the broadsheet template with the deprecation warning, and staged-item inclusion works identically

### Removed
- `magazine` and `typewriter` as canonical style packs — `magazine.css` and `typewriter.css` deleted; both names live on only as aliases of their successors for this release
- The `typewriter.md` build template and the typewriter front-page visual baseline (the broadsheet baseline carries the front-page regression surface)
- Zine v1's `.zn-*` vocabulary (replaced wholesale by v2's `.z2-*` — v1 was a default-sans Word doc with a marker title; nothing worth carrying)

### Added
- **Zine** (rebuilt) — the photocopier field zine, built from named inspirations (Sniffin' Glue paste-up, risograph one-ink discipline, Field Notes cover furniture, Ray Gun rotation-as-tension, Iffy Books how-to vocabulary): cover ink plate with rotated cut-paper title strips, halftone dot bands (pure CSS radial-gradient grids, sized in exact dot-grid multiples for WeasyPrint), tilted rubber stamp, dotted-leader spec rows, paste-up quote scraps with hard offset shadows (two-wrapper plate trick — WeasyPrint has no `box-shadow`), CSS-drawn tilted checkbox steps, inverted-xerox command bars with `$` prompts, accent stickers, marginal marker scrawl, "cut here" reference cards, and a back-cover colophon. Both faces are vendored (Courier Prime OFL, Permanent Marker Apache-2.0); mono palette renders pure photocopier, color palette adds the riso-red second ink via the existing `--mp-accent` token — no new palette tokens. Full vocabulary + reference sample in docs/composing.md
- Style-family test coverage: alias resolution + one-time deprecation warning, config validation across canonical names and aliases, all four packs render-smoked on both palettes, zine render-smoked on its reference sample, build exercised through the alias path

## [0.4.4] - 2026-06-11

### Added
- **The contributor inbox ("the masthead")**: people the reader trusts email articles in and they land in tomorrow's staging queue — `morning-paper inbox` (alias `inbox poll`) polls a mailbox over IMAP, stdlib only. New top-level `inbox:` config block: `enabled` (default false), `imap_host`/`imap_user`, `mailbox`, optional `subject_tag` filter (default `paper`), `reply`, optional `smtp_host`/`smtp_user` (derived from the IMAP values when omitted), and `contributors:` — the masthead, a strict `{email, name}` allowlist that is required non-empty when enabled and is THE gate: mail from anyone else is skipped and reported, never staged
- Passwords never go in config: the credential comes from `MORNING_PAPER_IMAP_PASSWORD` (and `MORNING_PAPER_SMTP_PASSWORD` when distinct), and the config loader rejects any `password` key in the inbox block with the fix in the error. Gmail/iCloud app-password walkthrough in the new [docs/inbox.md](docs/inbox.md), including the plus-addressing tip and the one-sentence contributor onboarding
- A link in the mail body stages through the same path as `stage <url>` (new shared `staging.stage_url` helper — same extractor, same honest truncation flags); a mail with no link stages as kind `note`. The staged item records `contributor: <name>`, and build editions render contributor items with a FROM <NAME> kicker
- Warm confirmation reply from the reader's own address when something stages ("Got it — this is in Morning Paper tomorrow morning (about N pages). ☕" — with the real page estimate); `reply: false` turns it off
- `inbox --dry-run` reports what WOULD stage without staging, replying, or marking mail read. Safety rules either way: messages are fetched with BODY.PEEK and marked Seen only after a successful stage; one bad message never crashes the poll (it lands in `skipped` with a reason); HTML-only payloads are stripped of script/style and tags — all mail content is treated as untrusted text
- `setup` skill now interviews for the masthead (who can feed the paper, app-password setup, the sentence to send contributors); `edition` skill polls the inbox before composing

## [0.4.3] - 2026-06-11

### Fixed
- **The first-edition cliff**: `init` defaults to `style: editorial` but `build` always rendered the typewriter template, whose classes do not exist in editorial.css — a new user's first paper printed unstyled while every signal said success. `build` now dispatches on `outputs.style`: a new editorial-native template (`resources/editorial-build.md` — masthead/dateline/oxford, front strip with run counts, dept-kicker sections with Signals and Hacker News as `table.data` rows, references) serves `editorial` and every non-typewriter style; `typewriter` keeps its original template. The front-page visual snapshot test now covers both
- **Staged items vanished from the edition**: `build` never read `staging/{date}/queue.json`, so everything queued with `stage` silently missed the paper it was queued for. Build now appends a "Staged for today" section (both templates) with each staged item's markdown, puts an on-page `.trunc-notice` on items staged incomplete, reports the included slugs as `staged_included` in the build JSON, and warns loudly when a queue exists but cannot be included (unreadable queue, missing staged file, or the portable fallback renderer — which cannot typeset staged markdown)
- Zine style advertised fonts it could never load: the Google Fonts `@import` for Permanent Marker and Open Sans is stripped at compose time (by design — no network at render). Permanent Marker, the zine's identity face, is now vendored (Apache 2.0, `resources/fonts/`) and injected as `@font-face` like Courier Prime; the body stack is now honestly `Helvetica/Arial` — Open Sans was never actually printing, and vendoring its variable-font files was not worth >1MB. Decision documented in zine.css
- `magazine` style now has a real treatment for fenced code blocks (bordered, smaller mono, `pre-wrap`) instead of browser-default mono bleeding into the page

### Added
- A truncated article now says so **on the page itself** — "Truncated at extraction; N of M words shown." in a dashed `.trunc-notice` box at the end of the clipped body — not only in the JSON and stderr
- `render` is honest about bring-your-own CSS: a frontmatter `css:` block replaces the style pack entirely, so it now warns on stderr and reports `"style": "custom-css"` in the JSON instead of naming a pack the page is not wearing
- `--output PATH` on `render` and `demo` — copy the produced PDF where you actually want it (a directory keeps the PDF's name); the JSON reflects the delivered path
- `outputs.font_scale` (0.8-1.5, default 1.0) — scales every style's base body size via a `:root` override appended in `compose_css`; applies to build, render, demo, and the `stage`/`estimate` page counts
- `.page-break` in the editorial pack — the documented escape hatch for single-sheet furniture that must land on its own page (docs/composing.md has the guidance)
- docs/composing.md: editorial masthead vocabulary (`.masthead-title`, `.dateline`, `.oxford`), page-break guidance, and the staged-copy flow into composed editions (queue seam, frontmatter stripping, carrying truncation honesty onto the page)

## [0.4.2] - 2026-06-11

### Added
- `local` article extractor — fetches the page directly from your machine and parses it with trafilatura (now a core dependency). It is the **default** for `print`/`stage`: the URLs you read never leave your computer. Headings, blockquotes, and inline images carry through to print; the validation gate and truncation reporting work identically to the jina path
- "Set up with AI (recommended)" section at the top of the README — a copy-paste prompt that walks any strong model through the full onboarding arc (read, explore, interview, install, doctor, demo, private newsroom repo, first printed edition, daily loop), mirrored in the For Agents section
- Stage JSON now carries `extractor_note`; `print` output adds a warning line when the extractor fell back

### Changed
- `jina` (`r.jina.ai`) is demoted from default to explicit option, with a
  privacy note stated plainly in README and docs: jina sends each URL you read
  to a third-party service. At the time, local extraction could chain
  `local -> jina` with an honest note; 0.8.2 makes that remote fallback
  explicit opt-in.
- Default config (`init`) now writes `article_extractor: local` with the privacy trade documented in a comment

## [0.4.1] - 2026-06-11

### Fixed
- `stage <url>` (and `print <url>`) no longer truncate long articles silently. The article renderer keeps the first 80 extracted blocks; an ~11k-word essay was being staged at ~4.5k words with `staged: true` and a page estimate computed on the clipped text. The stage JSON now carries `truncated`, `words_extracted`, and a plain-language `warning` (exit stays 0), `print` surfaces the same warning, and a mid-sentence-cut check also flags extractions clipped upstream
- README install guidance now leads with `uv tool install "morning-paper[pretty]"` (pipx as the alternative), documents the PEP 668 `externally-managed-environment` failure on brew/system Pythons, and keeps `pip` for venv users — the literal `pip install` line stranded non-venv users
- Demo's "Make it yours" line now bridges the uvx try-it path to a persistent install (`uv tool install "morning-paper[pretty]" && morning-paper init`) — `morning-paper` was not on PATH for uvx users who typed the old suggestion verbatim
- `.claude-plugin/plugin.json` version no longer lags the package (0.3.0 -> 0.4.1)
- Starter config comment now lists all six styles instead of three

### Changed
- Default `outputs.style`/`outputs.palette` are now `editorial`/`color` — the first personal edition now matches the look the demo sold (renderer stays `typewriter`)

### Added
- `build`, `demo`, `print`, and `render` JSON output now report `"pages"` — the page count of the produced PDF (null when no PDF is written)

## [0.4.0] - 2026-06-11

### Added
- `morning-paper demo` — zero-config, zero-network, zero-key sample edition ("Port Anselm", fully fictional and labeled as such) rendered through the editorial style; fails honestly with install hints when WeasyPrint is unavailable, and ends with the print/make-it-yours/post-it share loop
- Vendored Courier Prime Regular/Bold/Italic (SIL OFL 1.1, license shipped alongside) with runtime @font-face injection — offline-deterministic typesetting, Google Fonts @import stripped at compose time
- Ref-codes: kickers may carry a short code (`<span class="ref-code">R2</span>`) that runs in the page footer next to the folio — cite an article from anywhere in the paper
- Desk-sheet component family (`ds-*`) in the editorial pack: ruled writing lines, zone heads, registration marks, pen-scale checkboxes
- `.claude-plugin/marketplace.json` + hero README storefront — the repo is now a one-plugin Claude Code marketplace (`/plugin marketplace add dmthepm/morning-paper`, then `/plugin install morning-paper@morning-paper`), with the sample render above the fold and the uvx try-it path
- `doctor --json` and `doctor --strict`, with specific macOS Pango failure detection and the exact fix printed (`brew install pango gdk-pixbuf` plus the `DYLD_FALLBACK_LIBRARY_PATH` hint)
- `init` now detects the machine's timezone from `/etc/localtime` instead of assuming the author's

### Changed
- Honesty sweep: roadmap-command message tells the truth (`remove`/`list` say plainly the verb is not implemented and link the roadmap); unwired extras removed; Funding entry removed; defaults de-personalized (system timezone auto-detected, generic profile, sample feeds labeled)
- README rebuilt as the storefront: hero edition image, try-it demo block (`uvx`), plugin install instructions, and a styles table; documents the `jina` extractor's limits (anonymous tier, 40-second timeout, unsupported domains) and the pretty-stack requirement behind `stage`/`estimate` page numbers
- docs/composing.md documents editorial, ref-codes, and desk-sheet vocabulary
- ROADMAP marks `stage`/`add`, `queue`/`status`, `estimate`, vendored Courier Prime, and `doctor --json` as shipped

### Removed
- Unwired `[twitter]` and `[local]` extras from packaging (nothing imported them)
- Funding URL from package metadata

## [0.3.0] - 2026-06-11

### Added
- Agent-facing staging verbs: `stage <url|file>` (queues material for tomorrow's paper, answers with a page estimate), `queue` (staged items vs `page_budget`), `estimate <file.md>` (page count, nothing written) — all JSON; `add`/`status` are aliases
- `editorial` style pack — the unified paper system (one document, continuous folios on the outside duplex corner, running section heads, separators instead of forced page breaks, CSS-drawn marks instead of fallback glyphs, one-red-moment color discipline)
- Claude Code plugin: `setup` (cold-start interview -> config + private newsroom repo + morning routine) and `edition` (the daily editor pass) skills
- `page_budget` config key; README "For Agents" quickstart


## [0.2.1] - 2026-06-11

### Added
- `magazine` style pack — long-read essay page (serif body on the Palatino/Georgia chain, kicker/dek/byline header, pull quotes, raised-cap lede, end mark)
- `zine` style pack — pocket how-to guide (half-letter page, marker display type, checkbox steps, command blocks, warning boxes; print 2-up on Letter for folding)

### Fixed
- Avoided a WeasyPrint crash on floated `::first-letter` (drop caps render as raised caps instead)

## [0.2.0] - 2026-06-11

### Added
- `morning-paper render <file.md>` — typeset any markdown file through a style pack (`--style`, `--palette`, `--date`, `--slug`); the seam for agent-composed documents (see `docs/composing.md`)
- `morning-paper styles` — list available styles and palettes as JSON
- Style packs: `typewriter` (the newspaper), `flow` (continuous operator brief, no forced page breaks), `ops-card` (boxed reference one-pager)
- Palettes: `mono` (laser, weight carries emphasis) and `color` (inkjet: warm ink, working red, data blue) — designed separately, selectable per render
- Chart directives: `mp-bars`, `mp-spark`, `mp-stats` fenced blocks render to print-quality inline SVG / stat blocks (stdlib only); malformed data degrades to an honest placeholder
- `outputs.style` and `outputs.palette` config keys
- Real page footers (date, paper name, `Page N of M`) via CSS paged-media margin boxes on every style, including article print

### Changed
- Typewriter CSS moved out of template frontmatter into `resources/styles/typewriter.css`, re-tokenized onto shared palette variables
- Masthead no longer hardcodes `AT HOME`; HN section heading now reflects the configured item count
- Frontmatter `css:` is now an override; documents without it get the configured style pack instead of rendering unstyled

### Removed
- Private operator harness leftovers: `scripts/`, private fixtures/golden files, private runtime docs, stale `templates/` copies, and the internal script-map CLI commands (`pass1`–`digest`, `smoke`)
- Dead Chromium-style `pdf_options` header/footer blocks (they never applied under WeasyPrint)
- Article-specific extraction filters that could silently corrupt future articles

## [0.1.4] - 2026-04-15

### Changed
- `doctor` now states plainly whether you are on the real typewriter print path or a fallback-only install
- README install guidance now recommends `morning-paper[pretty]` as the primary product path
- Platform messaging is now explicit: macOS/Linux are the main pretty-renderer targets, Windows is best-effort

## [0.1.3] - 2026-04-15

### Added
- Real top-level CLI help with command descriptions, examples, config path, and docs link
- PyPI version check in `morning-paper doctor`
- Friendly roadmap guidance for planned commands like `add` and `status`

### Changed
- `morning-paper doctor` now surfaces upgrade guidance when a newer PyPI release exists
- Unknown roadmap commands now point to `ROADMAP.md` instead of failing with a bare usage line

## [0.1.2] - 2026-04-14

### Added
- Visual snapshot tests for the article page and newspaper front page
- Explicit extractor registry and `article_extractor` config surface
- `ROADMAP.md` and architecture notes for research-tool boundaries

### Changed
- Article print layout now preserves continuous reading order while keeping the approved page-one composition
- X article metadata now comes from FxTwitter with avatar fallbacks
- Jina article parsing now uses extractor-scoped helpers instead of mixing X-specific parsing into the generic render path
- Print/image constants are grouped in `article_print.py` for easier tuning
- Newspaper `typewriter` template now uses CSS custom properties instead of scattered magic values

### Fixed
- Silent bad-output fallback for the `typewriter` renderer
- Broken or shell-like X article extracts now fail cleanly instead of producing garbage PDFs
- Inline X/media images are trimmed and embedded more reliably in printed articles

## [0.1.1] - 2026-04-14

### Added
- Content validation gate: rejects shell/timeout/short/fetch-error content before rendering
- Clean error messages for failed article extraction
- Python 3.10 compatibility fix (datetime.UTC → timezone.utc)
- GitHub Actions CI and PyPI trusted publishing workflows

### Fixed
- Typewriter renderer now requires the pretty stack; no silent bad PDF fallback
- Legacy private commands show clear guidance instead of crashing on public installs

## [0.1.0] - 2026-04-14

Initial public release.

### Added
- `morning-paper init` to create a starter config
- `morning-paper build` to produce JSON, Markdown, HTML, and PDF outputs
- `morning-paper print <url>` for one-off article printing
- `morning-paper doctor` for install validation
- `morning-paper --version`
- `typewriter` renderer with optional `WeasyPrint` support
- `portable` PDF fallback using `fpdf2`
- Config validation for timezone, source limits, and output directory
- Guard messages for internal-only commands when installed as a public package

### Sources
- Hacker News (no auth required)
- RSS feeds (via `feedparser`)
- Article URLs for one-off printing

### Notes
- The public package remains file-first and local-friendly
- Richer print output is available through `morning-paper[pretty]`
