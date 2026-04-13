#!/usr/bin/env python3
"""Shared runtime helpers for the Morning Brief pipeline."""

from __future__ import annotations

import html
import json
import re
import subprocess
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


LA = ZoneInfo("America/Los_Angeles")
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) MorningBrief/1.0"


@dataclass
class Candidate:
    title: str
    source: str
    score: int
    why: str
    link: str
    seed_quality: str
    already_covered: str = "NO"


def la_now() -> datetime:
    return datetime.now(LA)


def pass1_target_date(now: datetime | None = None) -> str:
    current = now or la_now()
    if current.hour >= 18:
        return (current + timedelta(days=1)).strftime("%Y-%m-%d")
    return current.strftime("%Y-%m-%d")


def today_date(now: datetime | None = None) -> str:
    current = now or la_now()
    return current.strftime("%Y-%m-%d")


def yesterday_date(now: datetime | None = None) -> str:
    current = now or la_now()
    return (current - timedelta(days=1)).strftime("%Y-%m-%d")


def run_json(cmd: list[str], cwd: Path | None = None) -> Any:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(proc.stdout)


def fetch_json(url: str) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


def fetch_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as response:
        raw = response.read().decode("utf-8", errors="ignore")
    raw = re.sub(r"<script.*?</script>", " ", raw, flags=re.DOTALL | re.IGNORECASE)
    raw = re.sub(r"<style.*?</style>", " ", raw, flags=re.DOTALL | re.IGNORECASE)
    raw = re.sub(r"<[^>]+>", " ", raw)
    raw = html.unescape(raw)
    raw = re.sub(r"\s+", " ", raw)
    return raw.strip()


def sentence_excerpt(text: str, *, max_sentences: int = 3, max_chars: int = 800) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return ""
    parts = re.split(r"(?<=[.!?])\s+", text)
    excerpt = " ".join(parts[:max_sentences]).strip()
    if len(excerpt) > max_chars:
        excerpt = excerpt[: max_chars - 1].rstrip() + "…"
    return excerpt


def clean_line(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text


def source_domain(url: str) -> str:
    try:
        parsed = urllib.parse.urlparse(url)
        return parsed.netloc or url
    except Exception:
        return url


def title_keywords_score(title: str, body: str = "") -> int:
    haystack = f"{title} {body}".lower()
    score = 0
    positive = {
        "paperclip": 35,
        "hermes": 35,
        "agent": 25,
        "agents": 25,
        "anthropic": 20,
        "claude": 20,
        "openclaw": 30,
        "sovereign": 20,
        "startup": 15,
        "founder": 15,
        "lenny": 10,
        "karpathy": 10,
        "skool": 20,
        "community": 10,
        "workflow": 15,
        "automation": 15,
        "tool": 10,
        "tools": 10,
        "social media": 10,
        "newsletter": 10,
        "youtube": 10,
    }
    negative = {
        "crypto": -50,
        "bitcoin": -50,
        "ethereum": -50,
        "weather": -40,
        "gaming": -25,
        "iphone": -20,
        "android": -20,
    }
    for word, value in positive.items():
        if word in haystack:
            score += value
    for word, value in negative.items():
        if word in haystack:
            score += value
    return score


def candidate_score(title: str, body: str, *, source: str, points: int = 0, comments: int = 0) -> int:
    score = title_keywords_score(title, body)
    if source == "READWISE":
        score += 25
    if source == "HN":
        score += min(points // 10, 15)
        score += min(comments // 20, 10)
    if source == "BLOGWATCHER":
        score += 25
    return max(0, min(score, 100))


def previous_coverage_text(project_root: Path, hermes_home: Path, date_str: str) -> str:
    bits: list[str] = []
    prev_candidates = project_root / "staging" / f"candidates-{date_str}.md"
    prev_brief = hermes_home / "briefs" / f"{date_str}-brief.md"
    for path in (prev_candidates, prev_brief):
        if path.exists():
            bits.append(path.read_text(encoding="utf-8"))
    return "\n".join(bits).lower()


def write_markdown(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def parse_candidates(text: str) -> list[Candidate]:
    items: list[Candidate] = []
    current: dict[str, str] | None = None
    for raw in text.splitlines():
        line = raw.rstrip()
        match = re.match(r"^\d+\.\s+\*\*(.+?)\*\*\s+—\s+(.+?)\s+—\s+score:\s+(.+)$", line)
        if match:
            if current:
                items.append(
                    Candidate(
                        title=current["title"],
                        source=current["source"],
                        score=int(current["score"]),
                        why=current["why"],
                        link=current["link"],
                        seed_quality=current["seed_quality"],
                        already_covered=current["already_covered"],
                    )
                )
            current = {
                "title": match.group(1).strip(),
                "source": match.group(2).strip(),
                "score": re.sub(r"[^0-9]", "", match.group(3)) or "0",
                "why": "",
                "link": "",
                "seed_quality": "",
                "already_covered": "NO",
            }
            continue
        if current is None:
            continue
        stripped = line.strip()
        if stripped.startswith("Why"):
            current["why"] = stripped.split(":", 1)[-1].strip()
        elif stripped.startswith("Link:"):
            current["link"] = stripped.split(":", 1)[-1].strip()
        elif stripped.startswith("Seed quality:"):
            current["seed_quality"] = stripped.split(":", 1)[-1].strip()
        elif stripped.startswith("Already covered:"):
            current["already_covered"] = stripped.split(":", 1)[-1].strip()
    if current:
        items.append(
            Candidate(
                title=current["title"],
                source=current["source"],
                score=int(current["score"]),
                why=current["why"],
                link=current["link"],
                seed_quality=current["seed_quality"],
                already_covered=current["already_covered"],
            )
        )
    return items


def hn_search_by_url(url: str) -> Any:
    encoded = urllib.parse.quote(url, safe="")
    return fetch_json(
        "https://hn.algolia.com/api/v1/search?"
        f"restrictSearchableAttributes=url&query={encoded}&hitsPerPage=3"
    )


def hn_comments(story_id: str) -> Any:
    return fetch_json(
        f"https://hn.algolia.com/api/v1/search?tags=comment,story_{story_id}&hitsPerPage=5"
    )
