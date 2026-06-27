from __future__ import annotations

import html
import io
import json
import os
import subprocess
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

from .charts import expand_chart_directives
from .config import MorningPaperConfig
from .models import SourceItem
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


def _html_paragraphs(text: str, *, limit: int | None = 4) -> str:
    parts = [segment.strip() for segment in (text or "").split("\n") if segment.strip()]
    if limit is not None:
        parts = parts[:limit]
    return "\n".join(f"<p>{html.escape(part)}</p>" for part in parts)


def _render_broadsheet_strip(banner: SourceItem | None, rss_count: int, community_count: int, renderer: str) -> str:
    banner_value = html.escape(
        (banner.title[:64] + "…") if banner and len(banner.title) > 64 else (banner.title if banner else "No banner")
    )
    runtime_value = "Typewriter" if renderer == "typewriter" else "Portable"
    items = (
        ("Banner", banner_value),
        ("Signals", str(rss_count)),
        ("Community", str(community_count)),
        ("Print", html.escape(runtime_value)),
    )
    return "\n".join(
        f'<div class="strip-item"><div class="strip-label">{label}</div><div class="strip-value">{value}</div></div>'
        for label, value in items
    )


def _render_broadsheet_signal_rows(items: list[SourceItem]) -> str:
    if not items:
        return '<p class="not-configured">No signals available — add RSS feeds to your config.</p>'
    rows = ['<table class="data">', "<tr><th>Source</th><th>Signal</th><th>Date</th></tr>"]
    for item in items:
        date_value = html.escape(item.published_at[:10] if item.published_at else "—")
        summary = html.escape((item.summary or "")[:180])
        cell = html.escape(item.title)
        if summary:
            cell += f'<div class="q-u">{summary}</div>'
        rows.append(
            f'<tr><td class="lead">{html.escape(item.source_name)}</td><td>{cell}</td><td>{date_value}</td></tr>'
        )
    rows.append("</table>")
    return "\n".join(rows)


def _render_broadsheet_reads(items: list[SourceItem], *, limit: int = 2) -> str:
    if not items:
        return '<p class="not-configured">No full read available.</p>'
    reads: list[str] = []
    for item in items[:limit]:
        meta_parts = [item.source_name]
        if item.author:
            meta_parts.append(item.author)
        if item.published_at:
            meta_parts.append(item.published_at[:10])
        byline = html.escape(" · ".join(part for part in meta_parts if part))
        # A full-text feed carries the whole article in `body`; print it as a
        # real read (no paragraph cap). Summary-only feeds fall back to the
        # short blurb, still capped — a blurb that pretends to be a read is the
        # thing this avoids.
        if item.body:
            body_html = _html_paragraphs(item.body, limit=None)
        else:
            body_html = _html_paragraphs(item.summary or item.url)
        reads.append(
            '<div class="article-head">'
            f'<div class="dept-title">{html.escape(item.title)}</div>'
            f'<div class="mg-byline">From <strong>{byline}</strong></div>'
            "</div>\n"
            + body_html
        )
    return "\n".join(reads)


def _render_broadsheet_community_rows(items: list[SourceItem]) -> str:
    if not items:
        return '<p class="not-configured">No community signals configured.</p>'
    rows = ['<table class="data">', "<tr><th>#</th><th>Story</th><th>Activity</th></tr>"]
    for index, item in enumerate(items, 1):
        story = html.escape(item.title) + f'<div class="q-u">{html.escape(item.url)}</div>'
        rows.append(
            f'<tr><td class="num">{index}</td><td class="lead">{story}</td>'
            f"<td>{html.escape(item.summary)}</td></tr>"
        )
    rows.append("</table>")
    return "\n".join(rows)


