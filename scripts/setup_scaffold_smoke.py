#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
DATE = "2026-06-22"


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


def first_json_object(text: str) -> dict[str, object]:
    decoder = json.JSONDecoder()
    payload, _ = decoder.raw_decode(text.lstrip())
    if not isinstance(payload, dict):
        raise RuntimeError("expected a JSON object")
    return payload


def install_local_wrapper(bin_dir: Path, env: dict[str, str]) -> None:
    target = bin_dir / "morning-paper"
    py = shlex.quote(sys.executable)
    src = shlex.quote(str(SRC))
    home = shlex.quote(env["HOME"])
    xdg = shlex.quote(env["XDG_CONFIG_HOME"])
    target.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"HOME={home} XDG_CONFIG_HOME={xdg} PYTHONPATH={src}${{PYTHONPATH:+:$PYTHONPATH}} "
        f"{py} -m morning_paper.cli \"$@\"\n",
        encoding="utf-8",
    )
    os.chmod(target, 0o755)


def configure_default_config(config_path: Path, output_dir: Path) -> None:
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    data["name"] = "Friend Desk"
    data["profile"] = "Sandboxed setup-smoke friend validating the first newsroom path."
    data["outputs"]["directory"] = str(output_dir)
    data["sources"]["hacker_news"]["enabled"] = False
    data["sources"]["rss"] = []
    config_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def compose_first_draft(newsroom: Path, staged_title: str) -> Path:
    edition_dir = newsroom / "editions" / DATE
    draft = edition_dir / "draft.md"
    draft.write_text(
        f"""# Friend Desk Proves Setup Works - {DATE}

## The Read

The important result is that a cold private newsroom can accept a local source,
preserve setup state, survive the prepare step, and produce a reviewed PDF.
That is the first friend path: owned files in, printable paper out.

## Source Inventory

The scaffolded local-drop collector staged `{staged_title}` for this edition.
The built-in network sources are disabled for this smoke so the proof stays
deterministic and local.

## Reading

The staged note says the reader wants a simple first paper, durable state, and
clear next steps. The editor should ask for natural-language feedback after
delivery: what to keep, cut, expand, add as a source, or print tomorrow.
""",
        encoding="utf-8",
    )
    return draft


def assert_required_files(newsroom: Path) -> None:
    required = [
        "SETUP.md",
        "setup-state.json",
        "CLAUDE.md",
        "specs/the-read.md",
        "specs/front-page.md",
        "specs/reading.md",
        "preferences/voice.md",
        "preferences/algorithm-prior.yaml",
        "collectors/run_all.sh",
        "collectors/local-drop.sh",
        "examples/edition-skeleton.md",
    ]
    missing = [path for path in required if not (newsroom / path).exists()]
    if missing:
        raise RuntimeError(f"newsroom scaffold missing required files: {missing}")


