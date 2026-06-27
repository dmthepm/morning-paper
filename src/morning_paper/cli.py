from __future__ import annotations

import json
import platform
import re
import shutil
import subprocess
import sys
from datetime import datetime
from importlib import metadata
from importlib import import_module, resources
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

from .article_print import (
    ArticleExtractionError,
    article_truncation_warning,
    fetch_article,
    render_article_markdown,
)
from .config import DEFAULT_CONFIG_PATH, ConfigError, MorningPaperConfig, load_config, render_default_config
from .renderers import (
    TypewriterRendererUnavailable,
    _load_weasyprint,
    count_pages,
    _safe_filename,
    document_uses_custom_css,
    write_custom_markdown,
)
from .styles import PALETTES, STYLES, StyleError


DOCS_URL = "https://github.com/dmthepm/morning-paper"
PYPI_JSON_URL = "https://pypi.org/pypi/morning-paper/json"
SUPPORTED_WEASYPRINT_RANGE = ">=69.0,<70"
_SUPPORTED_WEASYPRINT_MIN = (69, 0, 0)
_SUPPORTED_WEASYPRINT_MAX = (70, 0, 0)
HELP_TEXT = f"""Morning Paper — your morning newspaper, built from your own sources.

Commands:
  demo              Print a sample edition right now — no config, no network
  init              Create a local config
  newsroom          Scaffold/update a private newsroom repo (init|state)
  sources           List or check configured sources and collector contract
  print <url>       Print a single article right now
  render <file.md>  Typeset any markdown file through a style pack
  stage <url|file>  Add source material to tomorrow's Assignment Board
                    (returns a page estimate)
  stage-social <record.json>
                    Add a complete social source record to tomorrow's Assignment Board
  inbox             Poll the contributor inbox: mail from your masthead becomes
                    source material for tomorrow's edition (--dry-run)
  queue             Show/list/read/remove Assignment Board items
  edition           Prepare/proof/apply durable edition files
                    (prepare|assignment-board|estimate|visual-qa|final-editor|
                    status|apply-feedback)
  estimate <file>   Page count for a markdown file, nothing written
  review <edition>  Editorial QC on a finished edition — warnings, never fails
                    (--json, --strict, --verbose, --explain CHECK)
  styles            List available styles and palettes
  routine           Optional local fallback scheduler (install [--time HH:MM]
                    [--command CMD] [--workdir PATH] | status | uninstall) —
                    launchd/systemd/cron; the run starts in the directory you
                    install from (your newsroom)
  doctor            Check config, dependencies, and renderer status (--json, --strict)
  --version         Show installed version

Agents: every command prints JSON (`doctor` via `--json`; `--version` prints
the bare version). `newsroom init` creates the private file contract; `edition
prepare` creates compaction-safe edition files; `edition final-editor` proves
the paper is ready to ship; `edition apply-feedback` records reader notes into
durable taste; `sources` inventories configured sources; `stage`, `stage-social`,
and `queue` are compatibility commands for adding source material to tomorrow's
Assignment Board.
See docs/composing.md.

Config: {DEFAULT_CONFIG_PATH}
Docs:   {DOCS_URL}
"""


def _version_key(value: str) -> tuple[int, ...]:
    parts = re.findall(r"\d+", value or "")
    return tuple(int(part) for part in parts) or (0,)


def _version_tuple(value: str | None) -> tuple[int, int, int]:
    parts = list(_version_key(value or "0"))[:3]
    while len(parts) < 3:
        parts.append(0)
    major, minor, patch = parts
    return major, minor, patch


def _weasyprint_support_report(version: str | None) -> dict[str, object]:
    if not version:
        return {
            "version": None,
            "supported": False,
            "requires": SUPPORTED_WEASYPRINT_RANGE,
            "error": f"WeasyPrint is not installed; install morning-paper[pretty] ({SUPPORTED_WEASYPRINT_RANGE})",
        }
    parsed = _version_tuple(version)
    supported = _SUPPORTED_WEASYPRINT_MIN <= parsed < _SUPPORTED_WEASYPRINT_MAX
    return {
        "version": version,
        "supported": supported,
        "requires": SUPPORTED_WEASYPRINT_RANGE,
        "error": ""
        if supported
        else f"installed WeasyPrint {version} is outside supported range {SUPPORTED_WEASYPRINT_RANGE}",
    }


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
    print("run: uv tool upgrade morning-paper  (or: pipx upgrade morning-paper)")


