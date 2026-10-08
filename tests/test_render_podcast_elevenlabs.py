"""The direct-provider gate makes no request until --render is explicit."""

import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "render_podcast_elevenlabs.py"
SPEC = importlib.util.spec_from_file_location("render_podcast_elevenlabs", SCRIPT)
renderer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(renderer)


class FakeResponse:
    headers = {"Content-Type": "audio/mpeg"}

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self):
        return b"fake audio bytes"


class RenderGateTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.script = root / "script.txt"
        self.script.write_text("A short reviewed script.")
        self.output = root / "source.mp3"
        self.args = ["--script", str(self.script), "--output", str(self.output),
                     "--voice-id", "voice_123", "--model-id", "model_456"]

    def test_dry_run_needs_no_key_and_makes_no_request(self):
        out = io.StringIO()
        with patch.dict("os.environ", {}, clear=True), patch.object(renderer.urllib.request, "urlopen") as urlopen:
            with contextlib.redirect_stdout(out):
                self.assertEqual(renderer.main(self.args), 0)
        urlopen.assert_not_called()
        self.assertFalse(self.output.exists())
        self.assertFalse(json.loads(out.getvalue())["paid_request"])

    def test_explicit_render_uses_environment_key_and_writes_audio_once(self):
        out = io.StringIO()
        with patch.dict("os.environ", {"ELEVENLABS_API_KEY": "test-only-key"}):
            with patch.object(renderer.urllib.request, "urlopen", return_value=FakeResponse()) as urlopen:
                with contextlib.redirect_stdout(out):
                    self.assertEqual(renderer.main(self.args + ["--render"]), 0)
        request = urlopen.call_args.args[0]
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(json.loads(request.data), {"text": "A short reviewed script.", "model_id": "model_456"})
        self.assertEqual(self.output.read_bytes(), b"fake audio bytes")
        self.assertNotIn("test-only-key", out.getvalue())
        with patch.object(renderer.urllib.request, "urlopen") as second:
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(renderer.main(self.args + ["--render"]), 1)
        second.assert_not_called()


if __name__ == "__main__":
    unittest.main()
