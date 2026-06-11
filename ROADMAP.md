# Roadmap

## Shipped (`v0.1.x`)

- `morning-paper init`, `build`, `print <url>`, `doctor`
- Hacker News and RSS sources
- `typewriter` renderer with `WeasyPrint`
- `portable` PDF fallback with `fpdf2`
- Article extraction via Jina Reader with inline image handling
- X/Twitter metadata via FxTwitter
- Content validation gate so bad extractions do not print garbage
- Pluggable extractor architecture
- Visual regression testing for the article page
- PyPI publishing with trusted GitHub publishing

## Shipped (`v0.2.0`)

- `morning-paper render <file.md>` — one-off local markdown typesetting through style packs
- Style packs (`typewriter`, `flow`, `ops-card`) + palettes (`mono`, `color`)
- Chart directives (`mp-bars`, `mp-spark`, `mp-stats`) → inline SVG, stdlib-only
- Page footers via CSS paged-media margin boxes
- `morning-paper styles` listing command

## Shipped (`v0.3.x`)

- `morning-paper stage <url|file>` (alias: `add`) — queue material for
  tomorrow's paper with a page estimate
- `morning-paper queue` (alias: `status`) — staged items vs the page budget
- `morning-paper estimate <file.md>` — page-budget estimation
- `editorial` style pack and the Claude Code plugin (`setup` + `edition` skills)
- vendored Courier Prime (OFL) for offline-deterministic rendering
- `doctor --json` and `doctor --strict` for machine-readable install checks

## Next (`v0.4`)

- queue management verbs: `morning-paper remove`, `morning-paper list`
- `doctor` render self-test (actually lay out a page, not just import checks)
- CI job that exercises the WeasyPrint path + a (style × palette) snapshot matrix
- palette-aware article image pipeline (color images on the color palette)
- source plugins for YouTube transcripts and X/Twitter thread workflows
- optional LLM scoring via OpenRouter / Anthropic / OpenAI
- named sections and better front-page composition

## Future

- preference learning
- shared community curation and page exchange
- agent slot competition against a page budget
- coverage / breadth analysis for major stories
- image-of-the-day or full-page visual mode
- E Ink / device delivery surfaces
- additional extractor backends beyond Jina
