"""The direct-provider gate makes no request until --render is explicit."""

import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
import urllib.request
from email.message import Message
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "render_podcast_elevenlabs.py"
SPEC = importlib.util.spec_from_file_location("render_podcast_elevenlabs", SCRIPT)
renderer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(renderer)


class FakeResponse:
    code = 200
    msg = "OK"
    headers = {"Content-Type": "audio/mpeg"}

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self):
        return b"fake audio bytes"

    def info(self):
        return self.headers


class RedirectResponse(io.BytesIO):
    def __init__(self, location):
        super().__init__(b"")
        self.code = 302
        self.msg = "Found"
        self.headers = Message()
        self.headers["Location"] = location

    def info(self):
        return self.headers


class RedirectTransport(urllib.request.BaseHandler):
    handler_order = 100

    def __init__(self, location):
        self.location = location
        self.requests = []

    def https_open(self, request):
        self.requests.append(request)
        return FakeResponse() if request.full_url == self.location else RedirectResponse(self.location)

    def http_open(self, request):
        self.requests.append(request)
        return FakeResponse()


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
            with patch.object(renderer.urllib.request, "build_opener") as build_opener:
                build_opener.return_value.open.return_value = FakeResponse()
                with contextlib.redirect_stdout(out):
                    self.assertEqual(renderer.main(self.args + ["--render"]), 0)
        request = build_opener.return_value.open.call_args.args[0]
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(json.loads(request.data), {"text": "A short reviewed script.", "model_id": "model_456"})
        self.assertEqual(self.output.read_bytes(), b"fake audio bytes")
        self.assertNotIn("test-only-key", out.getvalue())
        with patch.object(renderer.urllib.request, "build_opener") as second:
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(renderer.main(self.args + ["--render"]), 1)
        second.assert_not_called()

    def test_invalid_header_error_never_exposes_key(self):
        marker = "test-only-key-marker"
        err = io.StringIO()
        out = io.StringIO()
        with patch.dict("os.environ", {"ELEVENLABS_API_KEY": marker + "\n"}):
            with patch.object(renderer.urllib.request, "build_opener") as opener:
                with patch.object(renderer.urllib.request, "urlopen",
                                  side_effect=ValueError("Invalid header value " + marker)):
                    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                        self.assertEqual(renderer.main(self.args + ["--render"]), 1)
        opener.assert_not_called()
        self.assertNotIn(marker, out.getvalue())
        self.assertNotIn(marker, err.getvalue())
        self.assertFalse(self.output.exists())

    def test_request_exception_never_exposes_key(self):
        marker = "test-only-key-marker"
        err = io.StringIO()
        with patch.dict("os.environ", {"ELEVENLABS_API_KEY": marker}):
            with patch.object(renderer.urllib.request, "build_opener") as opener:
                opener.return_value.open.side_effect = ValueError("Invalid header value " + marker)
                with contextlib.redirect_stderr(err):
                    self.assertEqual(renderer.main(self.args + ["--render"]), 1)
        self.assertNotIn(marker, err.getvalue())
        self.assertFalse(self.output.exists())

    def test_redirects_make_only_one_request_and_never_forward_key(self):
        original_build_opener = urllib.request.build_opener
        for location in ("https://api.elevenlabs.io/other", "http://other.invalid/other"):
            with self.subTest(location=location):
                transport = RedirectTransport(location)

                def build_opener(*handlers):
                    return original_build_opener(urllib.request.ProxyHandler({}), transport, *handlers)

                err = io.StringIO()
                with patch.dict("os.environ", {"ELEVENLABS_API_KEY": "test-only-key"}):
                    with patch.object(renderer.urllib.request, "build_opener", side_effect=build_opener):
                        with patch.object(renderer.urllib.request, "urlopen",
                                          side_effect=lambda request, **kw: original_build_opener(
                                              urllib.request.ProxyHandler({}), transport).open(request, **kw)):
                            with contextlib.redirect_stderr(err):
                                self.assertEqual(renderer.main(self.args + ["--render"]), 1)
                self.assertEqual(len(transport.requests), 1)
                self.assertEqual(transport.requests[0].get_method(), "POST")
                self.assertEqual(transport.requests[0].full_url.split("/", 3)[:3],
                                 ["https:", "", "api.elevenlabs.io"])
                self.assertFalse(self.output.exists())
                self.assertIn("HTTP 302", err.getvalue())
                self.assertNotIn("test-only-key", err.getvalue())


if __name__ == "__main__":
    unittest.main()
