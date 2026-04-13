#!/usr/bin/env python3
"""
Deterministic Pass 4 assembler for the extracted Morning Brief repo.

This is not the final agent-driven synthesis layer. It is the first
versioned assembly entrypoint that:

- validates required inputs
- preserves the extracted template/style contract
- produces a canonical markdown artifact
- keeps the assembly logic out of cron prompts
"""

from __future__ import annotations

import argparse
import html
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable


@dataclass
class Section:
    heading: str
    body: str


@dataclass
class DraftSubsection:
    heading: str
    body: str


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def ensure_inputs(paths: Iterable[Path]) -> None:
    missing = [str(p) for p in paths if not p.exists()]
    if missing:
        raise FileNotFoundError("Missing required input(s):\n- " + "\n- ".join(missing))


def normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def html_p(text: str) -> str:
    return f"<p>{html.escape(text)}</p>"


def markdown_to_html(text: str) -> str:
    """Convert basic markdown to HTML. Handles **bold**, *italic*, - lists, ## headings."""
    lines = text.splitlines()
    html_lines: list[str] = []
    in_list = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            continue

        # Heading
        heading_match = re.match(r"^#{1,6}\s+(.*)$", stripped)
        if heading_match:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            content = heading_match.group(1)
            content = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", content)
            content = re.sub(r"\*(.+?)\*", r"<em>\1</em>", content)
            level = len(heading_match.group(0)) - len(heading_match.group(1))
            html_lines.append(f"<h{level}>{content}</h{level}>")
            continue

        # List item
        list_match = re.match(r"^[-*+]\s+(.*)$", stripped)
        if list_match:
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            content = list_match.group(1)
            content = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", content)
            content = re.sub(r"\*(.+?)\*", r"<em>\1</em>", content)
            html_lines.append(f"<li>{content}</li>")
            continue

        # Close list on non-list content
        if in_list:
            html_lines.append("</ul>")
            in_list = False

        # Inline formatting
        formatted = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", stripped)
        formatted = re.sub(r"\*(.+?)\*", r"<em>\1</em>", formatted)
        html_lines.append(f"<p>{formatted}</p>")

    if in_list:
        html_lines.append("</ul>")

    return "\n".join(html_lines)


def strip_markdown(text: str) -> str:
    text = text.strip()
    text = re.sub(r"`{1,3}", "", text)
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"^\s{0,3}#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*>\s?", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"_(.+?)_", r"\1", text)
    return normalize_ws(text)


