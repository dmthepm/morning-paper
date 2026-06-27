"""Assignment Board intake for tomorrow's paper.

`morning-paper stage <url|file>` drops source material into date-keyed storage
and answers with an honest page estimate, so an agent anywhere can reply "that
adds ~5 pages to tomorrow's Assignment Board." The editor's composition pass
reads the same storage. File-first, no database.

Layout:
    {outputs.directory}/staging/{date}/queue.json     — item metadata
    {outputs.directory}/staging/{date}/{slug}.md      — internal item-id markdown
"""

from __future__ import annotations

import html
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
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
    route: str = ""                   # editorial lane: tweet card | thread | long read | visual | cut
    source_status: str = ""           # complete | snippet_only | partial | discovery | incomplete
    social: dict[str, Any] | None = None


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
    route: str = "",
    source_status: str = "",
    social: dict[str, Any] | None = None,
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
        route=route,
        source_status=source_status,
        social=social,
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


def _required_social(record: dict[str, Any], *path: str) -> Any:
    current: Any = record
    for key in path:
        value = current.get(key) if isinstance(current, dict) else None
        if value is None or value == "":
            joined = ".".join(path)
            raise ValueError(f"social source record is missing `{joined}`")
        current = value
    return current


def _social_metrics_line(metrics: dict[str, Any]) -> str:
    parts: list[str] = []
    labels = (
        ("likes", "likes"),
        ("reposts", "reposts"),
        ("retweets", "reposts"),
        ("replies", "replies"),
        ("quotes", "quotes"),
        ("views", "views"),
    )
    seen: set[str] = set()
    for key, label in labels:
        if label in seen:
            continue
        value = metrics.get(key)
        if value in {None, ""}:
            continue
        seen.add(label)
        parts.append(f"{value} {label}")
    captured = metrics.get("captured_at")
    if captured:
        parts.append(f"captured {captured}")
    return " · ".join(parts)


def _social_media_blocks(social: dict[str, Any]) -> list[str]:
    media = social.get("media")
    if not isinstance(media, list):
        return []
    blocks: list[str] = []
    for item in media:
        if not isinstance(item, dict) or not item.get("print"):
            continue
        src = str(item.get("local_path") or item.get("thumbnail_url") or item.get("url") or "").strip()
        if not src:
            continue
        caption = str(item.get("caption") or item.get("alt") or item.get("type") or "media").strip()
        blocks.extend(
            [
                '<figure class="mp-social-media">',
                f'<img src="{html.escape(src, quote=True)}" alt="{html.escape(caption, quote=True)}" />',
                f"<figcaption>{html.escape(caption)}</figcaption>",
                "</figure>",
            ]
        )
    return blocks


