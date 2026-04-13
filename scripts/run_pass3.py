#!/usr/bin/env python3
"""Repo-owned Pass 3 for the Morning Brief pipeline."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from brief_runtime import today_date, write_markdown


def extract_story_sections(text: str) -> list[dict[str, str]]:
    matches = list(re.finditer(r"^##\s+(.+?)\s+— score:\s+(\d+)\s*$", text, flags=re.MULTILINE))
    output: list[dict[str, str]] = []
    for i, match in enumerate(matches):
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        output.append({"title": match.group(1).strip(), "score": match.group(2), "body": body})
    return output


def section_text(body: str, heading: str) -> str:
    pattern = rf"^###\s+{re.escape(heading)}\s*$"
    match = re.search(pattern, body, flags=re.MULTILINE)
    if not match:
        return ""
    start = match.end()
    next_match = re.search(r"^###\s+.+$", body[start:], flags=re.MULTILINE)
    end = start + next_match.start() if next_match else len(body)
    return body[start:end].strip()


def first_story(stories: list[dict[str, str]]) -> dict[str, str]:
    if not stories:
        raise ValueError("No rabbit hole stories found.")
    def rank(story: dict[str, str]) -> tuple[int, int, int]:
        happened = section_text(story["body"], "What happened")
        title_penalty = 30 if "?" in story["title"] else 0
        weighted = int(story["score"]) * 10 + min(len(happened), 250) - title_penalty
        return (weighted, int(story["score"]), len(happened))

    return sorted(stories, key=rank, reverse=True)[0]


def build_skool(story: dict[str, str]) -> str:
    happened = section_text(story["body"], "What happened")
    why = section_text(story["body"], "Why Devon cares")
    return "\n".join(
        [
            story["title"],
            "",
            f"Holy crapola. Last night I went down a rabbit hole on {story['title'].lower()} and it turned into one of those stories that says more about the stack than the headline does.",
            "",
            happened,
            "",
            f"The part I keep thinking about for us: {why}",
            "",
            "Question for the group: if this landed in your stack tomorrow, what would you change first?",
            "",
            "#community #aitools #agents",
        ]
    )


def build_tweets(stories: list[dict[str, str]]) -> str:
    top = stories[:3]
    lines = []
    for idx, story in enumerate(top, start=1):
        why = section_text(story["body"], "Why Devon cares")
        lines.extend(
            [
                f"Tweet {idx}:",
                f"{story['title']}",
                why[:260],
                "",
            ]
        )
    return "\n".join(lines).strip()


def build_podcast(stories: list[dict[str, str]]) -> str:
    key_lines = []
    for story in stories[:3]:
        why = section_text(story["body"], "Why Devon cares")
        key_lines.append(f"- {story['title']}: {why}")
    return "\n".join(
        [
            "[INTRO]",
            "Today’s brief kept circling the same theme: the stack is getting more capable, but also more fragile at the edges where tools, trust, and ownership meet.",
            "",
            "[KEY TAKEAWAYS]",
            *key_lines,
            "",
            "[OUTRO]",
            "The thing worth watching tomorrow is whether these are isolated signals or the start of a larger shift in how builders want to operate.",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Morning Brief Pass 3.")
    parser.add_argument("--date", default=today_date())
    parser.add_argument("--project-root", default="/Users/thoth/projects/noontide")
    parser.add_argument("--skip-full-reads", action="store_true",
                        help="Skip full-read synthesis (for debugging)")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    rabbit_path = project_root / "staging" / f"rabbit-holes-{args.date}.md"
    if not rabbit_path.exists():
        raise FileNotFoundError(f"Missing rabbit holes file: {rabbit_path}")

    # Step 1: Generate full reads via the synthesis script
    full_reads_text = ""
    if not args.skip_full_reads:
        full_reads_script = Path(__file__).parent / "run_full_reads.py"
        if full_reads_script.exists():
            try:
                result = subprocess.run(
                    [sys.executable, str(full_reads_script),
                     "--date", args.date,
                     "--project-root", str(project_root)],
                    capture_output=True, text=True, timeout=120
                )
                full_reads_path = project_root / "staging" / f"full-reads-{args.date}.md"
                if full_reads_path.exists():
                    full_reads_text = "\n" + full_reads_path.read_text(encoding="utf-8")
                if result.stdout.strip():
                    print(f"[Pass 3] Full reads synthesis:\n{result.stdout.strip()}", file=sys.stderr)
                if result.returncode != 0 and result.stderr:
                    print(f"[Pass 3] Full reads synthesis warning:\n{result.stderr.strip()}", file=sys.stderr)
            except Exception as e:
                print(f"[Pass 3] Could not run full reads synthesis: {e}", file=sys.stderr)

    # Step 2: Build social content drafts
    stories = extract_story_sections(rabbit_path.read_text(encoding="utf-8"))
    lead = first_story(stories)
    drafts_text = "\n".join(
        [
            f"# Content Drafts — {args.date}",
            "",
            "## A. Skool Post Draft",
            build_skool(lead),
            "",
            "## B. Scheduled Tweets",
            build_tweets(stories),
            "",
            "## C. Midday Podcast Script",
            build_podcast(stories),
            "",
        ]
    )

    # Combine: content drafts + full reads
    output_text = drafts_text + full_reads_text

    output = project_root / "staging" / "briefs" / f"{args.date}-content-drafts.md"
    write_markdown(output, output_text)
    print(json.dumps({
        "date": args.date,
        "output": str(output),
        "drafts_count": len(stories),
        "full_reads_included": bool(full_reads_text)
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
