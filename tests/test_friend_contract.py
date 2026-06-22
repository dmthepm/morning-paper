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

    cli_text = _read("src/morning_paper/cli.py")
    edition_workspace = _read("src/morning_paper/edition_workspace.py")
    assert "edition apply-feedback" in cli_text
    assert "def apply_feedback" in edition_workspace
    for route in ("voice", "prior", "checks", "the-read", "front-page", "reading"):
        assert route in edition_workspace
        assert route in cli_text


def test_package_and_plugin_descriptions_match_the_owned_algorithm_story() -> None:
    claude_manifest = json.loads(_read(".claude-plugin/plugin.json"))
    codex_manifest = json.loads(_read("plugins/morning-paper/.codex-plugin/plugin.json"))
    changelog = _read("CHANGELOG.md")
    readiness = _read("docs/product-readiness-0.8.md")
    roadmap = _read("ROADMAP.md")
    skill_suite = _read("docs/newsroom-skill-suite.md")
    install_smoke = _read("scripts/install_smoke.py")
    host_smoke = _read("scripts/host_plugin_smoke.py")
    setup_smoke = _read("scripts/setup_scaffold_smoke.py")
    codex_validator = _read("scripts/validate_codex_plugin.py")

    summary = _pyproject_field("description")
    version = _pyproject_field("version")
    assert summary.startswith("Own your algorithm")
    assert "personal newsroom" in summary
    assert "sources and preferences you own as files" in summary
    assert f"## [{version}]" in changelog
    assert "Friend-ready personal newsroom setup" in changelog
    assert f"Current release candidate: {version}" in readiness
    assert f"release candidate {version}" in readiness
    assert f"same {version} semver" in readiness
    assert "live 0.7.1 demo" not in readiness
    assert "historical live-host evidence" in readiness
    assert "## Shipped (`v0.8.x` friend-ready newsroom)" in roadmap
    assert "skills as newsroom desks" in readiness
    assert "Morning Paper skills are newsroom desks" in skill_suite
    assert "0.8.x ships exactly three plugin skills" in skill_suite
    assert "This section is a design direction, not shipped surface" in skill_suite
    assert "SHIPPED_SKILLS = (\"setup\", \"edition\", \"writing\")" in install_smoke
    assert "SHIPPED_SKILLS = (\"setup\", \"edition\", \"writing\")" in host_smoke
    assert "SHIPPED_SKILLS = (\"setup\", \"edition\", \"writing\")" in codex_validator
    assert "--isolated" in setup_smoke
    assert "setup_scaffold_smoke.py --isolated" in readiness
    assert "edition apply-feedback" in readiness
    for newsroom_file in ("EDITORIAL.md", "VISUALS.md", "SOURCES.md", "DELIVERY.md", "TASTELOG.md"):
        assert newsroom_file in skill_suite

    for manifest in (claude_manifest, codex_manifest):
        description = manifest["description"]
        assert manifest["version"] == version
        assert "personal newsroom" in description
        assert "preferences you own as files" in description


def test_chart_guardrails_are_current_work_not_future_roadmap() -> None:
    roadmap = _read("ROADMAP.md")
    composing = _read("docs/composing.md")
    spec = _read("docs/product-readiness-0.8.md")
    reviewers = _read("src/morning_paper/reviewers.py")

    assert "chart row/label bounds" not in roadmap
    assert "mp-bars` shows up to 12 rows" in composing
    assert "mp-stats`" in composing and "6 primary blocks" in composing
    assert "mp-spark`" in composing and "90 values" in composing
    assert "`visual-provenance`" in composing
    assert "check_visual_provenance" in reviewers
    assert "cap print" in spec
    assert "overflow notes" in spec


