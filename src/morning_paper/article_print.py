from __future__ import annotations

import html
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import requests

from .config import MorningPaperConfig
from .image_tools import process_for_print
from .renderers import _display_date, _display_time, _package_template_text, _render_info_row, _safe_filename


@dataclass(slots=True)
class Article:
    url: str
    title: str
    author: str
    source_name: str
    body: str
    image_url: str = ""
    profile_image_url: str = ""


def _clean_text(value: str) -> str:
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    return " ".join(value.split())


def _meta_content(html_text: str, key: str) -> str:
    patterns = [
        rf'<meta[^>]+property=["\']{re.escape(key)}["\'][^>]+content=["\']([^"\']+)["\']',
        rf'<meta[^>]+name=["\']{re.escape(key)}["\'][^>]+content=["\']([^"\']+)["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, html_text, flags=re.IGNORECASE)
        if match:
            return html.unescape(match.group(1).strip())
    return ""


def _reader_url(url: str) -> str:
    if url.startswith("https://"):
        return "https://r.jina.ai/http://" + url.removeprefix("https://")
    if url.startswith("http://"):
        return "https://r.jina.ai/http://" + url.removeprefix("http://")
    return "https://r.jina.ai/http://" + url


def _reader_text(url: str) -> str:
    response = requests.get(_reader_url(url), timeout=40)
    response.raise_for_status()
    return response.text


def _reader_metadata(url: str) -> dict[str, object]:
    try:
        reader = _reader_text(url)
    except Exception:
        return {"paragraphs": [], "title": "", "author": "", "image_url": "", "profile_image_url": ""}
    title = ""
    author = ""
    image_url = ""
    profile_image_url = ""
    title_match = re.search(r"^Title:\s*(.+)$", reader, flags=re.MULTILINE)
    if title_match:
        title = title_match.group(1).strip()
        x_match = re.match(r'^(.*?) on X: "(.*)" / X$', title)
        if x_match:
            author = x_match.group(1).strip()
            title = x_match.group(2).strip()
    image_matches = re.findall(r"!\[[^\]]*\]\((https://pbs\.twimg\.com[^)]+)\)", reader)
    if image_matches:
        preferred = [match for match in image_matches if "/media/" in match]
        profile = [match for match in image_matches if "/profile_images/" in match]
        image_url = (preferred[0] if preferred else image_matches[0]).replace("&name=small", "&name=large")
        if profile:
            profile_image_url = profile[0]
    paragraphs: list[str] = []
    noise = (
        "markdown content:",
        "[subscribe]",
        "http://",
        "https://",
        "published time:",
        "image:",
    )
    for raw in reader.splitlines():
        line = raw.strip()
        if not line:
            continue
        lowered = line.lower()
        if any(token in lowered for token in noise):
            continue
        if lowered.startswith("#"):
            continue
        if lowered.startswith("title:") or lowered.startswith("url source:"):
            continue
        if line.startswith("[!["):
            continue
        if len(line) < 40:
            continue
        if line in {")", "(", "].", ".)"}:
            continue
        if line.endswith("(") or line.endswith(")") or line.endswith(")."):
            continue
        if re.fullmatch(r"[\W_]+", line):
            continue
        paragraphs.append(line)
    return {
        "paragraphs": paragraphs,
        "title": title,
        "author": author,
        "image_url": image_url,
        "profile_image_url": profile_image_url,
    }


def _extract_body(url: str, raw_html: str) -> str:
    reader_paragraphs = _reader_metadata(url).get("paragraphs", [])
    if reader_paragraphs:
        return "\n\n".join(reader_paragraphs[:18])
    cleaned = _clean_text(raw_html)
    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    return "\n\n".join(sentence for sentence in sentences[:18] if sentence)[:4500]


def fetch_article(url: str) -> Article:
    response = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()
    raw_html = response.text
    reader_meta = _reader_metadata(url)
    title = _meta_content(raw_html, "og:title")
    if not title:
        match = re.search(r"<title>(.*?)</title>", raw_html, flags=re.IGNORECASE | re.DOTALL)
        title = _clean_text(match.group(1)) if match else url
    if reader_meta.get("title") and (title == url or "on x:" in title.lower() or title.lower() == "x"):
        title = str(reader_meta["title"])
    author = _meta_content(raw_html, "author") or _meta_content(raw_html, "twitter:creator") or str(reader_meta.get("author") or "")
    parsed = urlparse(url)
    handle = ""
    path_parts = [part for part in parsed.path.split("/") if part]
    if parsed.netloc.endswith("x.com") and path_parts:
        handle = f"@{path_parts[0]}"
    site_name = handle or _meta_content(raw_html, "og:site_name") or parsed.netloc
    image_url = _meta_content(raw_html, "og:image") or str(reader_meta.get("image_url") or "")
    body = _extract_body(url, raw_html)
    return Article(
        url=url,
        title=title,
        author=author,
        source_name=site_name,
        body=body,
        image_url=image_url,
        profile_image_url=str(reader_meta.get("profile_image_url") or ""),
    )


def render_article_markdown(config: MorningPaperConfig, articles: list[Article], *, date_str: str, images_dir: Path) -> str:
    date_label = datetime.fromisoformat(date_str).strftime("%A, %B %d, %Y")
    css = """
@import url('https://fonts.googleapis.com/css2?family=Courier+Prime:ital,wght@0,400;0,700;1,400&display=swap');
body { font-family: 'Courier Prime', 'Courier New', Courier, monospace; font-size: 9pt; line-height: 1.38; color: #111; background: #fff; }
@page { size: Letter; margin: 0.5in 0.48in 0.62in 0.48in; }
.paper-header { text-align: center; margin-bottom: 0.1in; }
.paper-date { font-size: 17.5pt; font-weight: 700; letter-spacing: 0.03em; }
.paper-subtitle { font-size: 7.6pt; color: #666; margin-top: 0.035in; letter-spacing: 0.065em; }
.paper-rule { border-bottom: 1.8px solid #111; margin-top: 0.07in; }
.article { margin-top: 0.08in; }
.article-title { font-size: 12.8pt; font-weight: 700; text-transform: uppercase; letter-spacing: 0.03em; margin-bottom: 0.06in; }
.article-body { column-count: 2; column-gap: 0.18in; font-size: 8.8pt; line-height: 1.32; color: #000; }
.article-body::after { content: ""; display: block; clear: both; }
.meta-card { float: left; width: 1.55in; border: 1.2px solid #111; padding: 0.055in; font-size: 7pt; background: #fff; margin: 0.01in 0.12in 0.08in 0; break-inside: avoid; }
.meta-top { display: grid; grid-template-columns: 0.44in 1fr; gap: 0.06in; align-items: start; }
.meta-avatar { width: 0.42in; height: 0.42in; object-fit: cover; border: 1px solid #bbb; }
.meta-author { font-weight: 700; margin-bottom: 0.03in; }
.meta-handle { color: #555; margin-bottom: 0.04in; }
.meta-stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.04in; margin: 0.05in 0; }
.meta-stat-label { font-size: 5.5pt; color: #666; text-transform: uppercase; }
.meta-stat-value { font-size: 7pt; font-weight: 700; }
.meta-image { width: 100%; margin-top: 0.06in; border: 1px solid #cfcfcf; }
.article-body p { margin: 0 0 0.05in 0; text-align: justify; text-indent: 0.13in; }
.article-body p:first-child { text-indent: 0; }
.article-quote { font-style: italic; font-size: 7.6pt; margin-top: 0.08in; color: #222; }
.article-link { font-size: 6.4pt; color: #444; margin-top: 0.03in; word-break: break-word; }
a { color: #111; text-decoration: underline; }
"""
    sections: list[str] = [
        "---",
        "pdf_options:",
        "  format: Letter",
        "  margin: 0.62in 0.55in 0.72in 0.55in",
        "  printBackground: true",
        "  displayHeaderFooter: true",
        "  headerTemplate: \"<span></span>\"",
        "  footerTemplate: \"<div style='font-size:7pt;color:#111;font-family:Courier New,monospace;width:100%;padding:0 0.55in;'><div style='display:flex;justify-content:space-between;align-items:baseline;'><span>Morning Paper</span><span>Page <span class='pageNumber'></span> of <span class='totalPages'></span></span></div></div>\"",
        "css: |",
    ]
    for line in css.strip().splitlines():
        sections.append(f"  {line}")
    sections.extend(
        [
            "---",
            '<div class="paper-header">',
            f'<div class="paper-date">{html.escape(date_label)}</div>',
            '<div class="paper-subtitle">Curated Intelligence · Volume 1</div>',
            '<div class="paper-rule"></div>',
            "</div>",
        ]
    )

    for article in articles:
        relative_image = ""
        relative_avatar = ""
        if article.image_url:
            try:
                image_name = f"{_safe_filename(article.title)[:32] or 'article'}.png"
                img_path = process_for_print(article.image_url, output_path=images_dir / image_name)
                relative_image = img_path.relative_to(images_dir.parent).as_posix()
            except Exception:
                relative_image = ""
        if article.profile_image_url:
            try:
                avatar_name = f"{_safe_filename(article.author or article.source_name)[:24] or 'author'}-avatar.png"
                avatar_path = process_for_print(
                    article.profile_image_url,
                    output_path=images_dir / avatar_name,
                    max_width=220,
                )
                relative_avatar = avatar_path.relative_to(images_dir.parent).as_posix()
            except Exception:
                relative_avatar = ""
        paragraphs = [p.strip() for p in article.body.split("\n\n") if p.strip()]
        body_html = "".join(f"<p>{html.escape(p)}</p>" for p in paragraphs[:30])
        meta_card = [
            '<div class="meta-card">',
            '<div class="meta-top">',
            (
                f'<img class="meta-avatar" src="{html.escape(relative_avatar)}" alt="{html.escape(article.author or article.source_name)}" />'
                if relative_avatar
                else '<div></div>'
            ),
            '<div>',
            f'<div class="meta-author">{html.escape(article.author or article.source_name)}</div>',
            f'<div class="meta-handle">{html.escape(article.source_name)}</div>',
            '</div>',
            '</div>',
            '<div class="meta-stats">',
            '<div><div class="meta-stat-label">Date</div><div class="meta-stat-value">' + html.escape(date_str) + "</div></div>",
            '<div><div class="meta-stat-label">Source</div><div class="meta-stat-value">' + html.escape(urlparse(article.url).netloc) + "</div></div>",
            '<div><div class="meta-stat-label">Mode</div><div class="meta-stat-value">Print</div></div>',
            "</div>",
        ]
        if relative_image:
            meta_card.append(f'<img class="meta-image" src="{html.escape(relative_image)}" alt="{html.escape(article.title)}" />')
        meta_card.append("</div>")
        sections.extend(
            [
                '<section class="article">',
                f'<div class="article-title">{html.escape(article.title)}</div>',
                '<div class="article-body">',
                "".join(meta_card),
                body_html,
                "</div>",
                f'<div class="article-link"><a href="{html.escape(article.url)}">{html.escape(article.url)}</a></div>',
                "</section>",
            ]
        )
    return "\n".join(sections)
