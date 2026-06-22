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
    },
    {
        "id": "business-owner-main-branch",
        "paper": "Operator Desk",
        "profile": "Business owner using Main Branch primitives: bets, pushes, risks, and asks.",
        "source": "# Main Branch pulse\n\nBet: improve onboarding. Push: finish the source layer. Risk: unclear owner feedback loop.\n",
    },
    {
        "id": "technical-agent-user",
        "paper": "Agent Lab",
        "profile": "Technical user validating agent tools, render contracts, and queue durability.",
        "source": "# Agent tool note\n\nThe queue, source inventory, and edition artifacts must survive compaction.\n",
    },
    {
        "id": "nontechnical-rss-newsletter",
        "paper": "Newsletter Morning",
        "profile": "Nontechnical reader with RSS/newsletters and no interest in YAML internals.",
        "source": "# Newsletter clipping\n\nA full-text newsletter item should become a readable page, not a feed blurb.\n",
    },
    {
        "id": "local-folder-source-dump",
        "paper": "Local Sources",
        "profile": "Reader with local markdown, text dumps, synced folders, and agent-produced files.",
        "source": "# Local folder dump\n\nThis came from a folder the user already owns. Nothing needed to move.\n",
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
    return f"""# {persona['paper']} Proves Its First Edition - {DATE}

## The Read

The useful thing today is that this reader can get from a cold setup to a
printable paper with sources they own as files.

## Source Inventory

The paper has a prepared source inventory and a queued local source:
{staged_title}.

## Reading

The first edition is deliberately modest. It proves the private newsroom,
queue, durable edition folder, renderer, review pass, and feedback sheet.
"""


def simulate(persona: dict[str, str], base: Path, env: dict[str, str]) -> dict[str, object]:
    root = base / persona["id"]
    config_path = root / "config.yaml"
    output_dir = root / "outputs"
    newsroom = root / "newsroom"
    root.mkdir(parents=True)

    require_ok(run_cli(["init", "--config", str(config_path)], env=env), f"{persona['id']} init")
    write_config(config_path, output_dir, persona["profile"])
    require_ok(run_cli(["newsroom", "init", str(newsroom), "--name", persona["paper"]], env=env), f"{persona['id']} newsroom")
    require_ok(
        run_cli(["edition", "prepare", str(newsroom), "--config", str(config_path), "--date", DATE], env=env),
        f"{persona['id']} edition prepare",
    )

    source_file = root / "source.md"
    source_file.write_text(persona["source"], encoding="utf-8")
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

    required = [
        "source-inventory.json",
        "collector-report.md",
        "queue-snapshot.json",
        "draft.md",
        "render-result.json",
        "review.json",
        "operator-answers.md",
        "feedback-plan.md",
    ]
    missing = [name for name in required if not (edition_dir / name).is_file()]
    pdf_path = Path(render_payload["outputs"]["pdf"])
    return {
        "persona": persona["id"],
        "ok": not missing and pdf_path.is_file(),
        "newsroom": str(newsroom),
        "edition_dir": str(edition_dir),
        "pdf": str(pdf_path),
        "pages": render_payload.get("pages"),
        "review_status": review_payload.get("status"),
        "missing": missing,
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