def _pretty_install_hint_lines() -> list[str]:
    lines = ['recommended install: uv tool install --python 3.13 "morning-paper[pretty]"']
    if sys.platform == "darwin":
        lines.append("macOS may also need: brew install pango gdk-pixbuf")
    elif sys.platform.startswith("linux"):
        lines.append("Linux may also need system libraries for WeasyPrint (for example pango/cairo packages)")
    elif sys.platform.startswith("win"):
        lines.append("Windows typewriter support is best-effort today; portable mode is more reliable")
    return lines


def _renderer_hint_lines(renderer_error: str | None) -> list[str]:
    if renderer_error and sys.platform == "darwin" and "pango" in renderer_error.lower():
        # WeasyPrint imported but could not load the Pango system library:
        # this is the one macOS failure with an exact known fix.
        return [
            "detected: WeasyPrint cannot load Pango (the text layout library)",
            "fix: brew install pango gdk-pixbuf",
            'if it still fails: export DYLD_FALLBACK_LIBRARY_PATH="/opt/homebrew/lib:$DYLD_FALLBACK_LIBRARY_PATH"',
        ]
    return _pretty_install_hint_lines()


def _dependency_report() -> dict[str, object]:
    packages = [
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
    ]
    versions: dict[str, str | None] = {}
    for package in packages:
        try:
            versions[package] = metadata.version(package)
        except metadata.PackageNotFoundError:
            versions[package] = None
    weasyprint_support = _weasyprint_support_report(versions.get("weasyprint"))
    return {
        "python": {
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
            "executable": sys.executable,
        },
        "packages": versions,
        "weasyprint": weasyprint_support,
        "native": {
            "pango": _native_tool_version("pango-view", "--version"),
        },
    }


def _native_tool_version(command: str, *args: str) -> dict[str, object]:
    path = shutil.which(command)
    if not path:
        return {"found": False, "path": None, "version": None, "error": ""}
    try:
        result = subprocess.run(
            [path, *args],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=5,
        )
    except Exception as exc:
        return {"found": True, "path": path, "version": None, "error": str(exc)}
    first_line = (result.stdout or "").strip().splitlines()
    return {
        "found": True,
        "path": path,
        "version": first_line[0] if first_line else "",
        "error": "" if result.returncode == 0 else (result.stdout or "").strip(),
    }


def _render_self_test(enabled: bool, typewriter_ready: bool, skip_reason: str = "") -> dict[str, object]:
    if not enabled:
        return {"run": False, "ok": False if skip_reason else None, "pages": None, "error": skip_reason}
    if not typewriter_ready:
        return {"run": False, "ok": False, "pages": None, "error": "typewriter renderer unavailable"}
    sample = """---
title: Morning Paper Doctor
---

# Morning Paper Doctor

This one-page proof verifies that WeasyPrint can lay out the production
style stack on this machine. The user should not need to know what WeasyPrint
is; `doctor --strict` owns that proof.
"""
    try:
        pages = count_pages(sample, style="broadsheet", palette="color")
    except Exception as exc:
        return {"run": True, "ok": False, "pages": None, "error": str(exc)}
    return {"run": True, "ok": pages >= 1, "pages": pages, "error": "" if pages >= 1 else "rendered zero pages"}


def _routine_status_line(routine_info: dict) -> str:
    # Absence is not a problem — the routine is an optional convenience tier.
    if routine_info.get("installed"):
        time_str = routine_info.get("time")
        scheduler = routine_info.get("scheduler")
        detail = f"daily at {time_str} via {scheduler}" if time_str else f"via {scheduler}"
        return f"routine: installed ({detail})"
    return "routine: not installed (optional — `morning-paper routine install` schedules the morning edition)"


