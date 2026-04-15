# Morning Paper

**Your morning newspaper, built from your own sources.**

Morning Paper is a Python CLI that builds a personalized daily paper as a
print-ready PDF. It starts with deterministic collectors, writes durable file
artifacts, and gives you a newspaper you can actually print and read.

No database. No Docker. No SaaS requirement.

## What It Does

- Builds a daily paper from Hacker News and RSS feeds
- Prints one or more articles on demand with `morning-paper print <url>`
- Produces JSON, Markdown, HTML, and PDF artifacts
- Works without an LLM key
- Uses a richer `typewriter` renderer when available and falls back cleanly

## Quick Start

For the real product-quality print path, install the pretty renderer:

```bash
pip install "morning-paper[pretty]"
morning-paper init
morning-paper doctor
morning-paper build
```

That writes your paper under:

```text
~/.local/share/morning-paper/<date>/
```

If you only want the basic fallback install:

```bash
pip install morning-paper
```

That path is functional, but it is not the renderer you should judge the product by.

## Platform Support

- macOS
  - recommended
  - install `morning-paper[pretty]`
  - may also need:

```bash
brew install pango gdk-pixbuf
```

- Linux
  - recommended
  - install `morning-paper[pretty]`
  - may also need system libraries for WeasyPrint such as pango/cairo packages from your distro

- Windows
  - CLI works
  - `portable` fallback works more reliably today
  - `typewriter` via `WeasyPrint` is best-effort, not the strongest supported path yet

## Install Notes

Use `morning-paper doctor` after install.

- `renderer: typewriter ready`
  - you are on the real print path
- `renderer: typewriter unavailable`
  - you are on a fallback-only install
  - high-quality print output is not available until the pretty stack is working

On macOS, the richer renderer may also need:

```bash
brew install pango gdk-pixbuf
```

## Example Commands

```bash
# Create a starter config
morning-paper init

# Build today's paper from your configured sources
morning-paper build

# Build a paper for a specific date
morning-paper build --date 2026-04-15

# Print an article right now
morning-paper print https://example.com/article

# Verify the install
morning-paper doctor

# Show the installed version
morning-paper --version
```

## Current Sources

| Source | Auth needed? | Status |
| --- | --- | --- |
| Hacker News | No | Included |
| RSS feeds | No | Included |
| Article URLs | No | Included via `print` |

## Rendering

Morning Paper currently supports two renderers:

- `typewriter`
  - the primary product look
  - the recommended install path
  - requires the pretty print stack
  - uses `WeasyPrint`
- `portable`
  - explicit pure Python fallback
  - lower fidelity
  - do not use this as your default judgment of Morning Paper's design quality
  - only use this if you intentionally want the simpler output

Default config:

```yaml
article_extractor: jina

outputs:
  renderer: typewriter
```

`jina` is the current default article extractor, but extraction is now a replaceable backend. The print renderer, validation, image pipeline, and metadata enrichment are designed to survive extractor upgrades.

If `typewriter` cannot render, Morning Paper now fails clearly instead of
silently generating a lower-quality PDF. If you explicitly want the simpler
fallback, set:

```yaml
outputs:
  renderer: portable
```

## Product Shape

Morning Paper is intentionally narrow.

It is:

- a CLI
- file-first
- print-oriented
- local-friendly

It is not:

- a second-brain platform
- a wiki
- a database-heavy personal knowledge system
- a closed feed or recommendation engine

## Install for Development

```bash
git clone https://github.com/dmthepm/morning-paper.git
cd morning-paper
pip install -e ".[dev]"
python -m pytest tests/
morning-paper doctor
```

## Roadmap

1. Keep improving article print fidelity in the `typewriter` renderer
2. Add queueing and staging commands for agent-driven daily workflows
3. Add optional LLM scoring without making it a requirement

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Community

- Main Branch: [skool.com/main](https://skool.com/main)
- Issues: [github.com/dmthepm/morning-paper/issues](https://github.com/dmthepm/morning-paper/issues)

## License

MIT
