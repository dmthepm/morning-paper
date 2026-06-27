from __future__ import annotations

import html
import io
import json
import os
import subprocess
import sys
import unicodedata
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
from pathlib import Path

from fpdf import FPDF
from markdown_it import MarkdownIt
import yaml

from .charts import expand_chart_directives
from .config import MorningPaperConfig
from .styles import compose_css, get_palette


class TypewriterRendererUnavailable(RuntimeError):
    pass


def _page_count_worker_env() -> dict[str, str]:
    env = os.environ.copy()
    src_root = str(Path(__file__).resolve().parents[1])
    existing = env.get("PYTHONPATH")
    if existing:
        paths = existing.split(os.pathsep)
        if src_root not in paths:
            env["PYTHONPATH"] = os.pathsep.join([src_root, existing])
    else:
        env["PYTHONPATH"] = src_root
    return env


def _safe_filename(label: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "-" for ch in label).strip("-") or "morning-paper"


def custom_output_paths(config: MorningPaperConfig, date_str: str, *, slug: str) -> dict[str, Path]:
    out_dir = config.outputs.directory / date_str / slug
    return {
        "dir": out_dir,
        "json": out_dir / f"{slug}.json",
        "markdown": out_dir / f"{slug}.md",
        "html": out_dir / f"{slug}.html",
        "pdf": out_dir / f"{slug}.pdf",
    }


def _pdf_text(value: str) -> str:
    text = (value or "").replace("\u00a0", " ")
    replacements = {
        "\u2013": "-",
        "\u2014": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2026": "...",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = unicodedata.normalize("NFKD", text).encode("latin-1", "ignore").decode("latin-1")
    return " ".join(text.split())


_MARKDOWN = MarkdownIt("commonmark", {"html": True, "linkify": True}).enable("table")


def _split_frontmatter(document: str) -> tuple[dict[str, object], str]:
    lines = document.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, document
    try:
        closing = lines[1:].index("---") + 1
    except ValueError:
        return {}, document
    meta = yaml.safe_load("\n".join(lines[1:closing])) or {}
    body = "\n".join(lines[closing + 1 :])
    return meta, body


def _load_weasyprint() -> tuple[object | None, str | None]:
    if sys.platform == "darwin":
        search_paths = ["/opt/homebrew/lib", "/usr/local/lib"]
        current = os.environ.get("DYLD_FALLBACK_LIBRARY_PATH", "")
        current_parts = [part for part in current.split(":") if part]
        merged = current_parts[:]
        for candidate in search_paths:
            if Path(candidate).exists() and candidate not in merged:
                merged.append(candidate)
        if merged:
            os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = ":".join(merged)
    import_buffer = io.StringIO()
    try:
        with redirect_stdout(import_buffer), redirect_stderr(import_buffer):
            from weasyprint import HTML  # type: ignore
    except (ImportError, OSError) as exc:
        return None, str(exc)
    return HTML, None


def document_uses_custom_css(markdown: str) -> bool:
    """True when frontmatter `css:` will replace the style pack entirely."""
    meta, _body = _split_frontmatter(markdown)
    return bool(str(meta.get("css", "")).strip())


def _render_html_from_markdown(
    markdown: str, *, style: str = "broadsheet", palette: str = "mono", font_scale: float = 1.0
) -> str:
    meta, body = _split_frontmatter(markdown)
    # Frontmatter `css:` is an override for callers bringing their own sheet;
    # otherwise the style pack + palette supply it.
    css = str(meta.get("css", "")).strip() or compose_css(
        str(meta.get("style", style)), str(meta.get("palette", palette)), font_scale=font_scale
    )
    palette_pack = get_palette(str(meta.get("palette", palette)))
    body = expand_chart_directives(body, ink=palette_pack.chart_ink, track=palette_pack.chart_track)
    title = html.escape(str(meta.get("title", "Morning Paper")))
    rendered_body = _MARKDOWN.render(body)
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<title>{title}</title>"
        f"<style>{css}</style>"
        "</head><body>"
        f"{rendered_body}"
        "</body></html>"
    )


def _render_typewriter_pdf(
    markdown: str, *, output_path: Path, style: str = "broadsheet", palette: str = "mono", font_scale: float = 1.0
) -> int:
    html_cls, error = _load_weasyprint()
    if html_cls is None:
        raise RuntimeError(error or "WeasyPrint unavailable")
    html_doc = _render_html_from_markdown(markdown, style=style, palette=palette, font_scale=font_scale)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    document = html_cls(string=html_doc, base_url=str(output_path.parent)).render()
    document.write_pdf(str(output_path))
    return len(document.pages)