def doctor(args: list[str] | None = None) -> int:
    usage = "usage: morning-paper doctor [--json] [--strict]"
    as_json = False
    strict = False
    for arg in args or []:
        if arg in {"-h", "--help"}:
            print(usage)
            return 0
        if arg == "--json":
            as_json = True
            continue
        if arg == "--strict":
            strict = True
            continue
        print(f"unknown doctor argument: {arg}", file=sys.stderr)
        return 2
    checks: list[dict[str, object]] = []
    required_modules = [
        "morning_paper.cli",
        "morning_paper.article_print",
        "morning_paper.config",
        "morning_paper.extractors",
        "morning_paper.image_tools",
        "morning_paper.inbox",
        "morning_paper.renderers",
        "morning_paper.routine",
        "morning_paper.sources",
    ]
    for module_name in required_modules:
        try:
            import_module(module_name)
            checks.append({"name": module_name, "ok": True})
        except Exception:
            checks.append({"name": module_name, "ok": False})
    missing = [str(check["name"]) for check in checks if not check["ok"]]
    dependency_report = _dependency_report()
    weasyprint_support = dependency_report["weasyprint"] if isinstance(dependency_report["weasyprint"], dict) else {}
    weasyprint_supported = bool(weasyprint_support.get("supported"))
    unsupported_renderer_error = str(weasyprint_support.get("error") or "")
    _, renderer_error = _load_weasyprint()
    typewriter_ready = renderer_error is None
    unsupported_typewriter = typewriter_ready and not weasyprint_supported
    hints = [] if typewriter_ready and not unsupported_typewriter else _renderer_hint_lines(renderer_error)
    render_self_test = _render_self_test(
        strict and not unsupported_typewriter,
        typewriter_ready,
        unsupported_renderer_error if strict and unsupported_typewriter else "",
    )
    # The routine is optional: report installed/not, never an error when absent.
    from .routine import routine_doctor_summary

    routine_info = routine_doctor_summary()
    if missing:
        status = "broken"
    elif unsupported_typewriter:
        status = "unsupported-renderer"
    elif render_self_test.get("run") and not render_self_test.get("ok"):
        status = "render-broken"
    elif typewriter_ready:
        status = "ok"
    else:
        status = "fallback-only"
    exit_code = 0
    if missing or (strict and (not typewriter_ready or unsupported_typewriter or not render_self_test.get("ok"))):
        exit_code = 1
    if as_json:
        payload: dict[str, object] = {
            "checks": checks,
            "renderer": {
                "typewriter": typewriter_ready,
                "error": renderer_error,
                "hints": hints,
                "render_self_test": render_self_test,
            },
            "dependencies": dependency_report,
            "routine": routine_info,
            "status": status,
        }
        print(json.dumps(payload, indent=2))
        return exit_code
    if missing:
        print("doctor: missing required files:", file=sys.stderr)
        for item in missing:
            print(f"- {item}", file=sys.stderr)
        return exit_code
    if not typewriter_ready:
        print("doctor: ok")
        print("renderer: typewriter unavailable")
        print(_routine_status_line(routine_info))
        print("status: fallback-only install; high-quality print output is not available yet")
        for line in hints:
            print(line)
        _print_update_notice()
        return exit_code
    print("doctor: ok")
    print("renderer: typewriter ready")
    if unsupported_typewriter:
        print(
            "renderer dependency: unsupported WeasyPrint "
            f"{weasyprint_support.get('version')} (requires {SUPPORTED_WEASYPRINT_RANGE})"
        )
    if render_self_test.get("run"):
        if render_self_test.get("ok"):
            print(f"renderer self-test: passed ({render_self_test.get('pages')} page(s))")
        else:
            print(f"renderer self-test: failed ({render_self_test.get('error')})")
    elif render_self_test.get("error"):
        print(f"renderer self-test: skipped ({render_self_test.get('error')})")
    print(_routine_status_line(routine_info))
    if status == "render-broken":
        print("status: typewriter imported, but the layout self-test failed")
    elif status == "unsupported-renderer":
        print("status: typewriter imported, but the installed WeasyPrint is outside the supported range")
        for line in hints:
            print(line)
    else:
        print("status: high-quality print path available")
    _print_update_notice()
    return exit_code


def _deliver_pdf(outputs: dict[str, object], output_arg: str | None) -> tuple[str | None, int]:
    """Copy the rendered PDF to the user's --output path; returns (final path, exit code).

    A trailing slash or an existing directory means "put it in there under its
    own name"; anything else is the destination file.
    """
    if not output_arg:
        return None, 0
    import shutil

    pdf_path = Path(str(outputs.get("pdf", "")))
    if not pdf_path.is_file():
        print("--output requires a produced PDF, but no PDF was written", file=sys.stderr)
        return None, 1
    target = Path(output_arg).expanduser()
    if output_arg.endswith(("/", "\\")) or target.is_dir():
        target = target / pdf_path.name
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(pdf_path, target)
    except OSError as exc:
        print(f"could not write --output path {target}: {exc}", file=sys.stderr)
        return None, 1
    return str(target), 0


