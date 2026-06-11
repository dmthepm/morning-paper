from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from importlib import import_module, resources
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

from .article_print import ArticleExtractionError, fetch_article, render_article_markdown
from .builder import build_paper
from .config import DEFAULT_CONFIG_PATH, ConfigError, MorningPaperConfig, load_config, render_default_config
from .renderers import TypewriterRendererUnavailable, _load_weasyprint, write_custom_markdown, _safe_filename
from .styles import PALETTES, STYLES, StyleError


DOCS_URL = "https://github.com/dmthepm/morning-paper"
ROADMAP_URL = f"{DOCS_URL}/blob/main/ROADMAP.md"
PYPI_JSON_URL = "https://pypi.org/pypi/morning-paper/json"
ROADMAP_COMMANDS = {"remove", "list"}
HELP_TEXT = f"""Morning Paper — your morning newspaper, built from your own sources.

Commands:
  demo              Print a sample edition right now — no config, no network
  init              Create a starter config
  build             Build today's paper from configured sources
  print <url>       Print a single article right now
  render <file.md>  Typeset any markdown file through a style pack
  stage <url|file>  Queue material for tomorrow's paper (returns a page estimate)
  queue             Show what's staged vs the page budget (JSON)
  estimate <file>   Page count for a markdown file, nothing written
  styles            List available styles and palettes
  doctor            Check config, dependencies, and renderer status
  --version         Show installed version

Agents: every command prints JSON. `stage` + `queue` are the seam for
"add this to tomorrow's brief" workflows. See docs/composing.md.

Config: {DEFAULT_CONFIG_PATH}
Docs:   {DOCS_URL}
"""


def _version_key(value: str) -> tuple[int, ...]:
    parts = re.findall(r"\d+", value or "")
    return tuple(int(part) for part in parts) or (0,)


def _fetch_latest_pypi_version() -> str | None:
    try:
        response = requests.get(PYPI_JSON_URL, timeout=2)
        response.raise_for_status()
        payload = response.json()
    except Exception:
        return None
    info = payload.get("info") if isinstance(payload, dict) else None
    version = info.get("version") if isinstance(info, dict) else None
    return str(version).strip() if version else None


def _print_update_notice() -> None:
    from . import __version__

    latest = _fetch_latest_pypi_version()
    if not latest or _version_key(latest) <= _version_key(__version__):
        return
    print(f"update available: {latest} (you have {__version__})")
    print("run: pip install --upgrade morning-paper")


def _pretty_install_hint_lines() -> list[str]:
    lines = ['recommended install: pip install "morning-paper[pretty]"']
    if sys.platform == "darwin":
        lines.append("macOS may also need: brew install pango gdk-pixbuf")
    elif sys.platform.startswith("linux"):
        lines.append("Linux may also need system libraries for WeasyPrint (for example pango/cairo packages)")
    elif sys.platform.startswith("win"):
        lines.append("Windows typewriter support is best-effort today; portable mode is more reliable")
    return lines


def doctor() -> int:
    missing: list[str] = []
    required_modules = [
        "morning_paper.cli",
        "morning_paper.article_print",
        "morning_paper.builder",
        "morning_paper.config",
        "morning_paper.extractors",
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
    _, renderer_error = _load_weasyprint()
    if renderer_error:
        print("doctor: ok")
        print("renderer: typewriter unavailable")
        print("status: fallback-only install; high-quality print output is not available yet")
        for line in _pretty_install_hint_lines():
            print(line)
        _print_update_notice()
        return 0
    print("doctor: ok")
    print("renderer: typewriter ready")
    print("status: high-quality print path available")
    _print_update_notice()
    return 0


def demo_command(args: list[str]) -> int:
    usage = "usage: morning-paper demo"
    for arg in args:
        if arg in {"-h", "--help"}:
            print(usage)
            return 0
        print(f"unknown demo argument: {arg}", file=sys.stderr)
        return 2
    _, renderer_error = _load_weasyprint()
    if renderer_error:
        print("demo needs the pretty print stack (WeasyPrint) to typeset the sample edition", file=sys.stderr)
        for line in _pretty_install_hint_lines():
            print(line, file=sys.stderr)
        print("then run `morning-paper doctor` to confirm the renderer is ready", file=sys.stderr)
        return 1
    markdown_text = resources.files("morning_paper").joinpath("resources", "demo.md").read_text(encoding="utf-8")
    config = MorningPaperConfig()
    config.outputs.style = "editorial"
    config.outputs.palette = "color"
    config.outputs.html = True
    config.outputs.pdf = True
    target_date = datetime.now(ZoneInfo(config.timezone)).date().isoformat()
    try:
        outputs, warnings = write_custom_markdown(
            config,
            markdown_text,
            date_str=target_date,
            slug="demo",
            metadata={"mode": "demo", "style": "editorial", "palette": "color"},
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
                "mode": "demo",
                "style": "editorial",
                "palette": "color",
                "warnings": warnings,
                "outputs": {key: str(value) for key, value in outputs.items() if key != "dir"},
                "output_dir": str(outputs["dir"]),
            },
            indent=2,
        )
    )
    print(f"Print it: lp {outputs['pdf']}")
    print("Make it yours: morning-paper init (or run the setup skill in Claude Code)")
    print("Post your paper: https://github.com/dmthepm/morning-paper/discussions")
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


