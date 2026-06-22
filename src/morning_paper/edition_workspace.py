from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .config import MorningPaperConfig
from .sources import source_inventory
from .staging import queue_status


FEEDBACK_ROUTES = {
    "editorial": "EDITORIAL.md",
    "visuals": "VISUALS.md",
    "sources": "SOURCES.md",
    "delivery": "DELIVERY.md",
    "taste": "TASTELOG.md",
}


def operator_answers_template(date_str: str) -> str:
    return f"""# Operator Answers - {date_str}

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

## Print Tomorrow
- URLs or files to stage for tomorrow's paper.
"""


def feedback_plan_template(date_str: str) -> str:
    return f"""# Feedback Plan - {date_str}

Use this after the reader marks up `operator-answers.md` or replies in chat.
The goal is not to preserve every reaction. The goal is to turn stable feedback
into the smallest durable newsroom change that makes tomorrow's paper better.

## Process

1. Read `operator-answers.md` and the reader's chat/photo notes.
2. Group each note by route below.
3. Update the smallest durable file that can carry the rule.
4. Append one line to `TASTELOG.md` for every accepted or rejected durable
   taste change.
5. Stage anything under "Print Tomorrow" with `morning-paper stage <url-or-file>`.
6. Leave a short "Applied Feedback" note in this file with paths changed.

## Routes

| Reader note | Durable target |
|---|---|
| Keep / cut / more / less / page budget / what earns ink | `EDITORIAL.md`, `specs/`, `preferences/voice.md` |
| Visuals, charts, illustrations, layout, print readability | `VISUALS.md` |
| Add, demote, remove, distrust, or change cadence of a source | `SOURCES.md`, `preferences/algorithm-prior.yaml`, `collectors/` |
| PDF, print, email/article view, archive, routine/automation behavior | `DELIVERY.md` |
| One-off URL or file to read tomorrow | `morning-paper stage <url-or-file>` |
| Stable accepted/rejected taste decision | `TASTELOG.md` |

## Guardrails

- Do not overfit one annoyed note into a permanent rule. Save as durable taste
  only when the reader asks, repeats it, or the paper clearly benefits.
- Do not store private source content in the public engine repo.
- Do not erase a source because it was empty once. Record failure and next
  action in `SOURCES.md`.
- If feedback conflicts with an existing rule, update `TASTELOG.md` with the
  decision and why the older rule changed.

## Applied Feedback

No feedback applied yet.
"""


def draft_template(date_str: str, paper_name: str) -> str:
    return f"""# {paper_name} - {date_str}

<!-- Draft starts here. Compose against EDITORIAL.md, VISUALS.md, SOURCES.md,
DELIVERY.md, specs/, preferences/, source-inventory.json, collector-report.md,
and queue-snapshot.json. Replace this placeholder before rendering. -->

## The Read

Not composed yet.
"""


def _write(path: Path, text: str, *, force: bool = False) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force:
        return "skipped"
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    return "written"


def _write_json(path: Path, payload: dict, *, force: bool = False) -> str:
    return _write(path, json.dumps(payload, indent=2), force=force)


def _append_section_note(path: Path, *, heading: str, note: str) -> None:
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    if heading not in text:
        text = text.rstrip() + f"\n\n{heading}\n"
    text = text.rstrip() + f"\n- {note}\n"
    path.write_text(text, encoding="utf-8")


def _append_applied_feedback(feedback_plan: Path, line: str, *, date_str: str) -> None:
    if not feedback_plan.exists():
        feedback_plan.write_text(feedback_plan_template(date_str).rstrip() + "\n", encoding="utf-8")
    text = feedback_plan.read_text(encoding="utf-8")
    text = text.replace("No feedback applied yet.", "").rstrip()
    text = text + f"\n- {line}\n"
    feedback_plan.write_text(text, encoding="utf-8")


