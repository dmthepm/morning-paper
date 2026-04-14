#!/usr/bin/env python3
"""Repo-owned Pass 1 for the Morning Brief pipeline."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timedelta
from pathlib import Path

from brief_runtime import (
    Candidate,
    candidate_score,
    clean_line,
    la_now,
    pass1_target_date,
    previous_coverage_text,
    run_json,
    sentence_excerpt,
    source_domain,
    write_markdown,
)


def x_handle_from_url(url: str) -> str:
    match = re.match(r"^https?://(?:www\.)?(?:x|twitter)\.com/([^/?#]+)/status/", url)
    if not match:
        return ""
    return f"@{match.group(1)}"


def recent_readwise_highlights(limit: int = 80) -> list[dict]:
    since = (la_now() - timedelta(days=2)).astimezone().isoformat()
    data = run_json(
        [
            "/usr/local/bin/readwise",
            "--json",
            "readwise-list-highlights",
            "--page-size",
            str(limit),
            "--updated-gt",
            since,
        ]
    )
    return data.get("results", [])


def hn_front_page(limit: int = 20) -> list[dict]:
    import urllib.request, json  # lazy import to keep startup small

    url = f"https://hn.algolia.com/api/v1/search?tags=front_page&hitsPerPage={limit}"
    with urllib.request.urlopen(url, timeout=30) as response:
        data = json.load(response)
    return data.get("hits", [])


def blogwatcher_articles() -> list[dict]:
    """Parse unread articles from blogwatcher CLI output."""
    import subprocess

    try:
        result = subprocess.run(
            [str(Path.home() / "go/bin/blogwatcher"), "articles"],
            text=True,
            capture_output=True,
            timeout=30,
            check=True,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return []

    articles: list[dict] = []
    in_section = False
    for line in result.stdout.splitlines():
        stripped = line.strip()
        if stripped.startswith("Unread articles"):
            in_section = True
            continue
        if in_section and stripped.startswith("["):
            # Parse: [57] [new] Title Here | Blog Name
            bracket_end = stripped.index("]")
            idx_str = stripped[1:bracket_end]
            rest = stripped[bracket_end + 1 :].strip()
            if rest.startswith("[new]"):
                rest = rest[5:].strip()
            # rest is "Title | Blog" or just "Title"
            if " | " in rest:
                title_part, blog_part = rest.rsplit(" | ", 1)
                url_line = ""
            else:
                title_part = rest
                blog_part = ""
                url_line = ""
            articles.append(
                {
                    "id": idx_str,
                    "title": title_part.strip(),
                    "blog": blog_part.strip(),
                    "url": "",
                }
            )
        elif in_section and stripped.startswith("URL:"):
            url_val = stripped.split("URL:", 1)[-1].strip()
            if articles:
                articles[-1]["url"] = url_val
        elif in_section and stripped.startswith("Blog:"):
            blog_val = stripped.split("Blog:", 1)[-1].strip()
            if articles:
                articles[-1]["blog"] = blog_val
        elif in_section and stripped.startswith("Published:"):
            pub_val = stripped.split("Published:", 1)[-1].strip()
            if articles:
                articles[-1]["published"] = pub_val
        elif in_section and stripped == "" and articles:
            in_section = False
    return articles


def candidate_from_highlight(item: dict, previous_text: str) -> Candidate | None:
    title = clean_line(item.get("text", "")[:140])
    if not title:
        return None
    url = item.get("url") or item.get("readwise_url") or ""
    handle = x_handle_from_url(url)
    source = f"X / {handle}" if handle else "READWISE"
    score = candidate_score(title, item.get("text", ""), source="READWISE")
    if score < 55:
        return None
    already = "YES" if title.lower() in previous_text or url.lower() in previous_text else "NO"
    return Candidate(
        title=title,
        source=source,
        score=score,
        why=sentence_excerpt(item.get("text", ""), max_sentences=2, max_chars=220),
        link=url,
        seed_quality="HIGH — Devon explicitly saved this, so it is a real taste signal.",
        already_covered=already,
    )


def candidate_from_hn(item: dict, previous_text: str) -> Candidate | None:
    title = clean_line(item.get("title", ""))
    url = item.get("url") or f"https://news.ycombinator.com/item?id={item.get('objectID')}"
    keyword_score = candidate_score(
        title,
        "",
        source="HN",
        points=int(item.get("points") or 0),
        comments=int(item.get("num_comments") or 0),
    )
    community_score = min(
        85,
        38 + int(item.get("points") or 0) // 20 + int(item.get("num_comments") or 0) // 25,
    )
    score = max(keyword_score, community_score)
    if score < 60:
        return None
    why = (
        f"HN put this on the front page ({item.get('points', 0)} points, "
        f"{item.get('num_comments', 0)} comments); this is the community blind-spot lane even if "
        "Devon did not bookmark it himself."
    )
    already = "YES" if title.lower() in previous_text or url.lower() in previous_text else "NO"
    seed_quality = "HIGH" if score >= 80 else "MEDIUM"
    return Candidate(
        title=title,
        source=f"HN / {source_domain(url)}",
        score=score,
        why=why,
        link=url,
        seed_quality=f"{seed_quality} — community signal with clear Devon relevance.",
        already_covered=already,
    )


def hn_card_from_item(item: dict, previous_text: str) -> Candidate | None:
    title = clean_line(item.get("title", ""))
    if not title:
        return None
    url = item.get("url") or f"https://news.ycombinator.com/item?id={item.get('objectID')}"
    already = "YES" if title.lower() in previous_text or url.lower() in previous_text else "NO"
    return Candidate(
        title=title,
        source=f"HN / {source_domain(url)}",
        score=int(item.get("points") or 0),
        why=(
            f"{item.get('points', 0)} points · {item.get('num_comments', 0)} comments"
            + (f" · by {item.get('author')}" if item.get("author") else "")
        ),
        link=url,
        seed_quality="HN front page",
        already_covered=already,
    )


def candidate_from_blogwatcher(item: dict, previous_text: str) -> Candidate | None:
    title = clean_line(item.get("title", "")[:140])
    if not title or not item.get("url"):
        return None
    score = candidate_score(title, "", source="BLOGWATCHER")
    # Boost for Devon-relevant sources
    blog = item.get("blog", "").lower()
    if any(k in blog for k in ["lenny", "every", "astral", "newport"]):
        score = min(score + 15, 100)
    if score < 45:
        return None
    already = "YES" if title.lower() in previous_text or item.get("url", "").lower() in previous_text else "NO"
    return Candidate(
        title=title,
        source=f"Blog / {item.get('blog', 'Unknown')}",
        score=score,
        why=f"New article from {item.get('blog', 'blog')} — {item.get('published', 'recently published')}.",
        link=item.get("url", ""),
        seed_quality="MEDIUM — blog feed signal from a trusted source.",
        already_covered=already,
    )


def dedupe(candidates: list[Candidate]) -> list[Candidate]:
    seen: set[str] = set()
    output: list[Candidate] = []
    for item in sorted(candidates, key=lambda c: (-c.score, c.source, c.title)):
        key = (item.link or item.title).lower()
        if key in seen:
            continue
        seen.add(key)
        output.append(item)
    return output


def signal_selection(candidates: list[Candidate], *, limit: int = 6) -> list[Candidate]:
    signals = [
        c for c in candidates
        if c.link and ("x.com/" in c.link or "twitter.com/" in c.link)
    ]
    return sorted(signals, key=lambda c: (-c.score, c.title))[:limit]


def hn_selection(candidates: list[Candidate], *, limit: int = 20) -> list[Candidate]:
    hn = [c for c in candidates if c.source.startswith("HN / ")]
    return sorted(hn, key=lambda c: (-c.score, c.title))[:limit]


def mixed_selection(candidates: list[Candidate], *, limit: int = 5) -> list[Candidate]:
    readwise = [c for c in candidates if c.source == "READWISE"]
    hn = [c for c in candidates if c.source.startswith("HN / ")]
    blogs = [c for c in candidates if c.source.startswith("Blog / ")]
    other = [
        c
        for c in candidates
        if c.source != "READWISE"
        and not c.source.startswith("HN / ")
        and not c.source.startswith("Blog / ")
    ]
    selected: list[Candidate] = []
    selected.extend(readwise[:3])
    selected.extend(hn[:1])
    selected.extend(blogs[:1])  # Up to 1 blog article
    for item in readwise[3:] + hn[1:] + blogs[1:] + other:
        if len(selected) >= limit:
            break
        if item not in selected:
            selected.append(item)
    return selected[:limit]


def to_markdown(date_str: str, candidates: list[Candidate], title: str = "Story Seeds") -> str:
    lines = [f"# {title} — {date_str}", "", f"## {title}", ""]
    if not candidates:
        lines.append("No qualifying story seeds found.")
        return "\n".join(lines)
    for idx, item in enumerate(candidates, start=1):
        lines.extend(
            [
                f"{idx}. **{item.title}** — {item.source} — score: {item.score}",
                f"   Why Devon cares: {item.why}",
                f"   Link: {item.link}",
                f"   Seed quality: {item.seed_quality}",
                f"   Already covered: {item.already_covered}",
                "",
            ]
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Morning Brief Pass 1.")
    parser.add_argument("--date", default=pass1_target_date())
    parser.add_argument("--project-root", default="/Users/thoth/projects/noontide")
    parser.add_argument("--hermes-home", default="/Users/thoth/.hermes")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    hermes_home = Path(args.hermes_home).resolve()
    prior_date = (datetime.strptime(args.date, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
    previous_text = previous_coverage_text(project_root, hermes_home, prior_date)

    candidates: list[Candidate] = []
    for item in recent_readwise_highlights():
        candidate = candidate_from_highlight(item, previous_text)
        if candidate:
            candidates.append(candidate)

    front_page = hn_front_page()
    for item in front_page:
        candidate = candidate_from_hn(item, previous_text)
        if candidate:
            candidates.append(candidate)

    for item in blogwatcher_articles():
        candidate = candidate_from_blogwatcher(item, previous_text)
        if candidate:
            candidates.append(candidate)

    ranked = [c for c in dedupe(candidates) if c.already_covered == "NO" or c.score >= 85]
    story_seeds = mixed_selection(ranked, limit=5)
    signals = signal_selection(ranked, limit=6)
    hn_cards = [card for item in front_page if (card := hn_card_from_item(item, previous_text))]

    output = project_root / "staging" / f"candidates-{args.date}.md"
    signals_output = project_root / "staging" / f"signals-{args.date}.md"
    hn_output = project_root / "staging" / f"hn-top-{args.date}.md"
    write_markdown(output, to_markdown(args.date, story_seeds, "Story Seeds"))
    write_markdown(signals_output, to_markdown(args.date, signals, "Signals"))
    write_markdown(hn_output, to_markdown(args.date, hn_cards, "Hacker News"))
    print(json.dumps({
        "date": args.date,
        "candidates_output": str(output),
        "signals_output": str(signals_output),
        "hn_output": str(hn_output),
        "story_seed_count": len(story_seeds),
        "signals_count": len(signals),
        "hn_count": len(hn_cards),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
