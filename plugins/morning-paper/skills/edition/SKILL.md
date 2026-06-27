---
name: edition
description: >
  Orchestrate today's Morning Paper edition end to end. Use every morning
  (manual, Claude Code routine, Codex automation, ChatGPT scheduled task, or
  local fallback), or when the user says "build my paper", "make today's
  paper", "produce today's Morning Paper", "print today's paper", or "today's
  edition". Prepare the edition workspace, assign newsroom roles when useful,
  collect sources, compose, render, review, prove, deliver, and route feedback.
  Requires setup to have run.
---

# Morning Paper — The Edition

You are the orchestrator for today's private newsroom run. Collectors and the
CLI are deterministic; the judgment is yours. The binding lesson from this
project's history: the agent composes against a good stylesheet; code renders
it faithfully; code never writes the paper.

The operating model is in `docs/private-newsroom-operating-model.md`: a
reader-owned newsroom, a host-native routine, CLI-backed proofs, and enough
context windows to report, edit, proof, deliver, and learn taste without relying
on chat memory. The skill architecture is in `docs/newsroom-skill-suite.md`;
the role model is in `ROLES.md`.

The unattended completion promise is in `docs/edition-run-contract.md`. Keep
working until the run is `complete`, `complete_with_notes`, or `blocked`. Do
not stop for ordinary source gaps, thin desks, or editorial uncertainty: record
source-health notes, cut/hold weak material, and ship the best honest paper.
Stop only for hard blockers such as no valid newsroom, no writable edition
folder, broken render/PDF stack, unreadable PDF, privacy/sensitivity conflict,
or final-editor artifacts that cannot be repaired.

Resumability rule: before substantive work, run:

```bash
morning-paper edition prepare . --date <edition-date>
```

from the newsroom root. It creates `editions/<date>/` and the required durable
files. If the run resumes after compaction, read the files in that folder first
and continue from the latest complete artifact instead of starting over. The
edition folder is the run state; do not invent a separate `RUN_STATE` file or
state machine. JSON artifacts with `"status": "pending"` are unfinished work.
If `data/*.tmp` exists, treat collector work as interrupted scratch: rerun the
collectors cleanly, refresh `collector-report.md`, `queue-snapshot.json`, and
`assignment-board.json`,
then compose.

Required durable artifacts:

- `source-inventory.json` — `morning-paper sources list/check --newsroom .`
  result, including built-in feeds and local collector scripts.
- `collector-report.md` — commands run, status lines, failures, and skips.
- `queue-snapshot.json` — compatibility snapshot from
  `morning-paper queue list --date <date>` after collectors and any pruning.
- `assignment-board.json` / `assignment-board.md` — source material projected
  into newsroom lanes.
- `desks/README.md` — the role handoff contract for orchestrator, assignment
  editor, beat reporters, editor, copy desk, art desk, producer, and taste
  editor artifacts.
- `draft.md` — current composed edition, written before estimating.
- `estimate-result.json` — JSON output from
  `morning-paper edition estimate . --date <date>` against the current draft.
- `render-result.json` — JSON output from `morning-paper render`.
- `review.json` — JSON output from `morning-paper review`.
- `visual-qa.json` — JSON output from
  `morning-paper edition visual-qa . --date <date>` against the rendered PDF.
- `final-editor.json` / `final-editor.md` — independent pre-delivery proof
  over newsroom contracts, source inventory, estimate result, render result,
  review result, PDF proof, visual QA, source warnings, page budget, and
  feedback route.
- `operator-answers.md` — a short feedback sheet for the reader to mark up or
  answer in chat.
- `desk-sheet.md` — optional print feedback sheet, created only when
  `preferences/desk-sheet.yaml` enables it.
- `feedback-plan.md` — the route from reader notes to durable newsroom files.

