"""The 0.5.0 style family: four canonical packs, one release of alias grace.

broadsheet (was editorial; absorbed magazine) — brief (was flow; absorbed
typewriter's link-card grid) — field-card (was ops-card) — zine (v2).
"""

from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

from morning_paper import styles
from morning_paper.config import ConfigError, load_config
from morning_paper.renderers import _load_weasyprint, count_pages
from morning_paper.styles import (
    PALETTES,
    STYLE_ALIASES,
    STYLES,
    StyleError,
    compose_css,
    get_style,
    resolve_style_name,
)


def _pretty_stack_ready() -> bool:
    html_cls, _error = _load_weasyprint()
    return html_cls is not None


class StyleFamilyTest(unittest.TestCase):
    def test_the_family_is_four_packs(self) -> None:
        self.assertEqual(sorted(STYLES), ["brief", "broadsheet", "field-card", "zine"])

    def test_alias_table_matches_the_audit(self) -> None:
        self.assertEqual(
            STYLE_ALIASES,
            {
                "editorial": "broadsheet",
                "magazine": "broadsheet",
                "flow": "brief",
                "typewriter": "brief",
                "ops-card": "field-card",
            },
        )
        for alias, canonical in STYLE_ALIASES.items():
            self.assertIn(canonical, STYLES, alias)
            self.assertNotIn(alias, STYLES, alias)

    def test_alias_resolves_and_warns_once_on_stderr(self) -> None:
        styles._WARNED_ALIASES.clear()
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            self.assertEqual(get_style("editorial").name, "broadsheet")
            get_style("editorial")  # second use: no repeat nagging
        output = stderr.getvalue()
        self.assertIn("style 'editorial' is now 'broadsheet'", output)
        self.assertEqual(output.count("deprecated"), 1)

    def test_canonical_names_resolve_silently(self) -> None:
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            for name in STYLES:
                self.assertEqual(resolve_style_name(name), name)
                self.assertEqual(get_style(name).name, name)
        self.assertEqual(stderr.getvalue(), "")

    def test_unknown_style_raises_with_the_canonical_list(self) -> None:
        with self.assertRaises(StyleError) as ctx:
            get_style("gazette")
        message = str(ctx.exception)
        self.assertIn("gazette", message)
        for name in STYLES:
            self.assertIn(name, message)

    def test_compose_css_accepts_aliases_and_matches_canonical(self) -> None:
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            for alias, canonical in STYLE_ALIASES.items():
                self.assertEqual(compose_css(alias, "mono"), compose_css(canonical, "mono"), alias)


class ConfigStyleValidationTest(unittest.TestCase):
    def _load_style(self, style: str) -> str:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.yaml"
            config_path.write_text(
                f"name: Test\noutputs:\n  directory: {tmp}/out\n  style: {style}\n",
                encoding="utf-8",
            )
            return load_config(config_path).outputs.style

    def test_config_accepts_canonical_names(self) -> None:
        for name in STYLES:
            self.assertEqual(self._load_style(name), name)

    def test_config_accepts_aliases_and_stores_canonical(self) -> None:
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            for alias, canonical in STYLE_ALIASES.items():
                self.assertEqual(self._load_style(alias), canonical)

    def test_config_rejects_unknown_style_with_canonical_list(self) -> None:
        with self.assertRaises(ConfigError) as ctx:
            self._load_style("gazette")
        self.assertIn("broadsheet", str(ctx.exception))


_FAMILY_SAMPLE = """\
<span class="mp-footer-date">2026-06-11</span><span class="mp-footer-name">Family Smoke</span>

# The Family Smoke Test

A paragraph of honest prose so every pack has something to typeset.

## Steps

- one thing
- another thing

```
$ morning-paper render sample.md --style broadsheet
```

```mp-stats
Packs | 4 | down from six
Aliases | 5 | one release of grace
```
"""

# The zine v2 sample (abridged from the audited prototype): cover plate with
# rotated strips, halftone bands, stamp, spec rows, paste-up scraps, steps,
# inverted command bars, warning, cut-out card, colophon.
_ZINE_V2_SAMPLE = """\
<span class="mp-footer-date">June 2026</span>
<span class="mp-footer-name">Morning Paper</span>

<div class="z2-masthead">Morning Paper &middot; Pocket Series &middot; Nº 2</div>

<div class="z2-plate">
  <div><span class="z2-strip">WAKE THE</span></div>
  <div><span class="z2-strip alt">PRINTER!</span></div>
  <div class="z2-plate-sub">the LaserJet revival guide</div>
</div>
<div class="z2-plate-dots"></div>
<div class="z2-dots-exit"></div>

<div class="z2-stamp-row"><span class="z2-stamp">Free &middot; Fold &middot; Staple</span></div>

<div class="z2-specs">
  <div class="row"><span class="k">Subject</span><span class="v">a jammed LaserJet</span></div>
  <div class="row"><span class="k">Time needed</span><span class="v">about five minutes</span></div>
</div>

<div class="z2-cut tilt-r"><div class="z2-cut-in">
  <div class="z2-toc-title">INSIDE THIS ISSUE</div>
  <div class="z2-toc-row"><span>Clear the stale queue</span><span class="pg">p.2</span></div>
</div></div>

<div class="page-break"></div>

<div class="z2-warn">
  <div class="z2-warn-head">Read this first</div>
  <div class="z2-warn-body">Clear the queue <strong>before</strong> powering on.</div>
</div>

# Clear the stale queue

<div class="z2-step"><strong>SSH in</strong> from any machine on the tailnet:</div>

<div class="z2-cmd">ssh homelab</div>

<div class="z2-step"><strong>Cancel everything stale:</strong></div>

<div class="z2-cmd">cancel -a HP-LaserJet-M15w</div>

<div class="z2-cut"><div class="z2-cut-in">
  <div class="say">"The queue remembers everything you ever asked it to do."</div>
  <div class="who">ops wisdom, June 2026</div>
</div></div>

<span class="z2-sticker">5 min job</span>

<div class="z2-note">solid light = good. blinking = it forgot you.</div>

<div class="z2-dots"></div>

<div class="z2-cutout">
  <div class="z2-cutout-label">&mdash; cut here &mdash;</div>
  <div class="t">PRINTER FIRST AID</div>
  <div class="r"><strong>queue jammed</strong> &mdash; <code>cancel -a</code></div>
</div>

<div class="z2-colophon"><div class="z2-colophon-in">
  <div class="big">Morning Paper &middot; Pocket Series</div>
  <div class="small">Set in Courier Prime &amp; Permanent Marker.<br/>Texture is pure CSS.</div>
</div></div>
"""


class RenderSmokeTest(unittest.TestCase):
    @unittest.skipUnless(_pretty_stack_ready(), "render smoke requires the pretty print stack (weasyprint)")
    def test_four_packs_render_both_palettes(self) -> None:
        for style in STYLES:
            for palette in PALETTES:
                pages = count_pages(_FAMILY_SAMPLE, style=style, palette=palette)
                self.assertGreaterEqual(pages, 1, (style, palette))

    @unittest.skipUnless(_pretty_stack_ready(), "render smoke requires the pretty print stack (weasyprint)")
    def test_zine_v2_renders_its_sample_on_both_palettes(self) -> None:
        for palette in PALETTES:
            pages = count_pages(_ZINE_V2_SAMPLE, style="zine", palette=palette)
            self.assertGreaterEqual(pages, 2, palette)


if __name__ == "__main__":
    unittest.main()
