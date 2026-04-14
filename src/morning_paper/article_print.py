from __future__ import annotations

import html
import re
from dataclasses import dataclass
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


def _extract_body(url: str, raw_html: str) -> str:
    try:
        reader = _reader_text(url)
        lines = [line.strip() for line in reader.splitlines() if line.strip()]
        return "\n\n".join(lines[2:18]) if len(lines) > 2 else "\n\n".join(lines[:16])
    except Exception:
        return _clean_text(raw_html)[:3000]


def fetch_article(url: str) -> Article:
    response = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()
    raw_html = response.text
    title = _meta_content(raw_html, "og:title")
    if not title:
        match = re.search(r"<title>(.*?)</title>", raw_html, flags=re.IGNORECASE | re.DOTALL)
        title = _clean_text(match.group(1)) if match else url
    author = _meta_content(raw_html, "author") or _meta_content(raw_html, "twitter:creator")
    site_name = _meta_content(raw_html, "og:site_name") or urlparse(url).netloc
    image_url = _meta_content(raw_html, "og:image")
    body = _extract_body(url, raw_html)
    return Article(
        url=url,
        title=title,
        author=author,
        source_name=site_name,
        body=body,
        image_url=image_url,
    )


def render_article_markdown(config: MorningPaperConfig, articles: list[Article], *, date_str: str, images_dir: Path) -> str:
    template = _package_template_text("typewriter.md")
    image_blocks: list[str] = []
    full_reads: list[str] = []
    for article in articles:
        relative_image = ""
        if article.image_url:
            try:
                image_name = f"{_safe_filename(article.title)[:32] or 'article'}.png"
                img_path = process_for_print(article.image_url, output_path=images_dir / image_name)
                relative_image = img_path.relative_to(images_dir.parent).as_posix()
            except Exception:
                relative_image = ""
        image_html = (
            f'<p><img src="{html.escape(relative_image)}" alt="{html.escape(article.title)}" /></p>'
            if relative_image
            else ""
        )
        body_paragraphs = []
        for paragraph in [p.strip() for p in article.body.split("\n\n") if p.strip()][:6]:
            body_paragraphs.append(f"<p>{html.escape(paragraph)}</p>")
        full_reads.append(
            '<div class="full-read">'
            f'<div class="full-read-title">{html.escape(article.title)}</div>'
            f'<div class="full-read-source">{html.escape(article.source_name)}'
            + (f" — {html.escape(article.author)}" if article.author else "")
            + "</div>"
            + image_html
            + f'<div class="full-read-body">{"".join(body_paragraphs)}</div>'
            + f'<p><a href="{html.escape(article.url)}">{html.escape(article.url)}</a></p>'
            + "</div>"
        )
        image_blocks.append(image_html)
    while len(full_reads) < 2:
        full_reads.append("<p>No full read available.</p>")
    replacements = {
        "{DATE}": _display_date(date_str),
        "{TIME}": _display_time(config.timezone),
        "{LOCATION}": "AT HOME",
        '<!-- Banner, tweet count, HN count, runtime -->': _render_info_row(None, len(articles), 0, config.outputs.renderer),
        '<!-- Tweets: short ones (< 180 chars) paired 2-col, long ones full-width -->': "<p>Article print mode.</p>",
        '<!-- Full Read content -->': full_reads[0],
        '<!-- Second Full Read -->': full_reads[1],
        '<!-- HN cards go here -->': "<p>No Hacker News section in article print mode.</p>",
        '<!-- Community content -->': "<p>Private harness only.</p>",
        '<!-- Agency content -->': "<p>Private harness only.</p>",
        '<!-- Ops content -->': "<p>Private harness only.</p>",
        '<!-- Pipeline status -->': "<p>Article print pipeline active.</p>",
        '<!-- Action items -->': "<p>Read and annotate.</p>",
        '<!-- Reference links -->': "<p>Generated by Morning Paper print.</p>",
    }
    for needle, value in replacements.items():
        template = template.replace(needle, value)
    return template
