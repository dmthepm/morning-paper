# Changelog

All notable changes to Morning Paper will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

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
- `jina` (`r.jina.ai`) is demoted from default to explicit option + automatic fallback. Privacy note, stated plainly in README and docs: jina sends each URL you read to a third-party service. When local extraction recovers too little content the engine chains `local -> jina` and flags the result with an honest note — never a silent fallback
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
- `morning-paper demo` — zero-config, zero-network, zero-key sample edition ("Port Anselm", fully fictional and labeled as such) rendered through the editorial style; ends with the print/make-it-yours/post-it share loop
- Vendored Courier Prime (OFL) with runtime @font-face injection — offline-deterministic rendering, Google Fonts @import stripped at compose time
- Ref-codes: kickers may carry a short code (`<span class="ref-code">R2</span>`) that runs in the page footer next to the folio — cite an article from anywhere in the paper
- Desk-sheet component family (`ds-*`) in the editorial pack: ruled writing lines, zone heads, registration marks, pen-scale checkboxes
- `.claude-plugin/marketplace.json` + hero README storefront (sample render above the fold, uvx try-it path, plugin install)
- `doctor --json` and `doctor --strict`, with specific macOS pango failure detection and the exact fix printed

### Changed
- Honesty sweep: roadmap-command message tells the truth; unwired extras removed; Funding entry removed; defaults de-personalized (system timezone auto-detected, generic profile, sample feeds labeled)
- docs/composing.md documents editorial, ref-codes, and desk-sheet vocabulary


### Added
- `morning-paper demo` — typeset the bundled fully synthetic sample edition (editorial style, color palette) with zero config, network, or keys; fails honestly with install hints when WeasyPrint is unavailable
- Vendored Courier Prime Regular/Bold/Italic (SIL OFL 1.1, license shipped alongside) so typewriter typesetting is offline-deterministic — no Google Fonts fetch at render time
- `.claude-plugin/marketplace.json` — the repo is now a one-plugin Claude Code marketplace: `/plugin marketplace add dmthepm/morning-paper`, then `/plugin install morning-paper@morning-paper`
- `doctor --json` — machine-readable `{checks, renderer, status}` output for agents
- `doctor --strict` — nonzero exit when the typewriter renderer is unavailable
- `doctor` and `demo` now detect the macOS Pango load failure specifically and print the exact fix (`brew install pango gdk-pixbuf` plus the `DYLD_FALLBACK_LIBRARY_PATH` hint)
- `init` now detects the machine's timezone from `/etc/localtime` instead of assuming the author's

### Changed
- README rebuilt as the storefront: hero edition image, try-it demo block (`uvx`), plugin install instructions, and a styles table
- Reserved-command message (`remove`, `list`) now says plainly the verb is not implemented yet and links the roadmap, instead of citing a stale version
- README documents the `jina` extractor's limits (anonymous tier, 40-second timeout, unsupported domains) and the pretty-stack requirement behind `stage`/`estimate` page numbers
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
