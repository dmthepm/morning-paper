from __future__ import annotations

import json
from pathlib import Path

import tomllib

from morning_paper.cli import HELP_TEXT


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_friend_install_path_uses_the_same_print_proof_everywhere() -> None:
    readme = _read("README.md")
    agents = _read("AGENTS.md")
    setup_skill = _read("plugins/morning-paper/skills/setup/SKILL.md")
    spec = _read("docs/product-readiness-0.8.md")

    assert "morning-paper doctor --strict" in readme
    assert "morning-paper demo --open" in readme
    assert "Do not set up my private newsroom yet" in readme
    assert "After the demo PDF is open, install the plugin" in readme

    assert "morning-paper doctor --strict" in agents
    assert "morning-paper demo --open" in agents

    assert "morning-paper doctor --strict" in setup_skill
    assert "morning-paper demo --output ./morning-paper-demo --open" in setup_skill

    assert "demo --open" in spec
    assert "doctor --strict" in spec
    assert "doctor            Check config, dependencies, and renderer status (--json, --strict)" in HELP_TEXT


def test_personal_newsroom_primitives_are_the_canonical_taste_files() -> None:
    expected = ["EDITORIAL.md", "VISUALS.md", "SOURCES.md", "DELIVERY.md", "TASTELOG.md"]
    contracts = [
        _read("README.md"),
        _read("AGENTS.md"),
        _read("plugins/morning-paper/skills/setup/SKILL.md"),
        _read("plugins/morning-paper/skills/edition/SKILL.md"),
        _read("src/morning_paper/newsroom.py"),
    ]

    for text in contracts:
        for filename in expected:
            assert filename in text

    for text in contracts:
        assert "product.md" not in text.lower()
        assert "design.md" not in text.lower()


def test_package_and_plugin_descriptions_match_the_owned_algorithm_story() -> None:
    pyproject = tomllib.loads(_read("pyproject.toml"))
    claude_manifest = json.loads(_read(".claude-plugin/plugin.json"))
    codex_manifest = json.loads(_read("plugins/morning-paper/.codex-plugin/plugin.json"))
    changelog = _read("CHANGELOG.md")

    summary = pyproject["project"]["description"]
    version = pyproject["project"]["version"]
    assert summary.startswith("Own your algorithm")
    assert "personal newsroom" in summary
    assert "sources and preferences you own as files" in summary
    assert f"## [{version}]" in changelog
    assert "Friend-ready personal newsroom setup" in changelog
    assert "release-candidate checks pass" in changelog

    for manifest in (claude_manifest, codex_manifest):
        description = manifest["description"]
        assert manifest["version"] == version
        assert "personal newsroom" in description
        assert "preferences you own as files" in description


def test_chart_guardrails_are_current_work_not_future_roadmap() -> None:
    roadmap = _read("ROADMAP.md")
    composing = _read("docs/composing.md")
    spec = _read("docs/product-readiness-0.8.md")

    assert "chart row/label bounds" not in roadmap
    assert "mp-bars` shows up to 12 rows" in composing
    assert "mp-stats`" in composing and "6 primary blocks" in composing
    assert "mp-spark`" in composing and "90 values" in composing
    assert "cap print" in spec
    assert "overflow notes" in spec
