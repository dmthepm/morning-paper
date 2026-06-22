from __future__ import annotations

import json
import re
from pathlib import Path

from morning_paper.cli import HELP_TEXT


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _pyproject_field(key: str) -> str:
    """Read a string field from pyproject's [project] table without tomllib.

    tomllib is stdlib only on Python 3.11+, but the package supports 3.10
    (requires-python >=3.10), so this test must too. The contract only needs
    two simple [project] string fields, so a tolerant regex beats taking a
    3.11-only import or a tomli dependency.
    """
    text = _read("pyproject.toml")
    section = text.split("[project]", 1)[-1].split("\n[", 1)[0]
    match = re.search(rf'^{re.escape(key)}\s*=\s*"([^"]*)"', section, re.M)
    assert match, f"{key} not found in [project] table of pyproject.toml"
    return match.group(1)


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
    claude_manifest = json.loads(_read(".claude-plugin/plugin.json"))
    codex_manifest = json.loads(_read("plugins/morning-paper/.codex-plugin/plugin.json"))
    changelog = _read("CHANGELOG.md")
    readiness = _read("docs/product-readiness-0.8.md")
    roadmap = _read("ROADMAP.md")

    summary = _pyproject_field("description")
    version = _pyproject_field("version")
    assert summary.startswith("Own your algorithm")
    assert "personal newsroom" in summary
    assert "sources and preferences you own as files" in summary
    assert f"## [{version}]" in changelog
    assert "Friend-ready personal newsroom setup" in changelog
    assert f"Current live\nrelease: {version}" in readiness
    assert f"`morning-paper` {version} is live" in readiness
    assert f"same {version} semver" in readiness
    assert "## Shipped (`v0.8.x` friend-ready newsroom)" in roadmap

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
