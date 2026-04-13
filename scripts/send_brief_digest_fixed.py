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
    actions = normalize_plaintext(strip_markup(extract_markdown_section(brief_text, "VIII. ACTION REQUIRED")))
    pages = page_count(brief_pdf)
    heading_lines = "\n".join(f"- {h}" for h in headings[:8])
pdf_link = f"[PDF]({brief_pdf})"
    github_link = f"[GitHub brief](https://github.com/dmthepm/thoth-workspace/briefs/{date}-brief-review.md)"
    digest = (
        f"Morning Brief review ready — {date}\\n"
        f"Pages: {pages if pages is not None else 'unknown'}\\n"
        "Sections:\\n"
        f"{heading_lines}\\n\\n"
        f"{pdf_link} | {github_link}"
    )

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

    send_message(tg_send, digest, dry_run=args.dry_run)

    if content_drafts.exists():
        drafts_text = read_text(content_drafts)
        skool = normalize_plaintext(extract_draft_section(drafts_text, "A. Skool Post Draft"))
        tweets = normalize_plaintext(extract_draft_section(drafts_text, "B. Scheduled Tweets"))
        podcast = normalize_plaintext(extract_draft_section(drafts_text, "C. Midday Podcast Script"))
        if skool:
            send_message(tg_send, f"Skool draft — {date}\n\n{skool}", dry_run=args.dry_run)
        if tweets:
            send_message(tg_send, f"Tweet drafts — {date}\n\n{tweets}", dry_run=args.dry_run)
        if podcast:
            send_message(tg_send, f"Podcast script — {date}\n\n{podcast}", dry_run=args.dry_run)
    else:
        send_message(
            tg_send,
            f"Content drafts missing for {date}. Expected file: {content_drafts}",
            dry_run=args.dry_run,
        )

    action_message = (
        f"Action required — {date}\n\n"
        f"{actions if actions else 'No action section found.'}\n\n"
        f"PDF: {brief_pdf}"
    )
    send_message(tg_send, action_message, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