def _render_social_markdown(record: dict[str, Any]) -> str:
    social = record.get("social") if isinstance(record.get("social"), dict) else {}
    author = social.get("author") if isinstance(social.get("author"), dict) else {}
    metrics = social.get("metrics") if isinstance(social.get("metrics"), dict) else {}
    thread = social.get("thread") if isinstance(social.get("thread"), list) else []
    title = str(record.get("title") or "Social source")
    source = str(record.get("source") or social.get("canonical_url") or "")
    handle = str(author.get("handle") or "").strip()
    name = str(author.get("name") or handle or "Unknown source").strip()
    fetched_at = str(social.get("fetched_at") or record.get("staged_at") or "").strip()
    metrics_line = _social_metrics_line(metrics)
    kind = str(record.get("kind") or "social").strip().replace("_", " ")
    parts = [
        f'<section class="mp-social-thread" data-platform="{html.escape(str(social.get("platform") or "social"))}" '
        f'data-post-id="{html.escape(str(social.get("root_post_id") or ""))}">',
        '<div class="mp-social-head">',
        f'<div class="mp-social-kicker">{html.escape(kind)}</div>',
        f'<h2 class="mp-social-title">{html.escape(title)}</h2>',
        '<div class="mp-social-meta">',
        f'<strong>{html.escape(handle or name)}</strong>',
        f' <span>{html.escape(name)}</span>' if handle and name != handle else "",
        f' · <span>{html.escape(fetched_at)}</span>' if fetched_at else "",
        f' · <span>{html.escape(metrics_line)}</span>' if metrics_line else "",
        "</div>",
        f'<div class="mp-social-source">{html.escape(source)}</div>' if source else "",
        "</div>",
    ]
    for index, post in enumerate(thread, start=1):
        if not isinstance(post, dict):
            continue
        text = str(post.get("full_text") or "").strip()
        if not text:
            continue
        post_handle = str(post.get("handle") or handle or "").strip()
        created_at = str(post.get("created_at") or "").strip()
        label_bits = [f"{index} / {len(thread)}" if len(thread) > 1 else "post"]
        if post_handle:
            label_bits.append(post_handle)
        if created_at:
            label_bits.append(created_at)
        escaped = "<br />".join(html.escape(line) for line in text.splitlines())
        parts.extend(
            [
                '<div class="mp-social-post">',
                f'<div class="mp-social-post-meta">{" · ".join(html.escape(bit) for bit in label_bits)}</div>',
                f"<blockquote>{escaped}</blockquote>",
                "</div>",
            ]
        )
    parts.extend(_social_media_blocks(social))
    warning = str(record.get("warning") or "").strip()
    if warning:
        parts.append(f'<div class="trunc-notice">{html.escape(warning)}</div>')
    parts.append("</section>")
    return "\n".join(part for part in parts if part)


def stage_social_record(
    config: MorningPaperConfig,
    record: dict[str, Any],
    *,
    date_str: str,
) -> StagedItem:
    """Stage a complete social source record without asking code to summarize it."""
    social = record.get("social") if isinstance(record.get("social"), dict) else {}
    if not social:
        raise ValueError("social source record is missing `social`")
    source_status = str(record.get("source_status") or record.get("hydration_status") or "").strip().lower()
    if source_status not in {"complete", "snippet_only", "partial", "discovery", "incomplete"}:
        raise ValueError("social source record needs `source_status`: complete, snippet_only, partial, discovery, or incomplete")
    _required_social(record, "source")
    _required_social(record, "title")
    _required_social(record, "social", "platform")
    _required_social(record, "social", "canonical_url")
    _required_social(record, "social", "author", "handle")
    thread = social.get("thread")
    if not isinstance(thread, list) or not thread:
        raise ValueError("social source record is missing `social.thread`")
    missing_text = [
        str(post.get("post_id") or index)
        for index, post in enumerate(thread, start=1)
        if not isinstance(post, dict) or not str(post.get("full_text") or "").strip()
    ]
    if source_status == "complete" and missing_text:
        raise ValueError("complete social source record has posts without `full_text`: " + ", ".join(missing_text))
    markdown = _render_social_markdown(record)
    warning = str(record.get("warning") or "")
    if source_status != "complete":
        warning = warning or "source record is incomplete; do not print as a full post"
    return stage_markdown(
        config,
        markdown,
        date_str=date_str,
        kind=str(record.get("kind") or "social"),
        source=str(record.get("source") or social.get("canonical_url")),
        title=str(record.get("title") or "Social source"),
        truncated=source_status != "complete" or bool(record.get("truncated")),
        words_extracted=int(record.get("words_extracted") or len(markdown.split())),
        warning=warning,
        extractor_note=str(record.get("extractor_note") or ""),
        route=str(record.get("route") or ""),
        source_status=source_status,
        social=social,
    )


def queue_status(config: MorningPaperConfig, date_str: str, *, page_budget: int | None = None, max_pages: int | None = None) -> dict:
    sdir = staging_dir(config, date_str)
    items = _load_queue(sdir)
    total = sum(int(item.get("est_pages", 0)) for item in items)
    payload = {
        "date": date_str,
        "items": items,
        "count": len(items),
        "est_pages_total": total,
        "staging_dir": str(sdir),
    }
    if page_budget:
        payload["page_budget"] = page_budget
        payload["budget_remaining"] = page_budget - total
    if max_pages:
        payload["max_pages"] = max_pages
    return payload


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
