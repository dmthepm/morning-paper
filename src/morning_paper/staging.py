"""Tomorrow's-brief staging: the queue any agent can feed.

`morning-paper stage <url|file>` drops material into a date-keyed staging
directory and answers with an honest page estimate, so an agent anywhere can
reply "that adds ~5 pages; it's in the queue for the editor." The editor's
composition pass reads the same queue. File-first, no database.

Layout:
    {outputs.directory}/staging/{date}/queue.json     — item metadata
    {outputs.directory}/staging/{date}/{slug}.md      — staged markdown
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from .config import MorningPaperConfig
from .renderers import _safe_filename, count_pages


@dataclass(slots=True)
class StagedItem:
    slug: str
    kind: str            # url | file | note
    source: str          # the URL or original path
    title: str
    words: int
    est_pages: int
    staged_at: str
    truncated: bool = False           # honesty flag: the staged copy is incomplete
    words_extracted: int | None = None  # words the extractor recovered before any render cap
    warning: str = ""                 # plain-language explanation when truncated
    extractor_note: str = ""          # honesty note: e.g. local extraction fell back to jina


def staging_dir(config: MorningPaperConfig, date_str: str) -> Path:
    return config.outputs.directory / "staging" / date_str


def default_edition_date(config: MorningPaperConfig) -> str:
    """Material staged during the day is for TOMORROW's paper."""
    now = datetime.now(ZoneInfo(config.timezone))
    return (now.date() + timedelta(days=1)).isoformat()


def _load_queue(path: Path) -> list[dict]:
    queue_file = path / "queue.json"
    if queue_file.exists():
        return json.loads(queue_file.read_text(encoding="utf-8"))
    return []


def _save_queue(path: Path, items: list[dict]) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "queue.json").write_text(json.dumps(items, indent=2), encoding="utf-8")


def stage_markdown(
    config: MorningPaperConfig,
    markdown: str,
    *,
    date_str: str,
    kind: str,
    source: str,
    title: str,
    truncated: bool = False,
    words_extracted: int | None = None,
    warning: str = "",
    extractor_note: str = "",
) -> StagedItem:
    sdir = staging_dir(config, date_str)
    slug = _safe_filename(title)[:48] or "staged"
    queue = _load_queue(sdir)
    existing = {item["slug"] for item in queue}
    base, n = slug, 2
    while slug in existing:
        slug, n = f"{base}-{n}", n + 1
    try:
        pages = count_pages(
            markdown,
            style=config.outputs.style,
            palette=config.outputs.palette,
            font_scale=config.outputs.font_scale,
        )
    except Exception:
        # estimation must never block staging; fall back to a words heuristic
        pages = max(1, round(len(markdown.split()) / 550))
    sdir.mkdir(parents=True, exist_ok=True)
    (sdir / f"{slug}.md").write_text(markdown, encoding="utf-8")
    item = StagedItem(
        slug=slug,
        kind=kind,
        source=source,
        title=title,
        words=len(markdown.split()),
        est_pages=pages,
        staged_at=datetime.now(ZoneInfo(config.timezone)).isoformat(timespec="seconds"),
        truncated=truncated,
        words_extracted=words_extracted,
        warning=warning,
        extractor_note=extractor_note,
    )
    queue.append(asdict(item))
    _save_queue(sdir, queue)
    return item


def queue_status(config: MorningPaperConfig, date_str: str) -> dict:
    sdir = staging_dir(config, date_str)
    items = _load_queue(sdir)
    total = sum(int(item.get("est_pages", 0)) for item in items)
    budget = config.page_budget
    return {
        "date": date_str,
        "items": items,
        "count": len(items),
        "est_pages_total": total,
        "page_budget": budget,
        "budget_remaining": (budget - total) if budget else None,
        "staging_dir": str(sdir),
    }
