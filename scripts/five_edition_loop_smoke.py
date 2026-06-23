#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

DATES = [
    "2026-06-22",
    "2026-06-23",
    "2026-06-24",
    "2026-06-25",
    "2026-06-26",
]

EDITIONS = [
    {
        "title": "Work Pulse",
        "source": "# Work pulse\n\nOnboarding is improving, but source setup still needs one simple path.\n",
        "route": "sources",
        "note": "Ask for one work stream and one saved-reading path before bigger integrations.",
        "why": "day one was strongest when the source ask stayed small",
        "useful": "source setup got simpler",
        "visual": "no visual issue",
        "source_confusion": "which source to add next",
    },
    {
        "title": "Saved Reading",
        "source": "# Saved reading\n\nA local-first essay argues that files make agent work easier to resume.\n",
        "route": "editorial",
        "note": "Lead with the connection across sources, not with a pile of unrelated links.",
        "why": "day two was useful when it connected work and reading",
        "useful": "connection across sources",
        "visual": "stats block fit",
        "source_confusion": "none",
    },
    {
        "title": "Visual Desk",
        "source": "# Visual desk\n\nA chart belongs only when it explains a tradeoff better than prose.\n",
        "route": "visuals",
        "note": "Use full-width or two-column visuals when a graphic would otherwise strand short lines.",
        "why": "day three protected the page from awkward visual furniture",
        "useful": "visual rule became explicit",
        "visual": "wide figure worked",
        "source_confusion": "none",
    },
    {
        "title": "Delivery Desk",
        "source": "# Delivery desk\n\nThe reader wants the PDF opened, then a short request for natural-language notes.\n",
        "route": "delivery",
        "note": "After delivery, ask for notes about content, layout, sources, page count, and what to print tomorrow.",
        "why": "day four made the return path clearer",
        "useful": "feedback request was concrete",
        "visual": "no visual issue",
        "source_confusion": "none",
    },
    {
        "title": "Algorithm Prior",
        "source": "# Algorithm prior\n\nThe paper should prefer fewer stronger items over comprehensive coverage.\n",
        "route": "prior",
        "note": "Prefer fewer stronger items over comprehensive coverage when the page budget is tight.",
        "why": "day five saved the taste rule in a structured preference file",
        "useful": "page budget had a taste rule",
        "visual": "no visual issue",
        "source_confusion": "none",
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


def configure(config_path: Path, output_dir: Path) -> None:
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    data["name"] = "Five-Day Desk"
    data["profile"] = "Reader tuning a personal newsroom across consecutive printed editions."
    data["outputs"]["directory"] = str(output_dir)
    data["outputs"]["style"] = "broadsheet"
    data["outputs"]["palette"] = "color"
    data["page_budget"] = 10
    data["sources"]["hacker_news"]["enabled"] = False
    data["sources"]["rss"] = []
    config_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def compose_draft(
    *,
    date_str: str,
    edition: dict[str, str],
    prior_feedback: list[str],
    current_title: str,
    previous_titles: list[str],
) -> str:
    carried = "\n".join(f"- {note}" for note in prior_feedback) or "- No feedback applied yet."
    previous_count = len(previous_titles)
    return f"""# Five-Day Desk Learns From The Reader - {date_str}

## The Read

Today's paper should prove a narrow editorial loop: read one source-backed
signal, carry forward stable reader feedback, and avoid reprinting old reads
just because they remain in memory.

## Today's Source Sets The Day

Current read: **{current_title}**.

{edition['source'].splitlines()[-1]}

## Feedback Carries Forward

{carried}

## The Budget Keeps Old Reads Out

Previous reads already logged: {previous_count}. Do not reprint them. The page
budget stays finite, so today gets one lead, one source note, and one concrete
feedback question.

```mp-stats
Edition day | {previous_count + 1} | of 5
Prior feedback rules | {len(prior_feedback)} | carried forward
Current read | 1 | printed
```

## Quality Notes Track The Tradeoffs

- Useful: {edition['useful']}.
- Generic risk: repeating a source without a new decision.
- Wasted pages: none allowed beyond the 10-page budget.
- Visual/layout issue: {edition['visual']}.
- Source confusion: {edition['source_confusion']}.

## The Editor Asks After Printing

Ask what to keep, cut, expand, change visually, add as a source, adjust about
delivery, or print tomorrow. Record stable feedback with
`morning-paper edition apply-feedback`.
"""


def assert_contains(path: Path, needle: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if needle not in text:
        raise RuntimeError(f"{label} missing expected text: {needle}")


def simulate(base: Path, env: dict[str, str]) -> dict[str, object]:
    config_path = base / "config.yaml"
    output_dir = base / "outputs"
    newsroom = base / "newsroom"
    require_ok(run_cli(["init", "--config", str(config_path)], env=env), "init")
    configure(config_path, output_dir)
    require_ok(run_cli(["newsroom", "init", str(newsroom), "--name", "Five-Day Desk"], env=env), "newsroom")

    prior_feedback: list[str] = []
    previous_titles: list[str] = []
    results: list[dict[str, object]] = []

    for date_str, edition in zip(DATES, EDITIONS, strict=True):
        require_ok(
            run_cli(["edition", "prepare", str(newsroom), "--config", str(config_path), "--date", date_str], env=env),
            f"{date_str} prepare",
        )

        source_path = base / f"{date_str}-source.md"
        source_path.write_text(edition["source"], encoding="utf-8")
        stage = run_cli(
            ["stage", str(source_path), "--title", edition["title"], "--config", str(config_path), "--date", date_str],
            env=env,
        )
        require_ok(stage, f"{date_str} stage")
        staged = json.loads(stage.stdout)
        current_title = str(staged["title"])

        queue = run_cli(["queue", "list", "--config", str(config_path), "--date", date_str], env=env)
        require_ok(queue, f"{date_str} queue")
        edition_dir = newsroom / "editions" / date_str
        (edition_dir / "queue-snapshot.json").write_text(queue.stdout, encoding="utf-8")
        (edition_dir / "collector-report.md").write_text(
            f"# Collector Report - {date_str}\n\nok: staged `{current_title}` from a local file.\n",
            encoding="utf-8",
        )

        draft = edition_dir / "draft.md"
        draft.write_text(
            compose_draft(
                date_str=date_str,
                edition=edition,
                prior_feedback=prior_feedback,
                current_title=current_title,
                previous_titles=previous_titles,
            ),
            encoding="utf-8",
        )
        draft_text = draft.read_text(encoding="utf-8")
        for note in prior_feedback:
            if note not in draft_text:
                raise RuntimeError(f"{date_str} did not carry prior feedback: {note}")
        for old_title in previous_titles:
            if old_title in draft_text:
                raise RuntimeError(f"{date_str} reprinted old read title: {old_title}")

        render = run_cli(["render", str(draft), "--config", str(config_path), "--date", date_str, "--slug", "edition"], env=env)
        require_ok(render, f"{date_str} render")
        render_payload = json.loads(render.stdout)
        (edition_dir / "render-result.json").write_text(json.dumps(render_payload, indent=2), encoding="utf-8")

        review = run_cli(["review", str(render_payload["output_dir"]), "--json", "--config", str(config_path)], env=env)
        require_ok(review, f"{date_str} review")
        review_payload = json.loads(review.stdout)
        (edition_dir / "review.json").write_text(json.dumps(review_payload, indent=2), encoding="utf-8")

        final_editor = run_cli(["edition", "final-editor", str(newsroom), "--config", str(config_path), "--date", date_str], env=env)
        require_ok(final_editor, f"{date_str} final-editor")
        final_payload = json.loads(final_editor.stdout)
        if final_payload.get("status") == "review":
            raise RuntimeError(
                f"{date_str} final editor requested revision:\n{json.dumps(final_payload, indent=2)}\n"
                f"review payload:\n{json.dumps(review_payload, indent=2)}"
            )

        feedback = run_cli(
            [
                "edition",
                "apply-feedback",
                str(newsroom),
                "--config",
                str(config_path),
                "--date",
                date_str,
                "--route",
                edition["route"],
                "--note",
                edition["note"],
                "--why",
                edition["why"],
            ],
            env=env,
        )
        require_ok(feedback, f"{date_str} apply feedback")
        feedback_payload = json.loads(feedback.stdout)
        target = Path(str(feedback_payload["target"]))
        assert_contains(target, edition["note"], f"{date_str} target feedback file")
        assert_contains(newsroom / "TASTELOG.md", edition["note"], f"{date_str} taste log")
        assert_contains(edition_dir / "feedback-plan.md", f"`{edition['route']}`", f"{date_str} feedback plan")

        pdf = Path(str(render_payload["outputs"]["pdf"]))
        if not pdf.is_file() or pdf.read_bytes()[:5] != b"%PDF-":
            raise RuntimeError(f"{date_str} PDF missing or invalid: {pdf}")
        pages = int(render_payload.get("pages") or 0)
        if pages < 1 or pages > 10:
            raise RuntimeError(f"{date_str} page count outside budget proof: {pages}")

        results.append(
            {
                "date": date_str,
                "title": current_title,
                "pages": pages,
                "review_status": review_payload.get("status"),
                "final_editor_status": final_payload.get("status"),
                "feedback_route": edition["route"],
                "feedback_target": feedback_payload["target_relative"],
                "pdf": str(pdf),
                "quality_notes": {
                    "useful": edition["useful"],
                    "generic": "repeating a source without a new decision",
                    "wasted_pages": "none beyond the page budget",
                    "visual_layout": edition["visual"],
                    "source_confusion": edition["source_confusion"],
                },
            }
        )
        prior_feedback.append(edition["note"])
        previous_titles.append(current_title)

    return {
        "ok": True,
        "newsroom": str(newsroom),
        "editions": results,
        "feedback_rules_carried": len(prior_feedback),
        "taste_log": str(newsroom / "TASTELOG.md"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--keep", action="store_true", help="keep the temporary simulation directory")
    args = parser.parse_args()

    env = os.environ.copy()
    env["PYTHONPATH"] = f"{SRC}{os.pathsep}{env.get('PYTHONPATH', '')}"
    with tempfile.TemporaryDirectory(prefix="morning-paper-five-edition-") as tmp:
        base = Path(tmp)
        report = simulate(base, env)
        print(json.dumps(report, indent=2))
        if args.keep:
            kept = Path(tempfile.mkdtemp(prefix="morning-paper-five-edition-kept-"))
            shutil.copytree(base, kept / "simulation", dirs_exist_ok=True)
            print(json.dumps({"kept": str(kept / "simulation")}, indent=2), file=sys.stderr)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