def render_broadsheet_markdown(config: MorningPaperConfig, collected: dict[str, list[SourceItem]], *, date_str: str) -> str:
    """Broadsheet-native build front page: masthead, strip, dept sections.

    The first paper a fresh `init` builds is broadsheet-styled, so the build
    template must speak the broadsheet class vocabulary (the 0.4.3
    first-edition cliff was a template whose classes the configured style
    did not define).
    """
    template = _package_template_text("broadsheet-build.md")
    banner = _banner_item(collected)
    rss_items = collected.get("rss") or []
    hn_items = collected.get("hacker_news") or []
    replacements = {
        "{NAME}": html.escape(config.name),
        "{DATE}": _display_date(date_str),
        "{TIME}": _display_time(config.timezone),
        "{COMMUNITY_COUNT}": str(len(hn_items)),
        "<!-- Strip: banner, signal count, community count, print runtime -->": _render_broadsheet_strip(
            banner, len(rss_items), len(hn_items), config.outputs.renderer
        ),
        "<!-- Signals: RSS items as table.data rows -->": _render_broadsheet_signal_rows(rss_items),
        "<!-- Featured Reads -->": _render_broadsheet_reads(rss_items, limit=2),
        "<!-- Community items as table.data rows -->": _render_broadsheet_community_rows(hn_items),
        "<!-- Reference links -->": (
            '<div class="dept-list">'
            "<p><strong>Sources:</strong> configured feeds, Assignment Board material, and local collectors</p>"
            "<p><strong>Generated by:</strong> Morning Paper</p>"
            "</div>"
        ),
    }
    for needle, value in replacements.items():
        template = template.replace(needle, value)
    return template


