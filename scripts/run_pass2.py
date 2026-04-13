#!/usr/bin/env python3
"""Repo-owned Pass 2 for the Morning Brief pipeline."""

from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path

from brief_runtime import (
    hn_comments,
    hn_search_by_url,
    parse_candidates,
    sentence_excerpt,
    today_date,
    write_markdown,
    fetch_text,
)


def build_story_block(title: str, score: int, url: str, why: str) -> str:
    article_text = ""
    if url and "x.com/" not in url and "twitter.com/" not in url:
        try:
            article_text = fetch_text(url)
        except Exception:
            article_text = ""

    what_happened = sentence_excerpt(article_text or why, max_sentences=4, max_chars=900)
    discussion_url = ""
    other_side = "No strong counterpoint surfaced automatically."
    links = [f"- {url}"] if url else []

    try:
        search = hn_search_by_url(url)
        if search.get("hits"):
            story = search["hits"][0]
            story_id = str(story.get("objectID"))
            discussion_url = f"https://news.ycombinator.com/item?id={story_id}"
            links.append(f"- {discussion_url}")
            comments = hn_comments(story_id).get("hits", [])
            snippets = []
            for comment in comments[:3]:
                raw_comment = html.unescape(comment.get("comment_text", ""))
                raw_comment = re.sub(r"<[^>]+>", " ", raw_comment)
                text = sentence_excerpt(raw_comment, max_sentences=1, max_chars=180)
                if text:
                    snippets.append(text)
            if snippets:
                other_side = " / ".join(snippets)
    except Exception:
        pass

    banner = "YES" if score >= 85 else "NO"
    why_devon = why
    return "\n".join(
        [
            f"## {title} — score: {score}",
            f"**Source:** {url or 'n/a'}",
            f"**Banner:** {banner}",
            "",
            "### What happened",
            what_happened or "Could not automatically extract a clean article summary.",
            "",
            "### The other side",
            other_side,
            "",
            "### Why Devon cares",
            why_devon,
            "",
            "### Links",
            *links,
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Morning Brief Pass 2.")
    parser.add_argument("--date", default=today_date())
    parser.add_argument("--project-root", default="/Users/thoth/projects/noontide")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    candidates_path = project_root / "staging" / f"candidates-{args.date}.md"
    if not candidates_path.exists():
        raise FileNotFoundError(f"Missing candidates file: {candidates_path}")

    candidates = parse_candidates(candidates_path.read_text(encoding="utf-8"))
    sections = [f"# Rabbit Holes — {args.date}", ""]
    for item in candidates:
        if item.score < 60:
            continue
        sections.append(build_story_block(item.title, item.score, item.link, item.why))
    output = project_root / "staging" / f"rabbit-holes-{args.date}.md"
    write_markdown(output, "\n".join(sections))
    print(json.dumps({"date": args.date, "output": str(output), "count": len(candidates)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
