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


class _FakeResponse:
    def __init__(self, *, text: str, status_code: int = 200) -> None:
        self.text = text
        self.content = text.encode("utf-8")
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"http error: {self.status_code}")


def _fake_get(url: str, timeout: int = 30) -> _FakeResponse:
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


if __name__ == "__main__":
    unittest.main()
