from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from . import __version__


SCRIPT_MODE = 0o755
SETUP_BEGIN = "<!-- morning-paper setup-state:begin -->"
SETUP_END = "<!-- morning-paper setup-state:end -->"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _write(path: Path, text: str, *, force: bool = False, mode: int | None = None) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force:
        return "skipped"
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    if mode is not None:
        os.chmod(path, mode)
    return "written"


def _state(root: Path, *, name: str) -> dict[str, object]:
    return {
        "status": "in_progress",
        "updated_at": _utc_now(),
        "newsroom_path": str(root),
        "paper_name": name,
        "installed_version": __version__,
        "engine_install_command": 'uv tool install --python 3.13 "morning-paper[pretty]"',
        "doctor": {
            "strict_passed": False,
            "renderer_self_test_passed": False,
            "python": "",
            "weasyprint": "",
        },
        "demo": {
            "pdf_path": "",
            "opened_on_screen": False,
        },
        "plugin_state": {
            "claude_code": "unknown",
            "codex": "unknown",
        },
        "source_choices": {
            "work_streams": [],
            "personal_feeds": [],
            "local_folders": [],
            "collectors": ["local-drop"],
            "inbox": "ask",
        },
        "printer_choice": {
            "mode": "ask",
            "command": "",
        },
        "pending_questions": [],
        "next_action": "finish interview, run sources check from the newsroom root, then compose first edition",
    }


def _setup_status_markdown(state: dict[str, object]) -> str:
    demo = state.get("demo") if isinstance(state.get("demo"), dict) else {}
    doctor = state.get("doctor") if isinstance(state.get("doctor"), dict) else {}
    plugin = state.get("plugin_state") if isinstance(state.get("plugin_state"), dict) else {}
    sources = state.get("source_choices") if isinstance(state.get("source_choices"), dict) else {}
    printer = state.get("printer_choice") if isinstance(state.get("printer_choice"), dict) else {}
    pending = state.get("pending_questions") if isinstance(state.get("pending_questions"), list) else []
    pending_lines = "\n".join(f"- {item}" for item in pending) if pending else "- None."
    return f"""{SETUP_BEGIN}
## Current Status
- Status: {state.get("status", "")}
- Updated: {state.get("updated_at", "")}
- Installed version: {state.get("installed_version", "")}
- Demo PDF: {demo.get("pdf_path", "")}
- Demo opened on screen: {demo.get("opened_on_screen", False)}
- Newsroom path: {state.get("newsroom_path", "")}
- Next action: {state.get("next_action", "")}

## Doctor
- Strict passed: {doctor.get("strict_passed", False)}
- Renderer self-test passed: {doctor.get("renderer_self_test_passed", False)}
- Python: {doctor.get("python", "")}
- WeasyPrint: {doctor.get("weasyprint", "")}

## Plugin State
- Claude Code: {plugin.get("claude_code", "unknown")}
- Codex: {plugin.get("codex", "unknown")}

## Source Choices
- Work streams: {", ".join(str(item) for item in sources.get("work_streams", []) or [])}
- Personal feeds: {", ".join(str(item) for item in sources.get("personal_feeds", []) or [])}
- Local folders / exports: {", ".join(str(item) for item in sources.get("local_folders", []) or [])}
- Collectors: {", ".join(str(item) for item in sources.get("collectors", []) or [])}
- Inbox: {sources.get("inbox", "")}

## Printer
- Mode: {printer.get("mode", "")}
- Command: {printer.get("command", "")}

## Pending Questions
{pending_lines}
{SETUP_END}"""


def _setup_doc(state: dict[str, object]) -> str:
    return f"""# Morning Paper Setup

{_setup_status_markdown(state)}
"""


def _refresh_setup_doc(path: Path, state: dict[str, object]) -> None:
    replacement = _setup_status_markdown(state)
    if path.exists():
        current = path.read_text(encoding="utf-8")
        if SETUP_BEGIN in current and SETUP_END in current:
            before, rest = current.split(SETUP_BEGIN, 1)
            _old, after = rest.split(SETUP_END, 1)
            path.write_text(before.rstrip() + "\n\n" + replacement + after, encoding="utf-8")
            return
    path.write_text(_setup_doc(state), encoding="utf-8")


