from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from morning_paper import cli
from morning_paper.config import MorningPaperConfig
from morning_paper.renderers import _load_weasyprint
from morning_paper.styles import PALETTES, STYLES, compose_css


def _pretty_stack_ready() -> bool:
    html_cls, _error = _load_weasyprint()
    return html_cls is not None


class VendoredFontsTest(unittest.TestCase):
    def test_compose_css_never_imports_google_fonts(self) -> None:
        for style in STYLES:
            for palette in PALETTES:
                css = compose_css(style, palette)
                self.assertNotIn("fonts.googleapis.com", css, (style, palette))

    def test_compose_css_embeds_vendored_courier_prime(self) -> None:
        css = compose_css("typewriter", "mono")
        self.assertIn("@font-face", css)
        self.assertIn("'Courier Prime'", css)
        self.assertIn("file://", css)
        for filename in ("CourierPrime-Regular.ttf", "CourierPrime-Bold.ttf", "CourierPrime-Italic.ttf"):
            self.assertIn(filename, css)


class DemoCommandTest(unittest.TestCase):
    @unittest.skipUnless(_pretty_stack_ready(), "demo render requires the pretty print stack (weasyprint)")
    def test_demo_renders_sample_edition_and_prints_next_steps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = MorningPaperConfig()
            config.outputs.directory = Path(tmp) / "out"
            stdout = io.StringIO()
            with patch("morning_paper.cli.MorningPaperConfig", return_value=config):
                with redirect_stdout(stdout):
                    rc = cli.main(["demo"])
            self.assertEqual(rc, 0)

            lines = stdout.getvalue().rstrip("\n").splitlines()
            payload = json.loads("\n".join(lines[:-3]))
            self.assertEqual(payload["mode"], "demo")
            self.assertEqual(payload["style"], "editorial")
            self.assertEqual(payload["palette"], "color")
            self.assertIsInstance(payload["pages"], int)
            self.assertGreaterEqual(payload["pages"], 1)
            for key in ("json", "markdown", "html", "pdf"):
                path = Path(payload["outputs"][key])
                self.assertTrue(path.exists(), key)
                self.assertGreater(path.stat().st_size, 0, key)

            self.assertEqual(lines[-3], f"Print it: lp {payload['outputs']['pdf']}")
            self.assertEqual(
                lines[-2],
                'Make it yours: uv tool install "morning-paper[pretty]" && morning-paper init (or run the setup skill in Claude Code)',
            )
            self.assertEqual(lines[-1], "Post your paper: https://github.com/dmthepm/morning-paper/discussions")

            # offline-deterministic: the typeset HTML carries vendored fonts, no network fetches
            html_text = Path(payload["outputs"]["html"]).read_text(encoding="utf-8")
            self.assertNotIn("fonts.googleapis.com", html_text)
            self.assertIn("@font-face", html_text)

            # honesty doctrine: the sample edition declares itself fictional
            markdown_text = Path(payload["outputs"]["markdown"]).read_text(encoding="utf-8")
            self.assertIn("fictional", markdown_text.lower())

    def test_demo_fails_honestly_without_pretty_stack(self) -> None:
        stderr = io.StringIO()
        with patch("morning_paper.cli._load_weasyprint", return_value=(None, "missing")):
            with redirect_stderr(stderr):
                rc = cli.main(["demo"])
        self.assertEqual(rc, 1)
        output = stderr.getvalue()
        self.assertIn("pretty print stack", output)
        self.assertIn("morning-paper doctor", output)

    def test_demo_rejects_unknown_arguments(self) -> None:
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            rc = cli.main(["demo", "--bogus"])
        self.assertEqual(rc, 2)
        self.assertIn("unknown demo argument", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
