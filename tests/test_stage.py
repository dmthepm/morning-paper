from __future__ import annotations

import io
import json
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

import yaml

from morning_paper import cli
from morning_paper.article_print import (
    MAX_RENDER_BLOCKS,
    Article,
    article_truncation_report,
    article_truncation_warning,
)


SENTENCE = "This is a complete sentence with enough words to look like a real paragraph of prose."
WORDS_PER_BLOCK = len(SENTENCE.split())


def _article(block_count: int) -> Article:
    return Article(
        url="https://example.com/long-essay",
        title="A Very Long Essay",
        author="Author",
        source_name="Example",
        body="",
        blocks=[("paragraph", SENTENCE) for _ in range(block_count)],
    )


class TruncationReportTest(unittest.TestCase):
    def test_render_cap_overflow_is_flagged(self) -> None:
        overflow = 40
        article = _article(MAX_RENDER_BLOCKS + overflow)
        report = article_truncation_report(article)
        self.assertTrue(report["truncated"])
        self.assertEqual(report["words_extracted"], WORDS_PER_BLOCK * (MAX_RENDER_BLOCKS + overflow))
        self.assertEqual(report["words_rendered"], WORDS_PER_BLOCK * MAX_RENDER_BLOCKS)
        self.assertIn(str(MAX_RENDER_BLOCKS), str(report["reason"]))
        warning = article_truncation_warning(article)
        self.assertIn("truncated", warning)
        self.assertIn(str(report["words_extracted"]), warning)

    def test_complete_article_is_not_flagged(self) -> None:
        article = _article(5)
        report = article_truncation_report(article)
        self.assertFalse(report["truncated"])
        self.assertEqual(report["words_extracted"], report["words_rendered"])
        self.assertEqual(article_truncation_warning(article), "")

    def test_mid_sentence_extraction_cut_is_flagged(self) -> None:
        article = _article(3)
        article.blocks[-1] = ("paragraph", "This final paragraph stops in the middle of a")
        report = article_truncation_report(article)
        self.assertTrue(report["truncated"])
        self.assertIn("mid-sentence", str(report["reason"]))


class OnPageTruncationNoticeTest(unittest.TestCase):
    def test_truncated_article_prints_notice_on_page(self) -> None:
        from morning_paper.article_print import render_article_markdown
        from morning_paper.config import MorningPaperConfig

        article = _article(MAX_RENDER_BLOCKS + 10)
        report = article_truncation_report(article)
        with tempfile.TemporaryDirectory() as tmp:
            markdown = render_article_markdown(
                MorningPaperConfig(),
                [article],
                date_str="2026-06-12",
                images_dir=Path(tmp) / "_images",
            )
        self.assertIn("trunc-notice", markdown)
        self.assertIn(
            f"Truncated at extraction; {report['words_rendered']} of {report['words_extracted']} words shown.",
            markdown,
        )

    def test_complete_article_prints_no_notice(self) -> None:
        from morning_paper.article_print import render_article_markdown
        from morning_paper.config import MorningPaperConfig

        with tempfile.TemporaryDirectory() as tmp:
            markdown = render_article_markdown(
                MorningPaperConfig(),
                [_article(5)],
                date_str="2026-06-12",
                images_dir=Path(tmp) / "_images",
            )
        self.assertNotIn("Truncated at extraction", markdown)


