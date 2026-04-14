from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from .builder import build_paper
from .config import DEFAULT_CONFIG_DIR, DEFAULT_CONFIG_PATH, load_config, render_default_config


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_MAP = {
    "pass1": REPO_ROOT / "scripts" / "run_pass1.py",
    "pass2": REPO_ROOT / "scripts" / "run_pass2.py",
    "pass3": REPO_ROOT / "scripts" / "run_pass3.py",
    "assemble": REPO_ROOT / "scripts" / "assemble_brief.py",
    "render": REPO_ROOT / "scripts" / "build_live_brief.py",
    "digest": REPO_ROOT / "scripts" / "send_brief_digest.py",
}


def run_script(script: Path, args: list[str]) -> int:
    if not script.exists():
        print(f"missing script: {script}", file=sys.stderr)
        return 1
    cmd = [sys.executable, str(script), *args]
    return subprocess.call(cmd, cwd=REPO_ROOT)


def doctor() -> int:
    required = [
        REPO_ROOT / "scripts" / "run_pass1.py",
        REPO_ROOT / "scripts" / "run_pass2.py",
        REPO_ROOT / "scripts" / "run_pass3.py",
        REPO_ROOT / "scripts" / "assemble_brief.py",
        REPO_ROOT / "scripts" / "build_live_brief.py",
        REPO_ROOT / "templates" / "typewriter-v5.md",
    ]
    missing = [str(path.relative_to(REPO_ROOT)) for path in required if not path.exists()]
    if missing:
        print("doctor: missing required files:", file=sys.stderr)
        for item in missing:
            print(f"- {item}", file=sys.stderr)
        return 1
    print("doctor: ok")
    return 0


def init_command(args: list[str]) -> int:
    config_path = DEFAULT_CONFIG_PATH
    force = False
    index = 0
    while index < len(args):
        arg = args[index]
        if arg in {"-h", "--help"}:
            print("usage: morning-paper init [--config PATH] [--force]")
            return 0
        if arg == "--config" and index + 1 < len(args):
            config_path = Path(args[index + 1]).expanduser().resolve()
            index += 2
            continue
        if arg == "--force":
            force = True
            index += 1
            continue
        print(f"unknown init argument: {arg}", file=sys.stderr)
        return 2
    config_path.parent.mkdir(parents=True, exist_ok=True)
    if config_path.exists() and not force:
        print(f"config already exists: {config_path}", file=sys.stderr)
        print("use --force to overwrite", file=sys.stderr)
        return 1
    config_path.write_text(render_default_config(), encoding="utf-8")
    print(json.dumps({"config": str(config_path), "created": True}, indent=2))
    return 0


def build_command(args: list[str]) -> int:
    config_path = DEFAULT_CONFIG_PATH
    date = None
    index = 0
    while index < len(args):
        arg = args[index]
        if arg in {"-h", "--help"}:
            print("usage: morning-paper build [--config PATH] [--date YYYY-MM-DD]")
            return 0
        if arg == "--config" and index + 1 < len(args):
            config_path = Path(args[index + 1]).expanduser().resolve()
            index += 2
            continue
        if arg == "--date" and index + 1 < len(args):
            date = args[index + 1]
            index += 2
            continue
        print(f"unknown build argument: {arg}", file=sys.stderr)
        return 2
    if not config_path.exists():
        print(f"missing config: {config_path}", file=sys.stderr)
        print("run `morning-paper init` first or pass --config", file=sys.stderr)
        return 1
    config = load_config(config_path)
    result = build_paper(config, date_str=date)
    print(json.dumps(result, indent=2))
    return 0


def smoke() -> int:
    script = REPO_ROOT / "scripts" / "smoke_test.sh"
    if not script.exists():
        print(f"missing smoke script: {script}", file=sys.stderr)
        return 1
    return subprocess.call(["bash", str(script)], cwd=REPO_ROOT)


def print_help() -> int:
    commands = ", ".join(["init", "build", *SCRIPT_MAP, "doctor", "smoke"])
    print("usage: morning-paper {" + commands + "} [args...]")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in {"-h", "--help", "help"}:
        return print_help()

    command, extra = argv[0], argv[1:]

    if command == "init":
        return init_command(extra)
    if command == "build":
        return build_command(extra)
    if command in SCRIPT_MAP:
        return run_script(SCRIPT_MAP[command], extra)
    if command == "doctor":
        return doctor()
    if command == "smoke":
        return smoke()
    print(f"unknown command: {command}", file=sys.stderr)
    print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
