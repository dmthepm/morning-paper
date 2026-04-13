# Style Forensics: 2026-04-12

This doc records the actual render authority discovered from the live Thoth
tuning loop on 2026-04-12.

It exists because the initial `morning-paper` extraction started from the
`~/projects/morning-brief/scripts/` seed before fully reconstructing the latest
Telegram tuning decisions.

## Evidence Reviewed

Session evidence:

- `~/.hermes/sessions/session_20260412_154301_50c0e6.json`

Live skill/template evidence:

- `~/.hermes/skills/media/x-article-print/SKILL.md`
- `~/.hermes/skills/x-article-to-print/SKILL.md`
- `~/.hermes/skills/productivity/morning-brief-print/SKILL.md`
- `~/.hermes/skills/productivity/morning-brief-print/templates/typewriter-v5.md`
- `~/.hermes/skills/productivity/morning-brief-print/templates/presidential.md`

Generated artifact evidence:

- `~/.hermes/briefs/2026-04-12-Morning-Paper-combined.md`
- `~/.hermes/briefs/2026-04-12-Morning-Paper-combined.pdf`
- `~/.hermes/briefs/2026-04-12-Morning-Brief.md`
- `~/.hermes/briefs/2026-04-12-brief-review.md`
- versioned article PDFs and markdown generated during the tuning loop

## What Actually Happened

The approved 2026-04-12 Morning Paper result was not produced by a pristine,
module-owned render system yet.

It was reached by:

1. iterating on X article render style
2. iterating on Morning Brief print structure
3. rebuilding a combined Morning Paper artifact from the known-good Morning
   Brief v2 structure
4. verifying page screenshots and PDF flow

## Stable Findings

These findings are stable enough to promote into public canon.

### 1. The current render family is newspaper/typewriter, not generic Markdown

Approved visual shape:

- Courier Prime body and headings
- monochrome / high-contrast print treatment
- large masthead on page 1 for Morning Paper
- compact meta-bars with author and stats
- two-column article flow where appropriate
- restrained rules, borders, and grayscale blocks

### 2. The main failure mode was structural corruption

The most important regression was not “wrong font” or “wrong spacing.”

It was:

- orphan `---` YAML separators leaking into combined article bodies
- article headings rendering as literal `##` text
- broken combined-output image paths

This means the public repo must treat concatenation and asset resolution as
first-class render concerns.

### 3. Known-good rebuild pattern

The working recovery pattern on 2026-04-12 was:

1. use the known-good Morning Brief v2 file structure
2. keep `css: |` as a literal YAML block
3. keep article headings outside raw HTML wrappers
4. use explicit article dividers instead of orphan `---`
5. use explicit relative image paths for combined output assets
6. visually verify the rendered PDF pages

### 4. Author portraits are part of the contract for article-style outputs

Combined Morning Paper article outputs should support:

- author portrait
- author name / handle / role
- compact stats/date row

If the asset path is ambiguous, the build should fail or degrade explicitly,
not silently render broken images.

## What Is Not Yet Public Canon

These are still runtime-specific or not yet generalized enough:

- Thoth-specific filesystem paths
- Telegram delivery details
- printer device assumptions
- any session-local one-off string substitutions that are not part of a public
  template contract

## Promotion Rule

When render changes are proposed in `morning-paper`, review all three layers:

1. latest tuned artifacts
2. relevant Hermes print skills/templates
3. current public template/docs

Do not promote a render change from seed code alone.
