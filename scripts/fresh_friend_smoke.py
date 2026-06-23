#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
DATE = "2026-06-22"


PERSONAS = [
    {
        "id": "creator-news-reader",
        "paper": "Creator Desk",
        "profile": "Creator who wants world news, creator economy signal, and one full read.",
        "source": "# Creator note\n\nA launch essay and a news trend belong in today's paper.\n",
        "next_sources": "newsletter folder, saved essays, YouTube watch history",
    },
    {
        "id": "business-owner-main-branch",
        "paper": "Operator Desk",
        "profile": "Business owner using Main Branch primitives: bets, pushes, risks, and asks.",
        "source": "# Main Branch pulse\n\nBet: improve onboarding. Push: finish the source layer. Risk: unclear owner feedback loop.\n",
        "next_sources": "Main Branch bets, GitHub activity, Linear tickets, Slack decisions",
    },
    {
        "id": "technical-agent-user",
        "paper": "Agent Lab",
        "profile": "Technical user validating agent tools, render contracts, and queue durability.",
        "source": "# Agent tool note\n\nThe queue, source inventory, and edition artifacts must survive compaction.\n",
        "next_sources": "agent logs, repo diffs, local markdown reports",
    },
    {
        "id": "nontechnical-rss-newsletter",
        "paper": "Newsletter Morning",
        "profile": "Nontechnical reader with RSS/newsletters and no interest in YAML internals.",
        "source": "# Newsletter clipping\n\nA full-text newsletter item should become a readable page, not a feed blurb.\n",
        "next_sources": "email newsletters, RSS feeds, saved articles",
    },
    {
        "id": "local-folder-source-dump",
        "paper": "Local Sources",
        "profile": "Reader with local markdown, text dumps, synced folders, and agent-produced files.",
        "source": "# Local folder dump\n\nThis came from a folder the user already owns. Nothing needed to move.\n",
        "next_sources": "Obsidian vault, synced folder, exported notes",
        "local_drop": {
            "folder-note.txt": "A source note from a folder the reader already owns.\n",
            "watch-history.csv": "watched_at,title\n2026-06-21,Example video\n",
            "saved-report.pdf": b"%PDF-1.4\n% synthetic unsupported fixture\n",
        },
        "expected_unsupported_drop": ["saved-report.pdf", "watch-history.csv"],
    },
]


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


def write_config(config_path: Path, output_dir: Path, profile: str) -> None:
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    data["profile"] = profile
    data["outputs"]["directory"] = str(output_dir)
    data["sources"]["hacker_news"]["enabled"] = False
    data["sources"]["rss"] = []
    config_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def compose_draft(persona: dict[str, str], staged_title: str) -> str:
    return f"""# {persona['paper']} Prints Its First Edition - {DATE}

## The Read

The first useful judgment is simple: this reader already has enough local
context to print a real paper. Morning Paper should start with the source they
own, prove the route from source to page, and ask for the next source only
after the first edition lands.

## Why It Matters Today

Reader profile: {persona['profile']}

The queued source, **{staged_title}**, gives the editor a concrete starting
point from the reader's own stack. This edition should be modest, but not
empty: one source-backed lead, one source desk note, one page-budget signal,
and one clear feedback route.

```mp-stats
Reader-owned sources | 1 | staged today
Edition artifacts | 10 | compaction-safe
Feedback route | 1 | feedback-plan.md
```

## Source Inventory

The paper has a prepared `source-inventory.json` and a queued local source:
{staged_title}. Tomorrow's best candidates: {persona['next_sources']}.

## Page Budget

This first edition should stay short. The goal is not volume yet; the goal is
trust. The reader should be able to mark what felt useful, what felt thin, and
which source should become part of the routine.

## Feedback Loop

After delivery, ask the reader what to keep, cut, expand, add as a source,
change visually, change about delivery, or print tomorrow. Route durable
changes through `feedback-plan.md` and record accepted/rejected taste in
`TASTELOG.md`.
"""


def seed_local_drop(persona: dict[str, object], newsroom: Path) -> None:
    local_drop = persona.get("local_drop")
    if not isinstance(local_drop, dict):
        return
    inbox = newsroom / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    for name, content in local_drop.items():
        path = inbox / str(name)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(str(content), encoding="utf-8")


