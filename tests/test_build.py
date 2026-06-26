from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from unittest.mock import patch

import yaml
import requests

from morning_paper import cli
from morning_paper.config import MorningPaperConfig


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


def _fake_get(url: str, timeout: int = 30, **kwargs: object) -> _FakeResponse:
    if "api.fxtwitter.com/hwchase17/status/2042978500567609738" in url:
        return _FakeResponse(
            text=json.dumps(
                {
                    "tweet": {
                        "likes": 3718,
                        "retweets": 486,
                        "replies": 102,
                        "views": 1844176,
                        "article": {"title": "Your harness, your memory"},
                        "author": {
                            "name": "Harrison Chase",
                            "screen_name": "hwchase17",
                            "followers": 98752,
                            "description": "@LangChain Always hiring: https://www.langchain.com/careers",
                            "avatar_url": "https://pbs.twimg.com/profile_images/example_avatar_200x200.jpg",
                        },
                    }
                }
            )
        )
    if "hn.algolia.com" in url:
        return _FakeResponse(
            text=json.dumps(
                {
                    "hits": [
                        {
                            "title": "Test HN Story",
                            "url": "https://example.com/hn-story",
                            "points": 100,
                            "num_comments": 50,
                            "author": "alice",
                            "created_at": "2026-04-14T10:00:00Z",
                            "objectID": "123",
                        }
                    ]
                }
            )
        )
    if "r.jina.ai" in url:
        return _FakeResponse(
            text=(
                "Title: Harrison Chase on X: \"Your harness, your memory\" / X\n\n"
                "Reader View\n\n"
                "Example body paragraph one with enough content to exercise the article "
                "printer correctly and ensure the validation gate sees a real extracted body.\n\n"
                "Example body paragraph two continues the sample article with enough detail "
                "to exceed the minimum content threshold and still look like a legitimate "
                "reader-mode extraction instead of a shell response.\n\n"
                "Example body paragraph three adds more material so the rendered bundle has "
                "substantial printable content."
            )
        )
    if "unavatar.io/x/hwchase17" in url:
        response = _FakeResponse(text="avatar-bytes", headers={"content-type": "image/jpeg"})
        response.content = b"\xff\xd8" + b"x" * 2000
        return response
    if "x.com/hwchase17/status/2042978500567609738" in url:
        return _FakeResponse(
            text="""
<html>
  <head>
    <title>X</title>
    <meta property="og:site_name" content="X" />
  </head>
  <body><article>
    <p>Body paragraph one has enough local article text to exercise the printer without relying on any remote reader fallback or third-party extraction service.</p>
    <p>Body paragraph two continues the story with specific detail about the printed edition, the source contract, and the local parsing path that should remain entirely on this machine.</p>
    <p>Body paragraph three gives the validation gate enough substance to treat this as a real article rather than a shell page or tiny teaser.</p>
  </article></body>
</html>
"""
        )
    if "example.com/article" in url:
        return _FakeResponse(
            text="""
<html>
  <head>
    <title>Printed Example</title>
    <meta property="og:title" content="Printed Example" />
    <meta property="og:site_name" content="Example" />
    <meta name="author" content="Devon" />
  </head>
  <body><article>
    <p>Body paragraph one has enough local article text to exercise the printer without relying on any remote reader fallback or third-party extraction service.</p>
    <p>Body paragraph two continues the story with specific detail about the printed edition, the source contract, and the local parsing path that should remain entirely on this machine.</p>
    <p>Body paragraph three gives the validation gate enough substance to treat this as a real article rather than a shell page or tiny teaser.</p>
  </article></body>
</html>
"""
        )
    if "example.com/short" in url:
        return _FakeResponse(
            text="""
<html>
  <head>
    <title>Short Example</title>
    <meta property="og:title" content="Short Example" />
    <meta property="og:site_name" content="Example" />
    <meta name="author" content="Devon" />
  </head>
  <body><article><p>Too short.</p></article></body>
</html>
"""
        )
    return _FakeResponse(
        text="""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Example Feed</title>
    <item>
      <title>Example RSS Story</title>
      <link>https://example.com/rss-story</link>
      <description><![CDATA[<p>Example RSS summary.</p>]]></description>
      <author>bob</author>
      <pubDate>Mon, 14 Apr 2026 09:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>"""
    )


