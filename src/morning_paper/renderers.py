from __future__ import annotations

import html
import io
import json
import os
import sys
import unicodedata
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import asdict
from datetime import datetime, timezone
from importlib import resources
from pathlib import Path
from zoneinfo import ZoneInfo

from fpdf import FPDF
from markdown_it import MarkdownIt
import yaml

from .config import MorningPaperConfig
from .models import SourceItem


class TypewriterRendererUnavailable(RuntimeError):
    pass


def _safe_filename(label: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "-" for ch in label).strip("-") or "morning-paper"


def output_paths(config: MorningPaperConfig, date_str: str) -> dict[str, Path]:
    slug = _safe_filename(config.name)
    out_dir = config.outputs.directory / date_str
    return {
        "dir": out_dir,
        "json": out_dir / f"{slug}.json",
        "markdown": out_dir / f"{slug}.md",
        "html": out_dir / f"{slug}.html",
        "pdf": out_dir / f"{slug}.pdf",
    }


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


def _banner_item(collected: dict[str, list[SourceItem]]) -> SourceItem | None:
    candidates = sorted(
        [item for items in collected.values() for item in items],
        key=lambda item: (item.score, item.published_at),
        reverse=True,
    )
    return candidates[0] if candidates else None


def _display_date(date_str: str) -> str:
    return datetime.fromisoformat(date_str).strftime("%d %B %Y").lstrip("0").upper()


def _display_time(timezone: str) -> str:
    now = datetime.now(ZoneInfo(timezone))
    return now.strftime("%H%M %Z")


def _package_template_text(name: str) -> str:
    return resources.files("morning_paper").joinpath("resources", name).read_text(encoding="utf-8")


_MARKDOWN = MarkdownIt("commonmark", {"html": True, "linkify": True})


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


def _html_paragraphs(text: str) -> str:
    parts = [segment.strip() for segment in (text or "").split("\n") if segment.strip()]
    return "\n".join(f"<p>{html.escape(part)}</p>" for part in parts[:4])


def _render_info_row(banner: SourceItem | None, rss_count: int, hn_count: int, renderer: str) -> str:
    banner_value = html.escape((banner.title[:64] + "…") if banner and len(banner.title) > 64 else (banner.title if banner else "No banner"))
    runtime_value = "Typewriter renderer" if renderer == "typewriter" else "Portable renderer"
    return "\n".join(
        [
            '<div class="info-block"><div class="info-label">Banner</div><div class="info-value">' + banner_value + "</div></div>",
            f'<div class="info-block"><div class="info-label">Signals</div><div class="info-value">{rss_count}</div></div>',
            f'<div class="info-block"><div class="info-label">Hacker News</div><div class="info-value">{hn_count}</div></div>',
            f'<div class="info-block"><div class="info-label">Renderer</div><div class="info-value">{html.escape(runtime_value)}</div></div>',
        ]
    )


def _render_signal_cards(items: list[SourceItem]) -> str:
    blocks: list[str] = []
    pair_buffer: list[str] = []
    for item in items:
        card = (
            '<div class="tweet">'
            f'<div class="tweet-header"><span class="tweet-author">{html.escape(item.source_name)}</span>'
            f'<span class="tweet-meta">{html.escape(item.published_at[:10] if item.published_at else "signal")}</span></div>'
            f'<div class="tweet-text">{html.escape(item.title)}</div>'
            f'<div class="tweet-stats">{html.escape(item.summary[:180])}</div>'
            "</div>"
        )
        if len((item.summary or item.title)) < 180:
            pair_buffer.append(card)
            if len(pair_buffer) == 2:
                blocks.append('<div class="tweet-pair">' + "".join(pair_buffer) + "</div>")
                pair_buffer = []
        else:
            if pair_buffer:
                blocks.append('<div class="tweet-pair">' + "".join(pair_buffer) + "</div>")
                pair_buffer = []
            blocks.append(card)
    if pair_buffer:
        blocks.append('<div class="tweet-pair">' + "".join(pair_buffer) + "</div>")
    return "\n".join(blocks) or "<p>No signals available.</p>"


