#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
DATE = "2026-06-24"


def run_cli(args: list[str], *, env: dict[str, str], cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "morning_paper.cli", *args],
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def require_ok(result: subprocess.CompletedProcess[str], label: str) -> None:
    if result.returncode != 0:
        raise RuntimeError(f"{label} failed ({result.returncode})\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")


def configure(config_path: Path, output_dir: Path) -> None:
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    data["name"] = "Acceptance Desk"
    data["profile"] = "Fresh-agent acceptance run proving the edition production contract."
    data["outputs"]["directory"] = str(output_dir)
    data["outputs"]["renderer"] = "portable"
    data["outputs"]["style"] = "broadsheet"
    data["outputs"]["palette"] = "color"
    data["sources"]["rss"] = []
    config_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def write_private_collector(newsroom: Path, scratch: Path) -> Path:
    collector = newsroom / "collectors" / "fresh-agent.sh"
    collector.write_text(
        f"""#!/usr/bin/env bash
set -euo pipefail
DATE="${{1:?date required}}"
CONFIG="${{2:?config required}}"
SCRATCH="${{3:?scratch required}}"
SOURCE="$SCRATCH/private-collector-pulse.md"
cat > "$SOURCE" <<'MD'
# Private collector pulse

The private collector found one source-backed story: the reader needs a
production proof that source material can travel from a private script, through
the Assignment Board, into a composed paper, and back into memory after
delivery.

## Evidence

- Collector lived inside the private newsroom.
- It staged markdown through the public CLI contract.
- No private credential or hosted integration was added to the engine.
MD
PYTHONPATH={SRC}${{PYTHONPATH:+:$PYTHONPATH}} {sys.executable} -m morning_paper.cli stage "$SOURCE" --title "Private collector pulse" --config "$CONFIG" --date "$DATE"
""",
        encoding="utf-8",
    )
    os.chmod(collector, 0o755)
    return collector


def compose_from_skeleton(skeleton: str, queue_title: str) -> str:
    composed = (
        skeleton
        .replace("Replace with the single judgment that matters today.", "Private collectors are useful only when their proof survives the whole edition loop.")
        .replace("Replace with assigned reads, or print \"not configured\".", queue_title)
        .replace("Replace with the one next action worth taking.", "Keep source logic private; keep proof public.")
        .replace('<div class="dept-kicker">The Read</div>', "## Featured Reads")
        .replace("Write a Headline With a Verb", "Private Collector Proof Reaches The Desk")
        .replace("State the judgment clearly; do not label a pile of links.", "A fresh agent can stage, assign, compose, render, deliver, and update memory.")
        .replace(
            "Replace this paragraph with the outside-in synthesis:\nwhat changed in the world, why it matters to this reader, and what to do next.",
            "The acceptance run proves the operating model: a private collector turns reader-owned context into staged markdown, the Assignment Board makes it inspectable, the agent composes the page, and the CLI renders and proves the artifacts.",
        )
        .replace("Sources checked | 0 | update after collectors", "Sources checked | 1 | private collector")
        .replace("Full reads assigned | 0 | update from Assignment Board", "Full reads assigned | 1 | Assignment Board")
        .replace("Open loops | 0 | update from memory", "Open loops | 0 | reads ledger updated")
        .replace(
            "## Featured Reads\n\n<div class=\"article-head\">",
            "## Featured Reads\n\nThe private collector proves the route from a reader-owned script to a printed page. The editor can inspect the staged material, see why it earned space, and verify after delivery that memory recorded the read.\n\n<div class=\"article-head\">",
        )
        .replace(
            "Assigned reads and full-text feeds go here. If there is nothing worth printing,\nsay \"not configured\" or \"reading pile is empty\" instead of padding.",
            f"""Private source material reached the page because the collector used the
same staging contract an agent can inspect and prune. The useful claim is not
that the collector ran; it is that every later artifact can prove what happened.

<div class="article-head"><div class="dept-title">Collector proves private source path</div></div>

The staged item, **{queue_title}**, says the foundation matters only when proof survives
collection, assignment, composition, render, delivery, and memory.

<div class="article-head"><div class="dept-title">Assignment Board stays current</div></div>

The board was refreshed after the private collector ran, so the editor saw the
live staged item instead of a stale prepared snapshot.""",
        )
    )
    return composed + """

## Source Signals

<div class="article-head"><div class="dept-title">Collector stayed private</div></div>

The source-specific script lived in the scaffolded newsroom and used the public
staging contract. That keeps source opinions, credentials, and scrape details
outside the engine while still giving the edition a traceable source record.

<div class="article-head"><div class="dept-title">Reads ledger closed the loop</div></div>

Delivery appended the printed read to memory before status ran. Tomorrow's
agent can prove the read already printed without relying on chat history.
"""


