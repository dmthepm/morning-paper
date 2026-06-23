#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import mailbox
import tempfile
from collections import Counter
from email.message import EmailMessage
from pathlib import Path


def _write_mbox(path: Path) -> None:
    mbox = mailbox.mbox(path)
    for index in range(3):
        msg = EmailMessage()
        msg["From"] = f"sender-{index}@example.com"
        msg["To"] = "reader@example.com"
        msg["Subject"] = f"Synthetic newsletter {index}"
        msg["Date"] = f"Mon, 2{index} Jun 2026 08:00:00 -0700"
        msg["Message-ID"] = f"<synthetic-{index}@example.com>"
        if index:
            msg["In-Reply-To"] = "<synthetic-0@example.com>"
            msg["References"] = "<synthetic-0@example.com>"
        if index == 1:
            msg["List-Unsubscribe"] = "<mailto:unsubscribe@example.com>"
        msg.set_content(f"Plain text body {index}.")
        msg.add_alternative(f"<html><body><p>HTML body {index}.</p></body></html>", subtype="html")
        if index == 2:
            msg.add_attachment(b"%PDF-1.4 synthetic", maintype="application", subtype="pdf", filename="brief.pdf")
        mbox.add(msg)
    mbox.flush()
    mbox.close()


def _write_mainbranch_repo(root: Path) -> None:
    for folder in ("core", "research", "decisions", "pushes/2026-06-22-source-intake", "bets", "documents", "log"):
        (root / folder).mkdir(parents=True, exist_ok=True)
    (root / "AGENTS.md").write_text("# Agent contract\n", encoding="utf-8")
    (root / "CLAUDE.md").write_text("# Claude notes\n", encoding="utf-8")
    (root / "core" / "offer.md").write_text("# Offer\n\nWho this serves.\n", encoding="utf-8")
    (root / "research" / "source-intake.md").write_text("# Research\n\nShape-aware source intake.\n", encoding="utf-8")
    (root / "decisions" / "2026-06-22-source.md").write_text("# Decision\n\nUse files first.\n", encoding="utf-8")
    (root / "pushes" / "2026-06-22-source-intake" / "push.md").write_text("# Push\n\nHarden intake.\n", encoding="utf-8")
    (root / "bets" / "source-ledger.md").write_text("# Bet\n\nSource ledger improves paper.\n", encoding="utf-8")


def _write_youtube_export(root: Path) -> None:
    root.mkdir(parents=True)
    watch = [
        {
            "header": "YouTube",
            "title": "Watched Local-first tools",
            "titleUrl": "https://www.youtube.com/watch?v=example1",
            "subtitles": [{"name": "Example Channel", "url": "https://www.youtube.com/channel/example"}],
            "time": "2026-06-20T14:00:00Z",
            "products": ["YouTube"],
            "activityControls": ["YouTube watch history"],
        },
        {
            "header": "YouTube",
            "title": "Watched Designing calmer feeds",
            "titleUrl": "https://www.youtube.com/watch?v=example2",
            "time": "2026-06-21T15:30:00Z",
        },
    ]
    (root / "watch-history.json").write_text(json.dumps(watch, indent=2), encoding="utf-8")
    transcripts = root / "transcripts"
    transcripts.mkdir()
    (transcripts / "example1.vtt").write_text(
        "WEBVTT\n\n00:00:00.000 --> 00:00:05.000\nA public-safe synthetic transcript cue.\n",
        encoding="utf-8",
    )


