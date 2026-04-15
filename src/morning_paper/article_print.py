from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import requests

from .config import MorningPaperConfig
from .image_tools import process_for_print
from .renderers import _display_date, _display_time, _package_template_text, _render_info_row, _safe_filename


class ArticleExtractionError(RuntimeError):
    pass


SKIP_DOMAINS = {
    "github.com",
    "www.github.com",
    "youtube.com",
    "www.youtube.com",
    "youtu.be",
    "news.ycombinator.com",
    "instagram.com",
    "www.instagram.com",
    "linkedin.com",
    "www.linkedin.com",
}

FAILURE_MARKERS = (
    "this page explicitly specify a timeout",
    "this page maybe not yet fully loaded",
    "people on x are the first to know",
    "don't miss what's happening",
    "join x today",
    "log in to x",
    "sign up for x",
)


@dataclass(slots=True)
class Article:
    url: str
    title: str
    author: str
    source_name: str
    body: str
    image_url: str = ""
    profile_image_url: str = ""
    blocks: list[tuple[str, str]] = field(default_factory=list)


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


def _normalized_domain(url: str) -> str:
    return urlparse(url).netloc.lower()


def _validate_article_content(url: str, *, title: str, body: str, blocks: list[tuple[str, str]]) -> None:
    domain = _normalized_domain(url)
    if domain in SKIP_DOMAINS:
        raise ArticleExtractionError(
            f"Could not extract article from this URL. `{domain}` is not supported by the public article printer yet."
        )

    text_fragments = [title, body]
    text_fragments.extend(value for kind, value in blocks if kind != "image")
    combined = "\n".join(part for part in text_fragments if part).strip()
    lowered = combined.lower()

    if any(marker in lowered for marker in FAILURE_MARKERS):
        if domain.endswith("x.com") or domain.endswith("twitter.com"):
            raise ArticleExtractionError(
                "Could not extract article from this URL. X.com requires authenticated or rendered access for this post."
            )
        raise ArticleExtractionError(
            "Could not extract article from this URL. The fetched page returned a shell or timeout response instead of article content."
        )

    real_text = re.sub(r"\s+", " ", combined)
    if len(real_text) < 200:
        raise ArticleExtractionError(
            "Could not extract enough article content to render a print page. Try another URL or a source with full readable text."
        )

    normalized_title = title.strip().lower()
    if normalized_title in {"x", "twitter / x", "x / x"}:
        if domain.endswith("x.com") or domain.endswith("twitter.com"):
            raise ArticleExtractionError(
                "Could not extract article from this X URL. The page title did not resolve to the actual post."
            )
        raise ArticleExtractionError(
            "Could not extract a valid article title from this URL."
        )