def role_handoff(role: str, phase: str, *, inputs: list[str], finding: str) -> str:
    input_lines = "\n".join(f"  - {item}" for item in inputs)
    return f"""---
role: {role}
phase: "{phase}"
status: ready
date: {DATE}
inputs:
{input_lines}
handoff:
  candidates: 1
  repeats_cut: 0
  needs_followup: false
---

## What I Checked
- The required edition artifacts for phase {phase}, including source proof and run state.

## Findings
- {finding}

## Handoff
- This desk leaves enough evidence for the next role to continue without chat memory.
"""


def main() -> int:
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{SRC}{os.pathsep}{env.get('PYTHONPATH', '')}"
    with tempfile.TemporaryDirectory(prefix="morning-paper-fresh-agent-") as tmp:
        base = Path(tmp)
        config_path = base / "config.yaml"
        output_dir = base / "outputs"
        newsroom = base / "newsroom"
        scratch = base / "collector-scratch"
        scratch.mkdir()

        require_ok(run_cli(["init", "--config", str(config_path)], env=env), "init")
        configure(config_path, output_dir)
        require_ok(run_cli(["newsroom", "init", str(newsroom), "--name", "Acceptance Desk"], env=env), "newsroom")
        collector = write_private_collector(newsroom, scratch)

        require_ok(run_cli(["edition", "prepare", str(newsroom), "--config", str(config_path), "--date", DATE], env=env), "prepare")
        collector_result = subprocess.run(
            [str(collector), DATE, str(config_path), str(scratch)],
            cwd=newsroom,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        require_ok(collector_result, "private collector")
        staged = json.loads(collector_result.stdout)

        board = run_cli(["edition", "assignment-board", str(newsroom), "--config", str(config_path), "--date", DATE], env=env)
        require_ok(board, "assignment board")
        board_payload = json.loads(board.stdout)
        if board_payload["summary"]["ready_to_edit"] != 1:
            raise RuntimeError(f"expected one ready item, got {json.dumps(board_payload['summary'], indent=2)}")

        edition_dir = newsroom / "editions" / DATE
        draft = edition_dir / "draft.md"
        draft.write_text(compose_from_skeleton(draft.read_text(encoding="utf-8"), staged["title"]), encoding="utf-8")
        desks = edition_dir / "desks"
        (desks / "04-editor.md").write_text(
            role_handoff("editor", "04", inputs=["draft.md", "assignment-board.json"], finding="The source earns a small proof-led edition."),
            encoding="utf-8",
        )
        (desks / "05-copy-desk.md").write_text(
            role_handoff("copy-desk", "05", inputs=["draft.md", "preferences/voice.md"], finding="The draft is short, direct, and source-backed."),
            encoding="utf-8",
        )
        (desks / "06-art-desk.md").write_text(
            role_handoff("art-desk", "06", inputs=["draft.md", "desk-sheet.md"], finding="The edition and Desk Sheet use printable furniture."),
            encoding="utf-8",
        )

        require_ok(run_cli(["edition", "estimate", str(newsroom), "--config", str(config_path), "--date", DATE], env=env), "estimate")
        render = run_cli(["render", str(draft), "--config", str(config_path), "--date", DATE, "--slug", "edition"], env=env)
        require_ok(render, "render")
        render_payload = json.loads(render.stdout)
        (edition_dir / "render-result.json").write_text(json.dumps(render_payload, indent=2), encoding="utf-8")
        require_ok(run_cli(["edition", "desk-sheet", str(newsroom), "--config", str(config_path), "--date", DATE], env=env), "desk sheet")

        review = run_cli(["review", str(render_payload["output_dir"]), "--json", "--config", str(config_path)], env=env)
        require_ok(review, "review")
        review_payload = json.loads(review.stdout)
        (edition_dir / "review.json").write_text(json.dumps(review_payload, indent=2), encoding="utf-8")
        if review_payload["status"] == "review":
            raise RuntimeError(f"review flagged acceptance draft: {json.dumps(review_payload, indent=2)}")
        require_ok(run_cli(["edition", "visual-qa", str(newsroom), "--config", str(config_path), "--date", DATE], env=env), "visual qa")

        ledger = newsroom / "memory" / "reads-ledger.md"
        ledger_entry = f"- {DATE} - Private collector pulse\n"
        ledger.write_text(ledger.read_text(encoding="utf-8") + ledger_entry, encoding="utf-8")
        (edition_dir / "delivery-result.json").write_text(
            json.dumps(
                {
                    "status": "delivered",
                    "date": DATE,
                    "pdf": render_payload["outputs"]["pdf"],
                    "delivered_to": ["acceptance-smoke"],
                    "printed_reads": ["Private collector pulse"],
                    "reads_ledger": str(ledger),
                    "reads_ledger_updated": True,
                    "reads_ledger_entries": [ledger_entry.strip()],
                    "updated_at": DATE + "T08:00:00Z",
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        final_editor = run_cli(["edition", "final-editor", str(newsroom), "--config", str(config_path), "--date", DATE], env=env)
        require_ok(final_editor, "final editor")
        final_editor_payload = json.loads(final_editor.stdout)
        if final_editor_payload["status"] == "review":
            raise RuntimeError(f"final editor blocked: {json.dumps(final_editor_payload, indent=2)}")

        (desks / "07-producer.md").write_text(
            role_handoff("producer", "07", inputs=["run-ticket.json", "final-editor.json", "delivery-result.json"], finding="Delivery and reads-ledger proof are present."),
            encoding="utf-8",
        )
        status = run_cli(["edition", "status", str(newsroom), "--config", str(config_path), "--date", DATE], env=env)
        require_ok(status, "status")
        status_payload = json.loads(status.stdout)
        if status_payload["status"] != "complete":
            raise RuntimeError(
                "status was not complete:\n"
                f"{json.dumps(status_payload, indent=2)}\n"
                "review payload:\n"
                f"{json.dumps(review_payload, indent=2)}\n"
                "final editor payload:\n"
                f"{json.dumps(final_editor_payload, indent=2)}"
            )

        sources_payload = json.loads((edition_dir / "source-inventory.json").read_text(encoding="utf-8"))
        report = {
            "ok": True,
            "newsroom": str(newsroom),
            "edition_dir": str(edition_dir),
            "collector": str(collector),
            "assignment_board": str(edition_dir / "assignment-board.json"),
            "draft": str(draft),
            "pdf": render_payload["outputs"]["pdf"],
            "desk_sheet_result": str(edition_dir / "desk-sheet-result.json"),
            "review_status": review_payload["status"],
            "final_editor_status": final_editor_payload["status"],
            "status": status_payload["status"],
            "reads_ledger": str(ledger),
            "configured_collectors": sources_payload.get("configured_collectors"),
            "editorial_source_ledger": sources_payload.get("editorial_source_ledger"),
        }
        print(json.dumps(report, indent=2))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
