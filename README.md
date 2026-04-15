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

Today, install from GitHub:

```bash
pip install git+https://github.com/dmthepm/morning-paper.git
morning-paper init
```

For the actual high-quality print path:

```bash
pip install "morning-paper[pretty] @ git+https://github.com/dmthepm/morning-paper.git"
morning-paper build
```

That writes your paper under:

```text
~/.local/share/morning-paper/<date>/
```

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
  - requires the pretty print stack
  - uses `WeasyPrint`
- `portable`
  - explicit pure Python fallback
  - lower fidelity
  - only use this if you intentionally want the simpler output

Default config:

```yaml
outputs:
  renderer: typewriter
```

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

1. Publish `v0.1.0` to PyPI for `pip install morning-paper`
2. Keep improving article print fidelity in the `typewriter` renderer
3. Add queueing and staging commands for agent-driven daily workflows
4. Add optional LLM scoring without making it a requirement

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Community

- Main Branch: [skool.com/main](https://skool.com/main)
- Issues: [github.com/dmthepm/morning-paper/issues](https://github.com/dmthepm/morning-paper/issues)

## License

MIT
