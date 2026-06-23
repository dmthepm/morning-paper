#!/usr/bin/env python3
"""Build and verify Morning Paper release artifacts from a clean source copy.

This avoids a real footgun: an in-place ``python -m build`` can reuse an ignored
``build/`` directory and copy stale generated files into the wheel. The release
path should build from a sanitized source copy, then prove the produced wheel
and sdist install and print.

Usage:
  python scripts/release_candidate_check.py --outdir dist --install-check
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import venv
import zipfile
from pathlib import Path


EXCLUDED_NAMES = {
    ".git",
    ".claude",
    ".codex",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "htmlcov",
}
EXCLUDED_SUFFIXES = (".egg-info",)
EXPECTED_MODULES = (
    "morning_paper/newsroom.py",
    "morning_paper/edition_workspace.py",
    "morning_paper/config.py",
    "morning_paper/article_print.py",
    "morning_paper/page_count_worker.py",
)
EXPECTED_SNIPPETS = {
    "morning_paper/edition_workspace.py": (
        "feedback_plan_template",
        "feedback-plan.md",
        "Applied Feedback",
        "final_editor_pass",
        "final-editor.json",
        "def apply_feedback",
    ),
    "morning_paper/newsroom.py": ("Work streams", "Personal feeds", "feedback-plan.md", "CONVERTERS.md"),
    "morning_paper/config.py": ("remote_extractor_fallback", "remote_extractor_fallback: false"),
    "morning_paper/article_print.py": ("allow_remote_fallback", "Remote fallback is opt-in"),
}
STALE_RESOURCE_MARKERS = ("typewriter.md", "typewriter-v5.md")
EXPECTED_DOCTOR_PACKAGES = (
    "feedparser",
    "fpdf2",
    "markdown-it-py",
    "Pillow",
    "PyYAML",
    "requests",
    "trafilatura",
    "weasyprint",
    "tinycss2",
    "cssselect2",
    "pydyf",
    "cffi",
    "fontTools",
)


def _ignore(_dir: str, names: list[str]) -> set[str]:
    ignored = set()
    for name in names:
        if name in EXCLUDED_NAMES or name.endswith(EXCLUDED_SUFFIXES):
            ignored.add(name)
    return ignored


def _run(
    cmd: list[str],
    *,
    cwd: Path | None = None,
    merge_stderr: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT if merge_stderr else subprocess.PIPE,
        check=False,
    )


def _require_ok(label: str, result: subprocess.CompletedProcess[str]) -> None:
    if result.returncode != 0:
        output = (result.stdout or "") + (("\n" + result.stderr) if result.stderr else "")
        raise RuntimeError(f"{label} failed with exit {result.returncode}:\n{output}")


def _project_version(repo: Path) -> str:
    text = (repo / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not match:
        raise RuntimeError("pyproject.toml has no project version")
    return match.group(1)


def _module_version(repo: Path) -> str:
    text = (repo / "src" / "morning_paper" / "__init__.py").read_text(encoding="utf-8")
    match = re.search(r'^__version__\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not match:
        raise RuntimeError("src/morning_paper/__init__.py has no __version__")
    return match.group(1)


def _json_version(path: Path) -> str:
    payload = json.loads(path.read_text(encoding="utf-8"))
    version = payload.get("version")
    if not isinstance(version, str) or not version:
        raise RuntimeError(f"{path} has no JSON version")
    return version


def _validate_repo_versions(repo: Path, version: str) -> dict[str, str]:
    versions = {
        "pyproject": version,
        "module": _module_version(repo),
        "claude_manifest": _json_version(repo / ".claude-plugin" / "plugin.json"),
        "codex_manifest": _json_version(repo / "plugins" / "morning-paper" / ".codex-plugin" / "plugin.json"),
    }
    mismatched = {name: value for name, value in versions.items() if value != version}
    if mismatched:
        raise RuntimeError(f"version drift: expected {version}, got {mismatched}")
    changelog = (repo / "CHANGELOG.md").read_text(encoding="utf-8")
    if f"## [{version}]" not in changelog:
        raise RuntimeError(f"CHANGELOG.md has no entry for {version}")
    return versions


def _copy_clean_source(repo: Path, temp_root: Path) -> Path:
    source = temp_root / "source"
    shutil.copytree(repo, source, ignore=_ignore)
    return source


def _build(source: Path, outdir: Path) -> tuple[Path, Path]:
    outdir.mkdir(parents=True, exist_ok=True)
    result = _run([sys.executable, "-m", "build", "--sdist", "--wheel", "--outdir", str(outdir), str(source)])
    _require_ok("artifact build", result)
    wheels = sorted(outdir.glob("morning_paper-*.whl"))
    sdists = sorted(outdir.glob("morning_paper-*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        raise RuntimeError(f"expected one wheel and one sdist in {outdir}, got {wheels} / {sdists}")
    return wheels[0], sdists[0]


def _inspect_wheel(wheel: Path, version: str) -> dict[str, object]:
    with zipfile.ZipFile(wheel) as zf:
        names = sorted(zf.namelist())
        metadata_name = f"morning_paper-{version}.dist-info/METADATA"
        metadata = zf.read(metadata_name).decode("utf-8") if metadata_name in names else ""
        module_text = {
            module: zf.read(module).decode("utf-8") if module in names else ""
            for module in EXPECTED_SNIPPETS
        }

    errors: list[str] = []
    if f"Version: {version}" not in metadata:
        errors.append("wheel metadata version mismatch")
    for module in EXPECTED_MODULES:
        if module not in names:
            errors.append(f"wheel missing {module}")
    for module, snippets in EXPECTED_SNIPPETS.items():
        text = module_text.get(module, "")
        for snippet in snippets:
            if snippet not in text:
                errors.append(f"wheel `{module}` missing expected snippet `{snippet}`")
    stale = [name for name in names if any(marker in name for marker in STALE_RESOURCE_MARKERS)]
    if stale:
        errors.append(f"wheel contains stale resources: {stale}")
    dev_debris = [
        name
        for name in names
        if any(part in EXCLUDED_NAMES for part in Path(name).parts) or name.endswith(EXCLUDED_SUFFIXES)
    ]
    if dev_debris:
        errors.append(f"wheel contains dev debris: {dev_debris[:10]}")
    if errors:
        raise RuntimeError("; ".join(errors))
    return {
        "wheel": str(wheel),
        "size": wheel.stat().st_size,
        "module_count": len([name for name in names if name.endswith(".py")]),
        "stale_resources": stale,
    }


def _inspect_sdist(sdist: Path, version: str) -> dict[str, object]:
    errors: list[str] = []
    expected_prefix = f"morning_paper-{version}/"
    with tarfile.open(sdist, "r:gz") as tf:
        names = sorted(tf.getnames())
        payload_names = [name for name in names if name and name != "pax_global_header"]
        root_name = expected_prefix.rstrip("/")
        if not all(name == root_name or name.startswith(expected_prefix) for name in payload_names):
            errors.append("sdist root directory does not match package version")
        required = [
            f"{expected_prefix}pyproject.toml",
            f"{expected_prefix}README.md",
            f"{expected_prefix}LICENSE",
            f"{expected_prefix}docs/source-conversion.md",
        ]
        for name in required:
            if name not in names:
                errors.append(f"sdist missing {name}")
        for module, snippets in EXPECTED_SNIPPETS.items():
            member_name = f"{expected_prefix}src/{module}"
            try:
                member = tf.extractfile(member_name)
                text = member.read().decode("utf-8") if member else ""
            except KeyError:
                errors.append(f"sdist missing {member_name}")
                continue
            for snippet in snippets:
                if snippet not in text:
                    errors.append(f"sdist `{module}` missing expected snippet `{snippet}`")
    if errors:
        raise RuntimeError("; ".join(errors))
    return {"path": str(sdist), "size": sdist.stat().st_size}


def _venv_python(root: Path) -> Path:
    if sys.platform.startswith("win"):
        return root / "Scripts" / "python.exe"
    return root / "bin" / "python"


def _venv_script(root: Path, name: str) -> Path:
    if sys.platform.startswith("win"):
        return root / "Scripts" / f"{name}.exe"
    return root / "bin" / name


def _install_and_print(artifact: Path, version: str, temp_root: Path) -> dict[str, object]:
    env_root = temp_root / f"venv-{artifact.suffix.replace('.', '')}-{artifact.name[:12]}"
    venv.EnvBuilder(with_pip=True).create(env_root)
    python = _venv_python(env_root)
    morning_paper = _venv_script(env_root, "morning-paper")

    _require_ok("upgrade pip", _run([str(python), "-m", "pip", "install", "--upgrade", "pip"]))
    _require_ok("install artifact", _run([str(python), "-m", "pip", "install", f"{artifact}[pretty]"]))

    version_result = _run([str(morning_paper), "--version"])
    _require_ok("version check", version_result)
    actual_version = version_result.stdout.strip()
    if actual_version != version:
        raise RuntimeError(f"{artifact.name}: expected version {version}, got {actual_version}")

    doctor_result = _run([str(morning_paper), "doctor", "--strict", "--json"], merge_stderr=False)
    _require_ok("doctor strict", doctor_result)
    doctor = json.loads(doctor_result.stdout)
    if doctor.get("status") != "ok":
        raise RuntimeError(f"{artifact.name}: doctor status was {doctor.get('status')}")
    packages = doctor.get("dependencies", {}).get("packages", {})
    missing_packages = [name for name in EXPECTED_DOCTOR_PACKAGES if not packages.get(name)]
    if missing_packages:
        raise RuntimeError(f"{artifact.name}: doctor did not report dependency versions for {missing_packages}")
    render_self_test = doctor.get("renderer", {}).get("render_self_test", {})
    if not render_self_test.get("ok"):
        raise RuntimeError(f"{artifact.name}: render self-test failed: {render_self_test}")

    pdf = temp_root / f"{artifact.name}.demo.pdf"
    demo_result = _run([str(morning_paper), "demo", "--output", str(pdf)], merge_stderr=False)
    _require_ok("demo render", demo_result)
    demo = json.loads(demo_result.stdout)
    output_pdf = Path(demo["outputs"]["pdf"])
    if not output_pdf.is_file() or output_pdf.stat().st_size <= 0:
        raise RuntimeError(f"{artifact.name}: demo PDF missing or empty: {output_pdf}")
    if output_pdf.read_bytes()[:5] != b"%PDF-":
        raise RuntimeError(f"{artifact.name}: demo output is not a PDF: {output_pdf}")

    return {
        "artifact": artifact.name,
        "version": actual_version,
        "doctor_status": doctor.get("status"),
        "dependencies": {name: packages.get(name) for name in EXPECTED_DOCTOR_PACKAGES},
        "weasyprint": packages.get("weasyprint"),
        "render_self_test": render_self_test,
        "demo_pages": demo.get("pages"),
        "demo_pdf": str(output_pdf),
        "demo_pdf_size": output_pdf.stat().st_size,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=Path(__file__).resolve().parent.parent, type=Path)
    parser.add_argument("--outdir", default=Path("dist"), type=Path)
    parser.add_argument("--install-check", action="store_true", help="install wheel and sdist with [pretty] and print")
    parser.add_argument("--keep-temp", action="store_true", help="keep the sanitized source and install venvs")
    args = parser.parse_args()

    repo = args.repo.resolve()
    outdir = args.outdir.resolve()
    version = _project_version(repo)
    versions = _validate_repo_versions(repo, version)

    with tempfile.TemporaryDirectory(prefix="morning-paper-release-check-") as temp:
        temp_root = Path(temp)
        source = _copy_clean_source(repo, temp_root)
        wheel, sdist = _build(source, outdir)
        summary: dict[str, object] = {
            "ok": True,
            "version": version,
            "versions": versions,
            "source": str(source),
            "outdir": str(outdir),
            "wheel": _inspect_wheel(wheel, version),
            "sdist": _inspect_sdist(sdist, version),
        }
        if args.install_check:
            summary["install_checks"] = [
                _install_and_print(wheel, version, temp_root),
                _install_and_print(sdist, version, temp_root),
            ]
        if args.keep_temp:
            kept = Path(tempfile.mkdtemp(prefix="morning-paper-release-kept-"))
            shutil.copytree(temp_root, kept / "run")
            summary["kept_temp"] = str(kept / "run")
        print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001 - release checks should fail plainly.
        print(f"release-candidate check failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
