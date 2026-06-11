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

## Next (`v0.2.x` / `v0.3`)

- `morning-paper add <url-or-file> [--date DATE]`
- `morning-paper status`
- page-budget estimation and overflow warnings
- vendor Courier Prime (OFL) for offline-deterministic rendering
- CI job that exercises the WeasyPrint path + a (style × palette) snapshot matrix
- palette-aware article image pipeline (color images on the color palette)
- `doctor --json` with a real render self-test
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
