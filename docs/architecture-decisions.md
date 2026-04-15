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
- Private deployments extend it for specific operators.
- Public repo owns:
  - collectors
  - normalized models
  - CLI
  - renderer implementations
  - tests
  - example configs
- Private deployments own their own scheduling, credentials, delivery, and operator-specific configuration.

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

Internal-only commands remain compatibility-only and should not define the public API.

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

## 11. X/Twitter Extraction Strategy

Decision date: 2026-04-14

### The problem

X.com is actively hostile to content extraction. There is no free, open source, zero-auth, reliable way to pull full threads from X in 2026.

### What we evaluated

| Approach | Auth/Cost | Reliability | Fit for a free CLI |
|---|---|---|---|
| Official X API (Pay-Per-Use) | $0.005/post, no free tier | High | No — unpredictable bills, too expensive |
| Apify Twitter actors | Apify token (free tier limited) | Very high | Good as optional backend |
| twscrape (vladkens/twscrape) | User's own X session cookies | Good (active maintenance) | Good as optional backend |
| trafilatura (general URLs) | None | Excellent for articles | Perfect for non-X URLs |
| Manual paste / local markdown | None | 100% | Perfect universal fallback |
| Headless browser (Playwright) | None | Medium | Poor — 200MB+ Chromium dep |

### Decision

- X is an **optional plugin**, never core. Core stays zero-auth.
- General article extraction uses Jina Reader (`r.jina.ai`) as the default — free, zero dependency (just an HTTP call), returns clean markdown with inline images. Works well for news articles, blogs, Substack, and even many X threads.
- trafilatura is available as an optional local fallback via `morning-paper[local]` for offline/privacy use.
- X/Twitter uses optional backends configured by the user:
  1. `apify` — user supplies their own Apify token (recommended for reliability)
  2. `twscrape` — pure Python, user adds their own X session (open source, no API cost)
  3. `manual` — user pastes thread content as markdown (always works)
- If no X backend is configured and user tries an X URL: clear message with options, never a broken/garbage PDF.

### pyproject.toml extras

```toml
[project.optional-dependencies]
pretty = ["weasyprint>=62.0"]
twitter = ["twscrape"]
local = ["trafilatura"]
```

### Content validation gate

Before rendering any article (X or otherwise), validate:
- Extracted text is above 200 characters of real content
- Text does not contain known failure markers ("This page explicitly specify a timeout", X noscript shells, HTTP error pages)
- If validation fails: report the failure, suggest alternatives, never render garbage to PDF

### Why not the Official X API

The February 2026 Pay-Per-Use pricing ($0.005/post, no free tier) makes it unsuitable for a free open source CLI. A user running 50-100 posts daily would pay $0.25-$2+/day with no cap. No major Python CLI tool (Ruff, Rich, HTTPie, Poetry) uses paid APIs as a core dependency. We follow the same pattern.

## 12. Article Extraction Architecture

Decision date: 2026-04-14

Default extractor: **Jina Reader** (`https://r.jina.ai/{url}`)

Request headers include `X-With-Images: true` which returns 33-90% more content on X Articles with better heading and image preservation.

Why Jina over trafilatura as the default:
- Zero pip dependency (just a `requests.get` call)
- Returns clean markdown with inline image URLs (tested: X articles return 8+ images as direct `pbs.twimg.com` URLs)
- Successfully extracts X Articles and long threads (2 out of 3 tested URLs worked, including full long-form content)
- Images come in print-friendly sizes (`small` variant, perfect for newspaper columns)
- trafilatura drops images and requires extra parsing for the same content

Fallback chain in `fetch_article()`:
1. Jina Reader → if content passes validation gate → return Article
2. If Jina fails validation → raise ArticleExtractionError with clear message
3. For X URLs specifically: suggest configuring twitter backend or manual paste

