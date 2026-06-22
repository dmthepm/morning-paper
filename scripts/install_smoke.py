#!/usr/bin/env python3
"""Install-smoke: prove a clean plugin install exposes setup/edition/writing.

The two host manifests each declare a ``skills`` path. This resolves both
exactly as each host would, and asserts that both land on the *same* real
directory carrying all three skills with valid frontmatter. It is the
file-level proof behind "a fresh friend's install carries the newsroom skills"
on Claude Code and Codex, runnable on a CI box with no CLI installed.

Usage: ``python3 scripts/install_smoke.py`` (run from the repo root).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REQUIRED_SKILLS = ("setup", "edition", "writing")


def resolve_skills(base: Path, skills_field: str) -> Path:
    # Both hosts treat the manifest `skills` value as relative to the manifest's
    # plugin root, joining and normalizing it.
    return (base / skills_field.lstrip("./")).resolve()


def assert_skills_dir(label: str, skills_dir: Path, errors: list[str]) -> None:
    if not skills_dir.is_dir():
        errors.append(f"{label}: skills path does not resolve to a directory: {skills_dir}")
        return
    for name in REQUIRED_SKILLS:
        skill_md = skills_dir / name / "SKILL.md"
        if not skill_md.is_file():
            errors.append(f"{label}: missing skill `{name}` ({skill_md})")
            continue
        text = skill_md.read_text(encoding="utf-8")
        if not text.startswith("---\n") or text.find("\n---", 4) == -1:
            errors.append(f"{label}: skill `{name}` has no closed YAML frontmatter")
            continue
        front = text[4:text.find("\n---", 4)]
        if not re.search(r"^name:\s*\S", front, re.MULTILINE):
            errors.append(f"{label}: skill `{name}` frontmatter missing `name`")


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    errors: list[str] = []

    # Claude Code: manifest at repo root, `skills` relative to repo root.
    cc_manifest = json.loads((repo_root / ".claude-plugin" / "plugin.json").read_text())
    cc_skills = resolve_skills(repo_root, cc_manifest["skills"])
    assert_skills_dir("Claude Code", cc_skills, errors)

    # Codex: manifest under plugins/morning-paper, `skills` relative to that root.
    codex_root = repo_root / "plugins" / "morning-paper"
    codex_manifest = json.loads((codex_root / ".codex-plugin" / "plugin.json").read_text())
    codex_skills = resolve_skills(codex_root, codex_manifest["skills"])
    assert_skills_dir("Codex", codex_skills, errors)

    # Single-source invariant: both hosts must resolve to the SAME real tree.
    if cc_skills != codex_skills:
        errors.append(
            "single-source violation: Claude Code and Codex resolve different skills trees "
            f"({cc_skills} vs {codex_skills})"
        )

    # Version parity across both manifests.
    if cc_manifest.get("version") != codex_manifest.get("version"):
        errors.append(
            f"version drift: Claude Code {cc_manifest.get('version')} != "
            f"Codex {codex_manifest.get('version')}"
        )

    if errors:
        print("Install-smoke failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Install-smoke passed: both hosts expose {', '.join(REQUIRED_SKILLS)} from {cc_skills}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
