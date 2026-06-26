#!/usr/bin/env python3
"""Structurally validate the Codex plugin + marketplace surface.

Mirrors the public plugin contract so CI catches drift without needing a host
runtime installed on the runner:

- ``plugins/morning-paper/.codex-plugin/plugin.json`` exists, is a JSON object,
  carries real ``name`` / ``version`` (strict semver) / ``description`` /
  ``author.name`` and a required ``interface`` block, declares no rejected field
  (notably ``hooks``), and resolves ``skills`` to ``skills`` inside the plugin
  root.
- the 0.8.x plugin exposes exactly the shipped ``setup`` / ``edition`` /
  ``writing`` skills, and every ``skills/<name>/SKILL.md`` opens with YAML
  frontmatter carrying a non-empty ``name`` and ``description``.
- ``.agents/plugins/marketplace.json`` names the plugin, points its source at a
  real subdirectory (never the marketplace root), and carries the policy and
  category every entry needs.

Usage: ``python3 scripts/validate_codex_plugin.py`` (run from the repo root).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*)(?:\.(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*))*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)

ALLOWED_MANIFEST_KEYS = {
    "id", "name", "version", "description", "skills", "apps",
    "mcpServers", "interface", "author", "homepage", "repository",
    "license", "keywords",
}
REQUIRED_INTERFACE_STRINGS = (
    "displayName", "shortDescription", "longDescription",
    "developerName", "category",
)
SHIPPED_SKILLS = ("setup", "edition", "writing")


def _load(path: Path, errors: list[str]) -> dict | None:
    if not path.is_file():
        errors.append(f"missing `{path}`")
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"`{path}` is not valid JSON: {exc}")
        return None
    if not isinstance(payload, dict):
        errors.append(f"`{path}` must contain a JSON object")
        return None
    return payload


def validate_manifest(plugin_root: Path, errors: list[str]) -> None:
    manifest = _load(plugin_root / ".codex-plugin" / "plugin.json", errors)
    if manifest is None:
        return

    for key in sorted(set(manifest) - ALLOWED_MANIFEST_KEYS):
        errors.append(f"manifest field `{key}` is not accepted by Codex validation")
    if "hooks" in manifest:
        errors.append("manifest declares `hooks`, which Codex rejects")

    for key in ("name", "description"):
        if not isinstance(manifest.get(key), str) or not manifest[key].strip():
            errors.append(f"manifest field `{key}` must be a non-empty string")
    version = manifest.get("version")
    if not isinstance(version, str) or SEMVER_RE.fullmatch(version) is None:
        errors.append("manifest field `version` must be strict semver")

    author = manifest.get("author")
    if not isinstance(author, dict) or not isinstance(author.get("name"), str) or not author["name"].strip():
        errors.append("manifest field `author.name` must be a non-empty string")

    skills = manifest.get("skills")
    if skills is not None:
        normalized = Path(skills).as_posix().rstrip("/") if isinstance(skills, str) else None
        if normalized != "skills" or Path(skills).is_absolute():
            errors.append("manifest field `skills` must resolve to `skills`")

    interface = manifest.get("interface")
    if not isinstance(interface, dict):
        errors.append("manifest field `interface` must be an object")
    else:
        for field in REQUIRED_INTERFACE_STRINGS:
            if not isinstance(interface.get(field), str) or not interface[field].strip():
                errors.append(f"manifest field `interface.{field}` must be a non-empty string")
        if "defaultPrompt" not in interface and "default_prompt" not in interface:
            errors.append("manifest field `interface.defaultPrompt` is required")
        caps = interface.get("capabilities")
        if not isinstance(caps, list) or not caps or not all(isinstance(c, str) and c.strip() for c in caps):
            errors.append("manifest field `interface.capabilities` must be a non-empty array of strings")
        for field in ("websiteURL", "privacyPolicyURL", "termsOfServiceURL"):
            value = interface.get(field)
            if value is not None and (not isinstance(value, str) or not value.startswith("https://")):
                errors.append(f"manifest field `interface.{field}` must be an absolute https URL")


def validate_skills(plugin_root: Path, errors: list[str]) -> None:
    skills_root = plugin_root / "skills"
    if not skills_root.is_dir():
        errors.append(f"missing skills directory `{skills_root}`")
        return
    found = []
    for skill_dir in sorted(skills_root.iterdir()):
        if skill_dir.name.startswith(".") or not skill_dir.is_dir():
            continue
        found.append(skill_dir.name)
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            errors.append(f"skill `{skill_dir.name}` is missing SKILL.md")
            continue
        text = skill_md.read_text(encoding="utf-8")
        if not text.startswith("---\n"):
            errors.append(f"skill `{skill_dir.name}` must open with YAML frontmatter")
            continue
        end = text.find("\n---", 4)
        if end == -1:
            errors.append(f"skill `{skill_dir.name}` frontmatter is not closed")
            continue
        front = text[4:end]
        if not re.search(r"^name:\s*\S", front, re.MULTILINE):
            errors.append(f"skill `{skill_dir.name}` frontmatter needs a non-empty `name`")
        if not re.search(r"^description:\s*\S|^description:\s*>", front, re.MULTILINE):
            errors.append(f"skill `{skill_dir.name}` frontmatter needs a non-empty `description`")
    if found != sorted(SHIPPED_SKILLS):
        errors.append(
            "shipped skill set changed without updating the Codex plugin contract "
            f"(expected {sorted(SHIPPED_SKILLS)}, found {found})"
        )
    for required in SHIPPED_SKILLS:
        if required not in found:
            errors.append(f"expected skill `{required}` not found under {skills_root}")


def validate_marketplace(repo_root: Path, plugin_root: Path, errors: list[str]) -> None:
    market = _load(repo_root / ".agents" / "plugins" / "marketplace.json", errors)
    if market is None:
        return
    if not isinstance(market.get("name"), str) or not market["name"].strip():
        errors.append("marketplace field `name` must be a non-empty string")
    plugins = market.get("plugins")
    if not isinstance(plugins, list) or not plugins:
        errors.append("marketplace field `plugins` must be a non-empty array")
        return
    entry = next((p for p in plugins if isinstance(p, dict) and p.get("name") == "morning-paper"), None)
    if entry is None:
        errors.append("marketplace has no `morning-paper` plugin entry")
        return
    source = entry.get("source")
    if not isinstance(source, dict) or source.get("source") != "local":
        errors.append("marketplace entry `source.source` must be `local`")
    path = source.get("path") if isinstance(source, dict) else None
    if path in (None, "", "./", "."):
        errors.append("marketplace entry `source.path` must point at a real subdirectory, not the root")
    elif not (repo_root / path).resolve().is_dir():
        errors.append(f"marketplace entry `source.path` `{path}` is not a directory")
    elif (repo_root / path).resolve() != plugin_root.resolve():
        errors.append("marketplace entry `source.path` must point at the plugin root")
    policy = entry.get("policy")
    if not isinstance(policy, dict) or policy.get("installation") not in {"AVAILABLE", "INSTALLED_BY_DEFAULT", "NOT_AVAILABLE"}:
        errors.append("marketplace entry `policy.installation` is missing or invalid")
    if not isinstance(policy, dict) or policy.get("authentication") not in {"ON_INSTALL", "ON_USE"}:
        errors.append("marketplace entry `policy.authentication` is missing or invalid")
    if not isinstance(entry.get("category"), str) or not entry["category"].strip():
        errors.append("marketplace entry `category` must be a non-empty string")


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    plugin_root = repo_root / "plugins" / "morning-paper"
    errors: list[str] = []
    validate_manifest(plugin_root, errors)
    validate_skills(plugin_root, errors)
    validate_marketplace(repo_root, plugin_root, errors)
    if errors:
        print("Codex plugin validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Codex plugin validation passed: {plugin_root}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
