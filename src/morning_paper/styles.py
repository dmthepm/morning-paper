from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from importlib import resources
from pathlib import Path


class StyleError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class StylePack:
    name: str
    css_resource: str
    description: str


@dataclass(frozen=True, slots=True)
class Palette:
    name: str
    css_resource: str
    description: str
    chart_ink: str
    chart_track: str


# The style family: four packs, four jobs — each a print genre a stranger
# could sketch (2026-06-11 style-system audit). Names say the job, never a
# font or a CSS property.
STYLES: dict[str, StylePack] = {
    "broadsheet": StylePack(
        name="broadsheet",
        css_resource="styles/broadsheet.css",
        description="The newspaper you READ: unified serif system for operator front + reading edition; no forced breaks, drawn marks, restrained color.",
    ),
    "brief": StylePack(
        name="brief",
        css_resource="styles/brief.css",
        description="A compact paper you work through with a pen: dense Courier, Assignment Board rows, status cards, link-card grid, no forced page breaks.",
    ),
    "field-card": StylePack(
        name="field-card",
        css_resource="styles/field-card.css",
        description="The reference card you tape next to the phone: boxed sans one-pager — scripts, checklists, do/don't splits.",
    ),
    "zine": StylePack(
        name="zine",
        css_resource="styles/zine.css",
        description="The pocket guide you hand to someone: half-letter photocopier paste-up — marker strips, halftone bands, checkbox steps, command blocks.",
    ),
}

# 0.4.x pack names resolve to their successors for one release of grace
# (0.5.0): magazine was broadsheet's article layer; typewriter's link-card
# grid lives on in brief. Using an alias prints a deprecation warning once.
STYLE_ALIASES: dict[str, str] = {
    "editorial": "broadsheet",
    "magazine": "broadsheet",
    "flow": "brief",
    "typewriter": "brief",
    "ops-card": "field-card",
}

_WARNED_ALIASES: set[str] = set()


def resolve_style_name(name: str) -> str:
    """Canonical pack name for `name`; deprecated aliases warn once on stderr.

    Unknown names pass through unchanged so get_style raises its usual
    StyleError with the canonical list.
    """
    canonical = STYLE_ALIASES.get(name)
    if canonical is None:
        return name
    if name not in _WARNED_ALIASES:
        _WARNED_ALIASES.add(name)
        print(
            f"warning: style '{name}' is now '{canonical}' — the old name is deprecated "
            "and will be removed in a future release",
            file=sys.stderr,
        )
    return canonical

PALETTES: dict[str, Palette] = {
    "mono": Palette(
        name="mono",
        css_resource="palettes/mono.css",
        description="Black-and-white for laser printers; weight carries emphasis.",
        chart_ink="#222222",
        chart_track="#dddddd",
    ),
    "color": Palette(
        name="color",
        css_resource="palettes/color.css",
        description="Designed for color inkjet: warm ink, working red, data blue.",
        chart_ink="#2b5d8c",
        chart_track="#e7dfd2",
    ),
}


def _resource_text(relative: str) -> str:
    return resources.files("morning_paper").joinpath("resources", relative).read_text(encoding="utf-8")


# Vendored fonts so rendering is offline-deterministic: same glyphs whether or
# not the network is up — and identical on every machine, not just one that
# happens to have Palatino/Helvetica installed. Every font family a shipped
# stylesheet declares first must be in this table — never advertise a face the
# engine cannot load.
#   MP Serif         — TeX Gyre Pagella, a Palatino-metric serif
#                      (GUST Font License, resources/fonts/GUST-FONT-LICENSE.txt)
#   MP Sans          — Arimo, a Helvetica/Arial-metric sans
#                      (SIL OFL 1.1, resources/fonts/LICENSE-Arimo.txt)
#   Courier Prime    — SIL OFL 1.1 (resources/fonts/OFL.txt)
#   Permanent Marker — Apache 2.0 (resources/fonts/LICENSE-PermanentMarker.txt)
# MP Serif/MP Sans are the body faces every pack leads with; the older system
# names (Palatino, Helvetica Neue) stay in the CSS chains as fallback so a
# font-stripped install still renders, just not pixel-identically.
_VENDORED_FONT_FACES: tuple[tuple[str, str, int, str], ...] = (
    ("MP Serif", "texgyrepagella-regular.otf", 400, "normal"),
    ("MP Serif", "texgyrepagella-bold.otf", 700, "normal"),
    ("MP Serif", "texgyrepagella-italic.otf", 400, "italic"),
    ("MP Sans", "Arimo-Regular.ttf", 400, "normal"),
    ("MP Sans", "Arimo-Bold.ttf", 700, "normal"),
    ("MP Sans", "Arimo-Italic.ttf", 400, "italic"),
    ("Courier Prime", "CourierPrime-Regular.ttf", 400, "normal"),
    ("Courier Prime", "CourierPrime-Bold.ttf", 700, "normal"),
    ("Courier Prime", "CourierPrime-Italic.ttf", 400, "italic"),
    ("Permanent Marker", "PermanentMarker-Regular.ttf", 400, "normal"),
)


