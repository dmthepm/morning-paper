# Changelog

All notable changes to Morning Paper will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

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