def assert_first_edition_quality(
    *,
    persona: dict[str, object],
    edition_dir: Path,
    render_payload: dict[str, object],
    review_payload: dict[str, object],
    final_editor_payload: dict[str, object],
) -> list[str]:
    errors: list[str] = []
    draft = (edition_dir / "draft.md").read_text(encoding="utf-8")
    queue = json.loads((edition_dir / "queue-snapshot.json").read_text(encoding="utf-8"))
    source_inventory = json.loads((edition_dir / "source-inventory.json").read_text(encoding="utf-8"))
    feedback_plan = (edition_dir / "feedback-plan.md").read_text(encoding="utf-8")
    operator_answers = (edition_dir / "operator-answers.md").read_text(encoding="utf-8")

    required_draft_phrases = [
        "## The Read",
        "first useful judgment",
        "Reader profile:",
        "```mp-stats",
        "## Source Inventory",
        "Tomorrow's best candidates:",
        "## Page Budget",
        "## Feedback Loop",
        "feedback-plan.md",
        "TASTELOG.md",
    ]
    for phrase in required_draft_phrases:
        if phrase not in draft:
            errors.append(f"{persona['id']}: draft missing `{phrase}`")
    forbidden = ["Not composed yet", "generic feed"]
    for phrase in forbidden:
        if phrase in draft:
            errors.append(f"{persona['id']}: draft contains placeholder/weak phrase `{phrase}`")
    if queue.get("count", 0) < 1:
        errors.append(f"{persona['id']}: queue snapshot has no staged source")
    if source_inventory.get("source_model", {}).get("posture") != "reader_stack_first":
        errors.append(f"{persona['id']}: source inventory lost reader-stack-first posture")
    expected_unsupported = persona.get("expected_unsupported_drop")
    if isinstance(expected_unsupported, list):
        newsroom_inventory = source_inventory.get("newsroom")
        local_drop = newsroom_inventory.get("local_drop") if isinstance(newsroom_inventory, dict) else {}
        if not isinstance(local_drop, dict):
            errors.append(f"{persona['id']}: source inventory missing local drop details")
        else:
            if int(local_drop.get("candidate_count") or 0) < 1:
                errors.append(f"{persona['id']}: local drop did not report supported candidates")
            if int(local_drop.get("unsupported_count") or 0) < len(expected_unsupported):
                errors.append(f"{persona['id']}: local drop did not report unsupported files")
            unsupported_sample = set(str(item) for item in local_drop.get("unsupported_sample_files", []))
            for filename in expected_unsupported:
                if str(filename) not in unsupported_sample:
                    errors.append(f"{persona['id']}: unsupported local drop sample missing `{filename}`")
        next_actions = source_inventory.get("next_actions")
        action_text = "\n".join(str(item) for item in next_actions) if isinstance(next_actions, list) else ""
        if "Unsupported local-drop files need a converter collector" not in action_text:
            errors.append(f"{persona['id']}: source inventory did not request a converter collector")
    for phrase in ("Applied Feedback", "EDITORIAL.md", "VISUALS.md", "SOURCES.md", "DELIVERY.md", "TASTELOG.md"):
        if phrase not in feedback_plan:
            errors.append(f"{persona['id']}: feedback plan missing `{phrase}`")
    for phrase in ("Keep", "Cut", "More", "Visuals", "Sources To Add", "Taste To Save", "Print Tomorrow"):
        if phrase not in operator_answers:
            errors.append(f"{persona['id']}: operator answers missing `{phrase}`")
    if review_payload.get("status") == "review":
        errors.append(f"{persona['id']}: review requested revision")
    if final_editor_payload.get("status") == "review":
        errors.append(f"{persona['id']}: final editor requested revision")
    if final_editor_payload.get("ship_rule") not in {"deliver", "deliver with a short final-editor note"}:
        errors.append(f"{persona['id']}: final editor did not produce a deliverable ship rule")
    if not Path(render_payload["outputs"]["pdf"]).is_file():
        errors.append(f"{persona['id']}: rendered PDF missing")
    if int(render_payload.get("pages") or 0) < 1:
        errors.append(f"{persona['id']}: rendered PDF has no pages")
    return errors


