from __future__ import annotations

import html
import json
import unicodedata
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from fpdf import FPDF

from .config import MorningPaperConfig
from .models import SourceItem


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


def write_outputs(config: MorningPaperConfig, collected: dict[str, list[SourceItem]], *, date_str: str) -> dict[str, Path]:
    paths = output_paths(config, date_str)
    paths["dir"].mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "date": date_str,
        "name": config.name,
        "items": {key: [asdict(item) for item in items] for key, items in collected.items()},
    }
    if config.outputs.json:
        paths["json"].write_text(json.dumps(payload, indent=2), encoding="utf-8")
    if config.outputs.markdown:
        paths["markdown"].write_text(render_markdown(config, collected, date_str=date_str), encoding="utf-8")
    if config.outputs.html:
        paths["html"].write_text(render_html(config, collected, date_str=date_str), encoding="utf-8")
    if config.outputs.pdf:
        render_pdf(config, collected, date_str=date_str, output_path=paths["pdf"])
    return paths
