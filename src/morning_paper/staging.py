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
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from .article_print import (
    article_truncation_report,
    article_truncation_warning,
    fetch_article,
    render_article_markdown,
)
from .config import MorningPaperConfig
from .renderers import _page_count_worker_env, _safe_filename


@dataclass(slots=True)
class StagedItem:
    slug: str
    kind: str            # url | file | note
    source: str          # the URL, original path, or contributor address
    title: str
    words: int
    est_pages: int
    staged_at: str
    truncated: bool = False           # honesty flag: the staged copy is incomplete
    words_extracted: int | None = None  # words the extractor recovered before any render cap
    warning: str = ""                 # plain-language explanation when truncated
    extractor_note: str = ""          # honesty note: e.g. explicit remote fallback ran
    contributor: str = ""             # masthead name when a trusted sender emailed this in


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


def _estimate_pages(config: MorningPaperConfig, markdown: str) -> int:
    """Estimate staged pages in an isolated process.

    WeasyPrint is a native-library stack; if it segfaults, a normal try/except
    cannot protect the inbox/stage workflow. Staging must still succeed, so the
    renderer runs in a worker process and any failure falls back to a word
    heuristic.
    """
    try:
        result = subprocess.run(
            [sys.executable, "-m", "morning_paper.page_count_worker"],
            input=json.dumps(
                {
                    "markdown": markdown,
                    "style": config.outputs.style,
                    "palette": config.outputs.palette,
                    "font_scale": config.outputs.font_scale,
                }
            ),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=20,
            check=False,
            env=_page_count_worker_env(),
        )
        if result.returncode == 0:
            payload = json.loads(result.stdout)
            pages = int(payload["pages"])
            if pages >= 1:
                return pages
    except Exception:
        pass
    return max(1, round(len(markdown.split()) / 550))


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
    contributor: str = "",
) -> StagedItem:
    sdir = staging_dir(config, date_str)
    slug = _safe_filename(title)[:48] or "staged"
    queue = _load_queue(sdir)
    existing = {item["slug"] for item in queue}
    base, n = slug, 2
    while slug in existing:
        slug, n = f"{base}-{n}", n + 1
    pages = _estimate_pages(config, markdown)
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
        contributor=contributor,
    )
    queue.append(asdict(item))
    _save_queue(sdir, queue)
    return item


def stage_url(
    config: MorningPaperConfig,
    url: str,
    *,
    date_str: str,
    title: str | None = None,
    contributor: str = "",
) -> StagedItem:
    """Fetch a URL the way `print` does and stage it for the given edition.

    The one staging path for URLs — the `stage` CLI command and the
    contributor inbox both call this, so the honesty flags (truncation,
    remote-fallback notes) are identical no matter how the URL arrived.
    Raises ArticleExtractionError when the page cannot be extracted.
    """
    article = fetch_article(
        url,
        extractor_name=config.article_extractor,
        allow_remote_fallback=config.remote_extractor_fallback,
    )
    markdown = render_article_markdown(
        config,
        [article],
        date_str=date_str,
        images_dir=config.outputs.directory / "staging" / date_str / "_images",
    )
    # Honesty rule: if extraction or the render cap clipped the article,
    # say so plainly in the staged record instead of staging silently.
    report = article_truncation_report(article)
    return stage_markdown(
        config,
        markdown,
        date_str=date_str,
        kind="url",
        source=url,
        title=title or article.title,
        truncated=bool(report["truncated"]),
        words_extracted=int(report["words_extracted"]),
        warning=article_truncation_warning(article),
        extractor_note=article.extraction_note,
        contributor=contributor,
    )


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


def queue_item(config: MorningPaperConfig, date_str: str, slug: str) -> dict:
    sdir = staging_dir(config, date_str)
    items = _load_queue(sdir)
    for item in items:
        if item.get("slug") == slug:
            markdown_path = sdir / f"{slug}.md"
            markdown = ""
            missing = not markdown_path.exists()
            if not missing:
                markdown = markdown_path.read_text(encoding="utf-8")
            return {
                "found": True,
                "date": date_str,
                "item": item,
                "markdown_path": str(markdown_path),
                "markdown_missing": missing,
                "markdown": markdown,
            }
    return {
        "found": False,
        "date": date_str,
        "slug": slug,
        "staging_dir": str(sdir),
    }


def remove_queue_item(config: MorningPaperConfig, date_str: str, slug: str) -> dict:
    sdir = staging_dir(config, date_str)
    items = _load_queue(sdir)
    kept = [item for item in items if item.get("slug") != slug]
    removed = len(kept) != len(items)
    markdown_path = sdir / f"{slug}.md"
    file_removed = False
    if removed:
        _save_queue(sdir, kept)
        if markdown_path.exists():
            markdown_path.unlink()
            file_removed = True
    return {
        "removed": removed,
        "date": date_str,
        "slug": slug,
        "markdown_path": str(markdown_path),
        "file_removed": file_removed,
        "count": len(kept),
        "staging_dir": str(sdir),
    }
