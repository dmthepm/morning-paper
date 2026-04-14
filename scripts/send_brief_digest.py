#!/usr/bin/env python3
"""
Send the Morning Brief review digest through the Hermes Telegram wrapper.
"""

from __future__ import annotations

import argparse
import html
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

try:
    import fitz  # type: ignore
except ImportError:
    fitz = None


def la_date() -> str:
    return datetime.now(ZoneInfo("America/Los_Angeles")).strftime("%Y-%m-%d")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def strip_markup(text: str) -> str:
    text = re.sub(r"```+", "", text)
    text = re.sub(r"<br\s*/?>", "\n", text)
    text = re.sub(r"</p>", "\n\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize_plaintext(text: str) -> str:
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    compact = []
    blank = False
    for line in lines:
        if not line:
            if not blank:
                compact.append("")
            blank = True
            continue
        compact.append(line)
        blank = False
    return "\n".join(compact).strip()


def extract_markdown_section(text: str, heading: str) -> str:
    pattern = rf"^##\s+{re.escape(heading)}\s*$"
    match = re.search(pattern, text, flags=re.MULTILINE)
    if not match:
        return ""
    start = match.end()
    next_match = re.search(r"^##\s+.+$", text[start:], flags=re.MULTILINE)
    end = start + next_match.start() if next_match else len(text)
    return text[start:end].strip()


def extract_action_section(text: str) -> str:
    patterns = [
        r"^##\s+(?:VIII|IX|X)\.\s+ACTION REQUIRED\s*$",
        r"^##\s+(?:VIII|IX|X)\.\s+ACTION REQUESTED\s*$",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.MULTILINE)
        if not match:
            continue
        start = match.end()
        next_match = re.search(r"^##\s+.+$", text[start:], flags=re.MULTILINE)
        end = start + next_match.start() if next_match else len(text)
        return text[start:end].strip()
    return ""


def extract_action_bullets(section_text: str) -> list[str]:
    bullets: list[str] = []
    if not section_text:
        return bullets

    html_bodies = re.findall(r'<div class="action-body">(.*?)</div>', section_text, flags=re.DOTALL)
    for body in html_bodies:
        plain = normalize_plaintext(strip_markup(body))
        if plain:
            bullets.append(plain)
    if bullets:
        return bullets

    for line in normalize_plaintext(strip_markup(section_text)).splitlines():
        cleaned = line.strip()
        if not cleaned:
            continue
        if cleaned in {"Action Required"} or re.fullmatch(r"Action \d+", cleaned):
            continue
        bullets.append(cleaned)
    return bullets


def extract_draft_section(text: str, heading: str) -> str:
    pattern = rf"^##\s+{re.escape(heading)}\s*$"
    match = re.search(pattern, text, flags=re.MULTILINE)
    if not match:
        return ""
    start = match.end()
    next_match = re.search(r"^##\s+.+$", text[start:], flags=re.MULTILINE)
    end = start + next_match.start() if next_match else len(text)
    return strip_markup(text[start:end]).strip()


def page_count(pdf_path: Path) -> int | None:
    if fitz is None or not pdf_path.exists():
        return None
    doc = fitz.open(pdf_path)
    count = doc.page_count
    doc.close()
    return count


def brief_headings(brief_text: str) -> list[str]:
    return [normalize_plaintext(html.unescape(line.strip().removeprefix("## ").strip())) for line in brief_text.splitlines() if line.startswith("## ")]


def extract_signal_titles_and_urls(brief_text: str, limit: int = 5) -> list[tuple[str, str]]:
    """
    Extract tweet titles and URLs from the SIGNALS section.
    Returns list of (title, url) pairs.
    """
    # Find the SIGNALS section (from ## I. SIGNALS to next ##)
    import re
    signals_match = re.search(r'^## I\. SIGNALS\s*$', brief_text, re.MULTILINE)
    if not signals_match:
        return []
    start = signals_match.end()
    next_match = re.search(r'^##\s+.+$', brief_text[start:], re.MULTILINE)
    end = start + (next_match.start() if next_match else len(brief_text))
    signals_html = brief_text[start:end]
    
    # Find each tweet block
    tweet_pattern = r'<div class="tweet">(.*?)</div>\s*<div class="tweet-stats">'
    tweets = re.findall(tweet_pattern, signals_html, re.DOTALL)
    results = []
    for tweet in tweets[:limit]:
        # Extract tweet-author text (first line of tweet-header)
        author_match = re.search(r'<div class="tweet-author">(.*?)</div>', tweet, re.DOTALL)
        title = author_match.group(1).strip() if author_match else ''
        # Extract URL from the last tweet-stats that starts with http
        url_match = re.search(r'<div class="tweet-stats">(https?://[^<]+)</div>', tweet)
        url = url_match.group(1).strip() if url_match else ''
        if title and url:
            results.append((title, url))
    return results


def extract_full_read_titles_and_urls(brief_text: str, limit: int = 2) -> list[tuple[str, str]]:
    """
    Extract full-read titles and URLs from the FULL READ sections.
    """
    import re
    # Find all full-read divs
    full_read_pattern = r'<div class="full-read">(.*?)</div>'
    full_reads = re.findall(full_read_pattern, brief_text, re.DOTALL)
    results = []
    for full in full_reads[:limit]:
        title_match = re.search(r'<div class="full-read-title">(.*?)</div>', full, re.DOTALL)
        title = title_match.group(1).strip() if title_match else ''
        # Try to find a link inside the body
        url_match = re.search(r'href="(https?://[^"]+)"', full)
        if not url_match:
            # Maybe the URL is plain text in the body
            url_match = re.search(r'(https?://[^\s<]+)', full)
        url = url_match.group(1).strip() if url_match else ''
        if title and url:
            results.append((title, url))
    return results


def send_message(tg_send: Path, message: str, *, dry_run: bool = False) -> None:
    if dry_run:
        print("---")
        print(message)
        return
    subprocess.run([str(tg_send), message], check=True, text=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Send the Morning Brief digest via tg-send.sh")
    parser.add_argument("--date", default=la_date())
    parser.add_argument("--brief-md")
    parser.add_argument("--brief-pdf")
    parser.add_argument("--content-drafts")
    parser.add_argument("--tg-send", default="/Users/thoth/scripts/tg-send.sh")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    date = args.date
    brief_md = Path(args.brief_md or f"/Users/thoth/.hermes/briefs/{date}-brief-review.md")
    brief_pdf = Path(args.brief_pdf or f"/Users/thoth/.hermes/briefs/{date}-brief-review.pdf")
    content_drafts = Path(args.content_drafts or f"/Users/thoth/projects/noontide/staging/briefs/{date}-content-drafts.md")
    tg_send = Path(args.tg_send)

    if not brief_md.exists():
        send_message(
            tg_send,
            f"Morning Brief review build missing for {date}. Expected markdown at {brief_md}.",
            dry_run=args.dry_run,
        )
        return 0

    brief_text = read_text(brief_md)
    headings = brief_headings(brief_text)
    action_bullets = extract_action_bullets(extract_action_section(brief_text))
    pages = page_count(brief_pdf)
    heading_lines = "\n".join(f"- {h}" for h in headings[:8])
    pdf_link = f"[PDF]({brief_pdf})"
    github_link = f"[GitHub brief](https://github.com/dmthepm/thoth-workspace/briefs/{date}-brief-review.md)"

    # Build single digest with everything
    digest_parts = []
    digest_parts.append(f"Morning Brief review ready — {date}")
    digest_parts.append(f"Pages: {pages if pages is not None else 'unknown'}")
    digest_parts.append("Sections:")
    digest_parts.append(heading_lines)
    digest_parts.append("")
    digest_parts.append(f"{pdf_link} | {github_link}")

    # Include content drafts summary if available
    if content_drafts.exists():
        drafts_text = read_text(content_drafts)
        skool = normalize_plaintext(extract_draft_section(drafts_text, "A. Skool Post Draft"))
        tweets = normalize_plaintext(extract_draft_section(drafts_text, "B. Scheduled Tweets"))
        podcast = normalize_plaintext(extract_draft_section(drafts_text, "C. Midday Podcast Script"))
        if skool or tweets or podcast:
            digest_parts.append("")
            digest_parts.append("Content Drafts ready:")
            if skool:
                digest_parts.append(f"• Skool post: {skool[:100]}...")
            if tweets:
                digest_parts.append(f"• Tweet drafts: {tweets[:100]}...")
            if podcast:
                digest_parts.append(f"• Podcast script: {podcast[:100]}...")
    else:
        digest_parts.append("")
        digest_parts.append(f"Content drafts missing for {date}.")

    # Include actions
    if action_bullets:
        digest_parts.append("")
        digest_parts.append("Action Required:")
        for line in action_bullets[:4]:
            digest_parts.append(f"• {line}")
    else:
        digest_parts.append("")
        digest_parts.append("No action section found.")

    digest = "\n".join(digest_parts)

    # Validate digest format
    try:
        from validate_brief import validate_telegram_digest
        issues = validate_telegram_digest(digest)
        for issue in issues:
            if issue['severity'] == 'ERROR':
                print(f"Telegram digest validation error: {issue['message']}", file=sys.stderr)
                sys.exit(1)
            else:
                print(f"Telegram digest validation warning: {issue['message']}", file=sys.stderr)
    except ImportError as e:
        print(f"Could not import validate_brief: {e}", file=sys.stderr)
        # Continue anyway

    # Send single digest message
    send_message(tg_send, digest, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