Role model: the host agent is the orchestrator. It owns the run, calls the CLI,
assigns roles, reads their handoffs, and delivers the edition. The Assignment
Editor does not own the whole run. When the host supports subagents, profiles,
or separate context windows, use `ROLES.md` and `docs/roles/` from the public
engine repo. Every role that runs writes one markdown artifact with YAML
frontmatter into `editions/<date>/desks/`. Beat reporters that run in parallel
use `03.1`, `03.2`, `03.3`, and so on. If the host cannot split contexts, run
the same roles sequentially and leave the same handoff files.

Substantial edition rule: a real edition (8+ estimated/rendered pages, or any
broad/source-rich run) needs the late desks. Run and persist `04-editor.md`,
`05-copy-desk.md`, `06-art-desk.md`, and, after final-editor/status,
`07-producer.md`. Reporter handoffs alone are not enough. If a subagent returns
richer findings than the current desk file, update the desk file before using
that work. The production record will hold substantial editions that skip these
gates.

## The pass

1. **Collect.** If the contributor inbox is configured, poll it first:
   `morning-paper inbox` — mail from the masthead becomes source material and
   the senders get their confirmations. Then run the user's collectors: the
   scaffolded newsroom has `collectors/run_all.sh` (it runs every collector
   for the edition date, then prints the Assignment Board); a bare-bones
   newsroom may have only manually added material or one simple source bridge.
   Collectors add material via `morning-paper stage`, so check the Assignment Board:
   `morning-paper queue list --date <edition-date>` and inspect uncertain
   items with `morning-paper queue show <item-id> --date <edition-date> --content`.
   Anything added via `stage` or the inbox belongs in today's paper unless you
   intentionally remove it with `queue remove` (a human or another agent put it
   there on purpose). Contributor items render with a FROM
   <NAME> kicker — the paper says who sent it in.
   Refresh `source-inventory.json` with `morning-paper sources check --newsroom .`
   when useful, then write `collector-report.md` and
   `queue-snapshot.json` before composing. Run `morning-paper edition
   assignment-board . --date <edition-date>` when the board needs refreshing.
   If the host supports subagents and the source surface is broad, split this
   pass: the Assignment Editor inventories source health and assigns beats;
   beat reporters test one source family or topic lane each. They find more
   candidates than the paper needs, preserve source specifics, mark repeat
   risk, and write role artifacts into `editions/<date>/desks/`. They do not
   write the final paper.
2. **Read the newsroom.** `specs/*` (section contracts), `EDITORIAL.md`
   (what earns ink), `VISUALS.md` (charts/images/layout), `SOURCES.md`
   (source purpose and cadence), `DELIVERY.md` (how the paper lands), and
   `preferences/*` (voice, reading weights, review tuning, desk-sheet
   preference). These outrank your taste. Also read, when present:
   `memory/reads-ledger.md` — the cumulative record of everything already
   printed; repeating a read the owner already got is a hard fail, and when
   today's paper ships, append today's reads to it. Read source-specific
   ledgers such as `memory/social-ledger.md` when present; repeating the same
   post, release, thread, or story angle is a hard fail unless it advanced, and
   then say what changed. Read the most recent
   `editions/<date>/operator-answers.md` — triaged owner ink (deep-read picks,
   board answers, steers); honor it exactly. Skim `TASTELOG.md` for recent
   accepted/rejected taste changes. If the newsroom keeps an `inbox/scans/`
   directory, check it for untriaged captures before composing.