def _load_print_config(config_path: Path) -> tuple[MorningPaperConfig, bool]:
    if config_path.exists():
        return load_config(config_path), True
    return MorningPaperConfig(), False


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
    try:
        config, has_user_config = _load_print_config(config_path)
    except ConfigError as exc:
        print(f"invalid config: {exc}", file=sys.stderr)
        return 1
    if not has_user_config:
        print("using built-in defaults for one-off print", file=sys.stderr)
        print("run `morning-paper init` to customize feeds, timezone, and output paths", file=sys.stderr)
    try:
        articles = [fetch_article(url, extractor_name=config.article_extractor) for url in urls]
    except ArticleExtractionError as exc:
        print(str(exc), file=sys.stderr)
        return 1
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


def styles_command() -> int:
    listing = {
        "styles": {name: pack.description for name, pack in sorted(STYLES.items())},
        "palettes": {name: pal.description for name, pal in sorted(PALETTES.items())},
    }
    print(json.dumps(listing, indent=2))
    return 0


def render_command(args: list[str]) -> int:
    config_path = DEFAULT_CONFIG_PATH
    date = None
    slug = None
    style = None
    palette = None
    source: Path | None = None
    index = 0
    usage = "usage: morning-paper render <file.md> [--style NAME] [--palette NAME] [--date YYYY-MM-DD] [--slug NAME] [--config PATH]"
    while index < len(args):
        arg = args[index]
        if arg in {"-h", "--help"}:
            print(usage)
            return 0
        if arg == "--config" and index + 1 < len(args):
            config_path = Path(args[index + 1]).expanduser().resolve()
            index += 2
            continue
        if arg == "--date" and index + 1 < len(args):
            date = args[index + 1]
            index += 2
            continue
        if arg == "--slug" and index + 1 < len(args):
            slug = args[index + 1]
            index += 2
            continue
        if arg == "--style" and index + 1 < len(args):
            style = args[index + 1]
            index += 2
            continue
        if arg == "--palette" and index + 1 < len(args):
            palette = args[index + 1]
            index += 2
            continue
        if arg.startswith("-"):
            print(f"unknown render argument: {arg}", file=sys.stderr)
            return 2
        if source is not None:
            print("render takes exactly one markdown file", file=sys.stderr)
            return 2
        source = Path(arg).expanduser()
        index += 1
    if source is None:
        print(usage, file=sys.stderr)
        return 2
    if not source.is_file():
        print(f"no such file: {source}", file=sys.stderr)
        return 1
    try:
        config, has_user_config = _load_print_config(config_path)
    except ConfigError as exc:
        print(f"invalid config: {exc}", file=sys.stderr)
        return 1
    if not has_user_config:
        print("using built-in defaults (run `morning-paper init` to customize)", file=sys.stderr)
    if style:
        config.outputs.style = style
    if palette:
        config.outputs.palette = palette
    # render exists to typeset: always produce html+pdf regardless of the
    # build-pipeline output toggles in config
    config.outputs.html = True
    config.outputs.pdf = True
    markdown_text = source.read_text(encoding="utf-8")
    target_date = date or datetime.now(ZoneInfo(config.timezone)).date().isoformat()
    target_slug = _safe_filename(slug or source.stem)[:48] or "render"
    try:
        outputs, warnings = write_custom_markdown(
            config,
            markdown_text,
            date_str=target_date,
            slug=target_slug,
            metadata={
                "mode": "render",
                "source": str(source),
                "style": config.outputs.style,
                "palette": config.outputs.palette,
            },
        )
    except StyleError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except TypewriterRendererUnavailable as exc:
        print(str(exc), file=sys.stderr)
        return 1
    for warning in warnings:
        print(f"warning: {warning}", file=sys.stderr)
    print(
        json.dumps(
            {
                "date": target_date,
                "mode": "render",
                "style": config.outputs.style,
                "palette": config.outputs.palette,
                "warnings": warnings,
                "outputs": {key: str(value) for key, value in outputs.items() if key != "dir"},
                "output_dir": str(outputs["dir"]),
            },
            indent=2,
        )
    )
    return 0


def _parse_common(args: list[str], usage: str) -> tuple[Path, str | None, list[str]] | int:
    config_path = DEFAULT_CONFIG_PATH
    date = None
    rest: list[str] = []
    index = 0
    while index < len(args):
        arg = args[index]
        if arg in {"-h", "--help"}:
            print(usage)
            return 0
        if arg == "--config" and index + 1 < len(args):
            config_path = Path(args[index + 1]).expanduser().resolve()
            index += 2
            continue
        if arg == "--date" and index + 1 < len(args):
            date = args[index + 1]
            index += 2
            continue
        rest.append(arg)
        index += 1
    return config_path, date, rest