def _files(root: Path, *, name: str, state: dict[str, object] | None = None) -> dict[str, str]:
    state = state or _state(root, name=name)
    constitution = """# Newsroom - operating constitution

The engine renders; this repo decides. The Morning Paper engine lays out and
prints faithfully. What runs, in what order, and in whose voice is decided here,
in files I own.

## The law (read in this precedence, top wins)

1. `specs/*` - section contracts. The Read leads.
2. `EDITORIAL.md` - the durable editorial taste system.
3. `VISUALS.md` - the print/email visual desk and visual guardrails.
4. `SOURCES.md` - source purpose, trust, cadence, and backlog.
5. `DELIVERY.md` - PDF, print, and email delivery preferences.
6. `preferences/voice.md` - how the paper talks. Overrides engine defaults.
7. `preferences/interests.yaml` - standing interests. Empty means ignore.
8. `preferences/source-budgets.yaml` - source/beat appetite and cut-first rules.
9. `preferences/checks.yaml` - review thresholds and muted findings.
10. `preferences/desk-sheet.yaml` - optional printed feedback sheet settings.
11. `memory/reads-ledger.md` - reads already printed. Never reprint a read.
12. `editions/<latest>/operator-answers.md` - reader feedback. Honor it exactly.
13. `editions/<latest>/feedback-plan.md` - route feedback to durable files.
14. `TASTELOG.md` - accepted/rejected taste changes over time.
15. `memory/MEMORY.md` and `memory/threads/` - running threads.
16. `collectors/` - source adapters. Empty sources print "not configured".

## Role Context

- Orchestrator: read this file, `ROLES.md`, all durable newsroom files,
  `preferences/`, `memory/`, and the current `editions/<date>/` artifacts.
- Assignment editor: read source inventory, collector report, queue snapshot,
  Assignment Board, `SOURCES.md`, `EDITORIAL.md`, `preferences/interests.yaml`,
  `preferences/source-budgets.yaml`, and ledgers.
- Beat reporter: read the assignment, relevant source contracts, raw collector
  output, queued items, ledgers, and the source/page appetite for that beat.
- Editor: read all reporter handoffs, Assignment Board, `EDITORIAL.md`,
  `VISUALS.md`, `specs/*`, `preferences/interests.yaml`,
  `preferences/source-budgets.yaml`, ledgers, and recent `TASTELOG.md`.
- Copy desk: read `draft.md`, `preferences/voice.md`, and review output.
- Art desk: read `draft.md`, `VISUALS.md`, `preferences/desk-sheet.yaml`,
  `preferences/source-budgets.yaml`, review, visual QA, and rendered proof pages.
- Producer/final editor: read render/review/visual-QA/final-editor outputs,
  production record, role handoffs, and the current PDF proof.
- Taste editor: read reader feedback, `feedback-plan.md`, role handoffs, and the
  smallest durable file that should carry the change.

## Honesty

A missing source prints "not configured". Never invent a headline, number,
quote, source, or trend. If a collector returns nothing, say so plainly.

## Delivery

Replace this with the saved print command, or keep "hand me the PDF path".

## Done Contract

Use Morning Paper's Edition Run Contract unless this newsroom overrides it:
sources checked, collectors reported honestly, edition composed, desk sheet
included when enabled, PDF rendered, review/visual QA/final-editor run, memory
updated, and configured delivery attempted. Source failures usually become
source-health notes, not blockers.

## Feedback loop

When the reader says "more like this", "less of that", "too busy", "email it
instead", or marks up the desk sheet, read the latest `feedback-plan.md`, then
update the smallest durable file that will make tomorrow better:

- editorial preference -> `EDITORIAL.md`, `preferences/voice.md`, or a section
  file in `specs/`
- visual/layout preference -> `VISUALS.md`
- source preference -> `SOURCES.md`, `preferences/interests.yaml`,
  `preferences/source-budgets.yaml`, `collectors/`, or `memory/reads-ledger.md`
- delivery preference -> `DELIVERY.md`
- a durable decision or rejected idea -> `TASTELOG.md`

After applying feedback, add an "Applied Feedback" note to `feedback-plan.md`
with the paths changed so the next agent can resume from evidence.
"""
    return {
        ".gitignore": """# Local source drops and machine secrets stay out of git.
.env
.env.*
env.sh
*.pem
*.key
*.token
setup-state.local.json

inbox/*
!inbox/README.md
!inbox/.gitkeep
""",
        "README.md": f"""# {name} Newsroom

This is your private Morning Paper newsroom: preferences, source contracts,
memory, and edition archives. The engine renders; this repo decides.

Start here after setup resumes:

1. Read `setup-state.json`.
2. Read `SETUP.md`.
3. Read `EDITORIAL.md`, `VISUALS.md`, `SOURCES.md`, `DELIVERY.md`,
   `TASTELOG.md`, and `preferences/source-budgets.yaml`.
4. Run `morning-paper sources check` from this newsroom root.
5. Run `collectors/run_all.sh $(date +%F)`.
6. Compose today's edition into `editions/<date>/draft.md`.
7. Render, review, deliver the PDF, then ask for feedback in
   `editions/<date>/operator-answers.md` and route durable changes through
	   `editions/<date>/feedback-plan.md`.
""",
        "SETUP.md": _setup_doc(state),
        "AGENTS.md": constitution,
        "CLAUDE.md": constitution,
        "EDITORIAL.md": """# Editorial System

This is the paper's durable editorial taste. It is the answer to "what makes
this worth reading tomorrow?" Update it when the reader gives feedback.

## North Star

The paper is a personal newsroom, not a feed. It saves attention, catches what
matters, and makes one printed or readable edition that lands once and ends.

## Editorial Jobs

- **Orient** - what changed since the last edition.
- **Prioritize** - what earns ink inside today's page budget.
- **Connect** - what two sources mean together that they do not mean alone.
- **Protect attention** - what to skip, damp, or defer.
- **Move** - what the reader should do, decide, ask, or read next.

## Default Mix

- Lead with The Read: one source-backed judgment, not a link roundup.
- Prefer full reads over blurbs when the source carries enough text.
- Keep personal/work loops concise and operational.
- Treat empty or blocked sources as "not configured"; never fill the gap.

## Feedback Routing

- "More like this" -> add a rule under Recurring Wins.
- "Less of this" -> add a rule under Dampeners.
- "This section is wrong" -> update the matching `specs/*.md`.
- "This voice is wrong" -> update `preferences/voice.md`.
- "I already read this" -> add it to `memory/reads-ledger.md`.
- Every accepted or rejected durable taste change -> add one line to
  `TASTELOG.md`.

## Recurring Wins

- Source-backed synthesis that changes what the reader does today.
- One surprising connection across sources.
- A clear page-budget tradeoff, stated plainly.

## Dampeners

- Viral velocity without relevance.
- Repeated reads.
- Summary that does not lead to a decision, question, or next move.
""",
        "VISUALS.md": f"""---
version: 1
surfaces:
  primary: pdf
  secondary:
    - print
    - email_article
default_visual_budget:
  major_visuals_per_edition: 0-3
  substantial_edition_minimum: one earned visual when sources allow
  minor_visuals_per_edition: as_earned
print_constraints:
  color_must_survive_mono: true
  no_tiny_labels: true
  inspect_pdf_pages_before_delivery: true
preferred_primitives:
  charts:
    - mp-bars
    - mp-spark
    - mp-stats
  chart_bounds:
    mp-bars: 12 rows
    mp-stats: 6 primary blocks
    mp-spark: 90 most recent values
  custom_allowed:
    - svg_diagram
    - generated_illustration
    - annotated_image
    - timeline
    - map
---

# Visual Desk

This is the newsroom's visual taste system. It borrows the useful part of
agent-readable design files - durable structured context - but it is not a
product UI spec. It is a visual desk for a personal newspaper.

## North Star

Visuals are editorial furniture. A chart, diagram, illustration, pull quote,
map, timeline, or generated image must explain something the prose cannot
explain as well. If it only decorates, cut it.

For 8+ page editions, the Art Desk should look for at least one earned visual
from the day's real sources. If no visual earns ink, the handoff should say why
instead of filling space.

## Visual Types

- **Chart** - use for comparison, movement, count, budget, or trend. Prefer
  `mp-bars`, `mp-spark`, and `mp-stats` before custom SVG. If a chart needs
  more than 12 bar rows, 6 stat blocks, or 90 sparkline values, split it or
  summarize before rendering.
- **Diagram** - use when the reader needs a relationship, workflow, stack, or
  system map.
- **Timeline** - use when sequence is the story.
- **Annotated image** - use when a real object, screenshot, product, place, or
  source artifact needs inspection.
- **Generated illustration** - use sparingly for texture or metaphor. It must
  add a layer of meaning, not fill space.
- **Pull quote / clipping** - use when one sentence deserves physical weight.

## Placement Rules

- A major visual spans the full available measure or exactly two grid columns.
- If a visual spans two columns, fill the remaining column with a note, legend,
  source box, related mini-chart, or short text block.
- Do not leave a visual floating narrower than the text above and below it.
- Keep labels readable on paper. If the label will be too small, move it into
  a legend or caption.
- Every visual carries a source note or says why it is synthetic.

## Reading Furniture

- Full-read metadata should be one readable line whenever possible: publication,
  date, word count, and the reason it earned ink.
- Preference tags should render as small labels or pills, not bracketed debug
  codes in the prose.
- Community and reading menus are coded choices with a reason to care. Keep raw
  URLs in source artifacts unless the URL itself is the story.

## Desk Sheet

The default feedback page is a No. 10-style writing sheet: mostly blank note
space, a small band of concrete asks, and a tomorrow picker. It is not a second
table of contents or a URL dump. Margins and page geometry are part of the
template; the edition runner should render it as a separate one-page sheet.

## Print Rules

- Color may support meaning but may not be the only way to read the visual.
- Avoid hairline marks that vanish on a home printer.
- Prefer fewer, stronger visual moves over a page of small widgets.
- After render, inspect page 1 and one inside page before delivery.

## Email / Article Rules

If this edition becomes an email later, the visual should degrade to one of:

- an inline image with caption and source;
- a plain-text table or bullet summary;
- a link to the PDF visual.

The email should still feel like one edition, not a feed.

## Feedback Routing

- "Too cramped" -> increase whitespace or reduce visual count.
- "More charts" -> add a recurring chart rule under Visual Types.
- "I liked that illustration" -> record what it clarified and when to reuse it.
- "This visual felt random" -> add a dampener here and cut similar visuals.
""",
        "SOURCES.md": """# Source Desk

This is the source taste system: what the paper reads, why each source earns a
place, how often it should be checked, and what to do when it fails.

This file is an editorial ledger and backlog. It is not an executable source
registry. Recurring intake lives in `collectors/`, `inbox/`, staged markdown,
and the edition queue; `morning-paper sources check --newsroom .` reports both
the executable collectors and this ledger separately.

## Source Principles

- Start from what the reader already has. Do not force sources to move.
- Prefer local files, exports, folders, feeds, and tools the reader controls.
- Treat source setup as experiments first: inspect shape, write the ledger,
  test the smallest collector, then decide whether it becomes recurring.
- A source is not trusted just because it is loud.
- A source with no data prints "not configured" or "nothing today".
- Credentials live in local env files, never in this repo.
- The local drop folder is `inbox/`: put `.md`, `.txt`, or `.url` files there
  and let `collectors/local-drop.sh` add them to the Assignment Board.
- Social platforms, communities, and markets should become beats, not raw link
  dumps: define what the paper should notice, how often, and why it matters.
- Social discovery is not the same as social printing. Snippet-only posts need
  a complete source record before they appear as tweet/thread cards.
- Source budgets live in `preferences/source-budgets.yaml`. They are ceilings
  and appetite signals, not quotas.

## Editorial Ledger

| Source | Type | Purpose | Cadence | Trust | Section | Status |
|---|---|---|---|---|---|---|
| Local drop | folder | Anything the reader or an agent saves | daily | reader-owned | Reading / The Read | configured |
| Work streams | tools / exports | Email, Slack, GitHub, Linear, Main Branch, or other operating systems | daily | source-specific | Work / Open Loops | ask |
| Personal feeds | feeds / exports | Newsletters, RSS, Twitter/X, YouTube, podcasts, blogs, or social/video history | daily/weekly | source-specific | Reading / Taste | ask |
| Local knowledge | folders / vaults | Obsidian, synced notes, reports, PDFs, CSVs, JSON, screenshots, or agent-produced files | daily/as needed | reader-owned | The Read / Reference | ask |

## Backlog

- Calendar, unread email, newsletters, and contributor messages.
- Slack, Discord, GitHub, Linear, Notion, project repos, or Main Branch.
- YouTube, podcast, Substack/RSS, Twitter/X, Instagram, TikTok, or local social exports.
- Obsidian vaults, synced folders, PDFs, CSVs, JSON dumps, screenshots, and agent reports.
- Host/browser/API scrape tools the reader already trusts, tested locally
  before they become routine dependencies.

## Source Health

Run `morning-paper sources check --newsroom .` during setup and when a source
changes. It reports configured inputs, reader-owned collectors, the local drop
folder, and suggested next actions. If a source fails, record the next action
here instead of hiding the failure in chat.

## Social Source Records

Print-ready social items should preserve:

- full text or `source_status: snippet_only`;
- author name, handle, date/time, canonical URL;
- metrics such as likes, reposts, replies, views, and quotes when available;
- thread, reply, quote-post, native-article, media, and linked-artifact context;
- media paths or URLs plus whether the visual is printer-friendly;
- route: `tweet card`, `thread`, `long read`, `visual`, `source health`, or `cut`.

If a collector can only discover an item, stage it with a clear source-completeness
note so the Assignment Board sends it to `needs_source_record`.

## Feedback Routing

- "Add this source" -> add it to Registry or Backlog, then create/adjust a
  collector or config entry.
- "This source is noisy" -> lower cadence, map it to a smaller section, or add
  it to dampeners in `preferences/interests.yaml`.
- "This source is important" -> map it to a section and say what job it does.
""",
        "DELIVERY.md": """# Delivery

This file records how the paper lands. The default is physical and tactile;
email and article views are secondary surfaces that should preserve the same
editorial hierarchy.

## Primary Surface

- PDF first.
- Print when possible.
- If no printer is configured, open the PDF and report the path.

## Print

- Command: not configured.
- Duplex: ask.
- Paper size: letter.
- Color: ask. Mono must still be readable.

## PDF

- Open on screen after demo and first edition when the host can do it.
- Archive markdown, HTML, JSON, and PDF under `editions/<date>/`.
- Check page 1 and one inside page before delivery.

## Email / Article View

Not configured by default. If the reader wants email, preserve the whole paper
as one calm edition:

1. masthead and date
2. The Read
3. source-backed sections
4. full reads or links
5. feedback prompt

Email must not become a feed. One edition, one landing, clear end.

## Optional Delivery Surfaces

Record preferences here before wiring scripts:

- Telegram or another messaging channel for the PDF.
- GitHub artifact links or committed edition archives.
- A mobile-friendly article view.
- "Read later" Assignment Board intake for links or files that should enter a future edition.

Credentials, bot tokens, and deploy secrets stay outside the repo.

## Done Contract Overrides

Default: follow Morning Paper's Edition Run Contract.

- Required delivery attempts: none beyond reporting the PDF path.
- Required source desks: none. Failed sources become source-health notes unless
  this file says otherwise.
- Desk sheet: follow `preferences/desk-sheet.yaml`.
- Hard blockers: invalid newsroom, unwritable edition folder, broken renderer,
  unreadable PDF, privacy/sensitivity conflict, or final-editor artifacts that
  cannot be repaired.

If you require Preview open, Telegram delivery, GitHub artifact links, printer
output, or a mandatory source desk, write that here explicitly.

## Feedback

After delivery, ask for natural-language notes. Route them back into
`EDITORIAL.md`, `VISUALS.md`, `SOURCES.md`, `DELIVERY.md`, `preferences/`,
`specs/`, `collectors/`, or `TASTELOG.md` before the next run.
""",
        "TASTELOG.md": """# Taste Log

One line per durable taste decision. This is not a diary; it is the change log
for the reader's personal newsroom.

## Format

```text
YYYY-MM-DD - accepted/rejected - feedback - file changed - why
```

## Entries

<!-- Example:
2026-06-22 - accepted - "source mix should feel like my whole life, not one feed" - SOURCES.md + interests.yaml - Balance work streams, personal feeds, local knowledge, and intentional reading.
-->
""",
        "specs/_template.md": """# Section: <name>

- **Pages**: <target, e.g. 1-2; or "as earned">
- **Source**: <which collector / feed / Assignment Board material feeds this>
- **Content**: <what belongs here, what does not>
- **Voice**: <register for this section; defaults to preferences/voice.md>
- **Failure mode**: <what to print when the source is empty - always
  "not configured", never invented>

Sections are renameable. The label is a preference, not a hardcode. The engine
renders whatever you compose; these specs tell the editor what each section is
for.
""",
        "specs/the-read.md": """# Section: The Read (the lead)

- **Pages**: 1, leading the edition.
- **Source**: everything collected today, read against standing interests
  (`preferences/interests.yaml`) and running threads.
- **Voice**: judgment first. Lead with the single thing that matters, stated as
  a claim I can act on - not "here is what happened."
- **Failure mode**: a quiet morning is honest. Never inflate.

## The four moves

1. **GAPS** - what is missing from today's coverage that I should be asking.
2. **CONNECTIONS** - two items from different sources that are the same story,
   or that only mean something together.
3. **ALIGNMENT / DRIFT** - whether the day's signal pulls toward or away from
   what I said I care about.
4. **NEXT MOVE** - the one concrete thing worth doing today because of this.

## Three rules

- **NO MIRRORING** - never just restate a headline back to me.
- **OUTSIDE-IN** - start from the world, land on my desk.
- **SURPRISE ONCE** - one non-obvious connection per edition, or admit the day
  was quiet.
""",
        "specs/front-page.md": """# Section: Front Page

- **Pages**: shares page 1 with The Read.
- **Source**: the masthead furniture and the day's strongest single item.
- **Content**: masthead, dateline, one headline written as a judgment with a
  verb, and 2-4 teasers pointing deeper into the edition.
- **Voice**: a front page has a point of view. The headline is an argument.
- **Failure mode**: print "not enough signal for a front-page lead."
""",
        "specs/reading.md": """# Section: Reading

- **Pages**: as earned inside the page budget.
- **Source**: Assignment Board and full-text feeds.
- **Content**: full reads, not link blurbs. No repeated reads.
- **Failure mode**: print "no full reads configured" and explain the next source to add.

## Two laws

- **Source mix** - never fill the reading section from a single source.
- **Fresh vs repeat** - check `memory/reads-ledger.md` before printing a read.
  When today's edition ships, append today's reads to the ledger.
""",
        "preferences/voice.md": """# Voice

Default register: dense operator.

Choose one active register and edit it freely:

## Dense operator
- Every word earns its ink.
- Judgment before summary.
- Specific beats clever.
- Spend saved space on more useful context, not padding.

## Classic newspaper
- Measured, vivid, and concrete.
- Let the lead carry the story before analysis.
- Use narrative only when it clarifies.

## Explanatory
- More scaffolding, gentler transitions.
- Define unfamiliar terms once.
- Prefer clarity over compression.

If a section is thin, say so instead of padding.
""",
        "preferences/interests.yaml": """# interests.yaml - your standing interests, in a file you can read.
# Use this for weights, not laws: what to notice more, what to dampen, and
# which questions to keep checking. EDITORIAL.md still decides what earns ink.
# This file never amplifies pure velocity; a thing being loud is not a reason
# to print it.
#
# Everything here is optional. Absent or empty means the editor ignores it.
#
# version: 1
# revealed_themes:
#   - your-theme
# recent_search_terms:
#   - a phrase you searched
# damp:
#   - a topic you are tired of
# standing_questions:
#   - what question should the paper keep checking?
""",
        "preferences/checks.yaml": """# checks.yaml - tune the `morning-paper review` copy desk.
# Defaults apply when this file is absent or a key is omitted.
#
# version: 1
# thresholds:
#   headline-line-count:
#     warn_at_lines: 3
#   headline-length:
#     nudge_at: 60
# mute:
#   - check: headline-length
#     when: { section: "Field Notes" }
""",
        "preferences/source-budgets.yaml": """# source-budgets.yaml - appetite by source family and beat.
# Budgets are ceilings and planning signals, not quotas. A source can earn
# zero pages on a quiet day. Never add filler to satisfy this file.

version: 1
edition:
  target_pages: 12
  max_pages: 20
  max_pages_about_the_paper: 3
beats:
  work_streams:
    target_pages: 2
    max_pages: 4
    require_complete_source_records: true
  personal_feeds:
    target_pages: 2
    max_pages: 4
    require_complete_source_records: true
  reading:
    target_pages: 4
    max_pages: 8
  local_knowledge:
    target_pages: 2
    max_pages: 4
cut_first:
  - process notes that belong in the production record
  - generic trend summaries without source objects
  - repeated stories unless the angle advanced
""",
        "preferences/desk-sheet.yaml": """# desk-sheet.yaml - reader-owned feedback sheet preferences.
# The engine reads this during `morning-paper edition prepare`.
# Turn it off if you prefer chat-only feedback or `operator-answers.md`.

enabled: true
template: no10
surface: separate-sheet

# No. 10-style writing sheet: mostly notes, a compact asks band, and a
# tomorrow picker. The edition can ask different questions in prose, but the
# page should stay printable and sparse.
notes_lines: 14
ask_count: 4
tomorrow_choices: 5
""",
        "collectors/CONVERTERS.md": """# Converter Playbook

Use this when `morning-paper sources check --newsroom .` reports unsupported
files in `inbox/`. A converter collector is a small private script that turns a
source the reader already owns into source markdown:

```bash
morning-paper stage /tmp/converted-source.md --title "Source name" --date YYYY-MM-DD
```

Do not move or mutate originals. Do not commit credentials. Do not silently use
remote extraction. If you skip rows, see only metadata, OCR a scan, or produce
a partial digest, say so in the markdown.

## CSV

- Inspect headers and row count.
- Group by date, project, person, topic, channel, or source.
- Add one digest, not every row.
- Good for analytics exports, watch history, calendar logs, tickets, and
  reading lists.

## JSON

- Identify whether the export is a list, object, or nested archive.
- Keep IDs, URLs, timestamps, and source names when present.
- Convert only the records relevant to the edition date or reader question.
- Good for app exports, social exports, API dumps, issue lists, and agent logs.

## PDF

- Prefer local text extraction (`pdftotext`, Python document tools, or the host
  agent's document tools).
- Record page count and extraction quality.
- If text is poor, stage a source trace instead of pretending it is a full read.
- Ask before slow/private OCR.

## Obsidian / Folders

- Do not ingest the whole vault by default.
- Select by folder, modified date, tag, backlink, or filename.
- Preserve local paths in the digest.
- Good for daily notes, project notes, reports, saved articles, and agent files.

## GitHub / Main Branch / Work Systems

- Prefer an existing CLI or export (`gh`, local reports, Main Branch output).
- Group by shipped work, blocked work, open asks, decisions, bets, pushes, and
  risks.
- Add one operational digest with source links.

## Social / Video / Browser Exports

- Treat exports as private taste/source intelligence, not a new feed.
- Group by story, creator, topic, repeated interest, or blind spot.
- Separate discovery from print. A search hit or clipped export row can point
  at something worth completing, but it is not yet a tweet/thread/article card.
- For print candidates, preserve full text, author, handle, date/time,
  canonical URL, metrics, media/artifact links, thread/reply/quote/article
  context, and `source_status`.
- Route each candidate as `tweet card`, `thread`, `long read`, `visual`,
  `source health`, or `cut`.
- Mark sensitive analysis before printing it. Keep raw private taste analysis
  out of the paper unless the reader asked for it.

## Agent Prompt

```text
Write a Morning Paper converter collector for the unsupported files in inbox/.
Keep it local-first. Turn the source into markdown, add it with
morning-paper stage --date YYYY-MM-DD, and report exactly what was skipped,
truncated, inferred, or unavailable. Do not move or mutate the originals.
```
""",
        "collectors/_lib.sh": """#!/usr/bin/env bash
# _lib.sh - shared helpers for collectors. Source this from each collector.
#
# Contract: a collector turns a source into Assignment Board material by calling
# `morning-paper stage`. The engine owns file layout, item-id collisions, page
# estimates, and honesty flags. Collectors never write engine files by hand.
set -euo pipefail

# Edition collectors run as part of today's compose pass, so their default is
# today's edition date. Ad hoc `stage` without --date still means read later.
EDITION_DATE="${1:-$(date +%F)}"

stage_markdown() {
  local title="$1" file="$2"
  [ -s "$file" ] || { unavailable "$title" "produced no content"; return 0; }
  morning-paper stage "$file" --title "$title" --date "$EDITION_DATE"
}

stage_url() {
  local title="$1" url="$2"
  morning-paper stage "$url" --title "$title" --date "$EDITION_DATE"
}

ok() { echo "ok: $1"; }
unavailable() { echo "unavailable: $1 - ${2:-not configured}"; }
""",
        "collectors/run_all.sh": """#!/usr/bin/env bash
# run_all.sh - run every collector for the edition date, then print the Assignment Board.
set -euo pipefail
cd "$(dirname "$0")"

EDITION_DATE="${1:-$(date +%F)}"
echo "collectors for $EDITION_DATE:"
for c in *.sh; do
  case "$c" in _lib.sh|run_all.sh) continue ;; esac
  echo "--- $c"
  bash "$c" "$EDITION_DATE" || echo "unavailable: $c - exited nonzero"
done
echo "Assignment Board:"
morning-paper queue list --date "$EDITION_DATE"
""",
        "collectors/shipped.sh": """#!/usr/bin/env bash
# shipped.sh - "shipped while you slept" from your own merged PRs.
# Needs the `gh` CLI authenticated; adds nothing if you shipped nothing.
set -euo pipefail
source "$(dirname "$0")/_lib.sh" "${1:-}"

command -v gh >/dev/null || { unavailable "Shipped" "gh CLI not installed"; exit 0; }
tmp="$(mktemp -t shipped.XXXXXX).md"
{
  echo "# Shipped while you slept"
  echo
  gh search prs --author=@me --merged --merged-at=">$(date -v-1d +%F 2>/dev/null || date -d yesterday +%F)" \
    --json title,url,repository \
    --jq '.[] | "- [\\(.title)](\\(.url)) - \\(.repository.name)"'
} > "$tmp"

if [ "$(grep -c '^- ' "$tmp")" -gt 0 ]; then
  stage_markdown "Shipped" "$tmp" && ok "Shipped"
else
  unavailable "Shipped" "nothing merged since yesterday"
fi
rm -f "$tmp"
""",
        "collectors/read.sh": """#!/usr/bin/env bash
# read.sh - add one URL as a full read for the current edition date.
set -euo pipefail
source "$(dirname "$0")/_lib.sh" "${1:-}"

URL="https://example.com/replace-with-something-worth-reading"
case "$URL" in
  *replace-with-*) unavailable "Read" "no URL set - edit collectors/read.sh"; exit 0 ;;
esac
stage_url "Today's read" "$URL" && ok "Read"
""",
        "collectors/local-drop.sh": """#!/usr/bin/env bash
# local-drop.sh - add files from inbox/ to the current edition's Assignment Board.
set -euo pipefail
source "$(dirname "$0")/_lib.sh" "${1:-}"

DROP_DIR="${MORNING_PAPER_DROP_DIR:-$(dirname "$0")/../inbox}"
mkdir -p "$DROP_DIR"
shopt -s nullglob

count=0
unsupported=()
for file in "$DROP_DIR"/*; do
  [ -f "$file" ] || continue
  base="$(basename "$file")"
  case "$base" in .* ) continue ;; esac
  case "$base" in README.md ) continue ;; esac
  case "$file" in
    *.md|*.markdown)
      stage_markdown "${base%.*}" "$file" && count=$((count + 1))
      ;;
    *.txt)
      tmp="$(mktemp -t morning-paper-drop.XXXXXX).md"
      { echo "# ${base%.*}"; echo; cat "$file"; } > "$tmp"
      stage_markdown "${base%.*}" "$tmp" && count=$((count + 1))
      rm -f "$tmp"
      ;;
    *.url)
      url="$(grep -Eo 'https?://[^[:space:]]+' "$file" | head -1 || true)"
      if [ -n "$url" ]; then
        stage_url "${base%.*}" "$url" && count=$((count + 1))
      fi
      ;;
    *)
      unsupported+=("$base")
      ;;
  esac
done

if [ "$count" -gt 0 ]; then
  ok "Local drop ($count)"
else
  unavailable "Local drop" "put .md, .txt, or .url files in $DROP_DIR"
fi
if [ "${#unsupported[@]}" -gt 0 ]; then
  unavailable "Unsupported local drop" "needs a converter collector: ${unsupported[*]}"
fi
""",
        "memory/reads-ledger.md": """# Reads ledger

<!-- One line per printed read; never reprint a read already listed here.
     The edition skill appends today's reads when the paper ships. -->
""",
        "memory/MEMORY.md": """# Memory index

<!-- Running threads load on item-id/title match: when today's news matches a
     thread below, the editor loads that thread and advances it instead of
     re-reporting the story cold. One line per thread. -->
""",
        "memory/threads/README.md": """# Threads

A thread is a story you are following across editions. One file per thread.
Each morning, advance or close: a thread either earns a second-day lead because
something moved, or it gets closed because it is over.
""",
        "editions/.gitignore": "*.pdf\n",
        "editions/operator-answers.template.md": """# Operator Answers - <date>

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
""",
        "examples/edition-skeleton.md": f"""---
title: {name} - Edition Skeleton
style: broadsheet
palette: color
---

<span class="mp-footer-date">{{DATE}}</span><span class="mp-footer-name">{name}</span>

<div class="masthead">
<div class="masthead-title">{name}</div>
<div class="dateline">{{DATE}} - Daily Edition</div>
<div class="oxford"></div>
</div>

<div class="strip">
<div class="strip-item"><div class="strip-label">The Read</div><div class="strip-value">Replace with the single judgment that matters today.</div></div>
<div class="strip-item"><div class="strip-label">Board</div><div class="strip-value">Replace with assigned reads, or print "not configured".</div></div>
<div class="strip-item"><div class="strip-label">Move</div><div class="strip-value alert">Replace with the one next action worth taking.</div></div>
</div>

<div class="dept-kicker">The Read</div>

<div class="article-head">
<div class="mg-kicker">Front Page</div>
<div class="mg-title">Write a Headline With a Verb</div>
<div class="mg-dek">State the judgment clearly; do not label a pile of links.</div>
<div class="mg-byline">By <strong>The Desk</strong> - Source-backed, never fabricated</div>
</div>

<p class="mg-lede">Replace this paragraph with the outside-in synthesis:
what changed in the world, why it matters to this reader, and what to do next.</p>

```mp-stats
Sources checked | 0 | update after collectors
Full reads assigned | 0 | update from Assignment Board
Open loops | 0 | update from memory
```

## Reading

Assigned reads and full-text feeds go here. If there is nothing worth printing,
say "not configured" or "reading pile is empty" instead of padding.
""",
        "inbox/README.md": """# Local Drop Inbox

Put reader-owned source files here when you want the next edition to consider
them. The scaffolded `collectors/local-drop.sh` adds copies for the edition
date; it does not move or mutate the originals.

Accepted starter formats:

- `.md` / `.markdown` - added as written.
- `.txt` - wrapped in a markdown heading, then added.
- `.url` - the first URL in the file is added.

Run:

```bash
collectors/local-drop.sh YYYY-MM-DD
morning-paper queue list --date YYYY-MM-DD
```

For PDFs, CSVs, JSON exports, browser dumps, Obsidian vaults, work-system
exports, or social/video history, ask the agent to write a converter collector
from `collectors/CONVERTERS.md`. The converter should turn the source into
markdown and call `morning-paper stage`.
""",
        "inbox/.gitkeep": "",
    }


