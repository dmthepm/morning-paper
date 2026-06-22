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
  - the generic source/staging contract
  - the generic stage/inbox/build/render contract
  - normalized models
  - CLI
  - renderer implementations
  - tests
  - example configs
- Collectors are NOT in the engine. The engine ships the stage/inbox contract
  any script or host-agent workflow can write to; each reader-specific source
  is a collector the operator authors and runs in their own private newsroom
  (see [docs/collectors.md](collectors.md)).
- Private deployments own their own collectors, scheduling, credentials, delivery, and operator-specific configuration.

Reason:
- The OSS package must stand on its own and remain portable.

## 3. Deterministic vs Agentic

Deterministic code owns:
- fetching configured web/feed inputs
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
- uses `WeasyPrint` through the `[pretty]` install path
- fails clearly when the production renderer is unavailable

`portable`:
- explicit guaranteed fallback
- always uses `fpdf2`

Reason:
- The style is part of the product.
- The user can intentionally choose the portable fallback, but the product path
  should not silently downgrade.

## 6. Premium Renderer

Optional extra:

```toml
[project.optional-dependencies]
pretty = ["weasyprint>=69.0,<70"]
```

Runtime behavior:
- try `WeasyPrint`
- catch both `ImportError` and `OSError`
- fail clearly when the user asked for the product renderer and it is missing
- `doctor --strict` verifies the supported WeasyPrint range and a real render
  self-test
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

Every command prints JSON (`doctor` via `--json`). `routine` is an advanced
local fallback scheduler; for most readers, recurring runs should use the
host-native primitive (Codex Automations, Claude Code routines, or ChatGPT
scheduled tasks). Any internal-only commands remain compatibility-only and do
not define the public API.

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

## 11. Social And Hard-To-Extract Sources

Decision date: 2026-04-14; reframed 2026-06-22

Social platforms, video sites, logged-in pages, paywalled sites, and
JavaScript-heavy pages change too often to make a single built-in scraper the
product. Morning Paper should not promise that any one third-party reader,
browser scrape, API, or open-source parser is the right universal answer.

Current decision:

- Core stays zero-auth and source-agnostic.
- Reader-owned exports, local files, pasted markdown, and private collectors
  are first-class.
- Browser/API/scrape tools are recipes in the private newsroom, not bundled
  product identity.
- If an external service, logged-in browser session, or paid API is used, the
  collector records that fact in the staged item.
- If source capture fails, the paper says "not configured" or "nothing today";
  it never prints guessed content.

Historical notes in older docs named X/Twitter-specific APIs, Jina behavior,
and tool pricing. Treat those as dated implementation research, not current
product guidance.

## 12. Article Extraction Architecture

Decision date: 2026-04-14; reframed 2026-06-22

Morning Paper treats extraction as replaceable plumbing behind a stable
contract.

Current shape:

- extractor interface: `src/morning_paper/extractors.py`;
- registered extractors include `local` and `jina`;
- config field: `article_extractor`;
- `fetch_article()` resolves the configured extractor, then applies shared
  validation, metadata enrichment, image handling, and PDF rendering.

The stable contract:

- an extractor returns normalized article content: title, author, blocks,
  paragraphs, and image references when available;
- validation rejects shell pages, too-short results, and obvious garbage;
- partial results carry a plain-language warning;
- remote readers and browser/API scrapes are explicit choices, never hidden
  default rescue paths;
- remote-reader results carry an extraction note so the editor knows the URL
  left the machine;
- rendering does not branch around extractor-specific hacks.

Reason:

- Jina and trafilatura are current implementation details, not the product
  promise.
- Different readers will prefer different privacy, fidelity, account, and cost
  tradeoffs.
- The renderer and editor loop should survive extractor changes unchanged.

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

Decision date: 2026-04-14; superseded by section 12 on 2026-06-22

Keep the extractor registry. Do not build renderer branches around specific
source sites or reader services. The current backend list is an implementation
detail; the durable contract is normalized article content plus honest notes
for partial or remote extraction.

## 16. Skill Distribution for Agent Runtimes

Decision date: 2026-04-14 (revised 0.7.1)

Morning Paper ships its skills as a plugin on two hosts — Claude Code and
Codex — from one source tree. The skill bodies live once, under
`plugins/morning-paper/skills/<name>/SKILL.md`, host-neutral and
self-contained:

- `plugins/morning-paper/skills/setup/SKILL.md` — cold-start: install,
  interview, scaffold the newsroom contracts, wire the routine
- `plugins/morning-paper/skills/edition/SKILL.md` — the daily editor pass
- `plugins/morning-paper/skills/writing/SKILL.md` — the prose revision
  discipline

Each host points its own thin manifest at that one tree. The Claude Code
manifest (`.claude-plugin/plugin.json`) sets `"skills":
"./plugins/morning-paper/skills/"`. The Codex manifest
(`plugins/morning-paper/.codex-plugin/plugin.json`) sets `"skills": "./skills/"`
relative to its own plugin root, carries the required `interface` block, and
omits `hooks` (Codex validation rejects it). The Codex marketplace
(`.agents/plugins/marketplace.json`) points at `./plugins/morning-paper` —
the live `codex plugin add` only surfaces a plugin whose source is a real
subdirectory, never the marketplace root, and the validator resolves `skills`
relative to that plugin root, so a single real directory satisfies both hosts
with no duplicated tree and no up-reference.

A thin `.claude/skills/morning-paper/SKILL.md` cheat-sheet stub existed through
0.6.1 and was removed in 0.7.0: it had no frontmatter, never shipped through the
plugin loader, and shadowed the real skills during local dev.

Purpose:
- make the CLI discoverable in Claude Code and Codex runtimes from one repo
- provide a stable command contract for always-on agent runtimes
- keep runtime integration thin: skills call the CLI, they do not reimplement the pipeline
- hold the single-source invariant: one strict-semver version across both
  manifests per release; never fork a skill's prose between hosts

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