def _render_full_reads(items: list[SourceItem], *, limit: int = 2) -> list[str]:
    reads: list[str] = []
    for item in items[:limit]:
        reads.append(
            '<div class="full-read">'
            f'<div class="full-read-title">{html.escape(item.title)}</div>'
            f'<div class="full-read-source">{html.escape(item.source_name)}</div>'
            f'<div class="full-read-body">{_html_paragraphs(item.summary or item.url)}</div>'
            "</div>"
        )
    while len(reads) < limit:
        reads.append("<p>No full read available.</p>")
    return reads


def _render_hn_cards(items: list[SourceItem]) -> str:
    cards: list[str] = []
    for index, item in enumerate(items, 1):
        cards.append(
            '<div class="hn-card">'
            '<div class="hn-card-header">'
            f'<span class="hn-rank">#{index}</span>'
            f'<span class="hn-domain">{html.escape(item.source_name)}</span>'
            "</div>"
            f'<div class="hn-title">{html.escape(item.title)}</div>'
            f'<div class="hn-meta">{html.escape(item.summary)}</div>'
            f'<div class="hn-desc">{html.escape(item.url)}</div>'
            "</div>"
        )
    return "\n".join(cards) or "<p>No HN items available.</p>"


def render_typewriter_markdown(config: MorningPaperConfig, collected: dict[str, list[SourceItem]], *, date_str: str) -> str:
    template = _package_template_text("typewriter.md")
    banner = _banner_item(collected)
    rss_items = collected.get("rss") or []
    hn_items = collected.get("hacker_news") or []
    reads = _render_full_reads(rss_items if rss_items else hn_items, limit=2)
    replacements = {
        "{DATE}": _display_date(date_str),
        "{TIME}": _display_time(config.timezone),
        "{LOCATION}": "AT HOME",
        '<!-- Banner, tweet count, HN count, runtime -->': _render_info_row(
            banner, len(rss_items), len(hn_items), config.outputs.renderer
        ),
        '<!-- Tweets: short ones (< 180 chars) paired 2-col, long ones full-width -->': _render_signal_cards(rss_items),
        '<!-- Full Read content -->': reads[0],
        '<!-- Second Full Read -->': reads[1],
        '<!-- HN cards go here -->': _render_hn_cards(hn_items),
        '<!-- Community content -->': "<p>Private harness only.</p>",
        '<!-- Agency content -->': "<p>Private harness only.</p>",
        '<!-- Ops content -->': "<p>Private harness only.</p>",
        '<!-- Pipeline status -->': "<p>Portable build path active.</p>",
        '<!-- Action items -->': "<p>Review the banner story and tune your feeds.</p>",
        '<!-- Reference links -->': "<p>Generated by Morning Paper.</p>",
    }
    for needle, value in replacements.items():
        template = template.replace(needle, value)
    return template


