from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import requests
import yaml

from morning_paper import cli
from morning_paper.article_print import JINA_FALLBACK_NOTE, Article, ArticleExtractionError, fetch_article
from morning_paper.config import ConfigError, MorningPaperConfig, load_config, render_default_config
from morning_paper.extractors import get_article_extractor


RICH_ARTICLE_HTML = """
<html>
  <head>
    <title>The Quiet Craft of Local Extraction — Example Journal</title>
    <meta property="og:title" content="The Quiet Craft of Local Extraction" />
    <meta property="og:image" content="https://example.com/images/lede.jpg" />
    <meta property="og:site_name" content="Example Journal" />
    <meta name="author" content="Devon Meadows" />
  </head>
  <body>
    <nav><a href="/">Home</a><a href="/about">About</a></nav>
    <article>
      <h1>The Quiet Craft of Local Extraction</h1>
      <p>Local extraction keeps the entire reading pipeline on the reader's own machine,
      which means the list of articles a person cares about never becomes a log line in
      somebody else's analytics dashboard or rate-limited queue.</p>
      <h2>Why it matters</h2>
      <p>The newspaper metaphor only works if the reader owns the route from source to
      page. A third-party reader service can vanish, throttle, or change its parser, and
      the morning ritual should not depend on any of those things going well today.</p>
      <p>This sample body is intentionally long enough to clear the two-hundred-character
      validation gate with room to spare, so the extractor tests exercise the same path a
      real essay would take on a real morning, ending cleanly with a full stop.</p>
    </article>
    <footer>Subscribe to the newsletter.</footer>
  </body>
</html>
"""

THIN_ARTICLE_HTML = """
<html>
  <head>
    <title>Thin Page</title>
    <meta property="og:title" content="Thin Page" />
    <meta property="og:site_name" content="Example" />
    <meta name="author" content="Devon" />
  </head>
  <body><article><p>Almost nothing here.</p></article></body>
</html>
"""

JINA_RICH_TEXT = (
    "Title: Thin Page\n\n"
    "Markdown Content:\n\n"
    "The remote reader recovered the full body of this article even though the raw "
    "page served almost nothing to a plain fetch without JavaScript execution.\n\n"
    "This second paragraph pushes the fallback extraction comfortably past the "
    "validation gate so the chained result renders as a legitimate article instead "
    "of failing on length.\n\n"
    "A third paragraph keeps the fallback clearly richer than the local attempt."
)


class _FakeResponse:
    def __init__(self, *, text: str, status_code: int = 200, headers: dict[str, str] | None = None) -> None:
        self.text = text
        self.content = text.encode("utf-8")
        self.status_code = status_code
        self.headers = headers or {}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"http error: {self.status_code}")

    def json(self) -> object:
        return json.loads(self.text)


def _fake_get_rich(url: str, timeout: int = 30, **kwargs: object) -> _FakeResponse:
    if "r.jina.ai" in url:
        raise AssertionError("local extraction succeeded; the jina remote reader must not be called")
    return _FakeResponse(text=RICH_ARTICLE_HTML)


def _fake_get_thin_with_jina(url: str, timeout: int = 30, **kwargs: object) -> _FakeResponse:
    if "r.jina.ai" in url:
        return _FakeResponse(text=JINA_RICH_TEXT)
    return _FakeResponse(text=THIN_ARTICLE_HTML)


