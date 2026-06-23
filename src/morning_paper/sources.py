from __future__ import annotations

import html
import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import feedparser
import requests

from .config import MorningPaperConfig
from .models import SourceItem

LOCAL_DROP_EXTENSIONS = (".md", ".markdown", ".txt", ".url")


def _clean_summary(value: str, *, max_chars: int = 280) -> str:
    text = html.unescape(value or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = " ".join(text.split())
    return text[:max_chars]


def _clean_body(value: str) -> str:
    """Strip a full-text feed body to readable plain text — never truncated.

    Full-text feeds (Substack/Atom full, paid full-text feeds) carry the whole
    article in `content:encoded`. We unescape entities and drop tags so the
    text flows into the print pipeline, but unlike `_clean_summary` we keep the
    entire body: a full read must print as a full read, not a blurb.
    """
    text = html.unescape(value or "")
    text = re.sub(r"(?i)</(p|div|br|li|h[1-6])\s*>", "\n", text)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"<[^>]+>", " ", text)
    lines = [" ".join(line.split()) for line in text.split("\n")]
    return "\n".join(line for line in lines if line).strip()


def _entry_body(entry: feedparser.FeedParserDict) -> str:
    """Full article text from a feed entry, if the feed ships it.

    feedparser exposes `content:encoded` (and Atom `content`) as
    `entry.content`, a list of dicts with a `value`. Summary-only feeds have
    no `content`, so this returns "" and the caller keeps the short summary.
    """
    content = entry.get("content")
    if not content:
        return ""
    if isinstance(content, (list, tuple)):
        raw = ""
        for part in content:
            value = part.get("value") if isinstance(part, dict) else getattr(part, "value", "")
            if value and len(str(value)) > len(raw):
                raw = str(value)
    else:
        raw = str(getattr(content, "value", "") or content)
    return _clean_body(raw)


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
                source_name="Community Signals",
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
            body = _entry_body(entry)
            items.append(
                SourceItem(
                    source_type="rss",
                    source_name=feed.name,
                    title=title,
                    url=link,
                    summary=summary,
                    body=body,
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


def _collector_inventory(newsroom: Path, *, check: bool = False) -> dict[str, object]:
    root = newsroom.expanduser().resolve()
    collectors_dir = root / "collectors"
    drop_dir = root / "inbox"
    collectors: list[dict[str, object]] = []
    if collectors_dir.is_dir():
        for script in sorted(collectors_dir.glob("*.sh")):
            if script.name in {"_lib.sh", "run_all.sh"}:
                continue
            executable = bool(script.stat().st_mode & 0o111)
            item: dict[str, object] = {
                "id": f"collector:{script.stem}",
                "type": "collector",
                "name": script.stem.replace("-", " ").title(),
                "role": "reader_owned",
                "path": str(script),
                "enabled": executable,
                "status": "configured" if executable else "not_executable",
                "command": f"collectors/{script.name} YYYY-MM-DD",
            }
            if script.name == "local-drop.sh":
                item.update(
                    {
                        "source_kind": "local_drop_folder",
                        "drop_dir": str(drop_dir),
                        "accepts": [".md", ".markdown", ".txt", ".url"],
                    }
                )
            if check:
                if shutil.which("bash") is None:
                    item.update({"status": "unchecked", "error": "bash not found"})
                else:
                    result = subprocess.run(
                        ["bash", "-n", str(script)],
                        check=False,
                        text=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                    )
                    if result.returncode == 0:
                        item.update({"syntax_ok": True, "error": ""})
                    else:
                        item.update(
                            {
                                "status": "error",
                                "syntax_ok": False,
                                "error": (result.stderr or result.stdout).strip(),
                            }
                        )
            collectors.append(item)
    drop_files = []
    unsupported_files = []
    converter_playbook = root / "collectors" / "CONVERTERS.md"
    if drop_dir.is_dir():
        for item in sorted(drop_dir.iterdir()):
            if not item.is_file() or item.name.startswith(".") or item.name == "README.md":
                continue
            if item.suffix.lower() in LOCAL_DROP_EXTENSIONS:
                drop_files.append(item.name)
            else:
                unsupported_files.append(item.name)
    return {
        "newsroom_path": str(root),
        "collectors_dir": str(collectors_dir),
        "collectors": collectors,
        "count": len(collectors),
        "status": "configured" if collectors_dir.is_dir() else "not_found",
        "local_drop": {
            "path": str(drop_dir),
            "status": "configured" if drop_dir.is_dir() else "not_found",
            "file_count": len(drop_files),
            "visible_file_count": len(drop_files) + len(unsupported_files),
            "candidate_count": len(drop_files),
            "sample_files": drop_files[:10],
            "unsupported_count": len(unsupported_files),
            "unsupported_sample_files": unsupported_files[:10],
            "accepts": list(LOCAL_DROP_EXTENSIONS),
            "converter_playbook": str(converter_playbook) if converter_playbook.is_file() else "",
            "next_action": (
                f"put .md, .txt, or .url files in {drop_dir}; for CSV, JSON, PDF, vault, "
                "work-system, or social/video exports, use collectors/CONVERTERS.md to write "
                "a converter collector"
            ),
        },
    }


def _source_next_actions(sources: list[dict[str, object]], newsroom_info: dict[str, object] | None) -> list[str]:
    actions: list[str] = []
    enabled_rss = [item for item in sources if item.get("type") == "rss" and item.get("enabled")]
    if not enabled_rss:
        actions.append(
            "Name one source the reader already uses: email/newsletter, Slack, GitHub, Linear, "
            "local folder, social export, video feed, RSS feed, or saved file."
        )
    if newsroom_info is None:
        actions.append("Pass --newsroom <path> to inventory private collectors and the local drop folder.")
        return actions

    local_drop = newsroom_info.get("local_drop") if isinstance(newsroom_info.get("local_drop"), dict) else {}
    if local_drop.get("status") == "configured":
        actions.append(str(local_drop.get("next_action") or "Put local files in the newsroom inbox."))
        if int(local_drop.get("unsupported_count") or 0) > 0:
            actions.append(
                "Unsupported local-drop files need a converter collector before they will be staged; start from collectors/CONVERTERS.md."
            )
    collectors = newsroom_info.get("collectors") if isinstance(newsroom_info.get("collectors"), list) else []
    if not collectors:
        actions.append("Create a collector script when the reader names a source that is not a feed or local file.")
    return actions


def source_inventory(
    config: MorningPaperConfig,
    *,
    check: bool = False,
    newsroom: Path | None = None,
) -> dict[str, object]:
    """Agent-readable source inventory.

    This is deliberately lighter than `collect_sources`: it answers setup and
    onboarding questions without composing an edition or fetching article URLs.
    """
    sources: list[dict[str, object]] = []
    hn = {
        "id": "hacker_news",
        "type": "built_in",
        "name": "Community Signals",
        "role": "optional_starter",
        "purpose": "technical radar only when the reader asks for it",
        "enabled": bool(config.sources.hacker_news.enabled),
        "limit": int(config.sources.hacker_news.limit),
        "status": "configured" if config.sources.hacker_news.enabled else "disabled",
    }
    if check and config.sources.hacker_news.enabled:
        try:
            sample = fetch_hacker_news(min(config.sources.hacker_news.limit, 1))
            hn.update({"status": "ok", "sample_count": len(sample), "error": ""})
        except Exception as exc:
            hn.update({"status": "error", "sample_count": 0, "error": str(exc)})
    sources.append(hn)

    for feed in config.sources.rss:
        item: dict[str, object] = {
            "id": f"rss:{feed.name}",
            "type": "rss",
            "name": feed.name,
            "role": "reader_owned",
            "purpose": "reader-supplied feed or newsletter",
            "url": feed.url,
            "enabled": True,
            "limit": int(feed.limit),
            "status": "configured",
        }
        if check:
            try:
                response = requests.get(feed.url, timeout=30)
                response.raise_for_status()
                parsed = feedparser.parse(response.content)
                entries = list(parsed.entries[: feed.limit])
                full_text_count = sum(1 for entry in entries if _entry_body(entry))
                item.update(
                    {
                        "status": "ok" if entries else "empty",
                        "sample_count": len(entries),
                        "full_text_count": full_text_count,
                        "content_mode": "full_text" if full_text_count else "summary_only",
                        "error": "",
                    }
                )
            except Exception as exc:
                item.update(
                    {
                        "status": "error",
                        "sample_count": 0,
                        "full_text_count": 0,
                        "content_mode": "unknown",
                        "error": str(exc),
                    }
                )
        sources.append(item)

    newsroom_info = _collector_inventory(newsroom, check=check) if newsroom is not None else None
    payload: dict[str, object] = {
        "sources": sources,
        "count": len(sources),
        "source_model": {
            "posture": "reader_stack_first",
            "entry_points": ["local_drop", "stage", "rss_or_feed_url", "inbox"],
            "reader_owned_inputs": [
                "local_drop",
                "collectors",
                "stage",
                "inbox",
                "exports",
                "work_systems",
                "social_and_video_feeds",
            ],
            "rule": "meet sources where they already live; do not force the reader into a new system",
        },
        "collector_contract": {
            "command": "morning-paper stage <url|file> --date YYYY-MM-DD",
            "meaning": "anything not built in should arrive as staged markdown for a specific edition date",
            "converter_playbook": (
                "collectors/CONVERTERS.md in a scaffolded private newsroom, plus "
                "docs/source-conversion.md in the engine repo"
            ),
        },
        "next_actions": _source_next_actions(sources, newsroom_info),
    }
    if newsroom_info is not None:
        payload["newsroom"] = newsroom_info
    return payload