def render_markdown(config: MorningPaperConfig, collected: dict[str, list[SourceItem]], *, date_str: str) -> str:
    banner = _banner_item(collected)
    lines = [
        f"# {config.name}",
        "",
        f"_Date: {date_str}_",
        "",
    ]
    if config.profile:
        lines.extend([config.profile.strip(), ""])
    if banner:
        lines.extend(
            [
                "## Banner",
                "",
                f"**{banner.title}**",
                "",
                f"{banner.summary or banner.source_name}",
                "",
                f"Link: {banner.url}",
                "",
            ]
        )
    if collected.get("hacker_news"):
        lines.extend(["## Hacker News", ""])
        for index, item in enumerate(collected["hacker_news"], 1):
            lines.extend(
                [
                    f"{index}. **{item.title}**",
                    f"   - {item.summary}",
                    f"   - {item.url}",
                ]
            )
        lines.append("")
    if collected.get("rss"):
        lines.extend(["## RSS", ""])
        for index, item in enumerate(collected["rss"], 1):
            summary = item.summary or item.source_name
            lines.extend(
                [
                    f"{index}. **{item.title}**",
                    f"   - {item.source_name}",
                    f"   - {summary}",
                    f"   - {item.url}",
                ]
            )
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def render_html(config: MorningPaperConfig, collected: dict[str, list[SourceItem]], *, date_str: str) -> str:
    banner = _banner_item(collected)
    html_parts = [
        "<!doctype html>",
        "<html><head><meta charset='utf-8'>",
        f"<title>{html.escape(config.name)} — {html.escape(date_str)}</title>",
        "<style>",
        "body{font-family:Georgia,serif;max-width:8.5in;margin:0 auto;padding:0.5in;background:#f8f5ee;color:#111;line-height:1.45;}",
        "h1,h2{font-family:'Courier New',monospace;letter-spacing:.04em;text-transform:uppercase;}",
        ".section{margin-top:0.4in;}",
        ".item{margin-bottom:0.18in;padding-bottom:0.12in;border-bottom:1px solid #ddd;}",
        ".meta{font-size:0.9em;color:#555;}",
        "a{color:#111;}",
        "</style></head><body>",
        f"<h1>{html.escape(config.name)}</h1>",
        f"<p><em>{html.escape(date_str)}</em></p>",
    ]
    if config.profile:
        html_parts.append(f"<p>{html.escape(config.profile.strip())}</p>")
    if banner:
        html_parts.extend(
            [
                "<div class='section'>",
                "<h2>Banner</h2>",
                f"<div class='item'><strong>{html.escape(banner.title)}</strong><div class='meta'>{html.escape(banner.summary or banner.source_name)}</div><div><a href='{html.escape(banner.url)}'>{html.escape(banner.url)}</a></div></div>",
                "</div>",
            ]
        )
    for label, key in (("Hacker News", "hacker_news"), ("RSS", "rss")):
        items = collected.get(key) or []
        if not items:
            continue
        html_parts.append(f"<div class='section'><h2>{html.escape(label)}</h2>")
        for item in items:
            html_parts.append(
                "<div class='item'>"
                f"<strong>{html.escape(item.title)}</strong>"
                f"<div class='meta'>{html.escape(item.source_name)}"
                + (f" · {html.escape(item.summary)}" if item.summary else "")
                + "</div>"
                f"<div><a href='{html.escape(item.url)}'>{html.escape(item.url)}</a></div>"
                "</div>"
            )
        html_parts.append("</div>")
    html_parts.append("</body></html>")
    return "\n".join(html_parts)


def render_typewriter_html(config: MorningPaperConfig, collected: dict[str, list[SourceItem]], *, date_str: str) -> str:
    markdown = render_typewriter_markdown(config, collected, date_str=date_str)
    return _render_html_from_markdown(markdown)


def render_pdf(config: MorningPaperConfig, collected: dict[str, list[SourceItem]], *, date_str: str, output_path: Path) -> None:
    pdf = FPDF(format="Letter")
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()
    pdf.set_title(f"{config.name} — {date_str}")
    pdf.set_author("Morning Paper")
    width = pdf.w - pdf.l_margin - pdf.r_margin
    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(width, 10, _pdf_text(config.name), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(width, 8, _pdf_text(date_str), new_x="LMARGIN", new_y="NEXT")
    if config.profile:
        pdf.ln(2)
        pdf.multi_cell(width, 6, _pdf_text(config.profile.strip()))
    banner = _banner_item(collected)
    if banner:
        pdf.ln(4)
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(width, 8, "Banner", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "B", 12)
        pdf.multi_cell(width, 6, _pdf_text(banner.title))
        pdf.set_font("Helvetica", "", 11)
        pdf.multi_cell(width, 6, _pdf_text(banner.summary or banner.source_name))
        pdf.multi_cell(width, 6, _pdf_text(banner.url))
    for label, key in (("Hacker News", "hacker_news"), ("RSS", "rss")):
        items = collected.get(key) or []
        if not items:
            continue
        pdf.ln(4)
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(width, 8, label, new_x="LMARGIN", new_y="NEXT")
        for index, item in enumerate(items, 1):
            pdf.set_font("Helvetica", "B", 11)
            pdf.multi_cell(width, 6, _pdf_text(f"{index}. {item.title}"))
            pdf.set_font("Helvetica", "", 10)
            meta = _pdf_text(item.summary or item.source_name)
            pdf.multi_cell(width, 5, meta)
            pdf.multi_cell(width, 5, _pdf_text(item.url))
            pdf.ln(1)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(output_path))


