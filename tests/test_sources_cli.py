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


class _FakeResponse:
    def __init__(self, text: str, status_code: int = 200) -> None:
        self.text = text
        self.content = text.encode("utf-8")
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"http error: {self.status_code}")


_FULL_TEXT_FEED = """<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>Full Text Item</title>
    <link href="https://example.com/full"/>
    <content type="html">&lt;p&gt;The whole article ships in the feed.&lt;/p&gt;</content>
    <updated>2026-06-20T09:00:00Z</updated>
  </entry>
</feed>"""


_SUMMARY_FEED = """<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <item>
      <title>Summary Item</title>
      <link>https://example.com/summary</link>
      <description>Only a short summary.</description>
    </item>
  </channel>
</rss>"""


class SourcesCliTest(unittest.TestCase):
    def _config_path(self, tmp_path: Path) -> Path:
        config_path = tmp_path / "config.yaml"
        rc = cli.main(["init", "--config", str(config_path)])
        self.assertEqual(rc, 0)
        config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        config["sources"]["hacker_news"]["enabled"] = False
        config["sources"]["rss"] = [
            {"name": "Full Feed", "url": "https://example.com/full.xml", "limit": 5},
            {"name": "Summary Feed", "url": "https://example.com/summary.xml", "limit": 5},
            {"name": "Broken Feed", "url": "https://example.com/broken.xml", "limit": 5},
        ]
        config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
        return config_path

    def test_sources_list_inventory_without_network_check(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = self._config_path(Path(tmp))
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                rc = cli.main(["sources", "list", "--config", str(config_path)])
        self.assertEqual(rc, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["count"], 4)
        self.assertEqual(payload["source_model"]["posture"], "reader_stack_first")
        self.assertIn("rss_or_feed_url", payload["source_model"]["entry_points"])
        self.assertNotIn("starter_inputs", payload["source_model"])
        self.assertIn("local_drop", payload["source_model"]["reader_owned_inputs"])
        self.assertIn("work_systems", payload["source_model"]["reader_owned_inputs"])
        self.assertIn("social_and_video_feeds", payload["source_model"]["reader_owned_inputs"])
        self.assertEqual(payload["sources"][0]["id"], "hacker_news")
        self.assertEqual(payload["sources"][0]["name"], "Community Signals")
        self.assertEqual(payload["sources"][0]["role"], "optional_starter")
        self.assertEqual(payload["sources"][0]["status"], "disabled")
        self.assertEqual(payload["sources"][1]["role"], "reader_owned")
        self.assertEqual(payload["sources"][1]["status"], "configured")
        self.assertIn("morning-paper stage", payload["collector_contract"]["command"])
        self.assertIn("Pass --newsroom", " ".join(payload["next_actions"]))

    def test_sources_list_suggests_whole_source_stack_when_no_feeds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config_path = tmp_path / "config.yaml"
            self.assertEqual(cli.main(["init", "--config", str(config_path)]), 0)
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                rc = cli.main(["sources", "list", "--config", str(config_path)])
        self.assertEqual(rc, 0)
        payload = json.loads(stdout.getvalue())
        next_actions = " ".join(payload["next_actions"])
        self.assertIn("Slack", next_actions)
        self.assertIn("GitHub", next_actions)
        self.assertIn("Linear", next_actions)
        self.assertIn("video feed", next_actions)
        self.assertNotIn("Hacker News", next_actions)

    def test_sources_list_can_include_newsroom_collectors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config_path = self._config_path(tmp_path)
            newsroom = tmp_path / "newsroom"
            self.assertEqual(cli.main(["newsroom", "init", str(newsroom)]), 0)
            (newsroom / "inbox" / "note.txt").write_text("Something to read.\n", encoding="utf-8")

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                rc = cli.main(["sources", "list", "--config", str(config_path), "--newsroom", str(newsroom)])
        self.assertEqual(rc, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["newsroom"]["status"], "configured")
        self.assertEqual(payload["newsroom"]["local_drop"]["status"], "configured")
        self.assertEqual(payload["newsroom"]["local_drop"]["visible_file_count"], 1)
        self.assertEqual(payload["newsroom"]["local_drop"]["candidate_count"], 1)
        self.assertEqual(payload["newsroom"]["local_drop"]["accepts"], [".md", ".markdown", ".txt", ".url"])
        self.assertEqual(payload["newsroom"]["local_drop"]["unsupported_count"], 0)
        self.assertEqual(payload["newsroom"]["local_drop"]["sample_files"], ["note.txt"])
        self.assertIn(str(newsroom / "inbox"), payload["newsroom"]["local_drop"]["path"])
        self.assertIn("put .md", " ".join(payload["next_actions"]))
        collectors = {item["id"]: item for item in payload["newsroom"]["collectors"]}
        self.assertIn("collector:local-drop", collectors)
        self.assertIn("collector:read", collectors)
        self.assertIn("collector:shipped", collectors)
        self.assertEqual(collectors["collector:local-drop"]["status"], "configured")
        self.assertEqual(collectors["collector:local-drop"]["role"], "reader_owned")
        self.assertEqual(collectors["collector:local-drop"]["source_kind"], "local_drop_folder")

    def test_sources_check_auto_detects_scaffolded_newsroom_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config_path = self._config_path(tmp_path)
            newsroom = tmp_path / "newsroom"
            self.assertEqual(cli.main(["newsroom", "init", str(newsroom)]), 0)
            (newsroom / "inbox" / "note.txt").write_text("Something to read.\n", encoding="utf-8")

            stdout = io.StringIO()
            with patch("morning_paper.sources.requests.get", return_value=_FakeResponse(_SUMMARY_FEED)):
                with patch("morning_paper.cli.Path.cwd", return_value=newsroom):
                    with redirect_stdout(stdout):
                        rc = cli.main(["sources", "check", "--config", str(config_path)])
        self.assertEqual(rc, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["newsroom"]["newsroom_path"], str(newsroom.resolve()))
        self.assertEqual(payload["newsroom"]["local_drop"]["candidate_count"], 1)
        collectors = {item["id"]: item for item in payload["newsroom"]["collectors"]}
        self.assertTrue(collectors["collector:local-drop"]["syntax_ok"])

    def test_sources_list_separates_unsupported_local_drop_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config_path = self._config_path(tmp_path)
            newsroom = tmp_path / "newsroom"
            self.assertEqual(cli.main(["newsroom", "init", str(newsroom)]), 0)
            (newsroom / "inbox" / "note.txt").write_text("Something to read.\n", encoding="utf-8")
            (newsroom / "inbox" / "report.pdf").write_bytes(b"%PDF-1.4\n")
            (newsroom / "inbox" / "data.csv").write_text("name,value\nA,1\n", encoding="utf-8")

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                rc = cli.main(["sources", "list", "--config", str(config_path), "--newsroom", str(newsroom)])
        self.assertEqual(rc, 0)
        payload = json.loads(stdout.getvalue())
        local_drop = payload["newsroom"]["local_drop"]
        self.assertEqual(local_drop["visible_file_count"], 3)
        self.assertEqual(local_drop["candidate_count"], 1)
        self.assertEqual(local_drop["sample_files"], ["note.txt"])
        self.assertEqual(local_drop["unsupported_count"], 2)
        self.assertEqual(local_drop["unsupported_sample_files"], ["data.csv", "report.pdf"])
        self.assertIn("Unsupported local-drop files need a converter collector", " ".join(payload["next_actions"]))

    def test_sources_check_reports_full_text_summary_and_errors(self) -> None:
        def fake_get(url: str, timeout: int = 30) -> _FakeResponse:
            if "full.xml" in url:
                return _FakeResponse(_FULL_TEXT_FEED)
            if "summary.xml" in url:
                return _FakeResponse(_SUMMARY_FEED)
            return _FakeResponse("missing", status_code=404)

        with tempfile.TemporaryDirectory() as tmp:
            config_path = self._config_path(Path(tmp))
            stdout = io.StringIO()
            with patch("morning_paper.sources.requests.get", side_effect=fake_get):
                with redirect_stdout(stdout):
                    rc = cli.main(["sources", "check", "--config", str(config_path)])
        self.assertEqual(rc, 0)
        payload = json.loads(stdout.getvalue())
        by_name = {item["name"]: item for item in payload["sources"]}
        self.assertEqual(by_name["Full Feed"]["status"], "ok")
        self.assertEqual(by_name["Full Feed"]["content_mode"], "full_text")
        self.assertEqual(by_name["Summary Feed"]["content_mode"], "summary_only")
        self.assertEqual(by_name["Broken Feed"]["status"], "error")
        self.assertIn("http error", by_name["Broken Feed"]["error"])

    def test_sources_check_runs_collector_syntax_check(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config_path = self._config_path(tmp_path)
            newsroom = tmp_path / "newsroom"
            self.assertEqual(cli.main(["newsroom", "init", str(newsroom)]), 0)

            stdout = io.StringIO()
            with patch("morning_paper.sources.requests.get", return_value=_FakeResponse(_SUMMARY_FEED)):
                with redirect_stdout(stdout):
                    rc = cli.main(["sources", "check", "--config", str(config_path), "--newsroom", str(newsroom)])
        self.assertEqual(rc, 0)
        payload = json.loads(stdout.getvalue())
        collectors = {item["id"]: item for item in payload["newsroom"]["collectors"]}
        self.assertTrue(collectors["collector:local-drop"]["syntax_ok"])


if __name__ == "__main__":
    unittest.main()