def _script_paths() -> Iterable[str]:
    return (
        "collectors/_lib.sh",
        "collectors/run_all.sh",
        "collectors/shipped.sh",
        "collectors/read.sh",
        "collectors/local-drop.sh",
    )


def scaffold_newsroom(path: Path, *, name: str = "Morning Paper", force: bool = False) -> dict[str, object]:
    root = path.expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    skipped: list[str] = []

    state_path = root / "setup-state.json"
    state = _state(root, name=name)
    state_status = _write(state_path, json.dumps(state, indent=2), force=force)
    (written if state_status == "written" else skipped).append("setup-state.json")

    scripts = set(_script_paths())
    for relative, text in _files(root, name=name, state=state).items():
        status = _write(root / relative, text, force=force, mode=SCRIPT_MODE if relative in scripts else None)
        (written if status == "written" else skipped).append(relative)

    return {
        "newsroom_path": str(root),
        "written": written,
        "skipped": skipped,
        "setup_state": str(state_path),
        "setup_doc": str(root / "SETUP.md"),
        "next_action": "read SETUP.md, update setup-state.json as choices are made, then run the first edition",
    }


def _parse_value(raw: str) -> object:
    lowered = raw.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered == "null":
        return None
    if raw.startswith("[") or raw.startswith("{"):
        return json.loads(raw)
    return raw