def simulate(base: Path, *, keep: bool) -> dict[str, object]:
    home = base / "home"
    xdg = home / ".config"
    bin_dir = base / "bin"
    output_dir = base / "outputs"
    newsroom = base / "Friend-Newsroom"
    for path in (home, xdg, bin_dir, output_dir):
        path.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["HOME"] = str(home)
    env["XDG_CONFIG_HOME"] = str(xdg)
    env["PYTHONPATH"] = f"{SRC}{os.pathsep}{env.get('PYTHONPATH', '')}"
    env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
    install_local_wrapper(bin_dir, env)

    doctor = run_cli(["doctor", "--strict", "--json"], env=env)
    require_ok(doctor, "doctor --strict")
    doctor_payload = json.loads(doctor.stdout)
    if doctor_payload.get("status") != "ok":
        raise RuntimeError(f"doctor status was not ok: {doctor.stdout}")
    if not doctor_payload.get("renderer", {}).get("render_self_test", {}).get("ok"):
        raise RuntimeError(f"doctor render self-test failed: {doctor.stdout}")

    require_ok(run_cli(["init"], env=env), "init")
    config_path = xdg / "morning-paper" / "config.yaml"
    configure_default_config(config_path, output_dir)

    demo = run_cli(["demo", "--output", str(base / "demo.pdf")], env=env)
    require_ok(demo, "demo")
    demo_payload = first_json_object(demo.stdout)
    demo_pdf = Path(demo_payload["outputs"]["pdf"])
    if not demo_pdf.is_file():
        raise RuntimeError(f"demo PDF missing: {demo_pdf}")

    require_ok(run_cli(["newsroom", "init", str(newsroom), "--name", "Friend Desk"], env=env), "newsroom init")
    assert_required_files(newsroom)

    state_updates = [
        "installed_version=local-worktree",
        f"demo.pdf_path={demo_pdf}",
        "demo.opened_on_screen=false",
        "doctor.strict_passed=true",
        "doctor.renderer_self_test_passed=true",
        f"doctor.python={doctor_payload['dependencies']['python']['version']}",
        f"doctor.weasyprint={doctor_payload['dependencies']['packages']['weasyprint']}",
        "plugin_state.codex=smoke-not-installed",
        "plugin_state.claude_code=smoke-not-installed",
        'source_choices.hacker_news=no',
        'source_choices.collectors=["local-drop"]',
        "printer_choice.mode=pdf",
        "next_action=run first edition and ask for feedback",
    ]
    require_ok(
        run_cli(["newsroom", "state", str(newsroom), *sum([["--set", item] for item in state_updates], [])], env=env),
        "newsroom state",
    )

    inbox = newsroom / "inbox"
    inbox.mkdir(exist_ok=True)
    (inbox / "first-source.md").write_text(
        "# First source\n\nThis is a local source the reader already owns. It should flow into today's edition.\n",
        encoding="utf-8",
    )
    collectors = subprocess.run(
        ["bash", "run_all.sh", DATE],
        cwd=newsroom / "collectors",
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    require_ok(collectors, "collectors/run_all.sh")
    if "Local drop" not in collectors.stdout:
        raise RuntimeError(f"local-drop collector did not report success:\n{collectors.stdout}")

    prepare = run_cli(["edition", "prepare", str(newsroom), "--date", DATE, "--force"], env=env)
    require_ok(prepare, "edition prepare")
    prepare_payload = json.loads(prepare.stdout)
    edition_dir = Path(prepare_payload["edition_dir"])

    queue = run_cli(["queue", "list", "--date", DATE], env=env)
    require_ok(queue, "queue list")
    (edition_dir / "queue-snapshot.json").write_text(queue.stdout, encoding="utf-8")
    queue_payload = json.loads(queue.stdout)
    items = queue_payload.get("items") or []
    if not items:
        raise RuntimeError("staged queue was empty after local-drop collector")
    staged_title = str(items[0].get("title") or "first source")

    (edition_dir / "collector-report.md").write_text(
        f"# Collector Report - {DATE}\n\n```text\n{collectors.stdout.strip()}\n```\n",
        encoding="utf-8",
    )
    draft = compose_first_draft(newsroom, staged_title)

    render = run_cli(
        [
            "render",
            str(draft),
            "--date",
            DATE,
            "--slug",
            "edition",
            "--output",
            str(edition_dir / "edition.pdf"),
        ],
        env=env,
    )
    require_ok(render, "render")
    render_payload = json.loads(render.stdout)
    (edition_dir / "render-result.json").write_text(json.dumps(render_payload, indent=2), encoding="utf-8")
    pdf_path = Path(render_payload["outputs"]["pdf"])
    if not pdf_path.is_file():
        raise RuntimeError(f"rendered PDF missing: {pdf_path}")

    review = run_cli(["review", str(render_payload["output_dir"]), "--json"], env=env)
    require_ok(review, "review")
    review_payload = json.loads(review.stdout)
    (edition_dir / "review.json").write_text(json.dumps(review_payload, indent=2), encoding="utf-8")
    if review_payload.get("status") != "clean":
        raise RuntimeError(f"review was not clean: {json.dumps(review_payload, indent=2)}")

    required_artifacts = [
        "source-inventory.json",
        "collector-report.md",
        "queue-snapshot.json",
        "draft.md",
        "render-result.json",
        "review.json",
        "operator-answers.md",
    ]
    missing_artifacts = [name for name in required_artifacts if not (edition_dir / name).is_file()]
    if missing_artifacts:
        raise RuntimeError(f"edition workspace missing artifacts: {missing_artifacts}")

    setup_doc = (newsroom / "SETUP.md").read_text(encoding="utf-8")
    if "run first edition and ask for feedback" not in setup_doc:
        raise RuntimeError("SETUP.md did not refresh next action")

    return {
        "ok": True,
        "kept": str(base) if keep else "",
        "home": str(home),
        "newsroom": str(newsroom),
        "demo_pdf": str(demo_pdf),
        "edition_dir": str(edition_dir),
        "pdf": str(pdf_path),
        "pages": render_payload.get("pages"),
        "review_status": review_payload.get("status"),
        "doctor": {
            "python": doctor_payload["dependencies"]["python"]["version"],
            "weasyprint": doctor_payload["dependencies"]["packages"]["weasyprint"],
            "pango_found": doctor_payload["dependencies"]["native"]["pango"]["found"],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--keep", action="store_true", help="keep the temporary sandbox")
    args = parser.parse_args()

    if args.keep:
        base = Path(tempfile.mkdtemp(prefix="morning-paper-setup-smoke-"))
        print(json.dumps(simulate(base, keep=True), indent=2))
        return 0

    with tempfile.TemporaryDirectory(prefix="morning-paper-setup-smoke-") as tmp:
        print(json.dumps(simulate(Path(tmp), keep=False), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
