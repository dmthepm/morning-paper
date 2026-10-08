"""The local builder must create a usable RSS enclosure without uploading."""

import importlib.util
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

from PIL import Image


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_podcast_feed.py"
SPEC = importlib.util.spec_from_file_location("build_podcast_feed", SCRIPT)
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


class FeedBuilderTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.audio = self.root / "clip.m4a"
        self.audio.write_bytes(b"local test audio")
        self.art = self.root / "art.png"
        Image.new("RGB", (1400, 1400), "navy").save(self.art)
        self.out = self.root / "feed"
        self.args = [
            "--output-dir", str(self.out), "--base-url", "https://example.invalid/podcast",
            "--audio", str(self.audio), "--artwork", str(self.art),
            "--show-title", "Sample Paper", "--show-description", "A spoken paper",
            "--author", "Sample Editor", "--episode-title", "First edition",
            "--episode-description", "A short test", "--published-at", "2026-10-07T12:00:00Z",
        ]

    @patch.object(builder, "duration", return_value=31)
    def test_builds_private_feed_with_exact_enclosure_length(self, _duration):
        self.assertEqual(builder.main(self.args), 0)
        root = ET.parse(self.out / "feed.xml").getroot()
        channel = root.find("channel")
        self.assertEqual(channel.findtext("title"), "Sample Paper")
        self.assertEqual(channel.findtext("language"), "en-us")
        self.assertEqual(channel.findtext(f"{{{builder.ITUNES}}}block"), "Yes")
        self.assertEqual(channel.find(f"{{{builder.ITUNES}}}image").get("href"),
                         "https://example.invalid/podcast/cover.png")
        item = channel.find("item")
        self.assertEqual(item.findtext(f"{{{builder.ITUNES}}}duration"), "31")
        enclosure = item.find("enclosure")
        self.assertEqual(enclosure.get("type"), "audio/x-m4a")
        self.assertEqual(int(enclosure.get("length")),
                         (self.out / "episodes" / Path(enclosure.get("url")).name).stat().st_size)
        self.assertEqual(len(json.loads((self.out / "episodes.json").read_text())), 1)
        self.assertEqual(builder.main(self.args), 1)  # same bytes cannot make another episode

    @patch.object(builder, "duration", return_value=31)
    def test_dry_run_writes_nothing(self, _duration):
        self.assertEqual(builder.main(self.args + ["--dry-run"]), 0)
        self.assertFalse(self.out.exists())

    @patch.object(builder, "duration", return_value=31)
    def test_requires_https_and_opaque_artwork(self, _duration):
        args = self.args.copy()
        args[args.index("--base-url") + 1] = "http://example.invalid/podcast"
        self.assertEqual(builder.main(args), 1)
        Image.new("RGBA", (1400, 1400), "navy").save(self.art)
        self.assertEqual(builder.main(self.args), 1)


if __name__ == "__main__":
    unittest.main()
