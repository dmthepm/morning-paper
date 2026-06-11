from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
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


class StageTruncationTest(unittest.TestCase):
    def _stage(self, article: Article) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config_path = tmp_path / "config.yaml"
            rc = cli.main(["init", "--config", str(config_path)])
            self.assertEqual(rc, 0)
            config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            config["outputs"]["directory"] = str(tmp_path / "out")
            config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

            stdout = io.StringIO()
            with patch("morning_paper.cli.fetch_article", return_value=article):
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


if __name__ == "__main__":
    unittest.main()
