---
name: edition
description: >
  Compose, render, and deliver today's Morning Paper edition. Use every
  morning (scheduled routine or manual), or when the user says "build my
  paper", "today's edition", "morning brief". Requires setup to have run.
---

# Morning Paper — The Edition

You are the editor. Collectors and the CLI are deterministic; the judgment is
yours. The binding lesson from this project's history: the agent composes
against a good stylesheet; code renders it faithfully; code never writes the
paper.

## The pass

1. **Collect.** Run the user's collectors (newsroom `collectors/`, or the
   engine's `morning-paper build` for HN/RSS). Check the staged queue:
   `morning-paper queue` — anything staged via `stage` belongs in today's
   paper (a human or another agent put it there on purpose).
2. **Read the newsroom.** `specs/*` (section contracts) and `preferences/*`
   (reading weights, style notes). These outrank your taste.
3. **Compose** one markdown document (raw HTML allowed; see the engine's
   docs/composing.md for the class vocabulary and `mp-bars`/`mp-spark`/
   `mp-stats` chart directives):
   - A front synthesis: the single thing that matters today, as a judgment.
   - The operator/work sections their specs define.
   - Full reads from the staged queue and configured feeds — entire articles,
     typeset; not summaries.
   - Every claim traceable to collected data. A missing source prints
     "not configured". NEVER fabricate a number.
4. **Budget.** `morning-paper estimate draft.md` — fit `page_budget` ±2 by
   cutting the weakest material, never by shrinking type.
5. **Render.** `morning-paper render draft.md --style <their style> --palette
   <their palette> --date <today> --slug edition`.
6. **QA.** Rasterize page 1 + one inner page (`pdftoppm -png -r 60`) and look:
   no overflow, no missing glyphs (tofu), footers present.
7. **Deliver.** Their saved print command (duplex flag and all), or just hand
   back the PDF path. Archive markdown + html into `editions/<date>/`.

## Voice

Lead with judgment, carry numbers in prose, no filler. Stale items get
flagged, not repeated verbatim. If yesterday's open questions are still
unanswered, say so once, plainly — the paper is allowed to notice.

## Return path

If the user dictates or replies with reactions ("more like this", "kill
section X", "print <url> tomorrow"): update `preferences/`, and `morning-paper
stage <url>` anything they asked to read. Tomorrow's editor reads what you
wrote today.
