from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest
from PIL import Image, ImageChops

from morning_paper.config import MorningPaperConfig
from morning_paper.models import SourceItem
from morning_paper.renderers import _load_weasyprint, _render_typewriter_pdf, render_typewriter_markdown


SNAPSHOT_DIR = Path(__file__).parent / "snapshots"
BASELINE_PAGE_1 = SNAPSHOT_DIR / "frontpage_typewriter_page1.png"
FONT_IMPORT = "  @import url('https://fonts.googleapis.com/css2?family=Courier+Prime:ital,wght@0,400;0,700;1,400&display=swap');"


def _pretty_stack_ready() -> bool:
    html_cls, _error = _load_weasyprint()
    if html_cls is None:
        return False
    return shutil.which("pdftoppm") is not None


def _fixture_item(source_type: str, source_name: str, title: str, summary: str, url: str, score: float, published_at: str) -> SourceItem:
    return SourceItem(
        source_type=source_type,
        source_name=source_name,
        title=title,
        url=url,
        summary=summary,
        author="",
        published_at=published_at,
        score=score,
        metadata={},
    )


def _render_frontpage_png(tmp_path: Path) -> Path:
    config = MorningPaperConfig()
    config.outputs.renderer = "typewriter"
    collected = {
        "rss": [
            _fixture_item(
                "rss",
                "Deep Signal",
                "A new wave of agent harnesses is forcing product teams to own memory, not rent it",
                "Founders are starting to treat memory as product surface, not infrastructure detail.",
                "https://example.com/rss-1",
                9.5,
                "2026-04-14T07:00:00+00:00",
            ),
            _fixture_item(
                "rss",
                "Operator Notes",
                "Why agent operators are shifting from dashboards to printed daily reviews",
                "The best operators increasingly want one compact artifact they can annotate by hand.",
                "https://example.com/rss-2",
                8.2,
                "2026-04-14T06:00:00+00:00",
            ),
            _fixture_item(
                "rss",
                "Infra Canon",
                "A small change in delivery loops can compound into dramatically better system reliability",
                "Daily review loops work because they compress signal and force prioritization.",
                "https://example.com/rss-3",
                7.0,
                "2026-04-14T05:30:00+00:00",
            ),
        ],
        "hacker_news": [
            _fixture_item(
                "hacker_news",
                "Hacker News",
                "Show HN: a structured print pipeline for long-form AI reading",
                "420 points · 188 comments",
                "https://news.ycombinator.com/item?id=1",
                420.0,
                "2026-04-14T08:00:00+00:00",
            ),
            _fixture_item(
                "hacker_news",
                "Hacker News",
                "Open source maintainers are using PDFs as a regression surface",
                "312 points · 94 comments",
                "https://news.ycombinator.com/item?id=2",
                312.0,
                "2026-04-14T09:00:00+00:00",
            ),
            _fixture_item(
                "hacker_news",
                "Hacker News",
                "A practical guide to stable paged-media CSS",
                "271 points · 61 comments",
                "https://news.ycombinator.com/item?id=3",
                271.0,
                "2026-04-14T10:00:00+00:00",
            ),
            _fixture_item(
                "hacker_news",
                "Hacker News",
                "Why local-first tooling still matters for agentic systems",
                "188 points · 55 comments",
                "https://news.ycombinator.com/item?id=4",
                188.0,
                "2026-04-14T11:00:00+00:00",
            ),
        ],
    }

    markdown = render_typewriter_markdown(config, collected, date_str="2026-04-14")
    markdown = markdown.replace(FONT_IMPORT, "")
    pdf_path = tmp_path / "frontpage.pdf"
    _render_typewriter_pdf(markdown, output_path=pdf_path)

    png_prefix = tmp_path / "frontpage"
    subprocess.run(
        ["pdftoppm", "-png", "-f", "1", "-l", "1", str(pdf_path), str(png_prefix)],
        check=True,
        capture_output=True,
        text=True,
    )
    return tmp_path / "frontpage-1.png"


@pytest.mark.skipif(not _pretty_stack_ready(), reason="visual snapshot requires weasyprint and pdftoppm")
def test_frontpage_typewriter_visual_snapshot(tmp_path: Path) -> None:
    page_png = _render_frontpage_png(tmp_path)
    assert page_png.exists()

    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    if os.environ.get("MORNING_PAPER_UPDATE_SNAPSHOTS") == "1" or not BASELINE_PAGE_1.exists():
        shutil.copyfile(page_png, BASELINE_PAGE_1)
        pytest.skip("visual snapshot baseline created or updated")

    current = Image.open(page_png).convert("L")
    baseline = Image.open(BASELINE_PAGE_1).convert("L")
    assert current.size == baseline.size

    diff = ImageChops.difference(current, baseline)
    bbox = diff.getbbox()
    if bbox is None:
        return

    histogram = diff.histogram()
    total_pixels = current.size[0] * current.size[1]
    total_diff = sum(value * count for value, count in enumerate(histogram))
    mean_diff = total_diff / total_pixels
    assert mean_diff < 0.35, f"visual regression too large: mean pixel diff {mean_diff:.3f}"