class LocalExtractorTest(unittest.TestCase):
    def test_local_extractor_parses_mocked_html(self) -> None:
        extractor = get_article_extractor("local")
        with patch("morning_paper.article_print.requests.get", side_effect=_fake_get_rich):
            extracted = extractor.extract("https://example.com/essay")

        self.assertEqual(extracted.title, "The Quiet Craft of Local Extraction")
        self.assertEqual(extracted.author, "Devon Meadows")
        self.assertEqual(extracted.image_url, "https://example.com/images/lede.jpg")
        kinds = {kind for kind, _ in extracted.blocks}
        self.assertIn("paragraph", kinds)
        self.assertIn("callout", kinds)  # headings carry through as callouts
        combined = " ".join(extracted.paragraphs)
        self.assertIn("Local extraction keeps the entire reading pipeline", combined)
        self.assertGreater(len(combined), 200)

    def test_fetch_article_local_path_never_calls_jina(self) -> None:
        with patch("morning_paper.article_print.requests.get", side_effect=_fake_get_rich):
            article = fetch_article("https://example.com/essay")

        self.assertEqual(article.extraction_note, "")
        self.assertEqual(article.title, "The Quiet Craft of Local Extraction")
        self.assertIn("Local extraction keeps the entire reading pipeline", article.body)

    def test_local_does_not_fall_back_to_jina_by_default(self) -> None:
        with patch("morning_paper.article_print.requests.get", side_effect=_fake_get_thin_with_jina):
            with self.assertRaises(ArticleExtractionError) as ctx:
                fetch_article("https://example.com/thin")

        self.assertIn("Could not extract enough article content", str(ctx.exception))

    def test_local_remote_fallback_is_explicit_and_honest(self) -> None:
        with patch("morning_paper.article_print.requests.get", side_effect=_fake_get_thin_with_jina):
            article = fetch_article("https://example.com/thin", allow_remote_fallback=True)

        self.assertEqual(article.extraction_note, JINA_FALLBACK_NOTE)
        self.assertIn("r.jina.ai", article.extraction_note)
        self.assertIn("The remote reader recovered the full body", article.body)

    def test_print_surfaces_fallback_note_as_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config_path = tmp_path / "config.yaml"
            rc = cli.main(["init", "--config", str(config_path)])
            self.assertEqual(rc, 0)
            config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            config["outputs"]["directory"] = str(tmp_path / "out")
            config["outputs"]["renderer"] = "portable"
            config["remote_extractor_fallback"] = True
            config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

            stdout = io.StringIO()
            with patch("morning_paper.article_print.requests.get", side_effect=_fake_get_thin_with_jina):
                with redirect_stdout(stdout):
                    rc = cli.main(
                        ["print", "https://example.com/thin", "--config", str(config_path), "--date", "2026-06-12"]
                    )
            self.assertEqual(rc, 0)
            payload = json.loads(stdout.getvalue())
            self.assertTrue(
                any("r.jina.ai" in warning for warning in payload["warnings"]),
                payload["warnings"],
            )

    def test_stage_carries_extractor_note(self) -> None:
        article = Article(
            url="https://example.com/thin",
            title="Thin Page",
            author="Devon",
            source_name="Example",
            body="",
            blocks=[("paragraph", "A complete sentence that stands in for staged article content.")],
            extraction_note=JINA_FALLBACK_NOTE,
        )
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config_path = tmp_path / "config.yaml"
            rc = cli.main(["init", "--config", str(config_path)])
            self.assertEqual(rc, 0)
            config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            config["outputs"]["directory"] = str(tmp_path / "out")
            config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

            stdout = io.StringIO()
            with patch("morning_paper.staging.fetch_article", return_value=article):
                with redirect_stdout(stdout):
                    rc = cli.main(
                        ["stage", article.url, "--config", str(config_path), "--date", "2026-06-12"]
                    )
            self.assertEqual(rc, 0)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["extractor_note"], JINA_FALLBACK_NOTE)


class ExtractorConfigTest(unittest.TestCase):
    def test_local_is_the_default_extractor(self) -> None:
        self.assertEqual(MorningPaperConfig().article_extractor, "local")
        self.assertFalse(MorningPaperConfig().remote_extractor_fallback)
        self.assertIn("article_extractor: local", render_default_config())
        self.assertIn("remote_extractor_fallback: false", render_default_config())

    def test_default_config_loads_with_local_extractor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config_path = tmp_path / "config.yaml"
            config_path.write_text(render_default_config(), encoding="utf-8")
            data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            data["outputs"]["directory"] = str(tmp_path / "out")
            config_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
            config = load_config(config_path)
            self.assertEqual(config.article_extractor, "local")
            self.assertFalse(config.remote_extractor_fallback)

    def test_remote_extractor_fallback_is_explicit_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config_path = tmp_path / "config.yaml"
            data = yaml.safe_load(render_default_config())
            data["outputs"]["directory"] = str(tmp_path / "out")
            data["remote_extractor_fallback"] = "true"
            config_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
            self.assertTrue(load_config(config_path).remote_extractor_fallback)

    def test_config_accepts_jina_and_rejects_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config_path = tmp_path / "config.yaml"
            base = yaml.safe_load(render_default_config())
            base["outputs"]["directory"] = str(tmp_path / "out")

            base["article_extractor"] = "jina"
            config_path.write_text(yaml.safe_dump(base, sort_keys=False), encoding="utf-8")
            self.assertEqual(load_config(config_path).article_extractor, "jina")

            base["article_extractor"] = "telepathy"
            config_path.write_text(yaml.safe_dump(base, sort_keys=False), encoding="utf-8")
            with self.assertRaises(ConfigError) as ctx:
                load_config(config_path)
            self.assertIn("local, jina", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