def _open_pdf(path: Path) -> dict[str, object]:
    if sys.platform == "darwin":
        command = ["open", str(path)]
    elif sys.platform.startswith("win"):
        command = ["cmd", "/c", "start", "", str(path)]
    else:
        command = ["xdg-open", str(path)]
    try:
        result = subprocess.run(command, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except OSError as exc:
        return {"requested": True, "ok": False, "command": command, "error": str(exc)}
    return {
        "requested": True,
        "ok": result.returncode == 0,
        "command": command,
        "error": "" if result.returncode == 0 else (result.stderr or result.stdout).strip(),
    }


def demo_command(args: list[str]) -> int:
    usage = "usage: morning-paper demo [--output PATH] [--open]"
    output_arg: str | None = None
    open_pdf = False
    index = 0
    while index < len(args):
        arg = args[index]
        if arg in {"-h", "--help"}:
            print(usage)
            return 0
        if arg == "--open":
            open_pdf = True
            index += 1
            continue
        if arg == "--output" and index + 1 < len(args):
            output_arg = args[index + 1]
            index += 2
            continue
        print(f"unknown demo argument: {arg}", file=sys.stderr)
        return 2
    _, renderer_error = _load_weasyprint()
    if renderer_error:
        print("demo needs the pretty print stack (WeasyPrint) to typeset the sample edition", file=sys.stderr)
        for line in _renderer_hint_lines(renderer_error):
            print(line, file=sys.stderr)
        print("then run `morning-paper doctor` to confirm the renderer is ready", file=sys.stderr)
        return 1
    markdown_text = resources.files("morning_paper").joinpath("resources", "demo.md").read_text(encoding="utf-8")
    config = MorningPaperConfig()
    config.outputs.style = "broadsheet"
    config.outputs.palette = "color"
    config.outputs.html = True
    config.outputs.pdf = True
    if output_arg:
        target = Path(output_arg).expanduser()
        if output_arg.endswith(("/", "\\")) or target.is_dir():
            config.outputs.directory = target
    target_date = datetime.now(ZoneInfo(config.timezone)).date().isoformat()
    try:
        outputs, warnings, pages = write_custom_markdown(
            config,
            markdown_text,
            date_str=target_date,
            slug="demo",
            metadata={"mode": "demo", "style": "broadsheet", "palette": "color"},
        )
    except TypewriterRendererUnavailable as exc:
        print(str(exc), file=sys.stderr)
        return 1
    for warning in warnings:
        print(f"warning: {warning}", file=sys.stderr)
    delivered, rc = _deliver_pdf(outputs, output_arg)
    if rc:
        return rc
    output_paths = {key: str(value) for key, value in outputs.items() if key != "dir"}
    if delivered:
        output_paths["pdf"] = delivered
    final_pdf = Path(str(delivered or outputs["pdf"]))
    open_result = _open_pdf(final_pdf) if open_pdf else {"requested": False, "ok": None, "command": [], "error": ""}
    print(
        json.dumps(
            {
                "date": target_date,
                "mode": "demo",
                "style": "broadsheet",
                "palette": "color",
                "pages": pages,
                "warnings": warnings,
                "outputs": output_paths,
                "output_dir": str(outputs["dir"]),
                "opened": open_result,
            },
            indent=2,
        )
    )
    if open_pdf and not open_result["ok"]:
        print(f"warning: could not open PDF automatically ({open_result['error']})", file=sys.stderr)
    print(f"Print it: lp {final_pdf}", file=sys.stderr)
    print(
        'Make it yours: uv tool install --python 3.13 "morning-paper[pretty]" '
        "&& morning-paper init (or run the setup skill in Claude Code/Codex)",
        file=sys.stderr,
    )
    print("Post your paper: https://github.com/dmthepm/morning-paper/discussions", file=sys.stderr)
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


def newsroom_command(args: list[str]) -> int:
    from .newsroom import scaffold_newsroom, update_setup_state

    usage = (
        "usage: morning-paper newsroom init <path> [--name NAME] [--force]\n"
        "       morning-paper newsroom state <path> [--set KEY=VALUE] [--pending TEXT] [--clear-pending]"
    )
    force = False
    name = "Morning Paper"
    sets: list[str] = []
    pending: list[str] = []
    clear_pending = False
    rest: list[str] = []
    index = 0
    while index < len(args):
        arg = args[index]
        if arg in {"-h", "--help"}:
            print(usage)
            return 0
        if arg == "--force":
            force = True
            index += 1
            continue
        if arg == "--name" and index + 1 < len(args):
            name = args[index + 1]
            index += 2
            continue
        if arg == "--set" and index + 1 < len(args):
            sets.append(args[index + 1])
            index += 2
            continue
        if arg == "--pending" and index + 1 < len(args):
            pending.append(args[index + 1])
            index += 2
            continue
        if arg == "--clear-pending":
            clear_pending = True
            index += 1
            continue
        rest.append(arg)
        index += 1
    if len(rest) != 2 or rest[0] not in {"init", "state"}:
        print(usage, file=sys.stderr)
        return 2
    try:
        if rest[0] == "init":
            payload = scaffold_newsroom(Path(rest[1]), name=name, force=force)
        else:
            payload = update_setup_state(Path(rest[1]), sets=sets, pending=pending, clear_pending=clear_pending)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(payload, indent=2))
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
        print("run `morning-paper init` to customize sources, timezone, and output paths", file=sys.stderr)
    try:
        articles = [
            fetch_article(
                url,
                extractor_name=config.article_extractor,
                allow_remote_fallback=config.remote_extractor_fallback,
            )
            for url in urls
        ]
    except ArticleExtractionError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    target_date = date or datetime.now(ZoneInfo(config.timezone)).date().isoformat()
    bundle_title = title or articles[0].title
    slug = _safe_filename(bundle_title)[:48] or "article-print"
    # Honesty rule: never silently clip — flag any article that will print incomplete.
    truncation_warnings = [
        f"{article.url} {message}"
        for article in articles
        if (message := article_truncation_warning(article))
    ]
    # Honesty rule: if the reader explicitly allowed remote fallback, say when
    # it actually happened — the reader should know this URL left the machine.
    truncation_warnings.extend(
        f"{article.url} {article.extraction_note}" for article in articles if article.extraction_note
    )
    try:
        outputs, warnings, pages = write_custom_markdown(
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
    warnings = truncation_warnings + warnings
    for warning in warnings:
        print(f"warning: {warning}", file=sys.stderr)
    print(
        json.dumps(
            {
                "date": target_date,
                "mode": "print",
                "article_count": len(articles),
                "pages": pages,
                "warnings": warnings,
                "outputs": {key: str(value) for key, value in outputs.items() if key != "dir"},
                "output_dir": str(outputs["dir"]),
            },
            indent=2,
        )
    )
    return 0


def styles_command() -> int:
    from .styles import STYLE_ALIASES

    listing = {
        "styles": {name: pack.description for name, pack in sorted(STYLES.items())},
        # 0.4.x names, accepted for one release with a deprecation warning
        "deprecated_aliases": dict(sorted(STYLE_ALIASES.items())),
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
    output_arg: str | None = None
    source: Path | None = None
    index = 0
    usage = "usage: morning-paper render <file.md> [--style NAME] [--palette NAME] [--output PATH] [--date YYYY-MM-DD] [--id NAME] [--config PATH]"
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
        if arg in {"--id", "--slug"} and index + 1 < len(args):
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
        if arg == "--output" and index + 1 < len(args):
            output_arg = args[index + 1]
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
    # artifact output toggles in config
    config.outputs.html = True
    config.outputs.pdf = True
    markdown_text = source.read_text(encoding="utf-8")
    target_date = date or datetime.now(ZoneInfo(config.timezone)).date().isoformat()
    target_slug = _safe_filename(slug or source.stem)[:48] or "render"
    # Honesty rule: a frontmatter `css:` block replaces the style pack
    # entirely — never report a style the page is not actually wearing.
    reported_style = config.outputs.style
    if document_uses_custom_css(markdown_text):
        reported_style = "custom-css"
        print(
            "warning: frontmatter `css:` overrides the configured style pack; "
            "rendering with the document's own stylesheet",
            file=sys.stderr,
        )
    try:
        outputs, warnings, pages = write_custom_markdown(
            config,
            markdown_text,
            date_str=target_date,
            slug=target_slug,
            metadata={
                "mode": "render",
                "source": str(source),
                "style": reported_style,
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
    delivered, rc = _deliver_pdf(outputs, output_arg)
    if rc:
        return rc
    output_paths = {key: str(value) for key, value in outputs.items() if key != "dir"}
    if delivered:
        output_paths["pdf"] = delivered
    print(
        json.dumps(
            {
                "status": "rendered",
                "date": target_date,
                "mode": "render",
                "style": reported_style,
                "palette": config.outputs.palette,
                "pages": pages,
                "warnings": warnings,
                "outputs": output_paths,
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
    from .staging import default_edition_date, stage_markdown, stage_url

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
        # the one URL-staging path, shared with the contributor inbox — the
        # honesty flags (truncation, extractor fallback) ride along in the JSON
        try:
            item = stage_url(config, target, date_str=date_str, title=title_override)
        except ArticleExtractionError as exc:
            print(json.dumps({"staged": False, "error": str(exc)}, indent=2))
            return 1
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


def stage_social_command(args: list[str]) -> int:
    from dataclasses import asdict

    from .staging import default_edition_date, stage_social_record

    usage = "usage: morning-paper stage-social <record.json> [--date YYYY-MM-DD] [--config PATH]"
    parsed = _parse_common(args, usage)
    if isinstance(parsed, int):
        return parsed
    config_path, date, rest = parsed
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
    try:
        record = json.loads(source.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"invalid social source record: {exc}", file=sys.stderr)
        return 1
    if not isinstance(record, dict):
        print("invalid social source record: root must be an object", file=sys.stderr)
        return 1
    date_str = date or default_edition_date(config)
    try:
        item = stage_social_record(config, record, date_str=date_str)
    except ValueError as exc:
        print(f"invalid social source record: {exc}", file=sys.stderr)
        return 1
    payload = {"staged": True, "edition_date": date_str, **asdict(item)}
    print(json.dumps(payload, indent=2))
    return 0


def inbox_command(args: list[str]) -> int:
    from .inbox import InboxError, poll_inbox

    usage = "usage: morning-paper inbox [poll] [--dry-run] [--date YYYY-MM-DD] [--config PATH]"
    dry_run = False
    if "--dry-run" in args:
        dry_run = True
        args = [arg for arg in args if arg != "--dry-run"]
    parsed = _parse_common(args, usage)
    if isinstance(parsed, int):
        return parsed
    config_path, date, rest = parsed
    if rest == ["poll"]:
        rest = []
    if rest:
        print(usage, file=sys.stderr)
        return 2
    try:
        config, _ = _load_print_config(config_path)
    except ConfigError as exc:
        print(f"invalid config: {exc}", file=sys.stderr)
        return 1
    try:
        result = poll_inbox(config, dry_run=dry_run, date_str=date)
    except InboxError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    for warning in result.get("warnings", []):
        print(f"warning: {warning}", file=sys.stderr)
    print(json.dumps(result, indent=2))
    return 0


def queue_command(args: list[str]) -> int:
    from .staging import default_edition_date, queue_item, queue_status, remove_queue_item

    usage = (
        "usage: morning-paper queue [status|list|show ITEM_ID|remove ITEM_ID] "
        "[--date YYYY-MM-DD] [--config PATH] [--content]"
    )
    include_content = False
    if "--content" in args:
        include_content = True
        args = [arg for arg in args if arg != "--content"]
    parsed = _parse_common(args, usage)
    if isinstance(parsed, int):
        return parsed
    config_path, date, rest = parsed
    action = rest[0] if rest else "status"
    if action not in {"status", "list", "show", "remove"}:
        print(usage, file=sys.stderr)
        return 2
    if action in {"status", "list"} and len(rest) > 1:
        print(usage, file=sys.stderr)
        return 2
    if action in {"show", "remove"} and len(rest) != 2:
        print(usage, file=sys.stderr)
        return 2
    try:
        config, _ = _load_print_config(config_path)
    except ConfigError as exc:
        print(f"invalid config: {exc}", file=sys.stderr)
        return 1
    date_str = date or default_edition_date(config)
    if action in {"status", "list"}:
        print(json.dumps(queue_status(config, date_str), indent=2))
        return 0
    if action == "show":
        payload = queue_item(config, date_str, rest[1])
        if not include_content and payload.get("markdown"):
            markdown = str(payload["markdown"])
            payload["markdown_preview"] = markdown[:1200]
            del payload["markdown"]
        print(json.dumps(payload, indent=2))
        return 0 if payload.get("found") else 1
    payload = remove_queue_item(config, date_str, rest[1])
    print(json.dumps(payload, indent=2))
    return 0 if payload.get("removed") else 1


def _detect_newsroom_cwd() -> Path | None:
    cwd = Path.cwd()
    required = [cwd / "setup-state.json", cwd / "SOURCES.md"]
    if all(path.is_file() for path in required) and (cwd / "collectors").is_dir():
        return cwd.resolve()
    return None


def sources_command(args: list[str]) -> int:
    from .sources import source_inventory

    usage = "usage: morning-paper sources [list|check] [--config PATH] [--newsroom PATH]"
    newsroom: Path | None = None
    if "--newsroom" in args:
        index = args.index("--newsroom")
        if index + 1 >= len(args):
            print(usage, file=sys.stderr)
            return 2
        newsroom = Path(args[index + 1]).expanduser().resolve()
        args = args[:index] + args[index + 2 :]
    else:
        newsroom = _detect_newsroom_cwd()
    parsed = _parse_common(args, usage)
    if isinstance(parsed, int):
        return parsed
    config_path, _date, rest = parsed
    action = rest[0] if rest else "list"
    if action not in {"list", "check"} or len(rest) > 1:
        print(usage, file=sys.stderr)
        return 2
    try:
        config, _ = _load_print_config(config_path)
    except ConfigError as exc:
        print(f"invalid config: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(source_inventory(config, check=action == "check", newsroom=newsroom), indent=2))
    return 0


def edition_command(args: list[str]) -> int:
    from .edition_workspace import (
        FEEDBACK_ROUTES,
        assignment_board_edition_workspace,
        apply_feedback,
        desk_sheet_edition_workspace,
        estimate_edition_workspace,
        final_editor_pass,
        prepare_edition_workspace,
        run_ticket_edition_workspace,
        visual_qa_edition_workspace,
    )

    usage = (
        "usage: morning-paper edition prepare <newsroom-path> "
        "[--date YYYY-MM-DD] [--config PATH] [--check-sources] [--force]\n"
        "       morning-paper edition assignment-board <newsroom-path> "
        "[--date YYYY-MM-DD] [--config PATH]\n"
        "       morning-paper edition estimate <newsroom-path> "
        "[--date YYYY-MM-DD] [--config PATH]\n"
        "       morning-paper edition desk-sheet <newsroom-path> "
        "[--date YYYY-MM-DD] [--config PATH]\n"
        "       morning-paper edition visual-qa <newsroom-path> "
        "[--date YYYY-MM-DD] [--config PATH]\n"
        "       morning-paper edition final-editor <newsroom-path> "
        "[--date YYYY-MM-DD] [--config PATH]\n"
        "       morning-paper edition status <newsroom-path> "
        "[--date YYYY-MM-DD] [--config PATH]\n"
        "       morning-paper edition apply-feedback <newsroom-path> --route ROUTE --note TEXT "
        "[--decision accepted|rejected] [--why TEXT] [--date YYYY-MM-DD]\n"
        f"       routes: {', '.join(FEEDBACK_ROUTES)}"
    )
    config_path = DEFAULT_CONFIG_PATH
    date: str | None = None
    check_sources = False
    force = False
    route = ""
    note = ""
    decision = "accepted"
    why = ""
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
        if arg == "--check-sources":
            check_sources = True
            index += 1
            continue
        if arg == "--force":
            force = True
            index += 1
            continue
        if arg == "--route" and index + 1 < len(args):
            route = args[index + 1]
            index += 2
            continue
        if arg == "--note" and index + 1 < len(args):
            note = args[index + 1]
            index += 2
            continue
        if arg == "--decision" and index + 1 < len(args):
            decision = args[index + 1]
            index += 2
            continue
        if arg == "--why" and index + 1 < len(args):
            why = args[index + 1]
            index += 2
            continue
        rest.append(arg)
        index += 1
    verbs = {
        "prepare",
        "assignment-board",
        "estimate",
        "desk-sheet",
        "visual-qa",
        "final-editor",
        "status",
        "run-ticket",
        "apply-feedback",
    }
    if len(rest) != 2 or rest[0] not in verbs:
        print(usage, file=sys.stderr)
        return 2
    try:
        config, _ = _load_print_config(config_path)
    except ConfigError as exc:
        print(f"invalid config: {exc}", file=sys.stderr)
        return 1
    date_str = date or datetime.now(ZoneInfo(config.timezone)).date().isoformat()
    try:
        if rest[0] == "prepare":
            payload = prepare_edition_workspace(
                Path(rest[1]),
                config,
                date_str=date_str,
                check_sources=check_sources,
                force=force,
            )
        elif rest[0] == "assignment-board":
            payload = assignment_board_edition_workspace(Path(rest[1]), config, date_str=date_str)
        elif rest[0] == "estimate":
            payload = estimate_edition_workspace(Path(rest[1]), config, date_str=date_str)
        elif rest[0] == "desk-sheet":
            payload = desk_sheet_edition_workspace(Path(rest[1]), config, date_str=date_str)
        elif rest[0] == "visual-qa":
            payload = visual_qa_edition_workspace(Path(rest[1]), date_str=date_str)
        elif rest[0] == "final-editor":
            payload = final_editor_pass(Path(rest[1]), config, date_str=date_str)
        elif rest[0] in {"status", "run-ticket"}:
            payload = run_ticket_edition_workspace(Path(rest[1]), config, date_str=date_str)
        else:
            payload = apply_feedback(
                Path(rest[1]),
                date_str=date_str,
                route=route,
                note=note,
                decision=decision,
                why=why,
            )
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(payload, indent=2))
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
            font_scale=config.outputs.font_scale,
        )
    except StyleError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"estimate requires the pretty print stack: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"file": str(source), "words": len(markdown.split()), "est_pages": pages}, indent=2))
    return 0


def _latest_edition_path(config: MorningPaperConfig) -> Path | None:
    """The most recent edition directory under outputs.directory (by date name).

    Editions live at outputs.directory/<YYYY-MM-DD>/ (and per-slug subdirs for
    render/print). Pick the newest date dir that holds a markdown file.
    """
    base = config.outputs.directory
    if not base.is_dir():
        return None
    date_dirs = sorted(
        (d for d in base.iterdir() if d.is_dir() and re.match(r"\d{4}-\d{2}-\d{2}$", d.name)),
        reverse=True,
    )
    for d in date_dirs:
        if any(d.glob("*.md")):
            return d
        # render/print write into a per-slug subdir
        for sub in sorted(d.iterdir()):
            if sub.is_dir() and any(sub.glob("*.md")):
                return sub
    return None


def review_command(args: list[str]) -> int:
    from .reviewers import explain, load_preferences, render_human, run_review

    usage = (
        "usage: morning-paper review [<edition-dir|file|date>] "
        "[--json] [--strict] [--verbose] [--explain CHECK] [--config PATH]"
    )
    config_path = DEFAULT_CONFIG_PATH
    as_json = False
    strict = False
    verbose = False
    explain_check: str | None = None
    target: str | None = None
    index = 0
    while index < len(args):
        arg = args[index]
        if arg in {"-h", "--help"}:
            print(usage)
            return 0
        if arg == "--json":
            as_json = True
            index += 1
            continue
        if arg == "--strict":
            strict = True
            index += 1
            continue
        if arg == "--verbose":
            verbose = True
            index += 1
            continue
        if arg == "--explain" and index + 1 < len(args):
            explain_check = args[index + 1]
            index += 2
            continue
        if arg == "--config" and index + 1 < len(args):
            config_path = Path(args[index + 1]).expanduser().resolve()
            index += 2
            continue
        if arg.startswith("-"):
            print(f"unknown review argument: {arg}", file=sys.stderr)
            return 2
        if target is not None:
            print("review takes at most one edition path or date", file=sys.stderr)
            return 2
        target = arg
        index += 1

    try:
        config, _ = _load_print_config(config_path)
    except ConfigError as exc:
        print(f"invalid config: {exc}", file=sys.stderr)
        return 1

    # resolve the edition: an explicit path, a date (→ outputs.directory/date),
    # or the latest edition when nothing is given
    edition_path: Path | None = None
    if target:
        candidate = Path(target).expanduser()
        if candidate.exists():
            edition_path = candidate
        elif re.match(r"\d{4}-\d{2}-\d{2}$", target):
            edition_path = config.outputs.directory / target
        else:
            print(f"no such edition: {target}", file=sys.stderr)
            return 1
    else:
        edition_path = _latest_edition_path(config)
        if edition_path is None:
            print(
                "no edition found to review — pass an edition path or date, "
                f"or render an edition first (looked under {config.outputs.directory})",
                file=sys.stderr,
            )
            return 1

    prefs = load_preferences(edition_path)
    report = run_review(edition_path, prefs=prefs)

    # exit 0 by default ALWAYS; --strict makes a flag (and only a flag) exit 1
    exit_code = 0
    if strict and report["summary"].get("flag", 0):
        exit_code = 1

    if explain_check:
        print(explain(report, explain_check))
        return exit_code
    if as_json:
        print(json.dumps(report, indent=2))
        return exit_code
    print(render_human(report, verbose=verbose).rstrip())
    return exit_code


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
    if command == "newsroom":
        return newsroom_command(extra)
    if command in {"sources", "source"}:
        return sources_command(extra)
    if command == "print":
        return print_command(extra)
    if command == "render":
        return render_command(extra)
    if command in {"stage", "add"}:
        return stage_command(extra)
    if command == "stage-social":
        return stage_social_command(extra)
    if command == "inbox":
        return inbox_command(extra)
    if command in {"queue", "status"}:
        return queue_command(extra)
    if command == "edition":
        return edition_command(extra)
    if command == "estimate":
        return estimate_command(extra)
    if command == "review":
        return review_command(extra)
    if command == "styles":
        return styles_command()
    if command == "routine":
        from .routine import routine_command

        return routine_command(extra)
    if command == "doctor":
        return doctor(extra)
    print(f"unknown command: {command}", file=sys.stderr)
    print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