def _write_generic_exports(root: Path) -> None:
    root.mkdir(parents=True)
    with (root / "saved-links.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["saved_at", "title", "url", "tags"])
        writer.writeheader()
        writer.writerow({"saved_at": "2026-06-22", "title": "Example read", "url": "https://example.com/read", "tags": "tools"})
    (root / "social-export.json").write_text(
        json.dumps({"likes": [{"created_at": "2026-06-22", "url": "https://example.com/post", "topic": "source ownership"}]}, indent=2),
        encoding="utf-8",
    )


def _write_local_folder(root: Path) -> None:
    root.mkdir(parents=True)
    (root / "daily-note.md").write_text("---\ntags: [paper]\n---\n# Daily Note\n\nRemember this source.\n", encoding="utf-8")
    (root / "project-brief.md").write_text("# Project Brief\n\n[[Daily Note]] connects here.\n", encoding="utf-8")
    (root / "raw.pdf").write_bytes(b"%PDF-1.4 synthetic unsupported")


def _analyze_mbox(path: Path) -> dict[str, object]:
    header_keys: Counter[str] = Counter()
    content_types: Counter[str] = Counter()
    part_types: Counter[str] = Counter()
    attachment_exts: Counter[str] = Counter()
    count = 0
    for msg in mailbox.mbox(path, create=False):
        count += 1
        for key in msg.keys():
            header_keys[key.lower()] += 1
        content_types[msg.get_content_type()] += 1
        if msg.is_multipart():
            for part in msg.walk():
                if part is msg:
                    continue
                part_types[part.get_content_type()] += 1
                filename = part.get_filename()
                disposition = str(part.get("content-disposition", "")).lower()
                if filename or "attachment" in disposition:
                    attachment_exts[Path(filename or "attachment").suffix.lower() or "<none>"] += 1
    return {
        "kind": "mbox",
        "messages": count,
        "structure": {
            "top_header_keys": header_keys.most_common(12),
            "message_content_types": content_types.most_common(),
            "part_content_types": part_types.most_common(),
            "attachment_extensions": attachment_exts.most_common(),
        },
        "useful_lanes": ["newsletters", "threads", "attachments", "unsubscribe/source candidates"],
        "privacy": "high: email addresses, subjects, bodies, and attachments stay private",
        "conversion_needs": ["thread digest collector", "newsletter candidate ledger", "attachment skip/convert notes"],
        "reader_questions": ["Which senders or newsletter patterns should influence the paper?"],
    }


def _analyze_mainbranch(root: Path) -> dict[str, object]:
    folders = ["core", "research", "decisions", "pushes", "bets", "documents", "log"]
    counts = {folder: sum(1 for _ in (root / folder).rglob("*.md")) if (root / folder).is_dir() else 0 for folder in folders}
    return {
        "kind": "mainbranch_repo",
        "structure": {"markers": {name: (root / name).exists() for name in ["AGENTS.md", "CLAUDE.md", *folders]}, "markdown_counts": counts},
        "useful_lanes": ["decisions", "active pushes", "bets", "research", "offer/context"],
        "privacy": "medium-high: business strategy and client facts stay in private newsroom collectors",
        "conversion_needs": ["daily pulse digest", "changed-files since last edition", "open decisions/asks"],
        "reader_questions": ["Which repo lanes should get ink: bets, pushes, decisions, research, or logs?"],
    }


def _json_keys(value: object) -> object:
    if isinstance(value, dict):
        return {key: _json_keys(child) for key, child in value.items()}
    if isinstance(value, list):
        return [_json_keys(value[0])] if value else []
    return type(value).__name__


def _analyze_youtube(root: Path) -> dict[str, object]:
    watch = json.loads((root / "watch-history.json").read_text(encoding="utf-8"))
    transcript_count = len(list((root / "transcripts").glob("*.vtt")))
    return {
        "kind": "youtube_export",
        "structure": {"watch_history_items": len(watch), "watch_history_shape": _json_keys(watch), "transcript_files": transcript_count},
        "useful_lanes": ["recurring topics", "channels", "videos to summarize", "available transcripts"],
        "privacy": "high: viewing history can reveal sensitive interests",
        "conversion_needs": ["topic digest", "channel/source candidate list", "transcript-to-markdown staging"],
        "reader_questions": ["Which topics should influence the algorithm, and which should be ignored?"],
    }


def _analyze_generic(root: Path) -> dict[str, object]:
    with (root / "saved-links.csv").open(encoding="utf-8") as handle:
        csv_fields = next(csv.reader(handle))
    data = json.loads((root / "social-export.json").read_text(encoding="utf-8"))
    return {
        "kind": "generic_exports",
        "structure": {"csv_fields": csv_fields, "json_shape": _json_keys(data)},
        "useful_lanes": ["saved links", "liked/saved posts", "dated items"],
        "privacy": "medium-high: export rows may include personal behavior",
        "conversion_needs": ["row sampler", "dedupe by URL", "dated markdown staging"],
        "reader_questions": ["Which tags or topics are signal, and which are guilty-scroll residue?"],
    }


def _analyze_local(root: Path) -> dict[str, object]:
    markdown = list(root.glob("*.md"))
    unsupported = [path.name for path in root.iterdir() if path.suffix.lower() not in {".md", ".markdown", ".txt", ".url"}]
    return {
        "kind": "local_folder",
        "structure": {"markdown_files": len(markdown), "unsupported_files": unsupported, "has_wikilinks": any("[[" in path.read_text(encoding="utf-8") for path in markdown)},
        "useful_lanes": ["notes", "project briefs", "linked context"],
        "privacy": "depends on folder; assume private until reader approves",
        "conversion_needs": ["markdown staging", "unsupported file converter guidance"],
        "reader_questions": ["Should this folder be a standing source or a one-time import?"],
    }


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="morning-paper-source-shape-") as tmp:
        base = Path(tmp)
        mbox_path = base / "mail.mbox"
        mainbranch = base / "mainbranch-repo"
        youtube = base / "youtube"
        generic = base / "exports"
        local = base / "local-folder"
        _write_mbox(mbox_path)
        _write_mainbranch_repo(mainbranch)
        _write_youtube_export(youtube)
        _write_generic_exports(generic)
        _write_local_folder(local)

        sources = [
            _analyze_mbox(mbox_path),
            _analyze_mainbranch(mainbranch),
            _analyze_youtube(youtube),
            _analyze_generic(generic),
            _analyze_local(local),
        ]
        ledger = {
            "ok": True,
            "source_model": "inspect shape -> ledger -> reader decision -> private converter/collector",
            "sources": sources,
            "engine_integrations_added": [],
            "private_converter_guidance": [
                {"kind": item["kind"], "conversion_needs": item["conversion_needs"]}
                for item in sources
                if item["conversion_needs"]
            ],
            "reader_discussion": [
                question for item in sources for question in item["reader_questions"]
            ],
        }
        required_kinds = {"mbox", "mainbranch_repo", "youtube_export", "generic_exports", "local_folder"}
        observed = {str(item["kind"]) for item in sources}
        if observed != required_kinds:
            raise RuntimeError(f"source shape coverage mismatch: {observed}")
        if ledger["engine_integrations_added"]:
            raise RuntimeError("source-shape smoke must not add engine integrations")
        if len(ledger["private_converter_guidance"]) != len(sources):
            raise RuntimeError("every complex source should point to private converter guidance")
        print(json.dumps(ledger, indent=2))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