def _font_src_format(filename: str) -> str:
    """The @font-face src format() hint WeasyPrint matches against the file.

    A wrong hint makes WeasyPrint skip the face, so derive it from the suffix:
    OpenType/CFF (.otf, e.g. Pagella) is 'opentype'; TrueType (.ttf) is
    'truetype'.
    """
    return "opentype" if filename.lower().endswith(".otf") else "truetype"

_GOOGLE_FONTS_IMPORT = re.compile(
    r"^@import\s+url\(\s*['\"]?https://fonts\.googleapis\.com/[^)]*\)\s*;\s*$",
    re.MULTILINE,
)

FONT_SCALE_MIN = 0.8
FONT_SCALE_MAX = 1.5


def _font_face_css() -> str:
    """@font-face rules pointing at the vendored font files.

    Absolute file:// URLs so WeasyPrint resolves them without a base_url.
    Families whose files are missing (stripped or non-filesystem install) are
    skipped and their font-family fallback chains carry the page.
    """
    rules: list[str] = []
    missing_families: set[str] = set()
    fonts = resources.files("morning_paper").joinpath("resources", "fonts")
    for family, filename, weight, font_style in _VENDORED_FONT_FACES:
        if family in missing_families:
            continue
        font_path = Path(str(fonts.joinpath(filename)))
        if not font_path.is_file():
            missing_families.add(family)
            rules = [rule for rule in rules if f"'{family}'" not in rule]
            continue
        rules.append(
            f"@font-face {{ font-family: '{family}'; "
            f"font-style: {font_style}; font-weight: {weight}; "
            f"src: url('{font_path.resolve().as_uri()}') "
            f"format('{_font_src_format(filename)}'); }}"
        )
    if not rules:
        return ""
    return "\n".join(rules) + "\n"


def get_style(name: str) -> StylePack:
    try:
        return STYLES[resolve_style_name(name)]
    except KeyError:
        raise StyleError(f"unknown style: {name} (available: {', '.join(sorted(STYLES))})") from None


def get_palette(name: str) -> Palette:
    try:
        return PALETTES[name]
    except KeyError:
        raise StyleError(f"unknown palette: {name} (available: {', '.join(sorted(PALETTES))})") from None


# The shared taste layer (layout-primitives spec Phase 1): keep-together,
# orphans/widows, atomic furniture, tasteful split seams. Composed FIRST so
# every pack's own rules win on equal specificity by source order — the four
# packs keep their exact look; the three that lacked keep-together gain it.
_BASE_CSS_RESOURCE = "styles/_base.css"


def compose_css(style: str = "broadsheet", palette: str = "mono", *, font_scale: float = 1.0) -> str:
    """Base taste layer, then palette tokens, then the style sheet.

    The composition is three sheets in cascade order:
        _base.css  +  palette sheet  +  style pack  [ + trailing :root scale ]
    `_base.css` is the shared keep-together / orphans-widows / atomic-furniture
    layer; because it is laid down first, any pack rule overrides it by source
    order, so the packs keep their exact current look and the only behavioral
    change is brief/field-card/zine gaining the widow/keep control broadsheet
    already had.

    Google Fonts @import lines in the shipped sheets are stripped and replaced
    with @font-face rules over the vendored files: no network at render time.

    `font_scale` multiplies each style's base body size (every sheet sets
    `body { font-size: calc(var(--mp-font-scale, 1) * …) }`); the knob is a
    `:root` override appended after the sheets so it wins the cascade.
    """
    if not FONT_SCALE_MIN <= font_scale <= FONT_SCALE_MAX:
        raise StyleError(
            f"font_scale must be between {FONT_SCALE_MIN} and {FONT_SCALE_MAX} (got {font_scale})"
        )
    style_pack = get_style(style)
    palette_pack = get_palette(palette)
    css = (
        _resource_text(_BASE_CSS_RESOURCE)
        + "\n"
        + _resource_text(palette_pack.css_resource)
        + "\n"
        + _resource_text(style_pack.css_resource)
    )
    css = _GOOGLE_FONTS_IMPORT.sub("", css)
    composed = _font_face_css() + css
    if font_scale != 1.0:
        composed += f"\n:root {{ --mp-font-scale: {font_scale}; }}\n"
    return composed
