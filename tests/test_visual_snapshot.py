from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image, ImageChops, ImageDraw

from morning_paper.article_print import Article, render_article_markdown
from morning_paper.config import MorningPaperConfig
from morning_paper.renderers import _load_weasyprint, _render_typewriter_pdf


SNAPSHOT_DIR = Path(__file__).parent / "snapshots"
BASELINE_PAGE_1 = SNAPSHOT_DIR / "article_typewriter_page1.png"
FONT_IMPORT = "  @import url('https://fonts.googleapis.com/css2?family=Courier+Prime:ital,wght@0,400;0,700;1,400&display=swap');"


def _pretty_stack_ready() -> bool:
    html_cls, _error = _load_weasyprint()
    if html_cls is None:
        return False
    return shutil.which("pdftoppm") is not None


def _make_fixture_image(target: Path, *, avatar: bool) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    size = (220, 220) if avatar else (1000, 620)
    image = Image.new("L", size, color=245)
    draw = ImageDraw.Draw(image)
    draw.rectangle((8, 8, size[0] - 8, size[1] - 8), outline=70, width=3)
    if avatar:
        draw.ellipse((34, 26, 186, 178), outline=40, width=6)
        draw.rectangle((62, 150, 158, 196), fill=70)
    else:
        draw.text((48, 28), "HARNESS", fill=55)
        draw.rectangle((350, 200, 640, 340), outline=40, width=4)
        draw.text((435, 255), "Model", fill=40)
        draw.line((130, 270, 345, 270), fill=60, width=3)
        draw.line((645, 270, 860, 270), fill=60, width=3)
        draw.line((495, 345, 495, 510), fill=60, width=3)
        draw.line((495, 195, 495, 80), fill=60, width=3)
    image.save(target)
    return target


def _fake_process_for_print(source: str, output_path: Path, max_width: int = 1200) -> Path:
    del max_width
    return _make_fixture_image(output_path, avatar="avatar" in source)


def _render_page_1_png(tmp_path: Path) -> Path:
    config = MorningPaperConfig()
    config.outputs.renderer = "typewriter"

    article = Article(
        url="https://x.com/hwchase17/status/2042978500567609738",
        title="Your harness, your memory",
        author="Harrison Chase",
        source_name="@hwchase17",
        body="",
        handle="@hwchase17",
        profile_image_url="fixture://avatar",
        followers=98752,
        likes=3718,
        retweets=486,
        replies=102,
        views=1844176,
        bio="LangChain",
        blocks=[
            (
                "paragraph",
                "Agent harnesses are becoming the dominant way to build agents, and they are not going anywhere. "
                "These harnesses are intimately tied to agent memory. If you used a closed harness, "
                "you are choosing to yield control of your agent memory to a third party.",
            ),
            (
                "paragraph",
                "The best way to build agentic systems has changed dramatically over the past three years. "
                "When ChatGPT came out, all you could do were simple RAG chains. Then models got better, "
                "and that gave rise to agent harnesses.",
            ),
            ("image", "fixture://diagram-1"),
            ("callout", "Agent harnesses are not going away."),
            (
                "paragraph",
                "There is sometimes sentiment that models will absorb more and more of the scaffolding. "
                "This is not true. An agent, by definition, is an LLM interacting with tools and data.",
            ),
            (
                "paragraph",
                "When things like web search are built into APIs, they are not part of the model. "
                "They are part of a lightweight harness sitting behind the API.",
            ),
            (
                "blockquote",
                "Asking to plug memory into an agent harness is like asking to plug driving into a car.",
            ),
            (
                "paragraph",
                "Memory is just a form of context. Short-term memory and long-term memory are both mediated "
                "by the harness, which means the harness design matters.",
            ),
        ],
    )

    with patch("morning_paper.article_print.process_for_print", side_effect=_fake_process_for_print):
        markdown = render_article_markdown(
            config,
            [article],
            date_str="2026-04-14",
            images_dir=tmp_path / "2026-04-14" / "snapshot" / "_article_images",
        )
        markdown = markdown.replace(FONT_IMPORT, "")
        pdf_path = tmp_path / "snapshot.pdf"
        _render_typewriter_pdf(markdown, output_path=pdf_path)

    png_prefix = tmp_path / "page"
    subprocess.run(
        ["pdftoppm", "-png", "-f", "1", "-l", "1", str(pdf_path), str(png_prefix)],
        check=True,
        capture_output=True,
        text=True,
    )
    return tmp_path / "page-1.png"


@pytest.mark.skipif(not _pretty_stack_ready(), reason="visual snapshot requires weasyprint and pdftoppm")
def test_article_typewriter_visual_snapshot(tmp_path: Path) -> None:
    page_png = _render_page_1_png(tmp_path)
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