def _set_dotted(state: dict[str, object], key: str, value: object) -> None:
    parts = [part for part in key.split(".") if part]
    if not parts:
        raise ValueError("empty setup-state key")
    cursor: dict[str, object] = state
    for part in parts[:-1]:
        existing = cursor.get(part)
        if not isinstance(existing, dict):
            existing = {}
            cursor[part] = existing
        cursor = existing
    cursor[parts[-1]] = value


def update_setup_state(
    path: Path,
    *,
    sets: list[str],
    pending: list[str],
    clear_pending: bool = False,
) -> dict[str, object]:
    root = path.expanduser().resolve()
    state_path = root / "setup-state.json"
    setup_path = root / "SETUP.md"
    if not state_path.is_file():
        raise FileNotFoundError(f"missing setup-state.json in {root}; run `morning-paper newsroom init {root}` first")
    state = json.loads(state_path.read_text(encoding="utf-8"))
    if not isinstance(state, dict):
        raise ValueError(f"invalid setup-state.json in {root}: expected object")
    for item in sets:
        if "=" not in item:
            raise ValueError(f"--set must be KEY=VALUE, got: {item}")
        key, raw = item.split("=", 1)
        _set_dotted(state, key, _parse_value(raw))
    if clear_pending:
        state["pending_questions"] = []
    if pending:
        existing = state.get("pending_questions")
        if not isinstance(existing, list):
            existing = []
        existing.extend(pending)
        state["pending_questions"] = existing
    state["updated_at"] = _utc_now()
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    _refresh_setup_doc(setup_path, state)
    return {
        "newsroom_path": str(root),
        "setup_state": str(state_path),
        "setup_doc": str(setup_path),
        "state": state,
    }