def stage_command(args: list[str]) -> int:
    from .staging import default_edition_date, stage_markdown

    usage = "usage: morning-paper stage <url|file.md> [--title T] [--date YYYY-MM-DD] [--config PATH]"
    title_override = None
    if "--title" in args:
        i = args.index("--title")
        if i + 1 < len(args):
            title_override = args[i + 1]
            args = args[:i] + args[i + 2 :]
    parsed = _parse_common(args, usage)
    if isinstance(parsed, int):
        return parsed
    config_path, date, rest = parsed
    if len(rest) != 1:
        print(usage, file=sys.stderr)
        return 2
    target = rest[0]
    try:
        config, _ = _load_print_config(config_path)
    except ConfigError as exc:
        print(f"invalid config: {exc}", file=sys.stderr)
        return 1
    date_str = date or default_edition_date(config)
    if target.startswith("http://") or target.startswith("https://"):
        try:
            article = fetch_article(target, extractor_name=config.article_extractor)
        except ArticleExtractionError as exc:
            print(json.dumps({"staged": False, "error": str(exc)}, indent=2))
            return 1
        markdown = render_article_markdown(
            config,
            [article],
            date_str=date_str,
            images_dir=config.outputs.directory / "staging" / date_str / "_images",
        )
        item = stage_markdown(
            config, markdown, date_str=date_str, kind="url", source=target,
            title=title_override or article.title,
        )
    else:
        source = Path(target).expanduser()
        if not source.is_file():
            print(f"no such file: {source}", file=sys.stderr)
            return 1
        item = stage_markdown(
            config, source.read_text(encoding="utf-8"), date_str=date_str,
            kind="file", source=str(source), title=title_override or source.stem,
        )
    from dataclasses import asdict

    payload = {"staged": True, "edition_date": date_str, **asdict(item)}
    print(json.dumps(payload, indent=2))
    return 0


def queue_command(args: list[str]) -> int:
    from .staging import default_edition_date, queue_status

    usage = "usage: morning-paper queue [--date YYYY-MM-DD] [--config PATH]"
    parsed = _parse_common(args, usage)
    if isinstance(parsed, int):
        return parsed
    config_path, date, rest = parsed
    if rest:
        print(usage, file=sys.stderr)
        return 2
    try:
        config, _ = _load_print_config(config_path)
    except ConfigError as exc:
        print(f"invalid config: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(queue_status(config, date or default_edition_date(config)), indent=2))
    return 0


def estimate_command(args: list[str]) -> int:
    from .renderers import count_pages

    usage = "usage: morning-paper estimate <file.md> [--style NAME] [--palette NAME] [--config PATH]"
    style = palette = None
    for flag in ("--style", "--palette"):
        if flag in args:
            i = args.index(flag)
            if i + 1 < len(args):
                value = args[i + 1]
                args = args[:i] + args[i + 2 :]
                if flag == "--style":
                    style = value
                else:
                    palette = value
    parsed = _parse_common(args, usage)
    if isinstance(parsed, int):
        return parsed
    config_path, _date, rest = parsed
    if len(rest) != 1:
        print(usage, file=sys.stderr)
        return 2
    source = Path(rest[0]).expanduser()
    if not source.is_file():
        print(f"no such file: {source}", file=sys.stderr)
        return 1
    try:
        config, _ = _load_print_config(config_path)
    except ConfigError as exc:
        print(f"invalid config: {exc}", file=sys.stderr)
        return 1
    markdown = source.read_text(encoding="utf-8")
    try:
        pages = count_pages(
            markdown,
            style=style or config.outputs.style,
            palette=palette or config.outputs.palette,
        )
    except StyleError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"estimate requires the pretty print stack: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"file": str(source), "words": len(markdown.split()), "est_pages": pages}, indent=2))
    return 0


def print_help() -> int:
    print(HELP_TEXT.rstrip())
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

    if command == "demo":
        return demo_command(extra)
    if command == "init":
        return init_command(extra)
    if command == "build":
        return build_command(extra)
    if command == "print":
        return print_command(extra)
    if command == "render":
        return render_command(extra)
    if command in {"stage", "add"}:
        return stage_command(extra)
    if command in {"queue", "status"}:
        return queue_command(extra)
    if command == "estimate":
        return estimate_command(extra)
    if command == "styles":
        return styles_command()
    if command == "doctor":
        return doctor()
    if command in ROADMAP_COMMANDS:
        print(f'"{command}" is planned for v0.2. See {ROADMAP_URL}', file=sys.stderr)
        return 2
    print(f"unknown command: {command}", file=sys.stderr)
    print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
