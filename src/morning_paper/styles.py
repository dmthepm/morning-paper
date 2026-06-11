from __future__ import annotations

import re
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


STYLES: dict[str, StylePack] = {
    "editorial": StylePack(
        name="editorial",
        css_resource="styles/editorial.css",
        description="THE unified paper: serif editorial system for operator and reading content; no forced breaks, drawn marks, restrained color.",
    ),
    "typewriter": StylePack(
        name="typewriter",
        css_resource="styles/typewriter.css",
        description="The newspaper look: Courier Prime, masthead, card sections.",
    ),
    "flow": StylePack(
        name="flow",
        css_resource="styles/flow.css",
        description="Continuous operator brief: dense, no forced page breaks.",
    ),
    "ops-card": StylePack(
        name="ops-card",
        css_resource="styles/ops-card.css",
        description="Boxed reference one-pager: scripts, checklists, cheat sheets.",
    ),
    "magazine": StylePack(
        name="magazine",
        css_resource="styles/magazine.css",
        description="Long-read essay page: serif body, pull quotes, wide margins.",
    ),
    "zine": StylePack(
        name="zine",
        css_resource="styles/zine.css",
        description="Pocket how-to guide: half-letter, marker display type, checkbox steps.",
    ),
}

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
# not the network is up. Every font family a shipped stylesheet declares first
# must be in this table — never advertise a face the engine cannot load.
#   Courier Prime    — SIL OFL 1.1 (resources/fonts/OFL.txt)
#   Permanent Marker — Apache 2.0 (resources/fonts/LICENSE-PermanentMarker.txt)
_VENDORED_FONT_FACES: tuple[tuple[str, str, int, str], ...] = (
    ("Courier Prime", "CourierPrime-Regular.ttf", 400, "normal"),
    ("Courier Prime", "CourierPrime-Bold.ttf", 700, "normal"),
    ("Courier Prime", "CourierPrime-Italic.ttf", 400, "italic"),
    ("Permanent Marker", "PermanentMarker-Regular.ttf", 400, "normal"),
)

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
            f"src: url('{font_path.resolve().as_uri()}') format('truetype'); }}"
        )
    if not rules:
        return ""
    return "\n".join(rules) + "\n"


def get_style(name: str) -> StylePack:
    try:
        return STYLES[name]
    except KeyError:
        raise StyleError(f"unknown style: {name} (available: {', '.join(sorted(STYLES))})") from None


def get_palette(name: str) -> Palette:
    try:
        return PALETTES[name]
    except KeyError:
        raise StyleError(f"unknown palette: {name} (available: {', '.join(sorted(PALETTES))})") from None


def compose_css(style: str = "typewriter", palette: str = "mono", *, font_scale: float = 1.0) -> str:
    """Palette tokens first, then the style sheet that consumes them.

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
    css = _resource_text(palette_pack.css_resource) + "\n" + _resource_text(style_pack.css_resource)
    css = _GOOGLE_FONTS_IMPORT.sub("", css)
    composed = _font_face_css() + css
    if font_scale != 1.0:
        composed += f"\n:root {{ --mp-font-scale: {font_scale}; }}\n"
    return composed
