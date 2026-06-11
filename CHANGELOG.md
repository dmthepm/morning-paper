# Changelog

All notable changes to Morning Paper will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

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