def simulate(persona: dict[str, object], base: Path, env: dict[str, str]) -> dict[str, object]:
    root = base / persona["id"]
    config_path = root / "config.yaml"
    output_dir = root / "outputs"
    newsroom = root / "newsroom"
    root.mkdir(parents=True)

    require_ok(run_cli(["init", "--config", str(config_path)], env=env), f"{persona['id']} init")
    write_config(config_path, output_dir, str(persona["profile"]))
    require_ok(
        run_cli(["newsroom", "init", str(newsroom), "--name", str(persona["paper"])], env=env),
        f"{persona['id']} newsroom",
    )
    seed_local_drop(persona, newsroom)
    require_ok(
        run_cli(["edition", "prepare", str(newsroom), "--config", str(config_path), "--date", DATE], env=env),
        f"{persona['id']} edition prepare",
    )

    source_file = root / "source.md"
    source_file.write_text(str(persona["source"]), encoding="utf-8")
    stage = run_cli(["stage", str(source_file), "--config", str(config_path), "--date", DATE], env=env)
    require_ok(stage, f"{persona['id']} stage")
    staged = json.loads(stage.stdout)

    queue = run_cli(["queue", "list", "--config", str(config_path), "--date", DATE], env=env)
    require_ok(queue, f"{persona['id']} queue")
    edition_dir = newsroom / "editions" / DATE
    (edition_dir / "queue-snapshot.json").write_text(queue.stdout, encoding="utf-8")
    (edition_dir / "collector-report.md").write_text(
        f"# Collector Report - {DATE}\n\nok: staged {staged['slug']} from local source.\n",
        encoding="utf-8",
    )
    draft_path = edition_dir / "draft.md"
    draft_path.write_text(compose_draft(persona, staged["title"]), encoding="utf-8")

    estimate = run_cli(["edition", "estimate", str(newsroom), "--config", str(config_path), "--date", DATE], env=env)
    require_ok(estimate, f"{persona['id']} estimate")

    render = run_cli(
        ["render", str(draft_path), "--config", str(config_path), "--date", DATE, "--slug", "edition"],
        env=env,
    )
    require_ok(render, f"{persona['id']} render")
    render_payload = json.loads(render.stdout)
    (edition_dir / "render-result.json").write_text(json.dumps(render_payload, indent=2), encoding="utf-8")

    review = run_cli(["review", str(render_payload["output_dir"]), "--json", "--config", str(config_path)], env=env)
    require_ok(review, f"{persona['id']} review")
    review_payload = json.loads(review.stdout)
    (edition_dir / "review.json").write_text(json.dumps(review_payload, indent=2), encoding="utf-8")

    visual_qa = run_cli(["edition", "visual-qa", str(newsroom), "--config", str(config_path), "--date", DATE], env=env)
    require_ok(visual_qa, f"{persona['id']} visual-qa")

    final_editor = run_cli(
        ["edition", "final-editor", str(newsroom), "--config", str(config_path), "--date", DATE],
        env=env,
    )
    require_ok(final_editor, f"{persona['id']} final-editor")
    final_editor_payload = json.loads(final_editor.stdout)
    quality_errors = assert_first_edition_quality(
        persona=persona,
        edition_dir=edition_dir,
        render_payload=render_payload,
        review_payload=review_payload,
        final_editor_payload=final_editor_payload,
    )

    required = [
        "source-inventory.json",
        "collector-report.md",
        "queue-snapshot.json",
        "estimate-result.json",
        "draft.md",
        "render-result.json",
        "review.json",
        "visual-qa.json",
        "final-editor.json",
        "final-editor.md",
        "operator-answers.md",
        "feedback-plan.md",
    ]
    missing = [name for name in required if not (edition_dir / name).is_file()]
    pdf_path = Path(render_payload["outputs"]["pdf"])
    return {
        "persona": persona["id"],
        "ok": not missing and not quality_errors and pdf_path.is_file(),
        "newsroom": str(newsroom),
        "edition_dir": str(edition_dir),
        "pdf": str(pdf_path),
        "pages": render_payload.get("pages"),
        "review_status": review_payload.get("status"),
        "final_editor_status": final_editor_payload.get("status"),
        "missing": missing,
        "quality_errors": quality_errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--keep", action="store_true", help="keep the temporary simulation directory")
    args = parser.parse_args()

    env = os.environ.copy()
    env["PYTHONPATH"] = f"{SRC}{os.pathsep}{env.get('PYTHONPATH', '')}"

    with tempfile.TemporaryDirectory(prefix="morning-paper-friend-") as tmp:
        base = Path(tmp)
        results = [simulate(persona, base, env) for persona in PERSONAS]
        report = {"base": str(base), "results": results, "ok": all(item["ok"] for item in results)}
        print(json.dumps(report, indent=2))
        if args.keep:
            kept = Path(tempfile.mkdtemp(prefix="morning-paper-friend-kept-"))
            import shutil

            shutil.copytree(base, kept / "simulations", dirs_exist_ok=True)
            print(json.dumps({"kept": str(kept / "simulations")}, indent=2), file=sys.stderr)
        return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