def _supported_metadata_version(package: str) -> str:
    versions = {
        "weasyprint": "69.0",
        "tinycss2": "1.4.0",
        "cssselect2": "0.8.0",
        "pydyf": "0.11.0",
        "cffi": "1.17.1",
        "Pillow": "11.3.0",
        "fontTools": "4.59.0",
    }
    return versions.get(package, "1.0")


class BuildFlowTest(unittest.TestCase):
    def test_init_then_build_writes_all_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config_path = tmp_path / "config.yaml"
            output_dir = tmp_path / "out"

            rc = cli.main(["init", "--config", str(config_path)])
            self.assertEqual(rc, 0)
            self.assertTrue(config_path.exists())

            config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            # the default config matches the visual identity the demo sells
            self.assertEqual(config["outputs"]["style"], "broadsheet")
            self.assertEqual(config["outputs"]["palette"], "color")
            self.assertEqual(config["outputs"]["renderer"], "typewriter")
            # local-first extraction: URLs stay on this machine by default
            self.assertEqual(config["article_extractor"], "local")
            # generated config should be reader-first; demo proves the engine
            self.assertFalse(config["sources"]["hacker_news"]["enabled"])
            self.assertEqual(config["sources"]["rss"], [])
            config["sources"]["hacker_news"]["enabled"] = True
            config["sources"]["rss"] = [
                {"name": "Example Feed A", "url": "https://example.com/a.xml", "limit": 5},
                {"name": "Example Feed B", "url": "https://example.com/b.xml", "limit": 5},
            ]
            config["outputs"]["directory"] = str(output_dir)
            config["outputs"]["renderer"] = "portable"
            config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

            stdout = io.StringIO()
            with patch("morning_paper.sources.requests.get", side_effect=_fake_get):
                with redirect_stdout(stdout):
                    rc = cli.main(["build", "--config", str(config_path), "--date", "2026-04-14"])
            self.assertEqual(rc, 0)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["counts"]["hacker_news"], 1)
            self.assertEqual(payload["counts"]["rss"], 2)
            for key in ("json", "markdown", "html", "pdf"):
                path = Path(payload["outputs"][key])
                self.assertTrue(path.exists(), key)
                self.assertGreater(path.stat().st_size, 0, key)
            markdown = Path(payload["outputs"]["markdown"]).read_text(encoding="utf-8")
            html = Path(payload["outputs"]["html"]).read_text(encoding="utf-8")
            self.assertIn("Community Signals", markdown)
            self.assertIn("Community Signals", html)
            self.assertNotIn("Hacker News", markdown)
            self.assertNotIn("Hacker News", html)
            self.assertEqual(payload["renderer"], "portable")
            self.assertIsInstance(payload["pages"], int)
            self.assertGreaterEqual(payload["pages"], 1)
            self.assertIsInstance(payload["warnings"], list)

    def test_print_writes_outputs_for_article_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config_path = tmp_path / "config.yaml"
            output_dir = tmp_path / "out"

            rc = cli.main(["init", "--config", str(config_path)])
            self.assertEqual(rc, 0)

            config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            config["outputs"]["directory"] = str(output_dir)
            config["outputs"]["renderer"] = "portable"
            config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

            stdout = io.StringIO()
            with patch("morning_paper.article_print.requests.get", side_effect=_fake_get):
                with redirect_stdout(stdout):
                    rc = cli.main(
                        [
                            "print",
                            "https://example.com/article",
                            "--config",
                            str(config_path),
                            "--date",
                            "2026-04-14",
                        ]
                    )
            self.assertEqual(rc, 0)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["mode"], "print")
            self.assertEqual(payload["article_count"], 1)
            for key in ("json", "markdown", "html", "pdf"):
                path = Path(payload["outputs"][key])
                self.assertTrue(path.exists(), key)
                self.assertGreater(path.stat().st_size, 0, key)
            self.assertIsInstance(payload["warnings"], list)

    def test_x_article_uses_fxtwitter_metadata_when_available(self) -> None:
        from morning_paper.article_print import fetch_article

        with patch("morning_paper.article_print.requests.get", side_effect=_fake_get):
            article = fetch_article("https://x.com/hwchase17/status/2042978500567609738")

        self.assertEqual(article.author, "Harrison Chase")
        self.assertEqual(article.handle, "@hwchase17")
        self.assertEqual(article.likes, 3718)
        self.assertEqual(article.retweets, 486)
        self.assertEqual(article.replies, 102)
        self.assertEqual(article.views, 1844176)
        self.assertEqual(article.followers, 98752)
        self.assertIn("LangChain", article.bio or "")
        self.assertEqual(article.profile_image_url, "https://pbs.twimg.com/profile_images/example_avatar_200x200.jpg")

    def test_fetch_article_fails_cleanly_for_unknown_extractor(self) -> None:
        from morning_paper.article_print import ArticleExtractionError, fetch_article

        with self.assertRaises(ArticleExtractionError) as ctx:
            fetch_article("https://example.com/article", extractor_name="missing")

        self.assertIn("unknown article extractor", str(ctx.exception))

    def test_print_uses_built_in_defaults_when_config_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            missing_config = tmp_path / "missing.yaml"
            output_dir = tmp_path / "out"
            default_config = MorningPaperConfig()
            default_config.outputs.directory = output_dir
            default_config.outputs.renderer = "portable"

            stdout = io.StringIO()
            stderr = io.StringIO()
            with patch("morning_paper.cli.DEFAULT_CONFIG_PATH", missing_config):
                with patch("morning_paper.article_print.requests.get", side_effect=_fake_get):
                    with patch("morning_paper.cli.MorningPaperConfig", return_value=default_config):
                        with redirect_stdout(stdout), redirect_stderr(stderr):
                            rc = cli.main(
                                [
                                    "print",
                                    "https://example.com/article",
                                    "--date",
                                    "2026-04-14",
                                ]
                            )
            self.assertEqual(rc, 0)
            self.assertIn("using built-in defaults for one-off print", stderr.getvalue())

            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["mode"], "print")
            for key in ("json", "markdown", "html", "pdf"):
                path = Path(payload["outputs"][key])
                self.assertTrue(path.exists(), key)
                self.assertGreater(path.stat().st_size, 0, key)

    def test_default_typewriter_fails_cleanly_without_pretty_stack(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config_path = tmp_path / "config.yaml"
            rc = cli.main(["init", "--config", str(config_path)])
            self.assertEqual(rc, 0)

            stderr = io.StringIO()
            with patch("morning_paper.renderers._render_typewriter_pdf", side_effect=RuntimeError("missing weasy")):
                with patch("sys.stderr", stderr):
                    rc = cli.main(["build", "--config", str(config_path), "--date", "2026-04-14"])

            self.assertEqual(rc, 1)
            self.assertIn("typewriter renderer requires the pretty print stack", stderr.getvalue())

    def test_print_fails_cleanly_for_shell_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config_path = tmp_path / "config.yaml"
            rc = cli.main(["init", "--config", str(config_path)])
            self.assertEqual(rc, 0)

            def fake_shell_get(url: str, timeout: int = 30, **kwargs: object) -> _FakeResponse:
                if "r.jina.ai" in url:
                    return _FakeResponse(
                        text=(
                            "Title: X\n\n"
                            "Markdown Content:\n"
                            "Warning: This page explicitly specify a timeout. "
                            "People on X are the first to know. "
                            "This page maybe not yet fully loaded.\n"
                        )
                    )
                return _FakeResponse(
                    text="""
<html>
  <head><title>X</title></head>
  <body>People on X are the first to know.</body>
</html>
"""
                )

            stderr = io.StringIO()
            with patch("morning_paper.article_print.requests.get", side_effect=fake_shell_get):
                with patch("sys.stderr", stderr):
                    rc = cli.main(
                        [
                            "print",
                            "https://x.com/example/status/123",
                            "--config",
                            str(config_path),
                            "--date",
                            "2026-04-14",
                        ]
                    )

            self.assertEqual(rc, 1)
            self.assertIn("X.com requires authenticated or rendered access", stderr.getvalue())

    def test_print_fails_cleanly_for_short_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config_path = tmp_path / "config.yaml"
            rc = cli.main(["init", "--config", str(config_path)])
            self.assertEqual(rc, 0)

            config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            config["outputs"]["renderer"] = "portable"
            config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

            def fake_short_get(url: str, timeout: int = 30, **kwargs: object) -> _FakeResponse:
                if "r.jina.ai" in url:
                    return _FakeResponse(text="Reader View\n\nToo short.\n")
                return _fake_get(url, timeout=timeout, **kwargs)

            stderr = io.StringIO()
            with patch("morning_paper.article_print.requests.get", side_effect=fake_short_get):
                with patch("sys.stderr", stderr):
                    rc = cli.main(
                        [
                            "print",
                            "https://example.com/short",
                            "--config",
                            str(config_path),
                            "--date",
                            "2026-04-14",
                        ]
                    )

            self.assertEqual(rc, 1)
            self.assertIn("Could not extract enough article content", stderr.getvalue())

    def test_print_fails_cleanly_for_fetch_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config_path = tmp_path / "config.yaml"
            rc = cli.main(["init", "--config", str(config_path)])
            self.assertEqual(rc, 0)

            def fake_broken_get(url: str, timeout: int = 30, **kwargs: object) -> _FakeResponse:
                if "broken.example.com" in url:
                    return _FakeResponse(text="missing", status_code=404)
                return _fake_get(url, timeout=timeout, **kwargs)

            stderr = io.StringIO()
            with patch("morning_paper.article_print.requests.get", side_effect=fake_broken_get):
                with patch("sys.stderr", stderr):
                    rc = cli.main(
                        [
                            "print",
                            "https://broken.example.com/article",
                            "--config",
                            str(config_path),
                            "--date",
                            "2026-04-14",
                        ]
                    )

            self.assertEqual(rc, 1)
            self.assertIn("Could not fetch article", stderr.getvalue())


def _build_no_pdf(
    *,
    style: str,
    staging: dict | None = None,
    configured_sources: bool = False,
) -> tuple[dict, str, str]:
    """Run a full build with pdf/html off; returns (payload, markdown text, stderr)."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        config_path = tmp_path / "config.yaml"
        output_dir = tmp_path / "out"
        rc = cli.main(["init", "--config", str(config_path)])
        assert rc == 0
        config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        config["outputs"]["directory"] = str(output_dir)
        config["outputs"]["style"] = style
        if configured_sources:
            config["sources"]["hacker_news"]["enabled"] = True
            config["sources"]["rss"] = [
                {"name": "Example Feed", "url": "https://example.com/feed.xml", "limit": 5}
            ]
        # pdf/html off: exercise the template path without the pretty stack
        config["outputs"]["pdf"] = False
        config["outputs"]["html"] = False
        config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

        if staging:
            staging_dir = output_dir / "staging" / "2026-04-14"
            staging_dir.mkdir(parents=True, exist_ok=True)
            (staging_dir / "queue.json").write_text(json.dumps(staging["queue"]), encoding="utf-8")
            for name, text in staging.get("files", {}).items():
                (staging_dir / name).write_text(text, encoding="utf-8")

        stdout = io.StringIO()
        stderr = io.StringIO()
        with patch("morning_paper.sources.requests.get", side_effect=_fake_get):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                rc = cli.main(["build", "--config", str(config_path), "--date", "2026-04-14"])
        assert rc == 0
        payload = json.loads(stdout.getvalue())
        markdown = Path(payload["outputs"]["markdown"]).read_text(encoding="utf-8")
        return payload, markdown, stderr.getvalue()


class BuildTemplateDispatchTest(unittest.TestCase):
    """Since 0.5.0 every build gets the broadsheet-native template, including
    builds configured with a retired 0.4.x style name (the alias path)."""

    def test_default_broadsheet_style_gets_broadsheet_template(self) -> None:
        payload, markdown, _stderr = _build_no_pdf(style="broadsheet")
        self.assertIn("masthead-title", markdown)
        self.assertIn("dept-kicker", markdown)
        self.assertIn('class="not-configured"', markdown)
        self.assertIn("No signals available", markdown)
        # no retired typewriter-template classes on a broadsheet page
        self.assertNotIn("page-1-header", markdown)
        self.assertNotIn("hn-card", markdown)
        self.assertEqual(payload["staged_included"], [])

    def test_configured_sources_render_broadsheet_data_table(self) -> None:
        _payload, markdown, _stderr = _build_no_pdf(style="broadsheet", configured_sources=True)
        self.assertIn('<table class="data">', markdown)

    def test_build_works_via_typewriter_alias(self) -> None:
        # the retired pack's users keep building: typewriter -> brief, and the
        # front page routes to the broadsheet template with a deprecation warning
        from morning_paper import styles

        styles._WARNED_ALIASES.clear()
        _payload, markdown, stderr = _build_no_pdf(style="typewriter")
        self.assertIn("masthead-title", markdown)
        self.assertNotIn("page-1-header", markdown)
        self.assertIn("style 'typewriter' is now 'brief'", stderr)

    def test_other_styles_use_broadsheet_template(self) -> None:
        _payload, markdown, _stderr = _build_no_pdf(style="field-card")
        self.assertIn("masthead-title", markdown)
        self.assertNotIn("page-1-header", markdown)


class StagedInclusionTest(unittest.TestCase):
    """P0 (0.4.3): material queued via `stage` must reach the edition."""

    _QUEUE_ITEM = {
        "slug": "staged-note",
        "kind": "file",
        "source": "/somewhere/staged-note.md",
        "title": "A Staged Note",
        "words": 18,
        "est_pages": 1,
        "staged_at": "2026-04-13T18:00:00",
        "truncated": False,
        "words_extracted": None,
        "warning": "",
        "extractor_note": "",
    }
    _STAGED_BODY = "# A staged note\n\nQueued yesterday, printed today — the staging seam works."

    def test_build_appends_staged_section_broadsheet(self) -> None:
        payload, markdown, _stderr = _build_no_pdf(
            style="broadsheet",
            staging={"queue": [self._QUEUE_ITEM], "files": {"staged-note.md": self._STAGED_BODY}},
        )
        self.assertEqual(payload["staged_included"], ["staged-note"])
        self.assertIn("Assignment Board", markdown)
        self.assertIn("A Staged Note", markdown)
        self.assertIn("the staging seam works", markdown)

    def test_build_appends_staged_section_via_alias(self) -> None:
        # staged inclusion still works for a 0.4.x config naming a retired pack
        payload, markdown, _stderr = _build_no_pdf(
            style="typewriter",
            staging={"queue": [self._QUEUE_ITEM], "files": {"staged-note.md": self._STAGED_BODY}},
        )
        self.assertEqual(payload["staged_included"], ["staged-note"])
        self.assertIn("Assignment Board", markdown)
        self.assertIn("the staging seam works", markdown)

    def test_truncated_staged_item_carries_on_page_notice(self) -> None:
        item = dict(self._QUEUE_ITEM)
        item.update(truncated=True, words_extracted=11000, warning="truncated: extracted 11000 words but only ~4500 will print")
        payload, markdown, _stderr = _build_no_pdf(
            style="broadsheet",
            staging={"queue": [item], "files": {"staged-note.md": self._STAGED_BODY}},
        )
        self.assertEqual(payload["staged_included"], ["staged-note"])
        self.assertIn("trunc-notice", markdown)
        self.assertIn("11000", markdown)

    def test_missing_staged_file_warns_loudly(self) -> None:
        payload, markdown, stderr = _build_no_pdf(
            style="broadsheet",
            staging={"queue": [self._QUEUE_ITEM], "files": {}},
        )
        self.assertEqual(payload["staged_included"], [])
        self.assertNotIn('edition-divider-label">Assignment Board', markdown)
        self.assertIn("ASSIGNMENT BOARD ITEM NOT INCLUDED", stderr)
        self.assertTrue(any("ASSIGNMENT BOARD ITEM NOT INCLUDED" in w for w in payload["warnings"]))

    def test_portable_renderer_warns_staged_items_not_included(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config_path = tmp_path / "config.yaml"
            output_dir = tmp_path / "out"
            rc = cli.main(["init", "--config", str(config_path)])
            self.assertEqual(rc, 0)
            config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            config["outputs"]["directory"] = str(output_dir)
            config["outputs"]["renderer"] = "portable"
            config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

            staging_dir = output_dir / "staging" / "2026-04-14"
            staging_dir.mkdir(parents=True, exist_ok=True)
            (staging_dir / "queue.json").write_text(json.dumps([self._QUEUE_ITEM]), encoding="utf-8")
            (staging_dir / "staged-note.md").write_text(self._STAGED_BODY, encoding="utf-8")

            stdout = io.StringIO()
            stderr = io.StringIO()
            with patch("morning_paper.sources.requests.get", side_effect=_fake_get):
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    rc = cli.main(["build", "--config", str(config_path), "--date", "2026-04-14"])
            self.assertEqual(rc, 0)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["staged_included"], [])
            self.assertIn("ASSIGNMENT BOARD ITEMS NOT INCLUDED", stderr.getvalue())
            self.assertIn("outputs.renderer: typewriter", stderr.getvalue())


class RenderCommandTest(unittest.TestCase):
    def _portable_config(self, tmp_path: Path) -> Path:
        config_path = tmp_path / "config.yaml"
        rc = cli.main(["init", "--config", str(config_path)])
        self.assertEqual(rc, 0)
        config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        config["outputs"]["directory"] = str(tmp_path / "out")
        config["outputs"]["renderer"] = "portable"
        config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
        return config_path

    def test_render_output_flag_delivers_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config_path = self._portable_config(tmp_path)
            source = tmp_path / "doc.md"
            source.write_text("# Hello\n\nA page of prose.\n", encoding="utf-8")
            target = tmp_path / "delivered" / "edition.pdf"

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                rc = cli.main(
                    ["render", str(source), "--config", str(config_path), "--output", str(target)]
                )
            self.assertEqual(rc, 0)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["outputs"]["pdf"], str(target))
            self.assertTrue(target.is_file())
            self.assertGreater(target.stat().st_size, 0)

    def test_render_frontmatter_css_reports_custom_css_and_warns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config_path = self._portable_config(tmp_path)
            source = tmp_path / "doc.md"
            source.write_text(
                "---\ntitle: Custom\ncss: |\n  body { font-family: Georgia; }\n---\n# Hello\n",
                encoding="utf-8",
            )

            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                rc = cli.main(["render", str(source), "--config", str(config_path)])
            self.assertEqual(rc, 0)
            payload = json.loads(stdout.getvalue())
            # honesty: never report a style pack the page is not wearing
            self.assertEqual(payload["style"], "custom-css")
            self.assertIn("frontmatter `css:` overrides the configured style pack", stderr.getvalue())

    def test_render_without_custom_css_reports_configured_style(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config_path = self._portable_config(tmp_path)
            source = tmp_path / "doc.md"
            source.write_text("# Hello\n\nPlain prose.\n", encoding="utf-8")

            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                rc = cli.main(["render", str(source), "--config", str(config_path)])
            self.assertEqual(rc, 0)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["style"], "broadsheet")
            self.assertNotIn("custom-css", stderr.getvalue())

    def test_render_applies_config_font_scale_to_html(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config_path = self._portable_config(tmp_path)
            config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            config["outputs"]["font_scale"] = 1.25
            config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
            source = tmp_path / "doc.md"
            source.write_text("# Hello\n\nLarge print, please.\n", encoding="utf-8")

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                rc = cli.main(["render", str(source), "--config", str(config_path)])
            self.assertEqual(rc, 0)
            payload = json.loads(stdout.getvalue())
            html_text = Path(payload["outputs"]["html"]).read_text(encoding="utf-8")
            self.assertIn("--mp-font-scale: 1.25", html_text)


class CliSurfaceTest(unittest.TestCase):
    def test_help_lists_commands_and_docs(self) -> None:
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            rc = cli.main(["help"])
        self.assertEqual(rc, 0)
        output = stdout.getvalue()
        self.assertIn("Morning Paper", output)
        self.assertIn("Commands:", output)
        self.assertIn("demo", output)
        self.assertIn("newsroom", output)
        self.assertIn("sources", output)
        self.assertIn("print <url>", output)
        self.assertIn("stage <url|file>", output)
        self.assertIn("https://github.com/dmthepm/morning-paper", output)

    def test_doctor_prints_update_notice_when_pypi_newer(self) -> None:
        from morning_paper import __version__

        major = int(__version__.split(".")[0])
        newer = f"{major + 1}.0.0"
        stdout = io.StringIO()
        with patch("morning_paper.cli._load_weasyprint", return_value=(None, "missing")):
            with patch("morning_paper.cli.requests.get", return_value=_FakeResponse(text=json.dumps({"info": {"version": newer}}))):
                with redirect_stdout(stdout):
                    rc = cli.doctor()
        self.assertEqual(rc, 0)
        output = stdout.getvalue()
        self.assertIn("doctor: ok", output)
        self.assertIn("renderer: typewriter unavailable", output)
        self.assertIn("fallback-only install", output)
        self.assertIn(f"update available: {newer} (you have {__version__})", output)
        self.assertIn("uv tool upgrade morning-paper", output)

    def test_doctor_skips_update_notice_when_offline(self) -> None:
        stdout = io.StringIO()
        with patch("morning_paper.cli._load_weasyprint", return_value=(None, "missing")):
            with patch("morning_paper.cli.requests.get", side_effect=requests.RequestException("offline")):
                with redirect_stdout(stdout):
                    rc = cli.doctor()
        self.assertEqual(rc, 0)
        output = stdout.getvalue()
        self.assertIn("doctor: ok", output)
        self.assertIn("renderer: typewriter unavailable", output)
        self.assertNotIn("update available", output)

    def test_roadmap_command_prints_guidance(self) -> None:
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            rc = cli.main(["remove"])
        self.assertEqual(rc, 2)
        output = stderr.getvalue()
        self.assertIn('"remove" is not implemented yet', output)
        self.assertIn("ROADMAP.md", output)

    def test_doctor_json_reports_renderer_and_checks(self) -> None:
        stdout = io.StringIO()
        with patch("morning_paper.cli._load_weasyprint", return_value=(object(), None)):
            with patch("morning_paper.cli.metadata.version", side_effect=_supported_metadata_version):
                with redirect_stdout(stdout):
                    rc = cli.main(["doctor", "--json"])
        self.assertEqual(rc, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["status"], "ok")
        self.assertTrue(payload["renderer"]["typewriter"])
        self.assertIsNone(payload["renderer"]["error"])
        self.assertFalse(payload["renderer"]["render_self_test"]["run"])
        self.assertIn("dependencies", payload)
        self.assertIn("python", payload["dependencies"])
        self.assertIn("weasyprint", payload["dependencies"]["packages"])
        self.assertIn("trafilatura", payload["dependencies"]["packages"])
        self.assertIn("feedparser", payload["dependencies"]["packages"])
        self.assertIn("requests", payload["dependencies"]["packages"])
        self.assertIn("fpdf2", payload["dependencies"]["packages"])
        self.assertEqual(
            payload["dependencies"]["weasyprint"],
            {"version": "69.0", "supported": True, "requires": ">=69.0,<70", "error": ""},
        )
        check_names = {check["name"] for check in payload["checks"]}
        self.assertIn("morning_paper.renderers", check_names)
        self.assertIn("morning_paper/resources/broadsheet-build.md", check_names)
        self.assertTrue(all(check["ok"] for check in payload["checks"]))

    def test_doctor_strict_rejects_unsupported_weasyprint(self) -> None:
        stdout = io.StringIO()
        with patch("morning_paper.cli._load_weasyprint", return_value=(object(), None)):
            with patch(
                "morning_paper.cli.metadata.version",
                side_effect=lambda package: "68.1" if package == "weasyprint" else _supported_metadata_version(package),
            ):
                with patch("morning_paper.cli.count_pages") as count_pages:
                    with patch("morning_paper.cli.requests.get", side_effect=requests.RequestException("offline")):
                        with redirect_stdout(stdout):
                            rc = cli.main(["doctor", "--strict"])
        self.assertEqual(rc, 1)
        count_pages.assert_not_called()
        output = stdout.getvalue()
        self.assertIn("renderer: typewriter ready", output)
        self.assertIn("unsupported WeasyPrint 68.1", output)
        self.assertIn("requires >=69.0,<70", output)
        self.assertIn("renderer self-test: skipped", output)
        self.assertIn("outside the supported range", output)

    def test_doctor_json_reports_unsupported_weasyprint(self) -> None:
        stdout = io.StringIO()
        with patch("morning_paper.cli._load_weasyprint", return_value=(object(), None)):
            with patch(
                "morning_paper.cli.metadata.version",
                side_effect=lambda package: "68.1" if package == "weasyprint" else _supported_metadata_version(package),
            ):
                with redirect_stdout(stdout):
                    rc = cli.main(["doctor", "--json"])
        self.assertEqual(rc, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["status"], "unsupported-renderer")
        self.assertTrue(payload["renderer"]["typewriter"])
        self.assertFalse(payload["renderer"]["render_self_test"]["run"])
        self.assertEqual(payload["dependencies"]["weasyprint"]["version"], "68.1")
        self.assertFalse(payload["dependencies"]["weasyprint"]["supported"])
        self.assertIn(">=69.0,<70", payload["dependencies"]["weasyprint"]["requires"])

    def test_doctor_strict_runs_render_self_test(self) -> None:
        stdout = io.StringIO()
        with patch("morning_paper.cli._load_weasyprint", return_value=(object(), None)):
            with patch("morning_paper.cli.metadata.version", side_effect=_supported_metadata_version):
                with patch("morning_paper.cli.count_pages", return_value=1) as count_pages:
                    with patch("morning_paper.cli.requests.get", side_effect=requests.RequestException("offline")):
                        with redirect_stdout(stdout):
                            rc = cli.main(["doctor", "--strict"])
        self.assertEqual(rc, 0)
        count_pages.assert_called_once()
        output = stdout.getvalue()
        self.assertIn("renderer: typewriter ready", output)
        self.assertIn("renderer self-test: passed (1 page(s))", output)

    def test_doctor_json_strict_reports_render_self_test(self) -> None:
        stdout = io.StringIO()
        with patch("morning_paper.cli._load_weasyprint", return_value=(object(), None)):
            with patch("morning_paper.cli.metadata.version", side_effect=_supported_metadata_version):
                with patch("morning_paper.cli.count_pages", return_value=2):
                    with redirect_stdout(stdout):
                        rc = cli.main(["doctor", "--json", "--strict"])
        self.assertEqual(rc, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["renderer"]["render_self_test"], {"run": True, "ok": True, "pages": 2, "error": ""})

    def test_doctor_strict_fails_when_render_self_test_fails(self) -> None:
        stdout = io.StringIO()
        with patch("morning_paper.cli._load_weasyprint", return_value=(object(), None)):
            with patch("morning_paper.cli.metadata.version", side_effect=_supported_metadata_version):
                with patch("morning_paper.cli.count_pages", side_effect=RuntimeError("layout crashed")):
                    with patch("morning_paper.cli.requests.get", side_effect=requests.RequestException("offline")):
                        with redirect_stdout(stdout):
                            rc = cli.main(["doctor", "--strict"])
        self.assertEqual(rc, 1)
        output = stdout.getvalue()
        self.assertIn("renderer: typewriter ready", output)
        self.assertIn("renderer self-test: failed (layout crashed)", output)

    def test_doctor_json_fallback_only_exits_zero_without_strict(self) -> None:
        stdout = io.StringIO()
        with patch("morning_paper.cli._load_weasyprint", return_value=(None, "missing")):
            with redirect_stdout(stdout):
                rc = cli.main(["doctor", "--json"])
        self.assertEqual(rc, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["status"], "fallback-only")
        self.assertFalse(payload["renderer"]["typewriter"])
        self.assertEqual(payload["renderer"]["error"], "missing")
        self.assertTrue(payload["renderer"]["hints"])

    def test_doctor_strict_exits_nonzero_when_typewriter_unavailable(self) -> None:
        stdout = io.StringIO()
        with patch("morning_paper.cli._load_weasyprint", return_value=(None, "missing")):
            with patch("morning_paper.cli.requests.get", side_effect=requests.RequestException("offline")):
                with redirect_stdout(stdout):
                    rc = cli.main(["doctor", "--strict"])
        self.assertEqual(rc, 1)
        output = stdout.getvalue()
        self.assertIn("renderer: typewriter unavailable", output)

    def test_doctor_pango_error_prints_macos_fix(self) -> None:
        pango_error = "cannot load library 'libpango-1.0-0': dlopen(libpango-1.0-0, 0x0002)"
        stdout = io.StringIO()
        with patch("morning_paper.cli.sys.platform", "darwin"):
            with patch("morning_paper.cli._load_weasyprint", return_value=(None, pango_error)):
                with patch("morning_paper.cli.requests.get", side_effect=requests.RequestException("offline")):
                    with redirect_stdout(stdout):
                        rc = cli.main(["doctor"])
        self.assertEqual(rc, 0)
        output = stdout.getvalue()
        self.assertIn("brew install pango gdk-pixbuf", output)
        self.assertIn("DYLD_FALLBACK_LIBRARY_PATH", output)

    def test_doctor_rejects_unknown_argument(self) -> None:
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            rc = cli.main(["doctor", "--bogus"])
        self.assertEqual(rc, 2)
        self.assertIn("unknown doctor argument", stderr.getvalue())

    def test_stage_alias_add_requires_target(self) -> None:
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            rc = cli.main(["add"])
        self.assertEqual(rc, 2)
        self.assertIn("usage: morning-paper stage", stderr.getvalue())

    def test_estimate_missing_file(self) -> None:
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            rc = cli.main(["estimate", "/nonexistent/x.md"])
        self.assertEqual(rc, 1)
        self.assertIn("no such file", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
