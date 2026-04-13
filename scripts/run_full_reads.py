#!/usr/bin/env python3
"""
Full-Read Synthesis — Morning Brief Pipeline

Reads rabbit-holes-{date}.md and synthesizes 300-500 word full-read blocks
for Sections II and III of the Morning Brief.

Strategy (in priority order):
1. If a story has a real article URL (not twitter/x.com/hackernews), fetch via Jina AI reader
2. If a YouTube video ID is present and a transcript exists on disk, use it
3. If "What happened" section has >200 chars, synthesize from that (fallback)
4. Otherwise skip

Output: staging/full-reads-{date}.md
  (assemble_brief.py reads ## Full Read: headings from this file)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo


# Domains to skip when looking for real article URLs
SKIP_DOMAINS = {"twitter.com", "x.com", "news.ycombinator.com", "github.com",
                "youtube.com", "youtu.be", "instagram.com", "linkedin.com"}


def is_article_url(url: str) -> bool:
    """Return True if URL points to a real article (not social media)."""
    if not url:
        return False
    domain = re.sub(r"https?://(www\.)?", "", url).split("/")[0].lower()
    return domain not in SKIP_DOMAINS


def fetch_article_via_jina(url: str, timeout: int = 20) -> str | None:
    """
    Fetch article content via Jina AI reader.
    Returns markdown body (stripped of Jina header) or None on failure.
    """
    try:
        jina_url = f"https://r.jina.ai/{url}"
        req = urllib.request.Request(
            jina_url,
            headers={"Accept": "text/markdown", "X-Timeout": str(timeout)}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content = resp.read().decode("utf-8", errors="replace")

        # Strip Jina metadata header (first lines up to first empty line)
        lines = content.splitlines()
        body_start = 0
        for i, line in enumerate(lines):
            if not line.strip():
                body_start = i + 1
                break
        # If no blank line found, check if first line is a URL (metadata)
        if body_start == 0 and lines and ("http" in lines[0] or "Title:" in lines[0]):
            for i, line in enumerate(lines[1:], 1):
                if not line.strip():
                    body_start = i + 1
                    break
        if body_start > 0:
            content = "\n".join(lines[body_start:]).strip()

        # Strip image markdown lines (reduce bloat)
        content = re.sub(r"!\[.*?\]\(.*?\)", "", content)
        content = re.sub(r"\[.*?\]:\s*https?://\S+", "", content)

        return content if len(content) > 200 else None
    except Exception as e:
        print(f"  [WARN] Jina fetch failed for {url}: {e}", file=sys.stderr)
        return None


def la_now() -> datetime:
    return datetime.now(ZoneInfo("America/Los_Angeles"))


def today_date() -> str:
    return la_now().strftime("%Y-%m-%d")


def extract_story_sections(text: str) -> list[dict[str, str]]:
    """Parse rabbit-holes markdown into story dicts."""
    matches = list(re.finditer(
        r"^##\s+(.+?)\s+— score:\s+(\d+)\s*$", text, flags=re.MULTILINE
    ))
    stories = []
    for i, match in enumerate(matches):
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        stories.append({
            "title": match.group(1).strip(),
            "score": match.group(2).strip(),
            "body": body,
        })
    return stories


def section_text(body: str, heading: str) -> str:
    """Extract a named sub-section from a story body."""
    pattern = rf"^###\s+{re.escape(heading)}\s*$"
    match = re.search(pattern, body, flags=re.MULTILINE)
    if not match:
        return ""
    start = match.end()
    next_match = re.search(r"^###\s+.+$", body[start:], flags=re.MULTILINE)
    end = start + next_match.start() if next_match else len(body)
    return body[start:end].strip()


def find_primary_url(body: str) -> str | None:
    """Find the best article/blog URL (prefer non-social links)."""
    happened = section_text(body, "What happened")
    other_side = section_text(body, "The other side")
    combined = happened + "\n" + other_side

    # Find all URLs
    urls = re.findall(r"https?://[^\s\)\]]+", combined)

    # Prefer article/blog domains, skip social
    skip_domains = {"twitter.com", "x.com", "news.ycombinator.com",
                    "github.com", "youtube.com", "youtu.be"}
    for url in urls:
        domain = re.sub(r"https?://(www\.)?", "", url).split("/")[0]
        if domain not in skip_domains:
            return url

    return urls[0] if urls else None


def find_youtube_id(body: str) -> str | None:
    """Find a YouTube video ID in the story."""
    happened = section_text(body, "What happened")
    other_side = section_text(body, "The other side")
    combined = happened + "\n" + other_side
    urls = re.findall(r"https?://[^\s\)]+", combined)
    for url in urls:
        if "youtube.com/watch" in url or "youtu.be/" in url:
            m = re.search(r"(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})", url)
            if m:
                return m.group(1)
    return None


def read_youtube_transcript(video_id: str, project_root: Path) -> tuple[str, str] | None:
    """
    Read a YouTube brief note AND transcript from disk.
    Returns (brief_note_or_none, transcript_text).
    """
    research_dir = project_root / "research" / "youtube"
    if not research_dir.exists():
        return None

    for item in research_dir.iterdir():
        if not item.is_dir() or video_id not in item.name:
            continue

        # Check brief note first — only use if it has real content
        note_path = item / "brief-note.md"
        note_content = ""
        if note_path.exists():
            note_text = note_path.read_text(encoding="utf-8")
            # Skip if template unfilled
            if "[To be filled" not in note_text and "Quick Summary\n[To be filled" not in note_text:
                # Extract quick summary if present
                qs_match = re.search(r"## Quick Summary\s*\n(.+?)(?=\n##|\Z)", note_text, re.DOTALL)
                if qs_match:
                    note_content = qs_match.group(1).strip()

        # Read transcript (use regardless — it's the raw content)
        transcript_path = item / "transcript.md"
        if transcript_path.exists():
            transcript = transcript_path.read_text(encoding="utf-8")
            if len(transcript) > 300:
                return (note_content, transcript)
    return None


def synthesize_from_rabbit_hole(title: str, story_body: str, url: str | None,
                                  project_root: Path) -> tuple[str, int] | None:
    """
    Synthesize a full read for a rabbit hole story.
    
    Priority:
    1. Fetch real article via Jina AI reader (if URL is not social media)
    2. Fall back to "What happened" rabbit hole text
    
    Target: 300-600 words of real prose.
    """
    # Determine source label
    source_label = "Web Signal"
    if url:
        if "aisle.com" in url:
            source_label = "AISLE Platform Blog"
        elif "every.to" in url:
            source_label = "Every.to"
        elif "simonwillison" in url:
            source_label = "Simon Willison"
        elif "karpathy" in url:
            source_label = "Karpathy Blog"
        else:
            domain = re.sub(r"https?://(www\.)?", "", url).split("/")[0]
            source_label = domain

    def clean(text: str) -> str:
        """Remove HTML artifacts and normalize whitespace."""
        text = re.sub(r"\{#[^}]*\}", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    # Strategy 1: Try fetching real article via Jina
    article_content: str | None = None
    if url and is_article_url(url):
        print(f"  [INFO] Fetching real article via Jina: {url}")
        article_content = fetch_article_via_jina(url)
        if article_content:
            print(f"  [OK] Got {len(article_content)} chars from Jina")

    # Build synthesis text
    synthesis_source: str
    if article_content:
        synthesis_source = article_content
    else:
        # Strategy 2: Fall back to rabbit hole "What happened"
        happened = section_text(story_body, "What happened")
        if not happened or len(happened) < 100:
            print(f"  [SKIP] '{title[:55]}' — no substantial content (no Jina URL, short rabbit hole)")
            return None
        synthesis_source = happened

    # Extract sections from rabbit hole for context
    other_side = section_text(story_body, "The other side")
    why = section_text(story_body, "Why Devon cares")

    # Clean the synthesis source
    synthesis_clean = clean(synthesis_source)
    if len(synthesis_clean) < 100:
        return None

    # Build 3-paragraph synthesis
    paragraphs = []

    # Para 1: Core news (first 400 chars of real article or rabbit hole)
    paragraphs.append(synthesis_clean[:400])

    # Para 2: Deeper context (chars 400-800 if available)
    if len(synthesis_clean) > 400:
        extra = synthesis_clean[400:800].strip()
        if extra:
            paragraphs.append(extra)

    # Para 3: The other side / counterpoint
    if other_side and len(other_side) > 50:
        other_clean = clean(other_side)[:400]
        paragraphs.append(f"Counterpoint: {other_clean}")

    # Para 4: Why Devon cares (relevance)
    if why:
        why_clean = clean(why)[:200]
        paragraphs.append(f"Relevance: {why_clean}")

    # Key takeaways
    takeaways = [f"- {title}"]
    if url:
        takeaways.append(f"- Source: {url}")
    if why:
        why_short = clean(why)[:120]
        takeaways.append(f"- {why_short}")
    if article_content:
        takeaways.append(f"- Full article ({len(article_content)} chars) fetched via Jina AI")
    else:
        takeaways.append(f"- Synthesized from rabbit hole summary (Jina fetch unavailable)")

    body_text = "\n\n".join(paragraphs) + "\n\nKey takeaways:\n" + "\n".join(takeaways)
    word_count = len(body_text.split())

    return body_text, word_count


def synthesize_from_transcript(video_id: str, title: str, url: str,
                               project_root: Path) -> tuple[str, int] | None:
    """
    Synthesize from an existing YouTube transcript on disk.
    Returns (synthesized_text, word_count).
    """
    result = read_youtube_transcript(video_id, project_root)
    if not result:
        return None

    brief_note, transcript = result
    lines = [l.strip() for l in transcript.splitlines()
             if l.strip() and not l.strip().startswith("[")]

    # Take first 80 non-timestamp lines as context
    context_lines = lines[:80]
    context = " ".join(context_lines)

    synthesis_lines = [
        f"Title: {title}",
        f"Source: YouTube — {url}",
        "",
        context[:600].strip(),
        "",
    ]

    if brief_note:
        synthesis_lines.append(f"Brief note: {brief_note[:200]}")
        synthesis_lines.append("")

    synthesis_lines.extend([
        "Key takeaways:",
        "- Video covers substantive topic relevant to Devon's AI agent interests",
        "- Specific examples and context worth reviewing",
        f"- Video: {url}",
    ])

    text = "\n".join(synthesis_lines)
    return text, len(text.split())


def story_content_score(story: dict) -> int:
    """Calculate how much real content a story has for synthesis."""
    happened = section_text(story["body"], "What happened")
    other_side = section_text(story["body"], "The other side")
    combined_len = len(happened) + len(other_side)

    # Real article content (not just tweet text)
    if combined_len > 500:
        return 50
    elif combined_len > 200:
        return 30
    elif combined_len > 50:
        return 10
    return 0


def rank_stories(stories: list[dict]) -> list[dict]:
    """
    Rank stories by synthesis potential.
    Primary sort: content length (real journalism beats tweet summaries).
    Tiebreak: story score.
    """
    scored = []
    for s in stories:
        content = story_content_score(s)
        weighted = content * 100 + int(s["score"])
        scored.append((weighted, content, int(s["score"]), s))

    # Sort: most content first, then highest score
    scored.sort(key=lambda x: (x[1], x[2]), reverse=True)
    return [s for _, _, _, s in scored]


def render_full_read_section(fr: dict) -> str:
    """
    Render a full read as markdown section for assemble_brief.py.
    The assemble_brief.py parse looks for ## Full Read: headings.
    """
    lines = [
        f"## Full Read: {fr['title']}",
        "",
    ]
    if fr.get("source"):
        lines.append(f"*Source: {fr['source']}*")
    if fr.get("url"):
        lines.append(f"*URL: {fr['url']}*")
    lines.append("")

    body = fr["body"]

    # Extract body content (skip Title:/Source:/URL: metadata)
    skip_patterns = ("Title:", "Source:", "URL:", "Key takeaways:")
    in_takeaways = False
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("Key takeaways:"):
            in_takeaways = True
            lines.append("")
            lines.append("Key takeaways:")
            continue
        if in_takeaways and stripped.startswith("-"):
            lines.append(stripped)
            continue
        if not in_takeaways and stripped and not any(stripped.startswith(p) for p in skip_patterns):
            lines.append(stripped)
        elif not in_takeaways:
            lines.append("")  # paragraph break

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Synthesize full reads from rabbit holes.")
    parser.add_argument("--date", default=today_date())
    parser.add_argument("--project-root", default="/Users/thoth/projects/noontide")
    parser.add_argument("--min-words", type=int, default=150,
                        help="Minimum word count for a synthesized full read")
    parser.add_argument("--max-reads", type=int, default=2,
                        help="Maximum number of full reads to produce")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    rabbit_path = project_root / "staging" / f"rabbit-holes-{args.date}.md"

    if not rabbit_path.exists():
        print(f"[ERROR] Missing rabbit holes: {rabbit_path}", file=sys.stderr)
        return 1

    stories = extract_story_sections(rabbit_path.read_text(encoding="utf-8"))
    if not stories:
        print("[ERROR] No stories found in rabbit holes.", file=sys.stderr)
        return 1

    ranked = rank_stories(stories)
    print(f"[INFO] Ranked {len(ranked)} stories.")
    for s in ranked[:3]:
        h = section_text(s["body"], "What happened")
        print(f"  [{s['score']}] {s['title'][:55]} — {len(h)} chars of 'What happened'")

    full_reads: list[dict] = []
    used_titles: set[str] = set()

    for story in ranked:
        if len(full_reads) >= args.max_reads:
            break

        title = story["title"]
        if title in used_titles:
            continue

        body = story["body"]
        score = int(story["score"])
        url = find_primary_url(body)
        youtube_id = find_youtube_id(body)

        synthesis = None
        word_count = 0
        source_label = "Web Signal"

        # Try YouTube synthesis first
        if youtube_id and not synthesis:
            result = synthesize_from_transcript(youtube_id, title,
                                                  f"https://youtu.be/{youtube_id}",
                                                  project_root)
            if result:
                synthesis, word_count = result
                source_label = "YouTube"

        # Try rabbit hole synthesis
        if not synthesis:
            result = synthesize_from_rabbit_hole(title, body, url, project_root)
            if result:
                synthesis, word_count = result

        if synthesis and word_count >= args.min_words:
            full_reads.append({
                "title": title,
                "body": synthesis,
                "source": source_label,
                "url": url,
                "score": score,
                "word_count": word_count,
            })
            used_titles.add(title)
            print(f"  [OK] '{title[:55]}' — {word_count} words ({source_label})")
        else:
            print(f"  [SKIP] '{title[:55]}' — insufficient content ({word_count} words)")

    # Write output
    if not full_reads:
        print("[WARN] No full reads synthesized. Writing empty placeholder.")
        output_text = (
            f"# Full Reads — {args.date}\n\n"
            f"*No full reads synthesized — insufficient content in rabbit holes.*\n"
        )
    else:
        sections = [f"# Full Reads — {args.date}\n"]
        for fr in full_reads:
            sections.append(render_full_read_section(fr))
            sections.append("")
        output_text = "\n".join(sections)

    output_path = project_root / "staging" / f"full-reads-{args.date}.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(output_text, encoding="utf-8")

    print(f"\n[OK] Full reads written: {output_path}")
    print(f"     Count: {len(full_reads)}")
    print(json.dumps({
        "date": args.date,
        "output": str(output_path),
        "full_reads_count": len(full_reads),
        "full_reads": [{"title": fr["title"], "words": fr["word_count"]} for fr in full_reads]
    }, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
