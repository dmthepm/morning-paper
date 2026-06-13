from __future__ import annotations

import html
import json
import re
from datetime import datetime, timezone

import feedparser
import requests

from .config import MorningPaperConfig
from .models import SourceItem


def _clean_summary(value: str, *, max_chars: int = 280) -> str:
    text = html.unescape(value or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = " ".join(text.split())
    return text[:max_chars]


def _hn_score(item: dict) -> float:
    points = int(item.get("points") or 0)
    comments = int(item.get("num_comments") or 0)
    return points + comments * 0.4


def fetch_hacker_news(limit: int) -> list[SourceItem]:
    url = f"https://hn.algolia.com/api/v1/search?tags=front_page&hitsPerPage={limit}"
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    payload = json.loads(response.text)
    items: list[SourceItem] = []
    for hit in payload.get("hits", []):
        title = str(hit.get("title") or "").strip()
        if not title:
            continue
        target_url = str(hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}")
        items.append(
            SourceItem(
                source_type="hacker_news",
                source_name="Hacker News",
                title=title,
                url=target_url,
                summary=f"{hit.get('points', 0)} points · {hit.get('num_comments', 0)} comments",
                author=str(hit.get("author") or ""),
                published_at=str(hit.get("created_at") or ""),
                score=_hn_score(hit),
                metadata={
                    "points": int(hit.get("points") or 0),
                    "comments": int(hit.get("num_comments") or 0),
                    "object_id": str(hit.get("objectID") or ""),
                },
            )
        )
    return items


def _entry_published(entry: feedparser.FeedParserDict) -> str:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if not parsed:
        return ""
    try:
        return datetime(*parsed[:6], tzinfo=timezone.utc).isoformat()
    except Exception:
        return ""


def fetch_rss_feeds(config: MorningPaperConfig) -> tuple[list[SourceItem], dict[str, str]]:
    items: list[SourceItem] = []
    errors: dict[str, str] = {}
    for feed in config.sources.rss:
        try:
            response = requests.get(feed.url, timeout=30)
            response.raise_for_status()
            parsed = feedparser.parse(response.content)
        except Exception as exc:
            errors[f"rss:{feed.name}"] = str(exc)
            continue
        for entry in parsed.entries[: feed.limit]:
            title = str(entry.get("title") or "").strip()
            link = str(entry.get("link") or "").strip()
            if not title or not link:
                continue
            summary = _clean_summary(str(entry.get("summary") or entry.get("description") or ""))
            items.append(
                SourceItem(
                    source_type="rss",
                    source_name=feed.name,
                    title=title,
                    url=link,
                    summary=summary,
                    author=str(entry.get("author") or ""),
                    published_at=_entry_published(entry),
                    score=1.0,
                    metadata={},
                )
            )
    return items, errors


def collect_sources(config: MorningPaperConfig) -> tuple[dict[str, list[SourceItem]], dict[str, str]]:
    payload: dict[str, list[SourceItem]] = {"hacker_news": [], "rss": []}
    errors: dict[str, str] = {}
    if config.sources.hacker_news.enabled:
        try:
            payload["hacker_news"] = fetch_hacker_news(config.sources.hacker_news.limit)
        except Exception as exc:
            payload["hacker_news"] = []
            errors["hacker_news"] = str(exc)
    if config.sources.rss:
        try:
            payload["rss"], rss_errors = fetch_rss_feeds(config)
            errors.update(rss_errors)
        except Exception as exc:
            payload["rss"] = []
            errors["rss"] = str(exc)
    return payload, errors
