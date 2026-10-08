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
        self.assertEqual(builder.main(self.args), 0)  # same bytes rebuild the one existing episode
        self.assertEqual(len(json.loads((self.out / "episodes.json").read_text())), 1)

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

    @patch.object(builder, "duration", return_value=31)
    def test_rejects_non_rgb_transparent_and_mislabeled_artwork_without_writing(self, _duration):
        Image.new("L", (1400, 1400), 80).save(self.art)
        self.assertEqual(builder.main(self.args), 1)
        self.assertFalse(self.out.exists())

        Image.new("RGB", (1400, 1400), "navy").save(self.art, transparency=(0, 0, 128))
        self.assertEqual(builder.main(self.args), 1)
        self.assertFalse(self.out.exists())

        wrong = self.root / "wrong.jpg"
        Image.new("RGB", (1400, 1400), "navy").save(self.art)
        wrong.write_bytes(self.art.read_bytes())  # opaque RGB PNG bytes with a JPEG suffix
        args = self.args.copy()
        args[args.index("--artwork") + 1] = str(wrong)
        self.assertEqual(builder.main(args), 1)
        self.assertFalse(self.out.exists())

        Image.new("RGB", (1400, 1400), "navy").save(self.art)
        self.assertEqual(builder.main(self.args + ["--cover-name", "../cover.png"]), 1)
        self.assertFalse(self.out.exists())

    @patch.object(builder, "duration", return_value=31)
    def test_existing_audio_rebuilds_host_and_visibility_without_losing_guid(self, _duration):
        self.assertEqual(builder.main(self.args), 0)
        old = json.loads((self.out / "episodes.json").read_text())[0]
        args = self.args.copy()
        args[args.index("--base-url") + 1] = "https://podcast.example.org/reader"
        args[args.index("--show-title") + 1] = "Second Paper"
        args[args.index("--episode-title") + 1] = "Retitled attempt"
        args[args.index("--published-at") + 1] = "2026-10-08T12:00:00Z"
        args += ["--visibility", "public", "--cover-name", "cover-new.png"]
        self.assertEqual(builder.main(args), 0)
        self.assertEqual(builder.main(args), 0)  # unchanged rerun is idempotent
        episodes = json.loads((self.out / "episodes.json").read_text())
        self.assertEqual(len(episodes), 1)
        self.assertEqual(episodes[0]["guid"], old["guid"])
        self.assertEqual(episodes[0]["published_at"], old["published_at"])
        self.assertEqual(episodes[0]["title"], old["title"])
        self.assertEqual(sorted(path.name for path in (self.out / "episodes").iterdir()), [old["file"]])
        channel = ET.parse(self.out / "feed.xml").getroot().find("channel")
        self.assertEqual(channel.findtext("title"), "Second Paper")
        self.assertIsNone(channel.find(f"{{{builder.ITUNES}}}block"))
        self.assertEqual(channel.find(f"{{{builder.ITUNES}}}image").get("href"),
                         "https://podcast.example.org/reader/cover-new.png")
        self.assertTrue((self.out / "cover-new.png").is_file())
        self.assertTrue(channel.find("item/enclosure").get("url").startswith("https://podcast.example.org/reader/"))

    @patch.object(builder, "duration", return_value=31)
    def test_rejects_unencoded_or_hostless_base_urls(self, _duration):
        self.assertEqual(builder.base_url("https://example.invalid/my%20paper"),
                         "https://example.invalid/my%20paper")
        for url in ("https://example.invalid/my podcast", "https://example.invalid/über",
                    "https://:443/podcast", "https://exa mple.invalid/podcast",
                    "https://example..invalid/podcast", "https://-example.invalid/podcast",
                    "https://example.invalid:/podcast", "https://@example.invalid/podcast"):
            with self.subTest(url=url):
                args = self.args.copy()
                args[args.index("--base-url") + 1] = url
                self.assertEqual(builder.main(args), 1)
                self.assertFalse(self.out.exists())


if __name__ == "__main__":
    unittest.main()