Content validation gate (implemented in v0.1.1):
- Minimum 200 characters of extracted text
- Reject known failure markers (X noscript shells, timeout warnings)
- Domain skiplist (youtube.com, github.com, instagram.com — domains Jina can't meaningfully extract)
- Network errors caught and reported cleanly

Image handling:
- Jina returns images as standard markdown `![alt](url)` syntax
- `article_print.py` downloads images, converts to B&W via `image_tools.py`, embeds in PDF
- Failed image downloads skip gracefully (never break the pipeline)
- Max 3 images per article to control page length

Honest limitations:
- Jina is an external free service — rate limits and future changes are possible
- Some X posts fail extraction (noscript shell returned) — validation gate catches these
- No offline mode without the optional `morning-paper[local]` extra (trafilatura)

## 13. X/Twitter Metadata via FxTwitter

Decision date: 2026-04-14

For X/Twitter post URLs, Morning Paper uses FxTwitter as the primary metadata source:

- endpoint: `https://api.fxtwitter.com/{handle}/status/{id}`
- used for:
  - author name
  - handle
  - profile image URL
  - followers
  - likes
  - retweets
  - replies
  - views
  - short bio/role line

Body text and inline article images still come from Jina Reader.

Fallback chain for X metadata:
1. FxTwitter API
2. `unavatar.io` for avatar only
3. X profile reader fallback for avatar only
4. render without avatar/stats if all metadata calls fail

Reason:
- FxTwitter returns the durable social metadata we need in one JSON response.
- Jina remains the better source for article body extraction and inline media.
- The split keeps the renderer honest: social metadata from a social metadata endpoint, long-form body from the article reader.

## 14. Typewriter Design Tokens

Decision date: 2026-04-14

The print layout should not rely on scattered magic numbers.

We keep the typewriter stylesheet lightweight, but all primary visual controls should live in CSS custom properties at the top of the template:

- page spacing
- column gap
- body size and line height
- paragraph indent
- byline avatar size
- byline typography
- image spacing and max height
- text and rule colors

Reason:
- WeasyPrint supports CSS custom properties directly.
- This keeps layout tuning coherent without introducing Sass, Tailwind, or a build step.
- New styles can inherit the same token model later instead of duplicating hard-coded values.

Rule:
- if a layout tweak changes a core visual dimension, prefer changing or adding a token instead of editing scattered declarations.

## 15. Pluggable Article Extractors

Decision date: 2026-04-14

Morning Paper should treat article extraction as a replaceable backend, not a permanent Jina implementation detail.

Current shape:
- extractor interface: `src/morning_paper/extractors.py`
- current registered extractor: `jina`
- config field: `article_extractor: jina`
- `fetch_article()` resolves the configured extractor, then applies shared validation, metadata enrichment, and rendering

Reason:
- Jina is useful, but it is not the only future parser.
- Different extractors will preserve different levels of fidelity for X articles, essays, paywalled pages, or saved-reader exports.
- The renderer and design system should survive extractor changes unchanged.

Contract:
- an extractor returns normalized article content:
  - title
  - author
  - blocks
  - paragraphs
  - primary image refs
  - profile image ref when available
- validation, image processing, FxTwitter enrichment, and PDF rendering remain outside the extractor

Rule:
- new extractors should register through the extractor registry instead of branching renderer logic around source-specific hacks.

## 16. Skill Distribution for Agent Runtimes

Decision date: 2026-04-14

Morning Paper should ship a simple skill file for agent runtimes that discover tools from repo-local instructions.

Path:
- `.claude/skills/morning-paper/SKILL.md`

Purpose:
- make the CLI discoverable in Claude Code style runtimes
- provide a stable command contract for Hermes/OpenClaw-style agent environments
- keep runtime integration thin: skills call the CLI, they do not reimplement the pipeline

## 17. Visual Snapshot Testing

Decision date: 2026-04-14

The typewriter renderer should have at least one rendered-page baseline test.

Current shape:
- fixture article rendered through the real article print path
- local deterministic fixture images
- font import removed in the test to reduce network/font drift
- PDF converted to a page image
- compared against a stored baseline image with a small diff threshold

Reason:
- layout regressions are often invisible to markdown- or JSON-level tests
- the article page is now stable enough that we should protect it from accidental shifts

Rule:
- the visual snapshot should remain narrow and intentional
- update the baseline only when a layout change is explicitly desired
- do not broaden this into a giant screenshot matrix before the main print lane settles

## 18. Relationship to Research Tools

Decision date: 2026-04-14

Morning Paper is a newspaper builder, not a research engine.

Research tools such as `last30days` or similar multi-source report builders should produce markdown or structured output. Morning Paper's job is to stage and print that material cleanly.

Relationship:
- research tool -> produces markdown or structured article output
- Morning Paper -> stages, lays out, and prints it

Reason:
- we do not want to duplicate every research or scraping workflow inside the newspaper renderer
- the extractor boundary exists so different content sources can plug in, but the core product remains the printed output

Rule:
- when a workflow is primarily about discovery, synthesis, or report generation across many sources, it belongs in a research tool
- when the goal is to turn selected material into a durable, readable paper, it belongs in Morning Paper
