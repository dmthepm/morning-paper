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

1. **Collect.** If the contributor inbox is configured, poll it first:
   `morning-paper inbox` — mail from the masthead becomes staged items and
   the senders get their confirmations. Then run the user's collectors: the
   scaffolded newsroom has `collectors/run_all.sh` (it runs every collector
   for the edition date, then prints `morning-paper queue`); a bare-bones
   newsroom may just have the engine's `morning-paper build` for HN/RSS.
   Collectors stage via `morning-paper stage`, so check the staged queue:
   `morning-paper queue` — anything staged via `stage` or the inbox belongs in
   today's paper (a human or another agent put it there on purpose). Staged
   items with a `contributor` name render with a FROM <NAME> kicker — the
   paper says who sent it in.
2. **Read the newsroom.** `specs/*` (section contracts) and `preferences/*`
   (reading weights, style notes). These outrank your taste. Also read, when
   present: `memory/reads-ledger.md` — the cumulative record of everything
   already printed; repeating a read the owner already got is a hard fail,
   and when today's paper ships, append today's reads to it. And the most
   recent `editions/<date>/operator-answers.md` — triaged owner ink (deep-read
   picks, queue answers, steers); honor it exactly. If the newsroom keeps an
   `inbox/scans/` directory, check it for untriaged captures before composing.
3. **Compose** one markdown document (raw HTML allowed; see the engine's
   docs/composing.md for the class vocabulary and `mp-bars`/`mp-spark`/
   `mp-stats` chart directives). The newsroom's `examples/edition-skeleton.md`
   (scaffolded by setup from the engine's `examples/brief.example.md`) is the
   masthead/strip/section furniture to start from — lead with The Read:
   - A front synthesis: the single thing that matters today, as a judgment.
   - The operator/work sections their specs define.
   - Full reads from the staged queue and configured feeds — entire articles,
     typeset; not summaries.
   - Every claim traceable to collected data. A missing source prints
     "not configured". NEVER fabricate a number.
4. **The revision pass (mandatory when `preferences/voice.md` exists, recommended always).**
   Load `skills/writing` and run its discipline over the draft: the Strunk
   per-sentence checks, the AI-tells kill list, the craft that makes a page
   worth reading. Aim: same information, markedly fewer words — then spend
   the reclaimed space on MORE useful context, not whitespace. The reader's
   voice preferences in `preferences/voice.md` override every default in
   that skill; honor them exactly.

5. **Budget.** `morning-paper estimate draft.md` — fit `page_budget` ±2 by
   cutting the weakest material, never by shrinking type.
6. **Render.** `morning-paper render draft.md --style <their style> --palette
   <their palette> --date <today> --slug edition`.
7. **QA.** Rasterize page 1 + one inner page (`pdftoppm -png -r 60`) and look:
   no overflow, no missing glyphs (tofu), footers present.
8. **Editorial review.** Run the copy desk over the finished edition before it
   ships: `morning-paper review <edition-dir> --json`. It reads the composed
   artifacts and returns editorial findings (long/label headlines, lopsided or
   dead sections, duplicate stories, stale leads) with `location` + `hint`. It
   never fails the build — exit is always 0; the JSON `status` is the signal:
   - `clean` → ship.
   - `notes` (only info/nudge) → ship; you may fold the one-line nudge summary
     into the delivery note.
   - `review` (≥1 `flag`) → revise the flagged headline/section using the
     finding's `hint`, then re-render and re-review. This is guidance, not a
     gate; if a flag is wrong for this paper, accept it and ship — or mute it
     in `preferences/checks.yaml` so tomorrow's review stays quiet. The newsroom
     `preferences/checks.yaml`, when present, already tunes thresholds and
     mutes; `review` reads it automatically.
9. **Deliver.** Their saved print command (duplex flag and all), or just hand
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