3. **Compose** one markdown document (raw HTML allowed; see the engine's
   docs/composing.md for the class vocabulary, visual/figure primitives, and
   `mp-bars`/`mp-spark`/`mp-stats` chart directives). The newsroom's
   `examples/edition-skeleton.md`
   is the masthead/strip/section furniture setup scaffolded for this reader —
   lead with The Read:
   - A front synthesis: the single thing that matters today, as a judgment.
   - The operator/work sections their specs define.
   - Full reads from the Assignment Board and configured sources — entire articles,
     typeset; not summaries.
   - Every claim traceable to collected data. A missing source prints
     "not configured". NEVER fabricate a number.
   - Reading furniture from `VISUALS.md`: full-read metadata should usually be
     one readable line; preference tags should feel like labels/pills, not
     bracketed debug codes; reading/community menus should be coded choices
     with reasons, not giant URL lists.
   - Social or fast-moving beat furniture from the newsroom specs: print
     specific posts, threads, releases, artifacts, and disagreements. Do not
     flatten them into generic "people are talking about" summaries unless the
     concrete evidence is visible on the page.
   - For X/social sections, show actual complete posts, threads, native
     articles, media, and linked artifacts. Search results are discovery, not
     print-ready copy. If a social item is truncated or snippet-only, put it in
     `needs_source_record` or Source Health instead of printing it as a tweet. See
     `docs/roles/beat-reporter.md` for the required social handoff fields.
   - Keep consumption and ideation separate. Do not weave agent advice, next
     actions, post ideas, or reader-specific prompts into source cards unless
     the newsroom explicitly asks for that shape. If ideation earns space, put
     it in a separate labeled box or back-page section.
   - A visual decision. If the edition runs long, add at least one earned
     chart, figure, diagram, or deliberately visual page from `VISUALS.md` and
     the collected data. If no visual earns ink, say why in the handoff.
   Keep process/self-reference small: unless the reader explicitly asks, no
   more than about three pages of a 20-page paper should be about the paper,
   run status, source health, or production notes. Put proof details in the run
   ticket and desk handoffs.
   For substantial editions, stop here and run `04-editor.md`: the Editor
   chooses the lead, page/source budgets, cuts, holds, repeats, and any extra
   reporting needed before draft lock.
4. **The revision pass (mandatory when `preferences/voice.md` exists, recommended always).**
   For substantial editions, run `05-copy-desk.md` as its own pass. Load
   `skills/writing` and run its discipline over the draft: the Strunk
   per-sentence checks, the AI-tells cut list, the craft that makes a page
   worth reading. Aim: same information, markedly fewer words — then spend the
   reclaimed space on more useful context, not padding. The reader's voice
   preferences in `preferences/voice.md` override every default in that skill;
   honor them exactly.

5. **Budget.** Run
   `morning-paper edition estimate . --date <edition-date>` and keep its JSON
   in `estimate-result.json`. Treat `page_budget` as a ceiling and appetite
   signal, not a quota. Cut the weakest material when over budget; do not shrink
   type, add filler, or add process pages when under budget. Track page budget,
   source budget, beat/topic budget, full-read budget, visual budget, and
   research budget. For new or changing source layouts, render a small proof
   page when useful so the editor can see how many real items fit before
   locking the whole edition. If you edit `draft.md` after estimating, rerun
   the estimate before rendering.
6. **Render.** `morning-paper render draft.md --style <their style> --palette
   <their palette> --date <today> --id edition`. Save the command's JSON as
   `render-result.json`.
7. **Visual QA.** Run
   `morning-paper edition visual-qa . --date <edition-date>` after render. It
   proves the PDF exists, has pages, rasterizes selected pages when `pdftoppm`
   is available, and writes `visual-qa.json`. Then look at the PDF yourself:
   no overflow, no missing glyphs (tofu), footers present. For every page that
   contains a chart, image, illustration, or diagram, verify it is either
   full-measure, part of a deliberate visual grid, or cut. It must not leave a
   narrow orphan line beside/under it, collide with labels, or lack a caption
   or source/synthetic note when provenance matters.
   When the host supports subagents, this is an art-desk pass: ask a fresh
   visual reviewer to inspect the draft/render/review output and propose only
   visuals that improve comprehension inside the page budget. For substantial
   editions, save this as `06-art-desk.md` before final-editor.