def apply_feedback(
    newsroom: Path,
    *,
    date_str: str,
    route: str,
    note: str,
    decision: str = "accepted",
    why: str = "",
) -> dict[str, object]:
    root = newsroom.expanduser().resolve()
    route_key = route.strip().lower()
    if route_key not in FEEDBACK_ROUTES:
        raise ValueError(f"route must be one of: {', '.join(sorted(FEEDBACK_ROUTES))}")
    decision_key = decision.strip().lower()
    if decision_key not in {"accepted", "rejected"}:
        raise ValueError("decision must be accepted or rejected")
    clean_note = " ".join(note.split())
    if not clean_note:
        raise ValueError("note is required")
    clean_why = " ".join(why.split()) or "recorded from reader feedback"

    target = root / FEEDBACK_ROUTES[route_key]
    if not target.exists():
        raise FileNotFoundError(f"missing newsroom file: {target}")

    stamp = datetime.now(timezone.utc).date().isoformat()
    target_line = f"{stamp} - {decision_key} - {clean_note} ({clean_why})"
    changed_paths: list[str] = []
    if target.name != "TASTELOG.md":
        _append_section_note(target, heading="## Feedback Notes", note=target_line)
        changed_paths.append(str(target))

    taste_log = root / "TASTELOG.md"
    if not taste_log.exists():
        raise FileNotFoundError(f"missing newsroom file: {taste_log}")
    taste_line = f"{stamp} - {decision_key} - {clean_note} - {target.name} - {clean_why}"
    _append_section_note(taste_log, heading="## Log", note=taste_line)
    changed_paths.append(str(taste_log))

    feedback_plan = root / "editions" / date_str / "feedback-plan.md"
    applied_line = f"{decision_key} `{route_key}` feedback -> `{target.name}`; paths changed: {', '.join(changed_paths)}"
    _append_applied_feedback(feedback_plan, applied_line, date_str=date_str)
    changed_paths.append(str(feedback_plan))

    return {
        "status": "applied",
        "date": date_str,
        "route": route_key,
        "decision": decision_key,
        "target": str(target),
        "taste_log": str(taste_log),
        "feedback_plan": str(feedback_plan),
        "paths_changed": changed_paths,
        "note": clean_note,
    }


def prepare_edition_workspace(
    newsroom: Path,
    config: MorningPaperConfig,
    *,
    date_str: str,
    check_sources: bool = False,
    force: bool = False,
) -> dict[str, object]:
    root = newsroom.expanduser().resolve()
    edition_dir = root / "editions" / date_str
    edition_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    skipped: list[str] = []

    def record(relative: str, status: str) -> None:
        (written if status == "written" else skipped).append(relative)

    source_payload = source_inventory(config, check=check_sources, newsroom=root)
    record("source-inventory.json", _write_json(edition_dir / "source-inventory.json", source_payload, force=force))

    collector_report = f"""# Collector Report - {date_str}

Status: not run by `morning-paper edition prepare`.

Run from the newsroom root:

```bash
collectors/run_all.sh {date_str}
morning-paper queue list --date {date_str}
```

Paste or summarize collector output here before composing. Missing collectors
must be reported as "not configured"; never invent source data.
"""
    record("collector-report.md", _write(edition_dir / "collector-report.md", collector_report, force=force))

    record("queue-snapshot.json", _write_json(edition_dir / "queue-snapshot.json", queue_status(config, date_str), force=force))
    record("draft.md", _write(edition_dir / "draft.md", draft_template(date_str, config.name), force=force))

    render_pending = {
        "status": "pending",
        "date": date_str,
        "command": f"morning-paper render {edition_dir / 'draft.md'} --date {date_str} --slug edition",
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    record("render-result.json", _write_json(edition_dir / "render-result.json", render_pending, force=force))

    review_pending = {
        "status": "pending",
        "date": date_str,
        "command": f"morning-paper review {edition_dir} --json",
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    record("review.json", _write_json(edition_dir / "review.json", review_pending, force=force))

    record("operator-answers.md", _write(edition_dir / "operator-answers.md", operator_answers_template(date_str), force=force))
    record("feedback-plan.md", _write(edition_dir / "feedback-plan.md", feedback_plan_template(date_str), force=force))

    return {
        "edition_dir": str(edition_dir),
        "date": date_str,
        "written": written,
        "skipped": skipped,
        "artifacts": {
            "source_inventory": str(edition_dir / "source-inventory.json"),
            "collector_report": str(edition_dir / "collector-report.md"),
            "queue_snapshot": str(edition_dir / "queue-snapshot.json"),
            "draft": str(edition_dir / "draft.md"),
            "render_result": str(edition_dir / "render-result.json"),
            "review": str(edition_dir / "review.json"),
            "operator_answers": str(edition_dir / "operator-answers.md"),
            "feedback_plan": str(edition_dir / "feedback-plan.md"),
        },
        "next_action": "run collectors, refresh queue-snapshot.json, compose draft.md, render, review, then ask for feedback and route it through feedback-plan.md",
    }
