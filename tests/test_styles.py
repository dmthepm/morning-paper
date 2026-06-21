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


class BaseTasteLayerTest(unittest.TestCase):
    """0.6.0 layout-primitives spec Phase 1: the shared keep-together base sheet.

    The base supplies orphans/widows, head-glue, atomic-furniture keeps, and
    tasteful split seams to ALL four packs; it is composed FIRST so each pack's
    own rules still win on source order (broadsheet's look is unchanged).
    """

    def test_base_sheet_resource_exists(self) -> None:
        from importlib import resources

        base = resources.files("morning_paper").joinpath("resources", "styles", "_base.css")
        self.assertTrue(base.is_file())

    def test_base_is_composed_first_then_palette_then_pack(self) -> None:
        # the three sheets in cascade order: _base + palette + pack
        css = compose_css("broadsheet", "color")
        i_base = css.find("the shared taste layer")  # _base.css header phrase
        i_palette = css.find("--mp-")  # palette tokens declare --mp-* first
        i_pack = css.find("THE unified Morning Paper system")  # broadsheet.css header
        self.assertGreaterEqual(i_base, 0)
        self.assertGreaterEqual(i_palette, 0)
        self.assertGreaterEqual(i_pack, 0)
        self.assertLess(i_base, i_palette, "base must precede palette")
        self.assertLess(i_palette, i_pack, "palette must precede the pack")
        # @font-face still leads (vendored fonts before any selector)
        i_font = css.find("@font-face")
        self.assertTrue(0 <= i_font < i_base, "font-face must precede the base sheet")

    def test_all_four_packs_carry_the_keep_together_contract(self) -> None:
        # the regression Phase 1 closes: brief/field-card/zine had NO
        # orphans/widows and no head-glue; now every pack does.
        for style in STYLES:
            css = compose_css(style, "mono")
            self.assertIn("orphans: 3; widows: 3", css, style)
            self.assertIn("break-after: avoid; page-break-after: avoid", css, style)
            self.assertIn(
                ".article-head { break-inside: avoid; page-break-inside: avoid; }", css, style
            )
            self.assertIn("box-decoration-break: clone", css, style)

    def test_base_uses_only_soft_breaks_no_forced_page_break(self) -> None:
        # doctrine guardrail: the default tier never forces a page; forced
        # breaks stay each pack's own documented .page-break escape hatch.
        from importlib import resources

        import re

        base = resources.files("morning_paper").joinpath(
            "resources", "styles", "_base.css"
        ).read_text(encoding="utf-8")
        # strip /* … */ comments so we test the actual CSS, not the prose that
        # names the quirks it avoids
        rules = re.sub(r"/\*.*?\*/", "", base, flags=re.DOTALL)
        self.assertNotIn("break-before: page", rules)
        self.assertNotIn("page-break-before: always", rules)
        # never the banked crash/no-op CSS
        self.assertNotIn("box-shadow", rules)
        self.assertNotIn("float", rules)

    def test_base_keeps_furniture_atomic(self) -> None:
        css = compose_css("brief", "color")
        for selector in (".mp-chart", ".mp-stat", ".move", ".action-required", "table.data tr", "blockquote"):
            self.assertIn(selector, css, selector)

    @unittest.skipUnless(_pretty_stack_ready(), "render requires the pretty print stack (weasyprint)")
    def test_broadsheet_default_look_unchanged_by_base(self) -> None:
        # The base is composed first, so equal-specificity pack rules win by
        # source order. The demo edition (broadsheet/color) must lay out
        # identically: same page count and same content placement per page.
        from importlib import resources

        from morning_paper.renderers import _load_weasyprint, _render_html_from_markdown

        md = resources.files("morning_paper").joinpath("resources", "demo.md").read_text(encoding="utf-8")
        html_cls, _ = _load_weasyprint()
        doc = html_cls(string=_render_html_from_markdown(md, style="broadsheet", palette="color")).render()
        # the broadsheet demo is a stable 2-page edition; the base must not
        # reflow it (the keep rules only newly affect the OTHER three packs).
        self.assertEqual(len(doc.pages), 2)

    @unittest.skipUnless(_pretty_stack_ready(), "render requires the pretty print stack (weasyprint)")
    def test_over_tall_kept_block_fails_soft(self) -> None:
        # fail-soft contract: a kept block taller than a page must flow, not
        # produce blank/infinite pages. A huge atomic table degrades cleanly.
        rows = "\n".join(
            f'<tr><td>row {n} with enough text to take real vertical space on the page</td></tr>'
            for n in range(400)
        )
        markdown = (
            '<span class="mp-footer-name">Soft</span>\n\n'
            '<table class="data">' + rows + "</table>\n"
        )
        pages = count_pages(markdown, style="broadsheet", palette="mono")
        # finite and plural — it flowed across pages rather than hanging
        self.assertGreater(pages, 1)
        self.assertLess(pages, 50)


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
