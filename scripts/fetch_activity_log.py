#!/usr/bin/env python3
"""
Fetch Paperclip company activity for the past 24h and format as a markdown
activity log section for the Morning Brief.

Data source: Paperclip activity API
  GET /api/companies/:companyId/activity

Activity types surfaced:
  - issue.created       → "Opened NOO-N: title"
  - issue.updated (done) → "Completed NOO-N: title"
  - issue.updated (todo/in_progress) → "Working on NOO-N: title"
  - issue.comment_added → "Commented on NOO-N"
  - agent.updated       → "Updated agent: name"
  - heartbeat.invoked    → (counted, not listed individually)
  - label.created       → "Added label: name"
  - project.created     → "Created project: name"
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path


COMPANY_ID = "75270a82-da27-442c-95c5-484cd461072e"
PAPERCLIP_API = "http://127.0.0.1:3100/api"


def fetch_activity(since_iso: str) -> list[dict]:
    """Fetch all activity events since given ISO timestamp."""
    url = f"{PAPERCLIP_API}/companies/{COMPANY_ID}/activity?since={since_iso}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as exc:
        return [{"error": str(exc)}]


def parse_created_at(value: str) -> datetime | None:
    if not value:
        return None
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def first_line(text: str, *, limit: int = 120) -> str:
    if not text:
        return ""
    line = text.strip().splitlines()[0].strip()
    line = re.sub(r"^\s*#{1,6}\s*", "", line)
    line = re.sub(r"^\s*[-*+]\s*", "", line)
    line = line.replace("`", "")
    line = re.sub(r"\s+", " ", line)
    return line[:limit].rstrip()


def filter_recent_events(events: list[dict], since: datetime) -> list[dict]:
    filtered: list[dict] = []
    for event in events:
        created_at = parse_created_at(event.get("createdAt", ""))
        if created_at is None or created_at < since:
            continue
        filtered.append(event)
    return filtered


def format_activity_log(events: list[dict]) -> str:
    """Format activity events into Morning Brief activity log markdown."""

    skip_actions = {
        "issue.read_marked",
        "heartbeat.cancelled",
        "heartbeat.completed",
        "heartbeat.invoked",
        "routine.run_triggered",
        "issue.checkout_lock_adopted",
        "issue.checkout_lock_created",
        "issue.checkout_lock_released",
        "issue.checkout_lock_denied",
        "session.created",
        "company.created",
        "agent.created",
        "goal.created",
        "project.created",
        "label.created",
    }
    relevant = [e for e in events if e.get("action", "") not in skip_actions]

    if not relevant:
        return "**No meaningful Paperclip activity in the last 24 hours.**"

    created: list[str] = []
    completed: list[str] = []
    in_progress: list[str] = []
    comments: list[str] = []
    agent_updates: list[str] = []
    seen: set[str] = set()

    for event in relevant:
        action = event.get("action", "")
        details = event.get("details", {}) or {}

        if action == "issue.created":
            ident = details.get("identifier", "?")
            title = first_line(details.get("title", ""))
            if not title:
                continue
            key = f"create:{ident}:{title}"
            if key not in seen:
                created.append(f"Opened {ident}: {title}")
                seen.add(key)
        elif action == "issue.updated":
            ident = details.get("identifier", "?")
            title = first_line(details.get("title", ""))
            new_status = details.get("status", "")
            prev = details.get("_previous", {})
            prev_status = prev.get("status", "")
            if new_status == "done":
                key = f"done:{ident}:{title}"
                if key not in seen:
                    line = f"Completed {ident}"
                    if title:
                        line += f": {title}"
                    completed.append(line)
                    seen.add(key)
            elif new_status in ("todo", "in_progress") and prev_status in ("backlog", None, ""):
                key = f"start:{ident}:{title}"
                if key not in seen:
                    line = f"Started {ident}"
                    if title:
                        line += f": {title}"
                    in_progress.append(line)
                    seen.add(key)
        elif action == "issue.comment_added":
            ident = details.get("identifier", "?")
            snippet = first_line(details.get("bodySnippet", ""), limit=100)
            if not snippet or snippet.lower() in {"approve", "ok", "done"}:
                continue
            key = f"comment:{ident}:{snippet}"
            if key not in seen:
                comments.append(f"Commented on {ident}: {snippet}")
                seen.add(key)
        elif action == "agent.updated":
            keys = details.get("changedTopLevelKeys", []) or details.get("changedAdapterConfigKeys", []) or []
            agent_id = event.get("entityId", "")[:8]
            if keys:
                key = f"agent:{agent_id}:{','.join(keys[:3])}"
                if key not in seen:
                    agent_updates.append(f"Updated agent `{agent_id}` config: {', '.join(keys[:3])}")
                    seen.add(key)

    lines: list[str] = []
    total = len(relevant)

    # Summary line
    summary_parts = [f"{total} meaningful events"]
    if created:
        summary_parts.append(f"{len(created)} issues opened")
    if completed:
        summary_parts.append(f"{len(completed)} completed")
    if comments:
        summary_parts.append(f"{len(comments)} notable comments")
    lines.append(f"**{' · '.join(summary_parts)}**")
    lines.append("")

    if completed:
        lines.append("**Completed:**")
        for line in completed[-4:]:
            lines.append(f"- {line}")
        lines.append("")

    if in_progress:
        lines.append("**Started:**")
        for line in in_progress[-4:]:
            lines.append(f"- {line}")
        lines.append("")

    if created:
        lines.append("**Opened:**")
        for line in created[-4:]:
            lines.append(f"- {line}")
        lines.append("")

    if agent_updates:
        lines.append("**Agent updates:**")
        for line in agent_updates[-2:]:
            lines.append(f"- {line}")
        lines.append("")

    if comments:
        lines.append("**Notable comments:**")
        for line in comments[-3:]:
            lines.append(f"- {line}")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch Paperclip activity for Morning Brief")
    parser.add_argument("--company-id", default=COMPANY_ID)
    parser.add_argument("--hours", type=int, default=24, help="Hours of history to fetch")
    parser.add_argument("--output", help="Write to file instead of stdout")
    args = parser.parse_args()

    since = datetime.now(timezone.utc) - timedelta(hours=args.hours)
    events = fetch_activity(since.isoformat())

    if events and isinstance(events[0], dict) and "error" in events[0]:
        output = f"<!-- Activity log unavailable: {events[0]['error']} -->"
    else:
        output = format_activity_log(filter_recent_events(events, since))

    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"Wrote activity log ({len(events)} events) to {args.output}", file=sys.stderr)
    else:
        print(output)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
