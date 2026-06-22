from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .config import MorningPaperConfig
from .sources import source_inventory
from .staging import queue_status


def operator_answers_template(date_str: str) -> str:
    return f"""# Operator Answers - {date_str}

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
"""


def draft_template(date_str: str, paper_name: str) -> str:
    return f"""# {paper_name} - {date_str}

<!-- Draft starts here. Compose against specs/, preferences/, source-inventory.json,
collector-report.md, and queue-snapshot.json. Replace this placeholder before
rendering. -->

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
        },
        "next_action": "run collectors, refresh queue-snapshot.json, compose draft.md, render, review, then ask for feedback",
    }