8. **Editorial review.** Run the copy desk over the finished edition before it
   ships: `morning-paper review <edition-dir> --json`. Save the output as
   `review.json`. It reads the composed artifacts and returns editorial
   findings (long/label headlines, lopsided or dead sections, duplicate
   stories, stale leads, unfurnished visuals) with `location` + `hint`. It
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
9. **Final editor.** Run the final pre-delivery proof:
   `morning-paper edition final-editor . --date <edition-date>`. Save nothing
   manually; the command writes `final-editor.json` and `final-editor.md`.
   If the host supports a separate context/subagent, have that fresh editor
   read `final-editor.md`, `render-result.json`, `review.json`, and the PDF
   path before delivery. The final editor checks estimate freshness, render
   freshness, review freshness, PDF readability/page count, visual QA, and the
   feedback route. The JSON `status` is the ship rule:
   - `clean` → deliver.
   - `notes` → deliver, but include the short final-editor note in the handoff.
   - `review` → revise, re-render, re-review, and run final-editor again; or
     record the explicit editorial rationale for shipping despite the flag.
10. **Production record.** Run `morning-paper edition status . --date <edition-date>`
   and save its JSON/markdown. It maps the whole edition run to `complete`,
   `complete_with_notes`, or `blocked`, and records whether desk role
   artifacts exist for the run. If the run is substantial and the ticket blocks
   on missing desk quality gates, run the missing desks, rerun estimate/render
   if the draft changed, then rerun final-editor/status.
11. **Producer and deliver.** For substantial editions, run `07-producer.md`
   after final-editor/status and rerun status so the ticket reflects the
   producer handoff. Then deliver using their saved print command (duplex flag
   and all), or just hand
   back the PDF path. If `preferences/desk-sheet.yaml` enables the separate
   desk sheet, render or hand back `desk-sheet.md` with the edition; the
   default is a No. 10-style writing sheet with generous note space, a small
   concrete asks band, and a tomorrow picker. Archive markdown + html into
   `editions/<date>/`. End by pointing at
   `operator-answers.md`, optional `desk-sheet.md`, and `feedback-plan.md`,
   then asking for natural-language feedback: what to keep, cut, expand,
   change visually, add as a source, change about delivery, save as taste, or
   print tomorrow. Then stop. Do not run `morning-paper edition prepare` for
   tomorrow or start tomorrow's edition unless the reader explicitly asks.

Default done status:

- `complete` — sources checked, edition rendered, review/visual QA/final-editor
  ran, ledgers updated, and configured delivery succeeded or was not configured.
- `complete_with_notes` — the PDF is readable and delivered or handed back, but
  source gaps, review nudges, visual notes, or delivery attempts need attention.
- `blocked` — no readable, honest edition can be produced without reader action
  or environment repair.

Write `operator-answers.md` like this:

```markdown
# Operator Answers — <date>

Read the paper with a pen. Reply in chat or mark this file up.

## Keep
- What should continue?

## Cut
- What felt low-signal, too long, too repetitive, or not yours?

## More
- What should get more pages, deeper reporting, or a recurring section?

## Visuals
- What chart, image, diagram, illustration, or layout choice helped or hurt?

## Sources To Add
- Feeds, folders, newsletters, repos, people, searches, exports, or tools.

## Delivery
- Did the PDF, printout, or email/article format land the way it should?

## Taste To Save
- Which note should become a durable rule in EDITORIAL.md, VISUALS.md,
  SOURCES.md, DELIVERY.md, specs/, preferences/, or TASTELOG.md?

## Tomorrow's Assignment Board
- URLs or files to add to tomorrow's Assignment Board.
```

## Voice

Lead with judgment, carry numbers in prose, no filler. Stale items get
flagged, not repeated verbatim. If yesterday's open questions are still
unanswered, say so once, plainly — the paper is allowed to notice.

## Return path

If the user dictates or replies with reactions ("more like this", "cut
section X", "that chart worked", "email this too", "print <url> tomorrow"):
read `feedback-plan.md`, choose the smallest durable route, then use
`morning-paper edition apply-feedback . --date <edition-date> --route
editorial|voice|visuals|sources|prior|delivery|checks|the-read|front-page|reading|taste --note "<reader note>" --why
"<why it should change tomorrow>"` for stable feedback. It updates the target
durable file, appends `TASTELOG.md`, and writes the "Applied Feedback" note.
Use `morning-paper stage <url>` for anything they asked to read tomorrow; it
adds the item to tomorrow's Assignment Board.
Tomorrow's editor reads what you wrote today.
