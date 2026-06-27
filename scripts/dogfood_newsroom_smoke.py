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
DATE = "2026-06-22"
FORBIDDEN_PRIVATE_TERMS = (
    "PRIVATE_READER_NAME",
    "PRIVATE_PROJECT_NAME",
    "PRIVATE_BRAND_NAME",
    "PRIVATE_CLIENT_CODE",
    "PRIVATE_SOURCE_NAME",
    "reader-newsroom",
    "private-newsroom.example",
)


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
    data["name"] = "Dogfood Desk"
    data["profile"] = "Creator/operator with work streams, saved reading, local exports, and personal feeds."
    data["outputs"]["directory"] = str(output_dir)
    data["outputs"]["style"] = "broadsheet"
    data["outputs"]["palette"] = "color"
    data["page_budget"] = 12
    data["sources"]["rss"] = []
    config_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def seed_sources(root: Path, newsroom: Path) -> dict[str, Path]:
    inbox = newsroom / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    sources = {
        "work": root / "work-pulse.md",
        "saved": root / "saved-read.md",
        "exports": root / "converted-exports.md",
        "local": inbox / "desk-note.md",
    }
    sources["work"].write_text(
        "# Work pulse\n\n"
        "- Bet: make first-run setup feel calm.\n"
        "- Push: finish converter guidance.\n"
        "- Risk: unsupported exports becoming invisible.\n"
        "- Ask: decide whether the daily paper should include a work-first lead.\n",
        encoding="utf-8",
    )
    sources["saved"].write_text(
        "# Saved read\n\n"
        "A long essay about local-first tools argues that durable files make agent work easier to resume.\n",
        encoding="utf-8",
    )
    sources["exports"].write_text(
        "# Personal algorithm export digest\n\n"
        "Rows inspected: 4 CSV history rows and 3 JSON watch events.\n\n"
        "## Repeated interests\n\n"
        "- Local-first software and private data control appeared three times.\n"
        "- Print, newsletters, and calmer reading surfaces appeared twice.\n\n"
        "## Source honesty\n\n"
        "This is a synthetic converter output for dogfood smoke; original CSV/JSON files stayed in inbox/.\n",
        encoding="utf-8",
    )
    sources["local"].write_text(
        "# Desk note\n\n"
        "The first useful paper should connect work pressure, source hygiene, and personal reading taste.\n",
        encoding="utf-8",
    )
    (inbox / "watch-history.csv").write_text("watched_at,title\n2026-06-21,Local-first video\n", encoding="utf-8")
    (inbox / "social-export.json").write_text(
        json.dumps({"likes": [{"topic": "personal knowledge", "url": "https://example.com/a"}]}, indent=2),
        encoding="utf-8",
    )
    return sources


def compose_draft(queue_titles: list[str]) -> str:
    titles = "\n".join(f"- {title}" for title in queue_titles)
    return f"""# Dogfood Desk Connects Work, Reading, and Exports - {DATE}

## The Read

The useful first edition is not a feed replacement. It is a private editorial
desk that notices the same pattern across work, saved reading, and exported
taste: source ownership only matters if it turns into a smaller, calmer
decision surface.

## What Changed

The work pulse says setup and converter guidance are the active risk. The
personal export digest points at the same theme from the reading side:
local-first tools, private data control, and calmer surfaces keep recurring.
The connection is the story. Today's paper should spend ink on the source loop,
not on a pile of unrelated links.

```mp-stats
Source lanes | 4 | work, local, saved, exports
Queue items | {len(queue_titles)} | staged today
Page budget | 12 | finite by design
```

## Queue

{titles}

## Source Desk

The unsupported CSV and JSON files stayed visible in `source-inventory.json`,
but they did not pretend to be readable. The converter digest became staged
markdown, which is the correct boundary: private adapter outside the engine,
honest markdown inside the edition queue.

## Editor Decision

Tomorrow's setup should ask for one work stream, one saved-reading path, and
one export or folder before chasing any bigger integration. If the reader gives
feedback after printing, route it to the smallest durable newsroom file.

<figure class="mp-figure mp-wide">
  <div class="mp-stats">
    <div><strong>4</strong><span>source lanes</span></div>
    <div><strong>1</strong><span>converter digest</span></div>
    <div><strong>0</strong><span>private facts</span></div>
  </div>
  <figcaption>Dogfood source mix.</figcaption>
  <span class="mp-source-note">Source: synthetic dogfood fixtures, {DATE}.</span>
</figure>
"""


def scan_private_terms(path: Path) -> dict[str, object]:
    hits: list[dict[str, str]] = []
    for file in path.rglob("*"):
        if not file.is_file() or file.suffix.lower() not in {".md", ".json", ".yaml", ".yml", ".txt"}:
            continue
        text = file.read_text(encoding="utf-8", errors="ignore")
        for term in FORBIDDEN_PRIVATE_TERMS:
            if term in text:
                hits.append({"file": str(file), "term": term})
    return {"ok": not hits, "hits": hits}