def _count_pages_direct(
    markdown: str, *, style: str = "broadsheet", palette: str = "mono", font_scale: float = 1.0
) -> int:
    html_cls, error = _load_weasyprint()
    if html_cls is None:
        raise RuntimeError(error or "WeasyPrint unavailable")
    html_doc = _render_html_from_markdown(markdown, style=style, palette=palette, font_scale=font_scale)
    return len(html_cls(string=html_doc).render().pages)


def count_pages(markdown: str, *, style: str = "broadsheet", palette: str = "mono", font_scale: float = 1.0) -> int:
    """Lay the document out in an isolated process; return its page count.

    The agent-facing `estimate`/`stage` verbs use this to answer "how many
    pages would this add?" before composition time. The isolation is deliberate:
    WeasyPrint is a native-library stack, and long-lived agent/test processes
    should not keep accumulating renderer state just to answer an estimate.
    """
    try:
        result = subprocess.run(
            [sys.executable, "-m", "morning_paper.page_count_worker"],
            input=json.dumps(
                {
                    "markdown": markdown,
                    "style": style,
                    "palette": palette,
                    "font_scale": font_scale,
                }
            ),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=20,
            check=False,
            env=_page_count_worker_env(),
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("page count worker timed out") from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"page count worker failed: {detail}")
    try:
        payload = json.loads(result.stdout)
        return int(payload["pages"])
    except Exception as exc:
        raise RuntimeError(f"page count worker returned invalid output: {result.stdout!r}") from exc


def _render_markdown_text_pdf(config: MorningPaperConfig, markdown: str, *, date_str: str, output_path: Path) -> int:
    _meta, body = _split_frontmatter(markdown)
    rendered_body = _MARKDOWN.render(body)
    plain = html.unescape(rendered_body)
    plain = plain.replace("</p>", "\n\n").replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")
    plain = plain.replace("</li>", "\n").replace("</h1>", "\n").replace("</h2>", "\n").replace("</h3>", "\n")
    import re
    plain = re.sub(r"<[^>]+>", " ", plain)
    plain = "\n".join(line.strip() for line in plain.splitlines())
    pdf = FPDF(format="Letter")
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()
    width = pdf.w - pdf.l_margin - pdf.r_margin
    pdf.set_title(f"{config.name} — {date_str}")
    pdf.set_author("Morning Paper")
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(width, 10, _pdf_text(config.name), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    for raw_line in plain.splitlines():
        line = raw_line.strip()
        if not line:
            pdf.ln(3)
            continue
        line = _pdf_text(line.replace("# ", "").replace("## ", "").replace("### ", ""))
        pdf.multi_cell(width, 5, line)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pages = pdf.page
    pdf.output(str(output_path))
    return pages


def write_custom_markdown(
    config: MorningPaperConfig,
    markdown: str,
    *,
    date_str: str,
    slug: str,
    metadata: dict[str, object] | None = None,
) -> tuple[dict[str, Path], list[str], int | None]:
    """Write artifacts for caller-supplied markdown; returns (paths, warnings, pdf page count).

    The page count is None when no PDF was produced.
    """
    paths = custom_output_paths(config, date_str, slug=slug)
    paths["dir"].mkdir(parents=True, exist_ok=True)
    warnings: list[str] = []
    pages: int | None = None
    if config.outputs.json:
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "date": date_str,
            "name": config.name,
            "renderer": config.outputs.renderer,
            "metadata": metadata or {},
        }
        paths["json"].write_text(json.dumps(payload, indent=2), encoding="utf-8")
    if config.outputs.markdown:
        paths["markdown"].write_text(markdown, encoding="utf-8")
    if config.outputs.html:
        paths["html"].write_text(
            _render_html_from_markdown(
                markdown,
                style=config.outputs.style,
                palette=config.outputs.palette,
                font_scale=config.outputs.font_scale,
            ),
            encoding="utf-8",
        )
    if config.outputs.pdf:
        if config.outputs.renderer == "typewriter":
            try:
                pages = _render_typewriter_pdf(
                    markdown,
                    output_path=paths["pdf"],
                    style=config.outputs.style,
                    palette=config.outputs.palette,
                    font_scale=config.outputs.font_scale,
                )
            except Exception as exc:
                raise TypewriterRendererUnavailable(
                    "typewriter renderer requires the pretty print stack. "
                    "Install `morning-paper[pretty]` and any required system libraries "
                    "(for macOS: `brew install pango gdk-pixbuf`), or set "
                    "`outputs.renderer: portable` if you explicitly want the fallback PDF. "
                    f"Detail: {exc}"
                )
        else:
            pages = _render_markdown_text_pdf(config, markdown, date_str=date_str, output_path=paths["pdf"])
    return paths, warnings, pages
