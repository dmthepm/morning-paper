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
  - the built-in HN + RSS build path
  - the generic stage/inbox/build/render contract
  - normalized models
  - CLI
  - renderer implementations
  - tests
  - example configs
- Collectors are NOT in the engine. The engine ships HN + RSS and the
  stage/inbox contract any script can write to; every other source is a
  collector the operator authors and runs in their own private newsroom
  (see [docs/collectors.md](collectors.md)).
- Private deployments own their own collectors, scheduling, credentials, delivery, and operator-specific configuration.

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
- `morning-paper demo` — zero-config sample edition
- `morning-paper init`
- `morning-paper build`
- `morning-paper print <url...>`
- `morning-paper render <file.md>` — typeset any markdown through a style pack
- `morning-paper stage <url|file>` (alias `add`) — queue material for tomorrow
- `morning-paper queue` (alias `status`) — staged items vs the page budget
- `morning-paper estimate <file.md>` — page count, nothing written
- `morning-paper inbox` — poll the contributor inbox
- `morning-paper review <edition>` — editorial QC on a finished edition
- `morning-paper routine` — schedule the daily edition (install/status/uninstall)
- `morning-paper styles` — list styles + palettes
- `morning-paper doctor`

Every command prints JSON (`doctor` via `--json`). `remove`/`list` (queue
management) remain on the roadmap and report so honestly when invoked. Any
internal-only commands remain compatibility-only and do not define the public API.

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

**Superseded for style packs (0.5.0, style-system audit):** a pack name is a
print genre a stranger could sketch — broadsheet, brief, field-card, zine —
never a font or a CSS property. The `typewriter` *style pack* retired into
`brief`; the `typewriter` *renderer* name (this section's original subject,
vs `portable`) is unchanged. The no-version-suffix rule stands.

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

### Decision (current, since 0.4.2)

- X is an **optional plugin**, never core. Core stays zero-auth.
- General article extraction is **local-first**: trafilatura ships as a core
  dependency and `article_extractor: local` is the default — the URLs the
  reader cares about never leave their machine. Local parsing returns clean
  blocks for news articles, blogs, and Substack.
- Jina Reader (`r.jina.ai`) is an explicit option and an automatic fallback:
  when local extraction recovers too little content, the engine retries
  through Jina and flags the result with an honest `extraction_note` (the URL
  was sent to a third-party service) — never a silent fallback. The privacy
  concern (every read URL sent to a third-party SaaS) is why local, not Jina,
  is the default; the original 0.1–0.4.1 default was Jina, flipped in 0.4.2.
- X/Twitter uses optional backends configured by the user:
  1. `apify` — user supplies their own Apify token (recommended for reliability)
  2. `twscrape` — pure Python, user adds their own X session (open source, no API cost)
  3. `manual` — user pastes thread content as markdown (always works)
- If no X backend is configured and user tries an X URL: clear message with options, never a broken/garbage PDF.

### pyproject.toml extras

```toml
[project.optional-dependencies]
pretty = ["weasyprint>=62.0"]
```

trafilatura is a core dependency (not an extra); the never-wired `twitter`
and `local` extras were removed in 0.4.2.

### Content validation gate

Before rendering any article (X or otherwise), validate:
- Extracted text is above 200 characters of real content
- Text does not contain known failure markers ("This page explicitly specify a timeout", X noscript shells, HTTP error pages)
- If validation fails: report the failure, suggest alternatives, never render garbage to PDF

### Why not the Official X API

The February 2026 Pay-Per-Use pricing ($0.005/post, no free tier) makes it unsuitable for a free open source CLI. A user running 50-100 posts daily would pay $0.25-$2+/day with no cap. No major Python CLI tool (Ruff, Rich, HTTPie, Poetry) uses paid APIs as a core dependency. We follow the same pattern.

## 12. Article Extraction Architecture

Decision date: 2026-04-14 (revised 0.4.2)

Default extractor: **local trafilatura** (the page is fetched and parsed on
this machine; URLs stay local). **Jina Reader** (`https://r.jina.ai/{url}`) is
the explicit option and the automatic fallback in the `local -> jina` chain
below, selectable via `article_extractor: jina`. Jina requests include
`X-With-Images: true` for better heading and image preservation on the pages it
handles (notably X Articles).

Jina's strengths (why it remains the fallback, and was the original default):
- Zero pip dependency (just a `requests.get` call)
- Returns clean markdown with inline image URLs (tested: X articles return 8+ images as direct `pbs.twimg.com` URLs)
- Successfully extracts X Articles and long threads where local sees only a noscript shell
- Images come in print-friendly sizes (`small` variant, perfect for newspaper columns)

Local trafilatura is the default anyway: keeping every read URL off third-party
infrastructure outweighs Jina's zero-dependency convenience.

Fallback chain in `fetch_article()` (as of 0.4.2):
1. Local trafilatura extraction → if it recovers enough content → return Article
2. If local recovers too little → Jina Reader retry, result carries an honest
   `extraction_note` ("the URL was sent to the third-party r.jina.ai service")
3. If the winning extraction fails the validation gate → raise
   ArticleExtractionError with clear message
4. For X URLs specifically: the local fetch sees the noscript shell, so jina
   handles X posts in practice; shell responses still fail with a clear error

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
- ~~No offline mode without the optional `morning-paper[local]` extra (trafilatura)~~ — resolved in 0.4.2: trafilatura is core and local extraction is the default

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
- registered extractors: `local` (default since 0.4.2) and `jina`
- config field: `article_extractor: local` (or `jina`)
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

Decision date: 2026-04-14 (revised 0.7.0)

Morning Paper ships its skills as a Claude Code plugin. The loader reads
`<root>/skills/<name>/SKILL.md`, so the registered surface is the three real
skills:

- `skills/setup/SKILL.md` — cold-start: install, interview, scaffold the
  newsroom contracts, wire the routine
- `skills/edition/SKILL.md` — the daily editor pass
- `skills/writing/SKILL.md` — the prose revision discipline

A thin `.claude/skills/morning-paper/SKILL.md` cheat-sheet stub existed through
0.6.1 and was removed in 0.7.0: it had no frontmatter, never shipped through the
plugin loader, and shadowed the real skills during local dev.

Purpose:
- make the CLI discoverable in Claude Code style runtimes
- provide a stable command contract for always-on agent runtimes
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