def render_build_markdown(config: MorningPaperConfig, collected: dict[str, list[SourceItem]], *, date_str: str) -> str:
    """The build front page for every style.

    Since 0.5.0 there is one build template — the broadsheet-native one. Its
    vocabulary is the closest match in every pack and degrades to readable
    text everywhere; the retired typewriter template's users (now the `brief`
    alias path) route here too.
    """
    return render_broadsheet_markdown(config, collected, date_str=date_str)


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
        lines.extend(["## Community Signals", ""])
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
            # Full-text feeds carry the whole article in `body`; print it.
            # Summary-only feeds keep the short blurb.
            read = item.body or item.summary or item.source_name
            lines.extend(
                [
                    f"{index}. **{item.title}**",
                    f"   - {item.source_name}",
                    f"   - {read}",
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
    for label, key in (("Community Signals", "hacker_news"), ("RSS", "rss")):
        items = collected.get(key) or []
        if not items:
            continue
        html_parts.append(f"<div class='section'><h2>{html.escape(label)}</h2>")
        for item in items:
            source_name = label if key == "hacker_news" else item.source_name
            html_parts.append(
                "<div class='item'>"
                f"<strong>{html.escape(item.title)}</strong>"
                f"<div class='meta'>{html.escape(source_name)}"
                + (f" · {html.escape(item.summary)}" if item.summary else "")
                + "</div>"
                f"<div><a href='{html.escape(item.url)}'>{html.escape(item.url)}</a></div>"
                "</div>"
            )
        html_parts.append("</div>")
    html_parts.append("</body></html>")
    return "\n".join(html_parts)


def render_typewriter_html(config: MorningPaperConfig, collected: dict[str, list[SourceItem]], *, date_str: str) -> str:
    markdown = render_build_markdown(config, collected, date_str=date_str)
    return _render_html_from_markdown(
        markdown,
        style=config.outputs.style,
        palette=config.outputs.palette,
        font_scale=config.outputs.font_scale,
    )


_STAGED_PLACEHOLDER = "<!-- Staged for today -->"


def _staged_section(config: MorningPaperConfig, date_str: str) -> tuple[str, list[str], list[str]]:
    """Collect Assignment Board material for this edition date into markdown.

    Returns (fragment, included slugs, warnings). The build pipeline must
    consume what `stage` added — board items silently vanishing from the
    edition was the 0.4.3 P0. Warnings are loud and specific: storage that
    exists but cannot be included is never silent.
    """
    from .staging import staging_dir  # function-level: staging imports renderers at module load

    sdir = staging_dir(config, date_str)
    queue_file = sdir / "queue.json"
    if not queue_file.exists():
        return "", [], []
    try:
        items = json.loads(queue_file.read_text(encoding="utf-8"))
    except Exception as exc:
        return "", [], [
            f"ASSIGNMENT BOARD ITEMS NOT INCLUDED: board storage exists for {date_str} but could not be read "
            f"({queue_file}): {exc}"
        ]
    if not isinstance(items, list) or not items:
        return "", [], []
    included: list[str] = []
    warnings: list[str] = []
    parts: list[str] = []
    for item in items:
        slug = str(item.get("slug") or "")
        md_path = sdir / f"{slug}.md"
        if not slug or not md_path.is_file():
            warnings.append(
                f"ASSIGNMENT BOARD ITEM NOT INCLUDED: '{item.get('title') or slug or '?'}' — source file missing: {md_path}"
            )
            continue
        try:
            staged_markdown = md_path.read_text(encoding="utf-8")
        except Exception as exc:
            warnings.append(
                f"ASSIGNMENT BOARD ITEM NOT INCLUDED: '{item.get('title') or slug}' — source file unreadable: {exc}"
            )
            continue
        _meta, body = _split_frontmatter(staged_markdown)
        title = html.escape(str(item.get("title") or slug))
        source = html.escape(str(item.get("source") or ""))
        # contributor-inbox items carry the masthead name — the kicker says who
        # put this in the reader's paper
        contributor = html.escape(str(item.get("contributor") or ""))
        notice = ""
        if item.get("truncated"):
            detail = html.escape(str(item.get("warning") or "the staged copy is incomplete"))
            notice = f'<div class="trunc-notice">Incomplete: {detail}</div>\n\n'
        kicker = f"From {contributor}" if contributor else f"Source · {html.escape(str(item.get('kind') or 'item'))}"
        head = (
            '<div class="article-head">'
            f'<div class="dept-kicker">{kicker}</div>'
            f'<div class="dept-title">{title}</div>'
            + (f'<div class="mg-byline">From <strong>{source}</strong></div>' if source else "")
            + "</div>\n\n"
        )
        parts.append(head + notice + body.strip() + "\n")
        included.append(slug)
    if not parts:
        return "", [], warnings
    section = (
        '\n<div class="edition-divider"><div class="oxford"></div>'
        '<div class="edition-divider-label">From The Desk</div></div>\n\n'
        + '\n<div class="dept-rule"></div>\n\n'.join(parts)
    )
    return section, included, warnings


def render_pdf(config: MorningPaperConfig, collected: dict[str, list[SourceItem]], *, date_str: str, output_path: Path) -> int:
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
    for label, key in (("Community Signals", "hacker_news"), ("RSS", "rss")):
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
            source_name = label if key == "hacker_news" else item.source_name
            meta = _pdf_text(item.summary or source_name)
            pdf.multi_cell(width, 5, meta)
            pdf.multi_cell(width, 5, _pdf_text(item.url))
            pdf.ln(1)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pages = pdf.page
    pdf.output(str(output_path))
    return pages


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


def write_outputs(
    config: MorningPaperConfig, collected: dict[str, list[SourceItem]], *, date_str: str
) -> tuple[dict[str, Path], list[str], int | None, list[str]]:
    """Write the configured artifacts; returns (paths, warnings, pdf page count, staged slugs).

    The page count is None when no PDF was produced. The staged slugs are the
    queue items from staging/{date} that made it into the edition.
    """
    paths = output_paths(config, date_str)
    paths["dir"].mkdir(parents=True, exist_ok=True)
    warnings: list[str] = []
    pages: int | None = None
    staged_included: list[str] = []
    if config.outputs.renderer == "typewriter":
        markdown = render_build_markdown(config, collected, date_str=date_str)
        staged_fragment, staged_included, staged_warnings = _staged_section(config, date_str)
        warnings.extend(staged_warnings)
        markdown = markdown.replace(_STAGED_PLACEHOLDER, staged_fragment)
    else:
        markdown = render_markdown(config, collected, date_str=date_str)
        # Honesty rule: the portable fallback renders items directly (fpdf),
        # so Assignment Board markdown cannot be typeset into it — say so
        # loudly rather than letting source material vanish.
        _fragment, would_include, staged_warnings = _staged_section(config, date_str)
        warnings.extend(staged_warnings)
        if would_include:
            warnings.append(
                f"ASSIGNMENT BOARD ITEMS NOT INCLUDED: {len(would_include)} item(s) are assigned for {date_str} but the "
                "portable renderer cannot typeset Assignment Board markdown; set `outputs.renderer: typewriter` "
                "to include them"
            )
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "date": date_str,
        "name": config.name,
        "renderer": config.outputs.renderer,
        "staged_included": staged_included,
        "items": {key: [asdict(item) for item in items] for key, items in collected.items()},
    }
    if config.outputs.json:
        paths["json"].write_text(json.dumps(payload, indent=2), encoding="utf-8")
    if config.outputs.markdown:
        paths["markdown"].write_text(markdown, encoding="utf-8")
    if config.outputs.html:
        html_text = (
            _render_html_from_markdown(
                markdown,
                style=config.outputs.style,
                palette=config.outputs.palette,
                font_scale=config.outputs.font_scale,
            )
            if config.outputs.renderer == "typewriter"
            else render_html(config, collected, date_str=date_str)
        )
        paths["html"].write_text(html_text, encoding="utf-8")
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
            pages = render_pdf(config, collected, date_str=date_str, output_path=paths["pdf"])
    return paths, warnings, pages, staged_included


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
