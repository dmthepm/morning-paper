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
    def __init__(self, *, text: str, status_code: int = 200) -> None:
        self.text = text
        self.content = text.encode("utf-8")
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"http error: {self.status_code}")


def _fake_get(url: str, timeout: int = 30, **kwargs: object) -> _FakeResponse:
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
  <body><article><p>Body paragraph one.</p><p>Body paragraph two.</p></article></body>
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
            self.assertEqual(payload["renderer"], "portable")
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


if __name__ == "__main__":
    unittest.main()
