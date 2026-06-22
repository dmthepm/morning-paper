#!/usr/bin/env python3
"""Smoke-test Morning Paper in real Claude Code and Codex plugin hosts.

This verifies host discovery and install behavior without mutating the user's
real Claude/Codex configuration:

- copy the current worktree to a sanitized temporary marketplace;
- install the plugin with a temporary CODEX_HOME;
- install the plugin with a temporary CLAUDE_CONFIG_DIR;
- inspect each installed cache for exactly the shipped setup/edition/writing skills.

It is intentionally local-only: CI often does not have Claude Code or Codex.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SHIPPED_SKILLS = ("setup", "edition", "writing")
EXCLUDED_NAMES = {
    ".git",
    ".claude",
    ".codex",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "htmlcov",
}
EXCLUDED_SUFFIXES = (".egg-info",)


def _ignore(_dir: str, names: list[str]) -> set[str]:
    ignored = set()
    for name in names:
        if name in EXCLUDED_NAMES or name.endswith(EXCLUDED_SUFFIXES):
            ignored.add(name)
    return ignored


def _run(cmd: list[str], *, env: dict[str, str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def _require_ok(label: str, result: subprocess.CompletedProcess[str], errors: list[str]) -> None:
    if result.returncode != 0:
        errors.append(f"{label} failed with exit {result.returncode}:\n{result.stdout}")


def _load_json(path: Path, errors: list[str]) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - report validation failures cleanly.
        errors.append(f"could not read JSON `{path}`: {exc}")
        return {}


def _assert_skill_tree(label: str, root: Path, errors: list[str]) -> None:
    if not root.is_dir():
        errors.append(f"{label}: missing installed plugin root `{root}`")
        return
    skills_root = root / "skills"
    found = sorted(path.name for path in skills_root.iterdir() if path.is_dir() and not path.name.startswith(".")) if skills_root.is_dir() else []
    if found != sorted(SHIPPED_SKILLS):
        errors.append(
            f"{label}: shipped skill set changed without updating the smoke contract "
            f"(expected {sorted(SHIPPED_SKILLS)}, found {found})"
        )
    for name in SHIPPED_SKILLS:
        skill = root / "skills" / name / "SKILL.md"
        if not skill.is_file():
            errors.append(f"{label}: missing `{skill}`")
            continue
        text = skill.read_text(encoding="utf-8")
        if not text.startswith("---\n") or f"name: {name}" not in text[:500]:
            errors.append(f"{label}: `{skill}` does not look like the `{name}` skill")


def _assert_no_dev_debris(label: str, root: Path, errors: list[str]) -> None:
    blocked = []
    for path in root.rglob("*"):
        rel_parts = path.relative_to(root).parts
        if any(part in {".git", ".claude", "__pycache__", ".pytest_cache", "build"} for part in rel_parts):
            blocked.append(path.relative_to(root).as_posix())
            if len(blocked) >= 10:
                break
    if blocked:
        errors.append(f"{label}: installed cache contains local dev debris: {blocked}")


def _copy_sanitized_repo(repo: Path, temp_root: Path) -> Path:
    sandbox = temp_root / "marketplace"
    shutil.copytree(repo, sandbox, ignore=_ignore)
    return sandbox


def _codex_smoke(repo: Path, temp_root: Path, version: str, errors: list[str]) -> dict[str, str]:
    codex = shutil.which("codex")
    if not codex:
        errors.append("Codex CLI not found on PATH")
        return {}
    home = temp_root / "codex-home"
    home.mkdir()
    env = os.environ.copy()
    env["CODEX_HOME"] = str(home)
    steps = [
        ("codex marketplace add", [codex, "plugin", "marketplace", "add", str(repo)]),
        ("codex plugin list", [codex, "plugin", "list", "--marketplace", "morning-paper"]),
        ("codex plugin add", [codex, "plugin", "add", "morning-paper@morning-paper"]),
    ]
    for label, cmd in steps:
        result = _run(cmd, env=env, cwd=repo)
        _require_ok(label, result, errors)
        if result.returncode != 0:
            break
    installed_root = home / "plugins" / "cache" / "morning-paper" / "morning-paper" / version
    _assert_skill_tree("Codex", installed_root, errors)
    _assert_no_dev_debris("Codex", installed_root, errors)
    return {"home": str(home), "installed_root": str(installed_root)}


def _claude_smoke(repo: Path, temp_root: Path, version: str, errors: list[str]) -> dict[str, str]:
    claude = shutil.which("claude")
    if not claude:
        errors.append("Claude Code CLI not found on PATH")
        return {}
    config = temp_root / "claude-config"
    config.mkdir()
    env = os.environ.copy()
    env["CLAUDE_CONFIG_DIR"] = str(config)
    steps = [
        ("claude marketplace add", [claude, "plugin", "marketplace", "add", str(repo), "--scope", "user"]),
        ("claude plugin install", [claude, "plugin", "install", "morning-paper@morning-paper", "--scope", "user"]),
    ]
    for label, cmd in steps:
        result = _run(cmd, env=env, cwd=repo)
        _require_ok(label, result, errors)
        if result.returncode != 0:
            break
    installed_root = config / "plugins" / "cache" / "morning-paper" / "morning-paper" / version
    _assert_skill_tree("Claude Code", installed_root / "plugins" / "morning-paper", errors)
    _assert_no_dev_debris("Claude Code", installed_root, errors)
    return {"config": str(config), "installed_root": str(installed_root)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=Path(__file__).resolve().parent.parent, type=Path)
    parser.add_argument("--keep-temp", action="store_true", help="keep the sanitized marketplace and temp homes")
    args = parser.parse_args()

    repo = args.repo.resolve()
    errors: list[str] = []
    manifest = _load_json(repo / ".claude-plugin" / "plugin.json", errors)
    version = str(manifest.get("version") or "")
    if not version:
        errors.append("Claude manifest has no version")

    with tempfile.TemporaryDirectory(prefix="morning-paper-host-smoke-") as temp:
        temp_root = Path(temp)
        sandbox = _copy_sanitized_repo(repo, temp_root)
        summary = {
            "source_repo": str(repo),
            "sanitized_marketplace": str(sandbox),
            "version": version,
            "codex": _codex_smoke(sandbox, temp_root, version, errors) if version else {},
            "claude": _claude_smoke(sandbox, temp_root, version, errors) if version else {},
        }
        print(json.dumps(summary, indent=2))
        if args.keep_temp:
            kept = Path(tempfile.mkdtemp(prefix="morning-paper-host-smoke-kept-"))
            shutil.copytree(temp_root, kept / "run")
            print(f"kept temp run at {kept / 'run'}")

    if errors:
        print("Host plugin smoke failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Host plugin smoke passed: Claude Code and Codex install exactly the shipped shared skills from a clean local marketplace.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
