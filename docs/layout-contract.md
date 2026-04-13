# Layout Contract

These are the current visual and structural invariants.

## Render Authority

The current approved render family is derived from the 2026-04-12 style audit:

- tuned Morning Paper artifacts on Thoth
- tuned Morning Brief artifacts on Thoth
- `x-article-print`
- `x-article-to-print`
- `morning-brief-print`
- `templates/typewriter-v5.md`

Do not treat extracted seed scripts as sufficient render authority by
themselves.

## Typography

- Body: `Courier Prime`
- Monospace fallback acceptable for runtime resilience
- Section hierarchy must remain visually restrained and compact

## Page Treatment

- Letter size
- white page background
- black text
- subtle gray cards are allowed for content grouping

## Header/Footer Rules

- page 1 title/date/rule live in the body
- PDF header template must be `"<span></span>"`
- footer uses a 3-column flex layout with page numbers
- use YAML literal blocks for CSS: `css: |`

## Content Blocks

- tweet cards: pair short items, full width for longer items
- HN cards: CSS columns, not flexbox
- cards must avoid being cut across page boundaries
- optional visual block should prefer a single processed monochrome asset, not multiple competing images

## Structural Rules

- no markdown `##` headers inside raw HTML blocks
- HN heading and subhead should stay HTML when inside an HTML section scaffold
- no forced page breaks unless explicitly part of an approved template rule
- no orphan `---` separators inside combined article bodies
- combined renders must use explicit article dividers, not frontmatter-style separators
- combined article image paths must be explicit and relative to the rendered markdown
- render review must include page screenshots, not only markdown inspection

## Golden Reference

The current approved styling family is derived from:

- the known-good Apr 5 brief family
- the 2026-04-12 tuned Morning Brief family
- the 2026-04-12 tuned Morning Paper family

Future changes should be diffed against golden outputs and tuned artifacts, not
improvised live in cron.