def _reader_metadata(url: str) -> dict[str, object]:
    try:
        reader = _reader_text(url)
    except Exception:
        return {
            "paragraphs": [],
            "blocks": [],
            "title": "",
            "author": "",
            "image_url": "",
            "profile_image_url": "",
        }
    title = ""
    author = ""
    image_url = ""
    profile_image_url = ""
    blocks: list[tuple[str, str]] = []
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
        "published time:",
        "image:",
    )
    preview_noise = {
        "sarah wooders",
        "@sarahwooders",
        "why memory isn't a plugin (it's the harness)",
    }

    current_kind: str | None = None
    current_lines: list[str] = []

    def flush_current() -> None:
        nonlocal current_kind, current_lines
        if not current_kind or not current_lines:
            current_kind = None
            current_lines = []
            return
        text = " ".join(part.strip() for part in current_lines if part.strip()).strip()
        if text:
            blocks.append((current_kind, text))
            if current_kind in {"paragraph", "blockquote", "callout"}:
                paragraphs.append(text)
        current_kind = None
        current_lines = []

    for raw in reader.splitlines():
        line = raw.strip()
        if not line:
            flush_current()
            continue
        lowered = line.lower()
        if any(token in lowered for token in noise):
            continue
        if lowered in preview_noise:
            flush_current()
            continue
        if lowered.startswith("#"):
            continue
        if lowered.startswith("title:") or lowered.startswith("url source:"):
            continue
        if line.startswith("[!["):
            flush_current()
            continue
        image_match = re.match(r"!\[[^\]]*\]\((https://pbs\.twimg\.com[^)]+)\)", line)
        if image_match:
            flush_current()
            candidate = image_match.group(1).replace("&name=small", "&name=large")
            if "/profile_images/" not in candidate:
                blocks.append(("image", candidate))
            continue
        if len(line) < 18 and not line.startswith(">") and not line.startswith("💡"):
            continue
        if line in {")", "(", "].", ".)"}:
            continue
        if line.endswith("(") or line.endswith(")") or line.endswith(")."):
            continue
        if re.fullmatch(r"[\W_]+", line):
            continue
        if line.startswith("💡"):
            flush_current()
            blocks.append(("callout", line.lstrip("💡").strip()))
            paragraphs.append(line.lstrip("💡").strip())
            continue
        if line.startswith(">"):
            cleaned = line.lstrip(">").strip()
            if not cleaned:
                continue
            if current_kind != "blockquote":
                flush_current()
                current_kind = "blockquote"
            current_lines.append(cleaned)
            continue
        if line.startswith("http://") or line.startswith("https://"):
            flush_current()
            continue
        if current_kind != "paragraph":
            flush_current()
            current_kind = "paragraph"
        current_lines.append(line)
    flush_current()

    normalized_blocks: list[tuple[str, str]] = []
    for kind, text in blocks:
        cleaned = re.sub(r"^[).,\s]+", "", text).strip()
        if not cleaned:
            continue
        lowered = cleaned.lower()
        if lowered.startswith("thank you to a few people"):
            break
        if lowered.startswith("this is why we are building"):
            break
        if lowered in {"examples of agent harnesses include", "sarah wooders wrote a"}:
            continue
        if lowered.startswith("on why “memory isn’t a plugin") or lowered.startswith('on why "memory isn'):
            continue
        if kind == "paragraph" and len(cleaned) < 34:
            continue
        if (
            normalized_blocks
            and kind == "paragraph"
            and normalized_blocks[-1][0] == "paragraph"
            and (
                len(normalized_blocks[-1][1]) < 75
                or not re.search(r"[.!?\"”:]$", normalized_blocks[-1][1])
                or cleaned[:1].islower()
            )
        ):
            previous = normalized_blocks[-1][1]
            normalized_blocks[-1] = ("paragraph", f"{previous} {cleaned}".strip())
            continue
        normalized_blocks.append((kind, cleaned))
    blocks = normalized_blocks
    paragraphs = [text for kind, text in blocks if kind in {"paragraph", "blockquote", "callout"}]
    return {
        "paragraphs": paragraphs,
        "blocks": blocks,
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
    domain = _normalized_domain(url)
    if domain in SKIP_DOMAINS:
        raise ArticleExtractionError(
            f"Could not extract article from this URL. `{domain}` is not supported by the public article printer yet."
        )
    try:
        response = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
    except requests.RequestException as exc:
        raise ArticleExtractionError(
            f"Could not fetch article from `{url}`. The source returned an HTTP or network error. Detail: {exc}"
        ) from exc
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
    blocks = list(reader_meta.get("blocks") or [])
    _validate_article_content(url, title=title, body=body, blocks=blocks)
    return Article(
        url=url,
        title=title,
        author=author,
        source_name=site_name,
        body=body,
        image_url=image_url,
        profile_image_url=str(reader_meta.get("profile_image_url") or ""),
        blocks=blocks,
    )


def render_article_markdown(config: MorningPaperConfig, articles: list[Article], *, date_str: str, images_dir: Path) -> str:
    date_label = datetime.fromisoformat(date_str).strftime("%A, %B %d, %Y")
    css = """
@import url('https://fonts.googleapis.com/css2?family=Courier+Prime:ital,wght@0,400;0,700;1,400&display=swap');
body { font-family: 'Courier Prime', 'Courier New', Courier, monospace; font-size: 9pt; line-height: 1.36; color: #090909; background: #fff; }
@page { size: Letter; margin: 0.44in 0.42in 0.58in 0.42in; }
.paper-header { text-align: center; margin: 0 0 0.08in 0; }
.paper-date { font-size: 18.2pt; font-weight: 700; letter-spacing: 0.03em; }
.paper-subtitle { font-size: 8.1pt; color: #4f4f4f; margin-top: 0.02in; letter-spacing: 0.065em; }
.paper-rule { border-bottom: 2.2px solid #111; margin-top: 0.05in; }
.article { margin-top: 0.05in; }
.article-title { font-size: 13.2pt; font-weight: 700; text-transform: uppercase; letter-spacing: 0.02em; margin: 0 0 0.05in 0; }
.article-body { column-count: 2; column-gap: 0.17in; font-size: 9.05pt; line-height: 1.24; color: #050505; }
.article-body::after { content: ""; display: block; clear: both; }
.meta-card { float: left; width: 1.6in; border: 1.4px solid #111; padding: 0.055in; font-size: 7pt; background: #fff; margin: 0.01in 0.11in 0.07in 0; break-inside: avoid; }
.meta-avatar { display: block; width: 100%; aspect-ratio: 1 / 1; object-fit: cover; border: 1px solid #b5b5b5; margin-bottom: 0.055in; }
.meta-author { font-size: 8.1pt; font-weight: 700; margin-bottom: 0.02in; }
.meta-handle { font-size: 6.9pt; color: #222; margin-bottom: 0.03in; }
.meta-date { font-size: 6.4pt; color: #555; text-transform: uppercase; letter-spacing: 0.04em; }
.article-body p { margin: 0 0 0.045in 0; text-align: justify; text-indent: 0.12in; }
.article-body p:first-child { text-indent: 0; }
.article-body .article-callout { font-weight: 700; margin: 0.055in 0; text-indent: 0; }
.article-body blockquote { margin: 0.07in 0.04in 0.08in 0.14in; padding-left: 0.11in; border-left: 1.8px solid #111; font-style: italic; font-size: 8.2pt; color: #111; break-inside: avoid; }
.article-body blockquote p { text-indent: 0; margin: 0; }
.article-image { margin: 0.06in 0 0.08in 0; break-inside: avoid; }
.article-image img { display: block; width: 100%; border: 1px solid #c9c9c9; }
.article-image--wide { column-span: all; }
.article-source { font-size: 6.6pt; color: #333; margin-top: 0.02in; }
.article-source a { color: #333; text-decoration: none; }
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
        relative_avatar = ""
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
        rendered_images: dict[str, str] = {}
        image_counter = 0

        def local_image(url: str) -> str:
            nonlocal image_counter
            if url in rendered_images:
                return rendered_images[url]
            image_counter += 1
            image_name = f"{_safe_filename(article.title)[:24] or 'article'}-{image_counter}.png"
            img_path = process_for_print(url, output_path=images_dir / image_name)
            rendered_images[url] = img_path.relative_to(images_dir.parent).as_posix()
            return rendered_images[url]

        block_items = article.blocks[:80] if article.blocks else [("paragraph", p.strip()) for p in article.body.split("\n\n") if p.strip()]
        body_parts: list[str] = []
        inserted_images = 0
        paragraph_count = 0
        for kind, value in block_items:
            if kind == "image":
                if inserted_images >= 3:
                    continue
                try:
                    relative_image = local_image(value)
                except Exception:
                    continue
                image_class = "article-image article-image--wide" if inserted_images == 0 else "article-image"
                body_parts.append(
                    f'<figure class="{image_class}"><img src="{html.escape(relative_image)}" alt="{html.escape(article.title)}" /></figure>'
                )
                inserted_images += 1
                continue
            if kind == "blockquote":
                body_parts.append(f"<blockquote><p>{html.escape(value)}</p></blockquote>")
                continue
            if kind == "callout":
                body_parts.append(f'<p class="article-callout"><strong>{html.escape(value)}</strong></p>')
                continue
            if not value:
                continue
            paragraph_count += 1
            body_parts.append(f"<p>{html.escape(value)}</p>")
        body_html = "".join(body_parts)
        meta_card = [
            '<div class="meta-card">',
            (
                f'<img class="meta-avatar" src="{html.escape(relative_avatar)}" alt="{html.escape(article.author or article.source_name)}" />'
                if relative_avatar
                else ""
            ),
            f'<div class="meta-author">{html.escape(article.author or article.source_name)}</div>',
            f'<div class="meta-handle">{html.escape(article.source_name)} · {html.escape(urlparse(article.url).netloc)}</div>',
            f'<div class="meta-date">{html.escape(date_label)}</div>',
        ]
        meta_card.append("</div>")
        display_source = article.url.replace("https://", "").replace("http://", "")
        sections.extend(
            [
                '<section class="article">',
                f'<div class="article-title">{html.escape(article.title)}</div>',
                '<div class="article-body">',
                "".join(meta_card),
                body_html,
                "</div>",
                f'<div class="article-source">Source: <a href="{html.escape(article.url)}">{html.escape(display_source)}</a></div>',
                "</section>",
            ]
        )
    return "\n".join(sections)