def _render_html_from_markdown(markdown: str) -> str:
    meta, body = _split_frontmatter(markdown)
    css = str(meta.get("css", "")).strip()
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


def _render_typewriter_pdf(markdown: str, *, output_path: Path) -> None:
    html_cls, error = _load_weasyprint()
    if html_cls is None:
        raise RuntimeError(error or "WeasyPrint unavailable")
    html_doc = _render_html_from_markdown(markdown)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    html_cls(string=html_doc, base_url=str(output_path.parent)).write_pdf(str(output_path))


def _render_markdown_text_pdf(config: MorningPaperConfig, markdown: str, *, date_str: str, output_path: Path) -> None:
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
    pdf.output(str(output_path))


def write_outputs(config: MorningPaperConfig, collected: dict[str, list[SourceItem]], *, date_str: str) -> tuple[dict[str, Path], list[str]]:
    paths = output_paths(config, date_str)
    paths["dir"].mkdir(parents=True, exist_ok=True)
    warnings: list[str] = []
    markdown = (
        render_typewriter_markdown(config, collected, date_str=date_str)
        if config.outputs.renderer == "typewriter"
        else render_markdown(config, collected, date_str=date_str)
    )
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "date": date_str,
        "name": config.name,
        "renderer": config.outputs.renderer,
        "items": {key: [asdict(item) for item in items] for key, items in collected.items()},
    }
    if config.outputs.json:
        paths["json"].write_text(json.dumps(payload, indent=2), encoding="utf-8")
    if config.outputs.markdown:
        paths["markdown"].write_text(markdown, encoding="utf-8")
    if config.outputs.html:
        html_text = (
            render_typewriter_html(config, collected, date_str=date_str)
            if config.outputs.renderer == "typewriter"
            else render_html(config, collected, date_str=date_str)
        )
        paths["html"].write_text(html_text, encoding="utf-8")
    if config.outputs.pdf:
        if config.outputs.renderer == "typewriter":
            try:
                _render_typewriter_pdf(markdown, output_path=paths["pdf"])
            except Exception as exc:
                raise TypewriterRendererUnavailable(
                    "typewriter renderer requires the pretty print stack. "
                    "Install `morning-paper[pretty]` and any required system libraries "
                    "(for macOS: `brew install pango gdk-pixbuf`), or set "
                    "`outputs.renderer: portable` if you explicitly want the fallback PDF. "
                    f"Detail: {exc}"
                )
        else:
            render_pdf(config, collected, date_str=date_str, output_path=paths["pdf"])
    return paths, warnings


def write_custom_markdown(
    config: MorningPaperConfig,
    markdown: str,
    *,
    date_str: str,
    slug: str,
    metadata: dict[str, object] | None = None,
) -> tuple[dict[str, Path], list[str]]:
    paths = custom_output_paths(config, date_str, slug=slug)
    paths["dir"].mkdir(parents=True, exist_ok=True)
    warnings: list[str] = []
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
        paths["html"].write_text(_render_html_from_markdown(markdown), encoding="utf-8")
    if config.outputs.pdf:
        if config.outputs.renderer == "typewriter":
            try:
                _render_typewriter_pdf(markdown, output_path=paths["pdf"])
            except Exception as exc:
                raise TypewriterRendererUnavailable(
                    "typewriter renderer requires the pretty print stack. "
                    "Install `morning-paper[pretty]` and any required system libraries "
                    "(for macOS: `brew install pango gdk-pixbuf`), or set "
                    "`outputs.renderer: portable` if you explicitly want the fallback PDF. "
                    f"Detail: {exc}"
                )
        else:
            _render_markdown_text_pdf(config, markdown, date_str=date_str, output_path=paths["pdf"])
    return paths, warnings
