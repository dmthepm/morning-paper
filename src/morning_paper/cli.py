from __future__ import annotations

import subprocess
import sys
from pathlib import Path


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


def smoke() -> int:
    script = REPO_ROOT / "scripts" / "smoke_test.sh"
    if not script.exists():
        print(f"missing smoke script: {script}", file=sys.stderr)
        return 1
    return subprocess.call(["bash", str(script)], cwd=REPO_ROOT)


def print_help() -> int:
    commands = ", ".join([*SCRIPT_MAP, "doctor", "smoke"])
    print("usage: morning-paper {" + commands + "} [args...]")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in {"-h", "--help", "help"}:
        return print_help()

    command, extra = argv[0], argv[1:]

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
