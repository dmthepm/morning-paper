from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from importlib import import_module, resources
from pathlib import Path
from zoneinfo import ZoneInfo

from .article_print import fetch_article, render_article_markdown
from .builder import build_paper
from .config import DEFAULT_CONFIG_PATH, ConfigError, load_config, render_default_config
from .renderers import TypewriterRendererUnavailable, write_custom_markdown, _safe_filename


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
        print(
            "This command requires the private Morning Brief harness. "
            "Use `morning-paper init` and `morning-paper build` instead.",
            file=sys.stderr,
        )
        return 1
    cmd = [sys.executable, str(script), *args]
    return subprocess.call(cmd, cwd=REPO_ROOT)


def doctor() -> int:
    missing: list[str] = []
    required_modules = [
        "morning_paper.cli",
        "morning_paper.article_print",
        "morning_paper.builder",
        "morning_paper.config",
        "morning_paper.image_tools",
        "morning_paper.renderers",
        "morning_paper.sources",
    ]
    for module_name in required_modules:
        try:
            import_module(module_name)
        except Exception:
            missing.append(module_name)
    try:
        resource = resources.files("morning_paper").joinpath("resources", "typewriter.md")
        if not resource.is_file():
            missing.append("morning_paper/resources/typewriter.md")
    except Exception:
        missing.append("morning_paper/resources/typewriter.md")
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
    try:
        config = load_config(config_path)
    except ConfigError as exc:
        print(f"invalid config: {exc}", file=sys.stderr)
        return 1
    try:
        result = build_paper(config, date_str=date)
    except TypewriterRendererUnavailable as exc:
        print(str(exc), file=sys.stderr)
        return 1
    for warning in result.get("warnings", []):
        print(f"warning: {warning}", file=sys.stderr)
    print(json.dumps(result, indent=2))
    return 0


def print_command(args: list[str]) -> int:
    config_path = DEFAULT_CONFIG_PATH
    date = None
    title = None
    urls: list[str] = []
    index = 0
    while index < len(args):
        arg = args[index]
        if arg in {"-h", "--help"}:
            print("usage: morning-paper print <url> [<url> ...] [--config PATH] [--date YYYY-MM-DD] [--title TITLE]")
            return 0
        if arg == "--config" and index + 1 < len(args):
            config_path = Path(args[index + 1]).expanduser().resolve()
            index += 2
            continue
        if arg == "--date" and index + 1 < len(args):
            date = args[index + 1]
            index += 2
            continue
        if arg == "--title" and index + 1 < len(args):
            title = args[index + 1]
            index += 2
            continue
        urls.append(arg)
        index += 1
    if not urls:
        print("print requires at least one URL", file=sys.stderr)
        return 2
    if not config_path.exists():
        print(f"missing config: {config_path}", file=sys.stderr)
        print("run `morning-paper init` first or pass --config", file=sys.stderr)
        return 1
    try:
        config = load_config(config_path)
    except ConfigError as exc:
        print(f"invalid config: {exc}", file=sys.stderr)
        return 1
    articles = [fetch_article(url) for url in urls]
    target_date = date or datetime.now(ZoneInfo(config.timezone)).date().isoformat()
    bundle_title = title or articles[0].title
    slug = _safe_filename(bundle_title)[:48] or "article-print"
    try:
        outputs, warnings = write_custom_markdown(
            config,
            render_article_markdown(
                config,
                articles,
                date_str=target_date,
                images_dir=config.outputs.directory / target_date / slug / "_article_images",
            ),
            date_str=target_date,
            slug=slug,
            metadata={"mode": "print", "urls": urls, "article_count": len(articles)},
        )
    except TypewriterRendererUnavailable as exc:
        print(str(exc), file=sys.stderr)
        return 1
    for warning in warnings:
        print(f"warning: {warning}", file=sys.stderr)
    print(
        json.dumps(
            {
                "date": target_date,
                "mode": "print",
                "article_count": len(articles),
                "warnings": warnings,
                "outputs": {key: str(value) for key, value in outputs.items() if key != "dir"},
                "output_dir": str(outputs["dir"]),
            },
            indent=2,
        )
    )
    return 0


def smoke() -> int:
    script = REPO_ROOT / "scripts" / "smoke_test.sh"
    if not script.exists():
        print(
            "This command requires the private Morning Brief harness. "
            "Use `morning-paper init` and `morning-paper build` instead.",
            file=sys.stderr,
        )
        return 1
    return subprocess.call(["bash", str(script)], cwd=REPO_ROOT)


def print_help() -> int:
    commands = ", ".join(["init", "build", "print", *SCRIPT_MAP, "doctor", "smoke"])
    print("usage: morning-paper {" + commands + "} [args...]")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in {"-V", "--version", "version"}:
        from . import __version__

        print(__version__)
        return 0
    if not argv or argv[0] in {"-h", "--help", "help"}:
        return print_help()

    command, extra = argv[0], argv[1:]

    if command == "init":
        return init_command(extra)
    if command == "build":
        return build_command(extra)
    if command == "print":
        return print_command(extra)
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
