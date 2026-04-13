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


def format_activity_log(events: list[dict]) -> str:
    """Format activity events into Morning Brief activity log markdown."""

    # Filter out read_marked and heartbeat.cancelled — noise
    skip_actions = {"issue.read_marked", "heartbeat.cancelled", "heartbeat.completed"}
    relevant = [e for e in events if e.get("action", "") not in skip_actions]

    if not relevant:
        return ""

    # Group events
    created: list[tuple] = []
    completed: list[tuple] = []
    in_progress: list[tuple] = []
    comments: list[tuple] = []
    agent_updates: list[tuple] = []
    other: list[tuple] = []
    heartbeat_count = 0

    for event in relevant:
        action = event.get("action", "")
        details = event.get("details", {}) or {}
        ts = event.get("createdAt", "")[:10]  # YYYY-MM-DD

        if action == "heartbeat.invoked":
            heartbeat_count += 1
        elif action == "issue.created":
            ident = details.get("identifier", "?")
            title = details.get("title", "")[:60]
            created.append((ts, f"Opened [{ident}](paperclip://issue/{ident}): {title}"))
        elif action == "issue.updated":
            ident = details.get("identifier", "?")
            title = details.get("title", "")[:60]
            new_status = details.get("status", "")
            prev = details.get("_previous", {})
            prev_status = prev.get("status", "")
            if new_status == "done":
                completed.append((ts, f"Completed [{ident}](paperclip://issue/{ident}): {title}"))
            elif new_status in ("todo", "in_progress") and prev_status in ("backlog", None, ""):
                in_progress.append((ts, f"Started [{ident}](paperclip://issue/{ident}): {title}"))
        elif action == "issue.comment_added":
            ident = details.get("identifier", "?")
            snippet = (details.get("bodySnippet", "") or "")[:80]
            comments.append((ts, f"Commented on [{ident}](paperclip://issue/{ident}): {snippet}"))
        elif action == "agent.updated":
            keys = details.get("changedTopLevelKeys", []) or details.get("changedAdapterConfigKeys", []) or []
            agent_id = event.get("entityId", "")[:8]
            if keys:
                agent_updates.append((ts, f"Updated agent `{agent_id[:8]}` config: {', '.join(keys[:3])}"))
        elif action == "label.created":
            name = details.get("name", "?")
            other.append((ts, f"Created label: {name}"))
        elif action == "project.created":
            name = details.get("name", "?")
            other.append((ts, f"Created project: {name}"))
        elif action == "goal.created":
            title = (details.get("title", "") or "")[:80]
            if title:
                other.append((ts, f"Created goal: {title}"))
        elif action not in skip_actions:
            other.append((ts, f"{action}: {str(details)[:80]}"))

    lines: list[str] = []
    total = len(relevant)

    # Summary line
    summary_parts = [f"{total} events"]
    if heartbeat_count > 0:
        summary_parts.append(f"{heartbeat_count} heartbeats")
    if created:
        summary_parts.append(f"{len(created)} issues opened")
    if completed:
        summary_parts.append(f"{len(completed)} completed")
    lines.append(f"**{' · '.join(summary_parts)}**")
    lines.append("")

    # Completed issues (most important)
    if completed:
        lines.append("**Completed:**")
        for _, line in completed[-5:]:  # last 5
            lines.append(f"- {line}")
        lines.append("")

    # Started issues
    if in_progress:
        lines.append("**Started:**")
        for _, line in in_progress[-5:]:
            lines.append(f"- {line}")
        lines.append("")

    # Opened issues
    if created:
        lines.append("**Opened:**")
        for _, line in created[-5:]:
            lines.append(f"- {line}")
        lines.append("")

    # Agent updates
    if agent_updates:
        lines.append("**Agent updates:**")
        for _, line in agent_updates[-3:]:
            lines.append(f"- {line}")
        lines.append("")

    # Comments
    if comments:
        lines.append("**Comments:**")
        for _, line in comments[-5:]:
            lines.append(f"- {line}")
        lines.append("")

    # Other
    if other:
        lines.append("**Other:**")
        for _, line in other[-5:]:
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
        output = format_activity_log(events)

    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"Wrote activity log ({len(events)} events) to {args.output}", file=sys.stderr)
    else:
        print(output)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
