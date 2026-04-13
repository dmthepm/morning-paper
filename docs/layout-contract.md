# Layout Contract

These are the current visual and structural invariants.

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

## Content Blocks

- tweet cards: pair short items, full width for longer items
- HN cards: CSS columns, not flexbox
- cards must avoid being cut across page boundaries
- optional visual block should prefer a single processed monochrome asset, not multiple competing images

## Structural Rules

- no markdown `##` headers inside raw HTML blocks
- HN heading and subhead should stay HTML when inside an HTML section scaffold
- no forced page breaks unless explicitly part of an approved template rule

## Golden Reference

The current approved styling family is derived from the known-good Apr 5 repo brief and final PDF on Thoth. Future changes should be diffed against golden outputs, not improvised live in cron.
