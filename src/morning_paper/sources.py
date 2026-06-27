from __future__ import annotations

import html
import re
import shutil
import subprocess
from pathlib import Path

import feedparser
import requests

from .config import MorningPaperConfig

LOCAL_DROP_EXTENSIONS = (".md", ".markdown", ".txt", ".url")


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


def _source_ledger_inventory(newsroom: Path) -> dict[str, object]:
    path = newsroom.expanduser().resolve() / "SOURCES.md"
    if not path.is_file():
        return {
            "path": str(path),
            "status": "not_found",
            "role": "editorial_source_ledger",
            "executable": False,
            "row_count": 0,
            "meaning": "SOURCES.md is a source judgment ledger/backlog, not an executable source registry.",
        }
    text = path.read_text(encoding="utf-8", errors="replace")
    table_rows = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if not cells or all(set(cell) <= {"-", ":"} for cell in cells):
            continue
        table_rows.append(cells)
    row_count = max(0, len(table_rows) - 1) if table_rows else 0
    return {
        "path": str(path),
        "status": "present",
        "role": "editorial_source_ledger",
        "executable": False,
        "row_count": row_count,
        "meaning": "SOURCES.md is not an executable source registry; it records source purpose, trust, cadence, health, and backlog while collectors and staging are executable intake.",
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
                "Unsupported local-drop files need a converter collector before they can reach the Assignment Board; start from collectors/CONVERTERS.md."
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

    This answers setup and onboarding questions without composing an edition
    or fetching article bodies.
    """
    sources: list[dict[str, object]] = []
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
    source_ledger = _source_ledger_inventory(newsroom) if newsroom is not None else None
    payload: dict[str, object] = {
        "sources": sources,
        "count": len(sources),
        "source_model": {
            "posture": "reader_stack_first",
            "entry_points": ["local_drop", "assignment_board", "rss_or_feed_url", "inbox"],
            "reader_owned_inputs": [
                "local_drop",
                "collectors",
                "assignment_board",
                "inbox",
                "exports",
                "work_systems",
                "social_and_video_feeds",
            ],
            "rule": "meet sources where they already live; do not force the reader into a new system",
        },
        "collector_contract": {
            "command": "morning-paper stage <url|file> --date YYYY-MM-DD",
            "meaning": "anything not built in should arrive as source material on the Assignment Board for a specific edition date",
            "converter_playbook": (
                "collectors/CONVERTERS.md in a scaffolded private newsroom, plus "
                "docs/source-conversion.md in the engine repo"
            ),
        },
        "next_actions": _source_next_actions(sources, newsroom_info),
    }
    if newsroom_info is not None:
        payload["newsroom"] = newsroom_info
        collectors = newsroom_info.get("collectors") if isinstance(newsroom_info.get("collectors"), list) else []
        payload["configured_collectors"] = {
            "count": len(collectors),
            "ids": [str(item.get("id")) for item in collectors if isinstance(item, dict) and item.get("id")],
            "meaning": "collector scripts are executable private newsroom intake",
        }
    if source_ledger is not None:
        payload["editorial_source_ledger"] = source_ledger
    return payload