class StageTruncationTest(unittest.TestCase):
    def _config_path(self, tmp_path: Path) -> Path:
        config_path = tmp_path / "config.yaml"
        rc = cli.main(["init", "--config", str(config_path)])
        self.assertEqual(rc, 0)
        config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        config["outputs"]["directory"] = str(tmp_path / "out")
        config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
        return config_path

    def _stage(self, article: Article) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config_path = self._config_path(tmp_path)

            stdout = io.StringIO()
            with patch("morning_paper.staging.fetch_article", return_value=article):
                with redirect_stdout(stdout):
                    rc = cli.main(
                        [
                            "stage",
                            article.url,
                            "--config",
                            str(config_path),
                            "--date",
                            "2026-06-12",
                        ]
                    )
            self.assertEqual(rc, 0)
            payload = json.loads(stdout.getvalue())

            queue_file = tmp_path / "out" / "staging" / "2026-06-12" / "queue.json"
            self.assertTrue(queue_file.exists())
            payload["_queue"] = json.loads(queue_file.read_text(encoding="utf-8"))
            return payload

    def test_stage_url_reports_truncation_honestly(self) -> None:
        overflow = 40
        payload = self._stage(_article(MAX_RENDER_BLOCKS + overflow))
        self.assertTrue(payload["staged"])
        self.assertTrue(payload["truncated"])
        self.assertEqual(payload["words_extracted"], WORDS_PER_BLOCK * (MAX_RENDER_BLOCKS + overflow))
        self.assertIn("truncated", payload["warning"])
        self.assertIn(str(payload["words_extracted"]), payload["warning"])
        # the queue carries the same honesty flags for later passes
        queued = payload["_queue"][0]
        self.assertTrue(queued["truncated"])
        self.assertEqual(queued["words_extracted"], payload["words_extracted"])
        self.assertEqual(queued["warning"], payload["warning"])

    def test_stage_url_of_complete_article_carries_no_warning(self) -> None:
        payload = self._stage(_article(5))
        self.assertTrue(payload["staged"])
        self.assertFalse(payload["truncated"])
        self.assertEqual(payload["warning"], "")

    def test_queue_show_and_remove_staged_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config_path = self._config_path(tmp_path)
            source = tmp_path / "field-note.md"
            source.write_text("# Field Note\n\nThis belongs in the next edition.\n", encoding="utf-8")

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                rc = cli.main(
                    [
                        "stage",
                        str(source),
                        "--config",
                        str(config_path),
                        "--date",
                        "2026-06-12",
                    ]
                )
            self.assertEqual(rc, 0)
            staged = json.loads(stdout.getvalue())
            slug = staged["slug"]

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                rc = cli.main(["queue", "list", "--config", str(config_path), "--date", "2026-06-12"])
            self.assertEqual(rc, 0)
            listed = json.loads(stdout.getvalue())
            self.assertEqual(listed["count"], 1)
            self.assertEqual(listed["items"][0]["slug"], slug)

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                rc = cli.main(["queue", "show", slug, "--config", str(config_path), "--date", "2026-06-12"])
            self.assertEqual(rc, 0)
            shown = json.loads(stdout.getvalue())
            self.assertTrue(shown["found"])
            self.assertNotIn("markdown", shown)
            self.assertIn("This belongs in the next edition.", shown["markdown_preview"])

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                rc = cli.main(
                    ["queue", "show", slug, "--content", "--config", str(config_path), "--date", "2026-06-12"]
                )
            self.assertEqual(rc, 0)
            shown = json.loads(stdout.getvalue())
            self.assertIn("# Field Note", shown["markdown"])

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                rc = cli.main(["queue", "remove", slug, "--config", str(config_path), "--date", "2026-06-12"])
            self.assertEqual(rc, 0)
            removed = json.loads(stdout.getvalue())
            self.assertTrue(removed["removed"])
            self.assertTrue(removed["file_removed"])
            self.assertFalse(Path(removed["markdown_path"]).exists())

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                rc = cli.main(["queue", "list", "--config", str(config_path), "--date", "2026-06-12"])
            self.assertEqual(rc, 0)
            listed = json.loads(stdout.getvalue())
            self.assertEqual(listed["count"], 0)

    def test_queue_show_and_remove_missing_slug_fail_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config_path = self._config_path(tmp_path)

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                rc = cli.main(["queue", "show", "missing", "--config", str(config_path), "--date", "2026-06-12"])
            self.assertEqual(rc, 1)
            shown = json.loads(stdout.getvalue())
            self.assertFalse(shown["found"])
            self.assertEqual(shown["slug"], "missing")

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                rc = cli.main(["queue", "remove", "missing", "--config", str(config_path), "--date", "2026-06-12"])
            self.assertEqual(rc, 1)
            removed = json.loads(stdout.getvalue())
            self.assertFalse(removed["removed"])

    def test_stage_file_survives_page_estimator_crash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config_path = self._config_path(tmp_path)
            source = tmp_path / "note.md"
            source.write_text("# Note\n\n" + ("word " * 700), encoding="utf-8")

            def crashed(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
                return subprocess.CompletedProcess(args=args, returncode=-11, stdout="", stderr="segfault")

            stdout = io.StringIO()
            with patch("morning_paper.staging.subprocess.run", side_effect=crashed):
                with redirect_stdout(stdout):
                    rc = cli.main(
                        [
                            "stage",
                            str(source),
                            "--config",
                            str(config_path),
                            "--date",
                            "2026-06-12",
                        ]
                    )
            self.assertEqual(rc, 0)
            payload = json.loads(stdout.getvalue())
            self.assertTrue(payload["staged"])
            self.assertGreaterEqual(payload["est_pages"], 1)

    def test_stage_social_record_preserves_complete_thread(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config_path = self._config_path(tmp_path)
            record = {
                "kind": "thread",
                "source": "https://x.com/reporter/status/123",
                "title": "Thread by @reporter: agent workflow",
                "source_status": "complete",
                "route": "thread",
                "social": {
                    "platform": "x",
                    "canonical_url": "https://x.com/reporter/status/123",
                    "root_post_id": "123",
                    "fetched_at": "2026-06-26T08:00:00-07:00",
                    "author": {
                        "name": "Reporter Name",
                        "handle": "@reporter",
                        "profile_url": "https://x.com/reporter",
                    },
                    "metrics": {
                        "likes": 1200,
                        "reposts": 90,
                        "replies": 41,
                        "views": 88000,
                        "captured_at": "2026-06-26T08:00:00-07:00",
                    },
                    "media": [
                        {
                            "type": "image",
                            "local_path": "/tmp/social-thumbnail.jpg",
                            "caption": "print-safe thumbnail",
                            "print": True,
                        }
                    ],
                    "thread": [
                        {
                            "post_id": "123",
                            "created_at": "2026-06-26T07:30:00-07:00",
                            "canonical_url": "https://x.com/reporter/status/123",
                            "full_text": "Here is the complete first post. No clipped ellipsis.",
                            "truncated": False,
                        },
                        {
                            "post_id": "124",
                            "created_at": "2026-06-26T07:31:00-07:00",
                            "canonical_url": "https://x.com/reporter/status/124",
                            "full_text": "Second complete post with the useful detail the paper should print.",
                            "truncated": False,
                        },
                    ],
                },
            }
            source = tmp_path / "social.json"
            source.write_text(json.dumps(record), encoding="utf-8")

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                rc = cli.main(
                    [
                        "stage-social",
                        str(source),
                        "--config",
                        str(config_path),
                        "--date",
                        "2026-06-12",
                    ]
                )
            self.assertEqual(rc, 0)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["kind"], "thread")
            self.assertEqual(payload["source_status"], "complete")
            self.assertFalse(payload["truncated"])
            self.assertEqual(payload["social"]["author"]["handle"], "@reporter")

            markdown = (
                tmp_path
                / "out"
                / "staging"
                / "2026-06-12"
                / f"{payload['slug']}.md"
            ).read_text(encoding="utf-8")
            self.assertIn("mp-social-thread", markdown)
            self.assertIn("Here is the complete first post", markdown)
            self.assertIn("Second complete post", markdown)
            self.assertIn("mp-social-media", markdown)
            self.assertIn("/tmp/social-thumbnail.jpg", markdown)
            self.assertIn("print-safe thumbnail", markdown)

    def test_stage_social_record_rejects_complete_record_missing_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config_path = self._config_path(tmp_path)
            record = {
                "kind": "tweet",
                "source": "https://x.com/reporter/status/123",
                "title": "Broken tweet",
                "source_status": "complete",
                "social": {
                    "platform": "x",
                    "canonical_url": "https://x.com/reporter/status/123",
                    "author": {"handle": "@reporter"},
                    "thread": [{"post_id": "123", "full_text": ""}],
                },
            }
            source = tmp_path / "social.json"
            source.write_text(json.dumps(record), encoding="utf-8")

            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                rc = cli.main(
                    [
                        "stage-social",
                        str(source),
                        "--config",
                        str(config_path),
                        "--date",
                        "2026-06-12",
                    ]
                )
            self.assertEqual(rc, 1)
            self.assertIn("posts without `full_text`", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