def test_current_facing_docs_do_not_center_old_starter_sources() -> None:
    current_docs = {
        "README.md": _read("README.md"),
        "AGENTS.md": _read("AGENTS.md"),
        "ROADMAP.md": _read("ROADMAP.md"),
        "docs/architecture-decisions.md": _read("docs/architecture-decisions.md"),
        "docs/collectors.md": _read("docs/collectors.md"),
        "docs/composing.md": _read("docs/composing.md"),
        "docs/product-readiness-0.8.md": _read("docs/product-readiness-0.8.md"),
        "plugins/morning-paper/skills/setup/SKILL.md": _read("plugins/morning-paper/skills/setup/SKILL.md"),
        "plugins/morning-paper/skills/edition/SKILL.md": _read("plugins/morning-paper/skills/edition/SKILL.md"),
        "src/morning_paper/cli.py": _read("src/morning_paper/cli.py"),
        "src/morning_paper/config.py": _read("src/morning_paper/config.py"),
        "src/morning_paper/sources.py": _read("src/morning_paper/sources.py"),
        "src/morning_paper/resources/demo.md": _read("src/morning_paper/resources/demo.md"),
    }
    forbidden = [
        "RSS and Hacker News",
        "starter inputs",
        "starter_inputs",
        "starter feeds",
        "starter config",
        "configured feeds",
        "customize feeds",
        "own feeds",
        "not the product identity",
        "without knowing what RSS",
        "automatic fallback",
        "auto-fallback",
    ]
    for path, text in current_docs.items():
        for phrase in forbidden:
            assert phrase not in text, f"{path} still contains stale framing: {phrase}"

    readme_sources = current_docs["README.md"].split("## Sources", 1)[1].split("## Daily Routine", 1)[0]
    for phrase in (
        "email newsletters",
        "Slack channels",
        "GitHub activity",
        "Linear tickets",
        "Twitter/X",
        "YouTube",
        "Obsidian vaults",
        "agent-generated reports",
    ):
        assert phrase in readme_sources


def test_recurrence_guidance_prefers_host_native_primitives() -> None:
    readme = _read("README.md")
    setup_skill = _read("plugins/morning-paper/skills/setup/SKILL.md")
    composing = _read("docs/composing.md")
    readiness = _read("docs/product-readiness-0.8.md")

    for text in (readme, setup_skill, composing, readiness):
        lowered = text.lower()
        assert "Codex automation" in text or "Codex: **automations**" in text
        assert "Claude Code routine" in text or "Claude Code: **routines**" in text
        assert "chatgpt" in lowered and "scheduled task" in lowered
        assert "local fallback" in text

    assert "Set up a Claude Code routine" in readme
    assert "Set up a Codex automation" in readme
    assert "Set up a scheduled task for my Morning Paper" in readme
    assert "/schedule" in readme
    assert "do not pretend you rendered the PDF" in readme
    assert "may not have access to project files" in readme
    assert "should not claim it rendered a local PDF" in composing
    assert "Codex automation environment" in setup_skill
    assert "with a schedule trigger" in setup_skill
    assert "/schedule" in setup_skill
    assert "project files" in setup_skill
    assert "Do not install a local scheduler unless they explicitly ask" in setup_skill


def test_remote_extraction_is_explicit_in_docs_and_release_artifacts() -> None:
    readme = _read("README.md")
    config = _read("src/morning_paper/config.py")
    article_print = _read("src/morning_paper/article_print.py")
    pyproject = _read("pyproject.toml")
    release_check = _read("scripts/release_candidate_check.py")
    changelog = _read("CHANGELOG.md")
    architecture = _read("docs/architecture-decisions.md")
    readiness = _read("docs/product-readiness-0.8.md")

    assert "Local extraction" in readme
    assert "keeps URL capture on your machine" in readme
    assert "remote readers or browser/API scrapes" in readme
    assert "explicit choices" in readme
    assert "remote_extractor_fallback: false" in config
    assert "allow_remote_fallback: bool = False" in article_print
    assert "Remote fallback is opt-in" in article_print
    assert '"trafilatura>=2.1,<3"' in pyproject
    assert "remote_extractor_fallback" in release_check
    assert "EXPECTED_DOCTOR_PACKAGES" in release_check
    assert '"trafilatura"' in release_check
    assert '"feedparser"' in release_check
    assert "`doctor --json` reports every core source/parser/render dependency version" in architecture
    assert "Trafilatura is currently the" in readiness
    assert "local article parser behind `article_extractor: local`" in readiness
    assert "`>=2.1,<3`" in readiness
    assert "no longer escalates" in changelog
    assert "Jina remote" in changelog
