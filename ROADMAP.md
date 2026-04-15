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

## Next (`v0.2`)

- `morning-paper add <url-or-file> [--date DATE]`
- `morning-paper status`
- page-budget estimation and overflow warnings
- source plugins for YouTube transcripts and X/Twitter thread workflows
- optional LLM scoring via OpenRouter / Anthropic / OpenAI
- named sections and better front-page composition
- one-off local markdown / Obsidian file printing
- second visual baseline for the newspaper front page

## Future

- preference learning
- shared community curation and page exchange
- agent slot competition against a page budget
- coverage / breadth analysis for major stories
- image-of-the-day or full-page visual mode
- E Ink / device delivery surfaces
- additional extractor backends beyond Jina
