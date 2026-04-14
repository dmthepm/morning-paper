# Architecture Decisions

## 1. Distribution

- Publish `morning-paper` to PyPI.
- Recommend `pipx install morning-paper` for CLI users.
- `uvx morning-paper ...` becomes available automatically once published.
- No Docker, npm, or standalone binary requirement for the public package.

Reason:
- The product is a Python CLI. Distribution should match the ecosystem.

## 2. Public vs Private Boundary

- `Morning Paper` is the public engine.
- `Morning Brief` is a private deployment of that engine.
- Public repo owns:
  - collectors
  - normalized models
  - CLI
  - renderer implementations
  - tests
  - example configs
- Private harness owns:
  - cron
  - credentials
  - Telegram delivery
  - printer/device integration
  - operator-specific weighting and scheduling

Reason:
- The OSS package must stand on its own and remain portable.

## 3. Deterministic vs Agentic

Deterministic code owns:
- fetching feeds
- fetching top stories
- extracting article bodies
- normalizing content
- rendering artifacts

Agentic logic owns:
- relevance scoring
- clustering
- synthesis
- editorial judgment
- tomorrow-vs-now decisions

Reason:
- A paper should still build without an LLM key.

## 4. Core Dependency Contract

Required dependencies stay pure Python:
- `feedparser`
- `fpdf2`
- `Pillow`
- `PyYAML`
- `requests`

Reason:
- `pip install morning-paper && morning-paper init && morning-paper build` must work without system packages.

## 5. Renderer Contract

Renderer values:
- `typewriter`
- `portable`

`typewriter`:
- the product look
- uses the public typewriter template
- prefers `WeasyPrint` when available
- falls back cleanly when not available

`portable`:
- explicit guaranteed fallback
- always uses `fpdf2`

Reason:
- The style is part of the product.
- The install path still needs to work on machines without native renderer support.

## 6. Premium Renderer

Optional extra:

```toml
[project.optional-dependencies]
pretty = ["weasyprint>=62.0"]
```

Runtime behavior:
- try `WeasyPrint`
- catch both `ImportError` and `OSError`
- fall back to `fpdf2`
- emit a clear warning telling the user to install `morning-paper[pretty]`
- on macOS, automatically include `/opt/homebrew/lib` and `/usr/local/lib` in `DYLD_FALLBACK_LIBRARY_PATH` before import

Reason:
- `WeasyPrint` gets much closer to the intended printed layout.
- It has native library friction, so it cannot be a required dependency.

## 7. Why Not `md-to-pdf`

Rejected.

Reason:
- wrong ecosystem for a Python CLI
- requires Node.js
- typically pulls browser runtime baggage
- complicates installation and debugging for end users

## 8. CLI Product Surface

Stable public commands:
- `morning-paper init`
- `morning-paper build`
- `morning-paper print <url...>`
- `morning-paper doctor`

Planned public commands:
- queue/add commands for agents to stage tomorrow's paper
- page-budget estimation

Private harness commands remain compatibility-only and should not define the public API.

## 9. Printed Output Standard

The printed artifact is a first-class product surface, not a garnish.

Implications:
- markdown remains the durable intermediate
- HTML/PDF rendering must be testable
- the renderer should produce reviewable artifacts during development
- style regressions should be treated as product regressions

## 10. Naming

- Keep the style name `typewriter`
- drop versioned public naming like `typewriter-v5`

Reason:
- `typewriter` describes the visual language
- version suffixes create fake product choices where none exist
