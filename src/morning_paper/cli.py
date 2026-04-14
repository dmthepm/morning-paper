from __future__ import annotations

import argparse
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Morning Paper CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    for name in SCRIPT_MAP:
        sub.add_parser(name, add_help=False)

    sub.add_parser("doctor")
    sub.add_parser("smoke")
    return parser


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    ns, extra = parser.parse_known_args(argv)

    if ns.command in SCRIPT_MAP:
        return run_script(SCRIPT_MAP[ns.command], extra)
    if ns.command == "doctor":
        return doctor()
    if ns.command == "smoke":
        return smoke()
    parser.error(f"unknown command: {ns.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