def main() -> int:
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{SRC}{os.pathsep}{env.get('PYTHONPATH', '')}"
    with tempfile.TemporaryDirectory(prefix="morning-paper-dogfood-") as tmp:
        base = Path(tmp)
        config_path = base / "config.yaml"
        output_dir = base / "outputs"
        newsroom = base / "newsroom"

        require_ok(run_cli(["init", "--config", str(config_path)], env=env), "init")
        configure(config_path, output_dir)
        require_ok(run_cli(["newsroom", "init", str(newsroom), "--name", "Dogfood Desk"], env=env), "newsroom")
        source_paths = seed_sources(base, newsroom)

        sources_check = run_cli(["sources", "check", "--config", str(config_path), "--newsroom", str(newsroom)], env=env)
        require_ok(sources_check, "sources check")
        sources_payload = json.loads(sources_check.stdout)
        unsupported = sources_payload["newsroom"]["local_drop"]["unsupported_count"]
        if unsupported < 2 or "CONVERTERS.md" not in " ".join(sources_payload["next_actions"]):
            raise RuntimeError("unsupported exports did not point at converter playbook")

        require_ok(run_cli(["edition", "prepare", str(newsroom), "--config", str(config_path), "--date", DATE], env=env), "prepare")
        staged_titles = []
        for title, path in (
            ("Work pulse", source_paths["work"]),
            ("Saved read", source_paths["saved"]),
            ("Personal algorithm export digest", source_paths["exports"]),
        ):
            stage = run_cli(["stage", str(path), "--title", title, "--config", str(config_path), "--date", DATE], env=env)
            require_ok(stage, f"stage {title}")
            staged_titles.append(json.loads(stage.stdout)["title"])

        queue = run_cli(["queue", "list", "--config", str(config_path), "--date", DATE], env=env)
        require_ok(queue, "queue")
        edition_dir = newsroom / "editions" / DATE
        (edition_dir / "source-inventory.json").write_text(json.dumps(sources_payload, indent=2), encoding="utf-8")
        (edition_dir / "queue-snapshot.json").write_text(queue.stdout, encoding="utf-8")
        (edition_dir / "collector-report.md").write_text(
            f"# Collector Report - {DATE}\n\nok: staged work, saved reading, and converter digest.\n",
            encoding="utf-8",
        )
        draft = edition_dir / "draft.md"
        draft.write_text(compose_draft(staged_titles), encoding="utf-8")

        estimate = run_cli(["edition", "estimate", str(newsroom), "--config", str(config_path), "--date", DATE], env=env)
        require_ok(estimate, "estimate")

        render = run_cli(["render", str(draft), "--config", str(config_path), "--date", DATE, "--slug", "edition"], env=env)
        require_ok(render, "render")
        render_payload = json.loads(render.stdout)
        (edition_dir / "render-result.json").write_text(json.dumps(render_payload, indent=2), encoding="utf-8")

        review = run_cli(["review", str(render_payload["output_dir"]), "--json", "--config", str(config_path)], env=env)
        require_ok(review, "review")
        review_payload = json.loads(review.stdout)
        (edition_dir / "review.json").write_text(json.dumps(review_payload, indent=2), encoding="utf-8")

        visual_qa = run_cli(["edition", "visual-qa", str(newsroom), "--config", str(config_path), "--date", DATE], env=env)
        require_ok(visual_qa, "visual-qa")

        final_editor = run_cli(["edition", "final-editor", str(newsroom), "--config", str(config_path), "--date", DATE], env=env)
        require_ok(final_editor, "final-editor")
        final_editor_payload = json.loads(final_editor.stdout)
        if final_editor_payload["status"] == "review":
            raise RuntimeError(
                "final editor requested revision:\n"
                f"{json.dumps(final_editor_payload, indent=2)}\n"
                "review payload:\n"
                f"{json.dumps(review_payload, indent=2)}"
            )

        feedback = run_cli(
            [
                "edition",
                "apply-feedback",
                str(newsroom),
                "--config",
                str(config_path),
                "--date",
                DATE,
                "--route",
                "sources",
                "--note",
                "Ask for one work stream, one saved-reading path, and one export or folder before bigger integrations.",
                "--why",
                "dogfood paper was useful when it connected all three",
            ],
            env=env,
        )
        require_ok(feedback, "apply feedback")
        private_scan = scan_private_terms(base)
        if not private_scan["ok"]:
            raise RuntimeError(f"private scan failed: {json.dumps(private_scan, indent=2)}")

        report = {
            "ok": True,
            "newsroom": str(newsroom),
            "edition_dir": str(edition_dir),
            "pdf": render_payload["outputs"]["pdf"],
            "pages": render_payload["pages"],
            "review_status": review_payload["status"],
            "final_editor_status": final_editor_payload["status"],
            "unsupported_local_drop": unsupported,
            "converter_playbook": sources_payload["newsroom"]["local_drop"]["converter_playbook"],
            "feedback_status": json.loads(feedback.stdout)["status"],
            "private_scan": private_scan,
        }
        print(json.dumps(report, indent=2))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