def to_slug_label(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")


def parse_candidates(text: str) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for raw in text.splitlines():
        line = raw.rstrip()
        match = re.match(r"^\d+\.\s+\*\*(.+?)\*\*\s+—\s+(.+?)\s+—\s+score:\s+(.+)$", line)
        if match:
            if current:
                items.append(current)
            current = {
                "title": match.group(1).strip(),
                "source": match.group(2).strip(),
                "score": match.group(3).strip(),
                "why": "",
                "link": "",
                "seed_quality": "",
                "already_covered": "",
            }
            continue
        if current is None:
            continue
        stripped = line.strip()
        if stripped.startswith("Why"):
            current["why"] = stripped.split(":", 1)[-1].strip()
        elif stripped.startswith("Link:"):
            current["link"] = stripped.split(":", 1)[-1].strip()
        elif stripped.startswith("Seed quality:"):
            current["seed_quality"] = stripped.split(":", 1)[-1].strip()
        elif stripped.startswith("Already covered:"):
            current["already_covered"] = stripped.split(":", 1)[-1].strip()
    if current:
        items.append(current)
    return items


def render_signals(items: list[dict[str, str]]) -> str:
    blocks = []
    for item in items:
        # For READWISE: no real author, show READWISE as the metadata label
        # For HN: show HN username (author) + source domain
        # Never use tweet text (item["title"]) as the author name
        source = item.get("source", "")
        if source == "READWISE":
            author_display = "READWISE HIGHLIGHT"
            meta_parts = ["READWISE"]
        elif source.startswith("HN"):
            # HN items may have author in a separate field; use source as meta
            author_display = "HACKER NEWS"
            meta_parts = [source]
        else:
            # For blog/other sources, use the source as the author label
            author_display = source.upper() if source else "SIGNAL"
            meta_parts = [source] if source else []

        body = html.escape(item.get("title", "")[:280])
        if item.get("score"):
            score_str = str(item["score"])
            meta_parts.append(f"score {score_str}")
        meta = " — ".join(meta_parts)
        link = html.escape(item.get("link") or "")
        blocks.append(
            "\n".join(
                [
                    '<div class="tweet">',
                    '  <div class="tweet-header">',
                    f'    <div class="tweet-author">{html.escape(author_display)}</div>',
                    f'    <div class="tweet-meta">{html.escape(meta)}</div>',
                    "  </div>",
                    f'  <div class="tweet-text">{body}</div>',
                    f'  <div class="tweet-stats">{link}</div>' if link else "",
                    "</div>",
                ]
            )
        )
    return "\n".join(blocks)


def extract_markdown_sections(text: str) -> list[Section]:
    matches = list(re.finditer(r"^##\s+(.+)$", text, flags=re.MULTILINE))
    sections: list[Section] = []
    for i, match in enumerate(matches):
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections.append(Section(match.group(1).strip(), text[start:end].strip()))
    return sections


def extract_subsections(text: str) -> list[DraftSubsection]:
    matches = list(re.finditer(r"^###\s+(.+)$", text, flags=re.MULTILINE))
    sections: list[DraftSubsection] = []
    for i, match in enumerate(matches):
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections.append(DraftSubsection(match.group(1).strip(), text[start:end].strip()))
    return sections


def section_map(text: str) -> dict[str, str]:
    return {section.heading: section.body for section in extract_markdown_sections(text)}


def first_non_heading_paragraph(text: str) -> str:
    paragraphs = [block.strip() for block in re.split(r"\n\s*\n", text) if block.strip()]
    for paragraph in paragraphs:
        cleaned = strip_markdown(paragraph)
        if cleaned and not cleaned.lower().startswith("devon context"):
            return cleaned
    return ""


def markdown_to_html_paragraphs(text: str, *, limit: int = 8) -> str:
    paragraphs = [block.strip() for block in re.split(r"\n\s*\n", text) if block.strip()]
    blocks: list[str] = []
    for paragraph in paragraphs:
        cleaned = strip_markdown(paragraph)
        if not cleaned or cleaned == "---":
            continue
        if blocks:
            last_plain = strip_markdown(re.sub(r"</?p>", "", blocks[-1]))
            if cleaned == last_plain:
                continue
        blocks.append(html_p(cleaned))
        if len(blocks) >= limit:
            break
    return "\n".join(blocks)


def render_full_read(title: str, body: str) -> str:
    lines = [line.rstrip() for line in body.splitlines() if line.strip()]
    source = ""
    paragraphs: list[str] = []
    for line in lines:
        if line.startswith("Source:") or line.startswith("URL:"):
            if not source:
                source = line
            else:
                source += " | " + line
        else:
            paragraphs.append(line)
    paragraphs_html = markdown_to_html_paragraphs("\n".join(paragraphs), limit=8)
    return "\n".join(
        [
            '<div class="full-read">',
            f'  <div class="full-read-title">{html.escape(title)}</div>',
            f'  <div class="full-read-source">{html.escape(source)}</div>' if source else "",
            '  <div class="full-read-body">',
            paragraphs_html,
            "  </div>",
            "</div>",
        ]
    )


def render_hn_cards(items: list[dict[str, str]]) -> str:
    blocks = []
    for idx, item in enumerate(items[:10], start=1):
        tag = "BANNER" if "banner" in item.get("score", "").lower() or "[banner]" in item.get("score", "").lower() else "SIGNAL"
        blocks.append(
            "\n".join(
                [
                    '<div class="hn-card">',
                    '  <div class="hn-card-header">',
                    f'    <span class="hn-rank">#{idx}</span>',
                    f'    <span class="hn-tag">{tag}</span>',
                    f'    <span class="hn-domain">{html.escape(item["source"])}</span>',
                    "  </div>",
                    f'  <div class="hn-title">{html.escape(item["title"])}</div>',
                    f'  <div class="hn-desc">{html.escape(item.get("why") or item.get("seed_quality") or "")}</div>',
                    f'  <div class="hn-meta">{html.escape(item.get("link") or "")}</div>' if item.get("link") else "",
                    "</div>",
                ]
            )
        )
    return "\n".join(blocks)


def render_content_drafts(text: str) -> str:
    sections = extract_markdown_sections(text)
    blocks = []
    for section in sections:
        lower_heading = section.heading.lower()
        if lower_heading.startswith("full read"):
            continue
        if "devon-specific content drafts" in lower_heading:
            for subsection in extract_subsections(section.body):
                if subsection.heading.lower().startswith("a. skool post"):
                    continue
                body_html = markdown_to_html_paragraphs(subsection.body, limit=8)
                if not body_html:
                    continue
                blocks.append(
                    "\n".join(
                        [
                            '<div class="content-draft">',
                            f'  <div class="draft-label">{html.escape(subsection.heading)}</div>',
                            f'  <div class="draft-body">{body_html}</div>',
                            "</div>",
                        ]
                    )
                )
            continue
        body_html = markdown_to_html_paragraphs(section.body, limit=8)
        if not body_html:
            continue
        blocks.append(
            "\n".join(
                [
                    '<div class="content-draft">',
                    f'  <div class="draft-label">{html.escape(section.heading)}</div>',
                    f'  <div class="draft-body">{body_html}</div>',
                    "</div>",
                ]
            )
        )
    return "\n".join(blocks)


def extract_devon_actions(rabbit_holes_text: str) -> list[str]:
    bullets: list[str] = []
    for match in re.finditer(r"###\s+What This Means for Devon\s*(.*?)(?=\n##|\Z)", rabbit_holes_text, flags=re.DOTALL):
        for raw in match.group(1).splitlines():
            stripped = raw.strip()
            if not re.match(r"^\d+\.", stripped):
                continue
            cleaned = strip_markdown(stripped)
            if cleaned:
                bullets.append(cleaned)
        if bullets:
            break
    return bullets


def render_action_required(candidates: list[dict[str, str]], context_summary: str, rabbit_holes_text: str) -> str:
    bullets = []
    if candidates:
        bullets.append(f"Review banner story: {candidates[0]['title']}")
    if len(candidates) > 1:
        bullets.append(f"Decide whether to deepen: {candidates[1]['title']}")
    devon_actions = extract_devon_actions(rabbit_holes_text)
    if devon_actions:
        bullets.append(devon_actions[0])
    else:
        first_para = first_non_heading_paragraph(context_summary)
        if first_para:
            bullets.append(first_para[:220])
    items = []
    for idx, bullet in enumerate(bullets[:4], start=1):
        items.append(
            "\n".join(
                [
                    '<div class="action-item">',
                    f'  <div class="action-label">Action {idx}</div>',
                    f'  <div class="action-body">{html.escape(bullet)}</div>',
                    "</div>",
                ]
            )
        )
    return "\n".join(
        [
            '<div class="action-required">',
            "  <h2>Action Required</h2>",
            *items,
            "</div>",
        ]
    )


def render_references(candidates: list[dict[str, str]]) -> str:
    refs = []
    for item in candidates[:8]:
        link = item.get("link") or ""
        refs.append(
            f'<div class="ref-item"><span class="ref-label">{html.escape(item["title"])}:</span> {html.escape(link)}</div>'
        )
    return '<div class="ref-list">\n' + "\n".join(refs) + "\n</div>"


def build_info_row(
    context_summary: str,
    candidates: list[dict[str, str]],
    weather_text: str = "Weather: unavailable",
    paperclip_status: str = "Paperclip: OK",
) -> str:
    summary = first_non_heading_paragraph(context_summary)
    top_story = candidates[0]["title"] if candidates else "No candidate stories"
    story_count = str(len(candidates))
    blocks = [
        ("Weather", weather_text),
        ("Paperclip", paperclip_status),
        ("Top Story", top_story[:120] if top_story else "No candidate stories"),
        ("Signals", story_count),
    ]
    html_blocks = []
    for label, value in blocks:
        html_blocks.append(
            "\n".join(
                [
                    '<div class="info-block">',
                    f'  <div class="info-label">{html.escape(label)}</div>',
                    f'  <div class="info-value">{html.escape(value)}</div>',
                    "</div>",
                ]
            )
        )
    return '<div class="info-row">\n' + "\n".join(html_blocks) + "\n</div>"


def render_skool_or_context(content_drafts_text: str, context_summary_text: str) -> str:
    for section in extract_markdown_sections(content_drafts_text):
        if "devon-specific content drafts" not in section.heading.lower():
            continue
        for subsection in extract_subsections(section.body):
            if "skool" not in subsection.heading.lower():
                continue
            body = markdown_to_html_paragraphs(subsection.body, limit=8)
            title = "Main Branch Skool Community Post"
            title_html = html.escape(title)
            leading_title = f"<p>{title_html}</p>"
            if body.startswith(leading_title):
                body = body[len(leading_title):].lstrip()
            if body:
                return "\n".join(
                    [
                        '<div class="skool-post">',
                        f'  <div class="skool-title">{title_html}</div>',
                        f'  <div class="skool-body">{body}</div>',
                        "</div>",
                    ]
                )
    excerpt = first_non_heading_paragraph(context_summary_text) or "No Skool/community snapshot available."
    return "\n".join(
        [
            '<div class="skool-post">',
            '  <div class="skool-title">Community / Direction Snapshot</div>',
            f'  <div class="skool-body">{html_p(excerpt)}</div>',
            "</div>",
        ]
    )


def render_operations(
    context_summary_text: str,
    rabbit_holes_text: str,
    activity_log_text: str = "",
    maintenance_log_text: str = "",
) -> str:
    bullets: list[str] = []
    match = re.search(r"##\s+Project Index\s*(.*)", context_summary_text, flags=re.DOTALL)
    if match:
        for raw in match.group(1).splitlines():
            stripped = raw.strip()
            if not stripped.startswith("-"):
                continue
            cleaned = strip_markdown(stripped)
            if cleaned:
                bullets.append(cleaned)
    for match in re.finditer(r"###\s+What This Means for Devon\s*(.*?)(?=\n##|\Z)", rabbit_holes_text, flags=re.DOTALL):
        for raw in match.group(1).splitlines():
            stripped = raw.strip()
            if not re.match(r"^\d+\.", stripped):
                continue
            cleaned = strip_markdown(stripped)
            if cleaned:
                bullets.append(cleaned)
        if len(bullets) >= 6:
            break
    if not bullets:
        fallback = first_non_heading_paragraph(context_summary_text) or strip_markdown(rabbit_holes_text[:400])
        if fallback:
            bullets.append(fallback)
    ops_parts: list[str] = []
    if maintenance_log_text.strip():
        # Parse markdown into HTML before wrapping — avoids raw **bold** staying as literal text
        md_html = markdown_to_html(maintenance_log_text.strip())
        ops_parts.append(f'<div class="activity-log">{md_html}</div>')
    if activity_log_text.strip():
        # Parse markdown into HTML before wrapping — avoids raw **bold** staying as literal text
        md_html = markdown_to_html(activity_log_text.strip())
        ops_parts.append(f'<div class="activity-log">{md_html}</div>')
    if bullets:
        ops_parts.append("<ul>\n" + "\n".join(f"<li>{html.escape(bullet)}</li>" for bullet in bullets if bullet) + "\n</ul>")
    return "\n\n".join(ops_parts)


def render_pipeline_status(input_paths: list[Path]) -> str:
    items = []
    for path in input_paths:
        items.append(f"<li>{html.escape(path.name)} — present</li>")
    return "<ul>\n" + "\n".join(items) + "\n</ul>"


def assemble(
    template_text: str,
    *,
    date_label: str,
    time_label: str,
    location: str,
    candidates_text: str,
    rabbit_holes_text: str,
    content_drafts_text: str,
    context_summary_text: str,
    activity_log_text: str = "",
    maintenance_log_text: str = "",
    weather_text: str = "Weather: unavailable",
    paperclip_status_text: str = "Paperclip: OK",
    input_paths: list[Path],
) -> str:
    candidates = parse_candidates(candidates_text)
    draft_sections = section_map(content_drafts_text)

    full_read_keys = [key for key in draft_sections if key.lower().startswith("full read")]
    full_read_1 = (
        render_full_read(full_read_keys[0], draft_sections[full_read_keys[0]])
        if full_read_keys
        else '<div class="full-read"><div class="full-read-title">Full Read I</div><div class="full-read-body"><p>No full read available.</p></div></div>'
    )
    full_read_2 = (
        render_full_read(full_read_keys[1], draft_sections[full_read_keys[1]])
        if len(full_read_keys) > 1
        else '<div class="full-read"><div class="full-read-title">Full Read II</div><div class="full-read-body"><p>No second full read available.</p></div></div>'
    )

    template_text = template_text.replace("{DATE}", date_label)
    template_text = template_text.replace("{TIME}", time_label)
    template_text = template_text.replace("{LOCATION}", location)

    info_row = build_info_row(context_summary_text, candidates, weather_text, paperclip_status_text)
    template_text = re.sub(
        r'<div class="info-row">\s*<!-- Weather, Paperclip, Banner -->\s*</div>',
        info_row,
        template_text,
        count=1,
        flags=re.DOTALL,
    )

    replacements = [
        (r"Tweets: short ones \(< 180 chars\) paired 2-col, long ones full-width", render_signals(candidates)),
        (r"Full Read content", full_read_1),
        (r"Second Full Read", full_read_2),
        (r"HN cards go here", render_hn_cards(candidates)),
        (r"Community content", render_skool_or_context(content_drafts_text, context_summary_text)),
        (r"Agency content", render_content_drafts(content_drafts_text)),
        (r"Ops content", render_operations(context_summary_text, rabbit_holes_text, activity_log_text, maintenance_log_text)),
        (r"Pipeline status", render_pipeline_status(input_paths)),
        (r"Action items", render_action_required(candidates, context_summary_text, rabbit_holes_text)),
        (r"Reference links", render_references(candidates)),
    ]
    for marker, replacement in replacements:
        template_text = re.sub(rf"<!--\s*{marker}\s*-->", lambda _: replacement, template_text, count=1)
    return template_text + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Assemble a canonical Morning Brief markdown artifact.")
    parser.add_argument("--template", required=True, help="Path to the extracted template markdown")
    parser.add_argument("--candidates", required=True, help="Path to candidates markdown")
    parser.add_argument("--rabbit-holes", required=True, dest="rabbit_holes", help="Path to rabbit-holes markdown")
    parser.add_argument("--content-drafts", required=True, dest="content_drafts", help="Path to content-drafts markdown")
    parser.add_argument("--context-summary", required=True, dest="context_summary", help="Path to Devon context summary")
    parser.add_argument("--activity-log", dest="activity_log", help="Path to Thoth activity log markdown (optional)")
    parser.add_argument("--maintenance-log", dest="maintenance_log", help="Path to runtime maintenance markdown (optional)")
    parser.add_argument("--output", required=True, help="Path to write assembled markdown")
    parser.add_argument("--date-label", required=True, help="Display date label, e.g. 5 APRIL 2026")
    parser.add_argument("--time-label", default="0600 PT", help="Display time label")
    parser.add_argument("--location", default="AT HOME", help="Display location label")
    parser.add_argument("--weather", default="Weather: unavailable", help="Weather status string (e.g. '72°F / AQI 45')")
    parser.add_argument("--paperclip-status", default="Paperclip: OK", help="Paperclip health status string")
    parser.add_argument("--metadata-output", help="Optional JSON metadata output path")
    args = parser.parse_args()

    input_paths = [
        Path(args.template),
        Path(args.candidates),
        Path(args.rabbit_holes),
        Path(args.content_drafts),
        Path(args.context_summary),
    ]
    ensure_inputs(input_paths)

    activity_log_text = ""
    if args.activity_log:
        al_path = Path(args.activity_log)
        if al_path.exists():
            activity_log_text = al_path.read_text(encoding="utf-8")

    maintenance_log_text = ""
    if args.maintenance_log:
        ml_path = Path(args.maintenance_log)
        if ml_path.exists():
            maintenance_log_text = ml_path.read_text(encoding="utf-8")

    assembled = assemble(
        read_text(Path(args.template)),
        date_label=args.date_label,
        time_label=args.time_label,
        location=args.location,
        candidates_text=read_text(Path(args.candidates)),
        rabbit_holes_text=read_text(Path(args.rabbit_holes)),
        content_drafts_text=read_text(Path(args.content_drafts)),
        context_summary_text=read_text(Path(args.context_summary)),
        activity_log_text=activity_log_text,
        maintenance_log_text=maintenance_log_text,
        weather_text=args.weather,
        paperclip_status_text=args.paperclip_status,
        input_paths=input_paths,
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(assembled, encoding="utf-8")

    metadata = {
        "output": str(output_path),
        "assembled_at": datetime.now().isoformat(),
        "inputs": {to_slug_label(path.stem): str(path) for path in input_paths},
        "size_bytes": output_path.stat().st_size,
    }
    if args.metadata_output:
        meta_path = Path(args.metadata_output)
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print(json.dumps(metadata, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
