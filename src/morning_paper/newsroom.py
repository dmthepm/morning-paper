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
            "hacker_news": "ask",
            "rss": [],
            "collectors": ["local-drop"],
            "inbox": "ask",
        },
        "printer_choice": {
            "mode": "ask",
            "command": "",
        },
        "pending_questions": [],
        "next_action": "finish interview, run sources check, then compose first edition",
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
- Hacker News: {sources.get("hacker_news", "")}
- RSS: {", ".join(str(item) for item in sources.get("rss", []) or [])}
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
    return {
        "README.md": f"""# {name} Newsroom

This is your private Morning Paper newsroom: preferences, source contracts,
memory, and edition archives. The engine renders; this repo decides.

Start here after setup resumes:

1. Read `setup-state.json`.
2. Read `SETUP.md`.
3. Read `EDITORIAL.md`, `VISUALS.md`, `SOURCES.md`, `DELIVERY.md`, and
   `TASTELOG.md`.
4. Run `morning-paper sources check`.
5. Run `collectors/run_all.sh $(date +%F)`.
6. Compose today's edition into `editions/<date>/draft.md`.
7. Render, review, deliver the PDF, then ask for feedback in
   `editions/<date>/operator-answers.md`.
""",
        "SETUP.md": _setup_doc(state),
        "CLAUDE.md": """# Newsroom - operating constitution

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
7. `preferences/algorithm-prior.yaml` - standing interests. Empty means ignore.
8. `memory/reads-ledger.md` - reads already printed. Never reprint a read.
9. `editions/<latest>/operator-answers.md` - reader feedback. Honor it exactly.
10. `TASTELOG.md` - accepted/rejected taste changes over time.
11. `memory/MEMORY.md` and `memory/threads/` - running threads.
12. `collectors/` - source adapters. Empty sources print "not configured".

## Honesty

A missing source prints "not configured". Never invent a headline, number,
quote, source, or trend. If a collector returns nothing, say so plainly.

## Delivery

Replace this with the saved print command, or keep "hand me the PDF path".

## Feedback loop

When the reader says "more like this", "less of that", "too busy", "email it
instead", or marks up the desk sheet, update the smallest durable file that
will make tomorrow better:

- editorial preference -> `EDITORIAL.md`, `preferences/voice.md`, or a section
  file in `specs/`
- visual/layout preference -> `VISUALS.md`
- source preference -> `SOURCES.md`, `preferences/algorithm-prior.yaml`,
  `collectors/`, or `memory/reads-ledger.md`
- delivery preference -> `DELIVERY.md`
- a durable decision or rejected idea -> `TASTELOG.md`
""",
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
        "VISUALS.md": f"""# Visual Desk

This is the newsroom's visual taste system. It borrows the useful part of
agent-readable design files - durable structured context - but it is not a
product UI spec. It is a visual desk for a personal newspaper.

```yaml
version: 1
surfaces:
  primary: pdf
  secondary:
    - print
    - email_article
default_visual_budget:
  major_visuals_per_edition: 0-3
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
```

## North Star

Visuals are editorial furniture. A chart, diagram, illustration, pull quote,
map, timeline, or generated image must explain something the prose cannot
explain as well. If it only decorates, cut it.

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

## Source Principles

- Start from what the reader already has. Do not force sources to move.
- Prefer local files, exports, folders, feeds, and tools the reader controls.
- A source is not trusted just because it is loud.
- A source with no data prints "not configured" or "nothing today".
- Credentials live in local env files, never in this repo.

## Registry

| Source | Type | Purpose | Cadence | Trust | Section | Status |
|---|---|---|---|---|---|---|
| Local drop | folder | Anything the reader or an agent saves | daily | reader-owned | Reading / The Read | configured |
| RSS | feed | Full-text reads and newsletters | daily | source-specific | Reading | ask |
| Hacker News | starter | Optional technical radar | ask | mixed | optional | ask |

## Backlog

- YouTube export or watch history.
- Instagram/TikTok/X export or local scraper output.
- Email newsletters via feed, IMAP, MCP, or exported files.
- Slack/Discord/work chat summaries.
- Main Branch facts, bets, pushes, and open loops.
- Obsidian vault or synced notes folder.

## Source Health

Run `morning-paper sources check --newsroom .` during setup and when a source
changes. If a source fails, record the next action here instead of hiding the
failure in chat.

## Feedback Routing

- "Add this source" -> add it to Registry or Backlog, then create/adjust a
  collector or config entry.
- "This source is noisy" -> lower cadence, map it to a smaller section, or add
  it to dampeners in `preferences/algorithm-prior.yaml`.
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
2026-06-22 - accepted - "less Hacker News" - SOURCES.md + algorithm-prior.yaml - HN is a starter source, not the paper identity.
-->
""",
        "specs/_template.md": """# Section: <name>

- **Pages**: <target, e.g. 1-2; or "as earned">
- **Source**: <which collector / feed / staged material feeds this>
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
  (`preferences/algorithm-prior.yaml`) and running threads.
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
- **Source**: staged queue and full-text feeds.
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
        "preferences/algorithm-prior.yaml": """# algorithm-prior.yaml - your standing interests, in a file you can read.
# This is the "own your algorithm" artifact: the editor amplifies what you say
# you care about. It never amplifies pure velocity; a thing being loud is not
# a reason to print it.
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
        "collectors/_lib.sh": """#!/usr/bin/env bash
# _lib.sh - shared helpers for collectors. Source this from each collector.
#
# Contract: a collector turns a source into staged markdown by calling
# `morning-paper stage`. The engine owns file layout, slug collisions, page
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
# run_all.sh - run every collector for the edition date, then print the queue.
set -euo pipefail
cd "$(dirname "$0")"

EDITION_DATE="${1:-$(date +%F)}"
echo "collectors for $EDITION_DATE:"
for c in *.sh; do
  case "$c" in _lib.sh|run_all.sh) continue ;; esac
  echo "--- $c"
  bash "$c" "$EDITION_DATE" || echo "unavailable: $c - exited nonzero"
done
echo "queue:"
morning-paper queue list --date "$EDITION_DATE"
""",
        "collectors/shipped.sh": """#!/usr/bin/env bash
# shipped.sh - "shipped while you slept" from your own merged PRs.
# Needs the `gh` CLI authenticated; stages nothing if you shipped nothing.
set -euo pipefail
source "$(dirname "$0")/_lib.sh" "${1:-}"

command -v gh >/dev/null || { unavailable "Shipped" "gh CLI not installed"; exit 0; }
tmp="$(mktemp -t shipped.XXXXXX).md"
{
  echo "# Shipped while you slept"
  echo
  gh search prs --author=@me --merged --merged-at=">$(date -v-1d +%F 2>/dev/null || date -d yesterday +%F)" \
    --json title,url,repository \
    | jq -r '.[] | "- [\\(.title)](\\(.url)) - \\(.repository.name)"'
} > "$tmp"

if [ "$(grep -c '^- ' "$tmp")" -gt 0 ]; then
  stage_markdown "Shipped" "$tmp" && ok "Shipped"
else
  unavailable "Shipped" "nothing merged since yesterday"
fi
rm -f "$tmp"
""",
        "collectors/read.sh": """#!/usr/bin/env bash
# read.sh - stage one URL as a full read for the current edition date.
set -euo pipefail
source "$(dirname "$0")/_lib.sh" "${1:-}"

URL="https://example.com/replace-with-something-worth-reading"
case "$URL" in
  *replace-with-*) unavailable "Read" "no URL set - edit collectors/read.sh"; exit 0 ;;
esac
stage_url "Today's read" "$URL" && ok "Read"
""",
        "collectors/local-drop.sh": """#!/usr/bin/env bash
# local-drop.sh - stage files from inbox/ for the current edition.
set -euo pipefail
source "$(dirname "$0")/_lib.sh" "${1:-}"

DROP_DIR="${MORNING_PAPER_DROP_DIR:-$(dirname "$0")/../inbox}"
mkdir -p "$DROP_DIR"
shopt -s nullglob

count=0
for file in "$DROP_DIR"/*; do
  [ -f "$file" ] || continue
  base="$(basename "$file")"
  case "$base" in .* ) continue ;; esac
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
  esac
done

if [ "$count" -gt 0 ]; then
  ok "Local drop ($count)"
else
  unavailable "Local drop" "put .md, .txt, or .url files in $DROP_DIR"
fi
""",
        "memory/reads-ledger.md": """# Reads ledger

<!-- One line per printed read; never reprint a read already listed here.
     The edition skill appends today's reads when the paper ships. -->
""",
        "memory/MEMORY.md": """# Memory index

<!-- Running threads load on slug match: when today's news matches a thread
     slug below, the editor loads that thread and advances it instead of
     re-reporting the story cold. One line per thread. -->
""",
        "memory/threads/README.md": """# Threads

A thread is a story you are following across editions. One file per thread.
Each morning, advance or kill: a thread either earns a second-day lead because
something moved, or it gets killed because it is over.
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

## Sources To Add
- Feeds, folders, newsletters, repos, people, searches, exports, or tools.

## Print Tomorrow
- URLs or files to stage for tomorrow's paper.
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
<div class="strip-item"><div class="strip-label">Queue</div><div class="strip-value">Replace with staged reads, or print "not configured".</div></div>
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
Full reads queued | 0 | update from queue
Open loops | 0 | update from memory
```

## Reading

Queued reads and full-text feeds go here. If there is nothing worth printing,
say "not configured" or "reading pile is empty" instead of padding.
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
