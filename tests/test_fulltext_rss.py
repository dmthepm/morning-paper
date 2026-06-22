from __future__ import annotations

import unittest
from unittest.mock import patch

import requests

from morning_paper.config import MorningPaperConfig, RssFeedConfig
from morning_paper.models import SourceItem
from morning_paper.renderers import _render_broadsheet_reads
from morning_paper.sources import _entry_body, fetch_rss_feeds


# A full article body long enough to exceed the 280-char summary cap several
# times over, with eight distinct paragraphs — more than the summary path's
# 4-paragraph clip, so a full read is unmistakable from a blurb.
_PARAS = [
    f"Paragraph {n} of the full essay. " + ("It carries real prose. " * 6)
    for n in range(1, 9)
]
_BODY_HTML = "".join(f"<p>{p}</p>" for p in _PARAS)
_FULL_WORD_COUNT = sum(len(p.split()) for p in _PARAS)


class _FakeResponse:
    def __init__(self, *, text: str, status_code: int = 200) -> None:
        self.text = text
        self.content = text.encode("utf-8")
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"http error: {self.status_code}")


_FULLTEXT_ATOM = f"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Full Text Feed</title>
  <entry>
    <title>The Full Essay</title>
    <link href="https://example.com/full-essay"/>
    <author><name>Jordan</name></author>
    <updated>2026-06-20T09:00:00Z</updated>
    <summary>A short blurb that should stay short.</summary>
    <content type="html"><![CDATA[{_BODY_HTML}]]></content>
  </entry>
</feed>"""


_SUMMARY_ONLY_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Summary Feed</title>
    <item>
      <title>Summary Only Story</title>
      <link>https://example.com/summary-only</link>
      <description><![CDATA[<p>Just a teaser, no full body here.</p>]]></description>
      <pubDate>Sat, 20 Jun 2026 09:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>"""


def _config_with_feed(name: str) -> MorningPaperConfig:
    config = MorningPaperConfig()
    config.sources.rss = [RssFeedConfig(name=name, url=f"https://example.com/{name}.xml", limit=5)]
    return config


class FullTextRssTest(unittest.TestCase):
    def test_content_encoded_lands_in_body_full(self) -> None:
        config = _config_with_feed("full")
        with patch("morning_paper.sources.requests.get", return_value=_FakeResponse(text=_FULLTEXT_ATOM)):
            items, errors = fetch_rss_feeds(config)
        self.assertEqual(errors, {})
        self.assertEqual(len(items), 1)
        item = items[0]
        # the full text comes through whole, never clipped
        self.assertGreater(len(item.body.split()), 200)
        self.assertGreaterEqual(len(item.body.split()), _FULL_WORD_COUNT - 5)
        self.assertIn("Paragraph 1", item.body)
        self.assertIn("Paragraph 8", item.body)
        # summary stays the short blurb, capped at 280
        self.assertLessEqual(len(item.summary), 280)
        self.assertIn("short blurb", item.summary)

    def test_summary_only_feed_has_empty_body(self) -> None:
        config = _config_with_feed("summary")
        with patch("morning_paper.sources.requests.get", return_value=_FakeResponse(text=_SUMMARY_ONLY_RSS)):
            items, errors = fetch_rss_feeds(config)
        self.assertEqual(errors, {})
        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item.body, "")
        self.assertIn("teaser", item.summary)
        self.assertLessEqual(len(item.summary), 280)

    def test_entry_body_handles_missing_content(self) -> None:
        # feedparser dict without `content` → empty body, no crash
        self.assertEqual(_entry_body({}), "")
        self.assertEqual(_entry_body({"content": []}), "")

    def test_render_full_body_prints_a_real_read(self) -> None:
        item = SourceItem(
            source_type="rss",
            source_name="Full Text Feed",
            title="The Full Essay",
            url="https://example.com/full-essay",
            summary="A short blurb that should stay short.",
            body="\n".join(_PARAS),
            author="Jordan",
            published_at="2026-06-20T09:00:00Z",
        )
        rendered = _render_broadsheet_reads([item], limit=2)
        # every paragraph of the full read prints — not a 4-paragraph clip
        self.assertEqual(rendered.count("<p>"), len(_PARAS))
        self.assertIn("Paragraph 1", rendered)
        self.assertIn("Paragraph 8", rendered)

    def test_render_summary_only_clips_to_blurb(self) -> None:
        item = SourceItem(
            source_type="rss",
            source_name="Summary Feed",
            title="Summary Only Story",
            url="https://example.com/summary-only",
            summary="\n".join(f"Blurb line {n}." for n in range(1, 9)),
            body="",
            author="",
        )
        rendered = _render_broadsheet_reads([item], limit=2)
        # the summary path still caps at 4 paragraphs — no regression
        self.assertEqual(rendered.count("<p>"), 4)
        self.assertIn("Blurb line 1.", rendered)
        self.assertNotIn("Blurb line 8.", rendered)


if __name__ == "__main__":
    unittest.main()
