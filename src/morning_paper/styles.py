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


# Courier Prime is vendored (SIL OFL 1.1; resources/fonts/OFL.txt) so rendering
# is offline-deterministic: same glyphs whether or not the network is up.
_VENDORED_FONT_FACES: tuple[tuple[str, int, str], ...] = (
    ("CourierPrime-Regular.ttf", 400, "normal"),
    ("CourierPrime-Bold.ttf", 700, "normal"),
    ("CourierPrime-Italic.ttf", 400, "italic"),
)

_GOOGLE_FONTS_IMPORT = re.compile(
    r"^@import\s+url\(\s*['\"]?https://fonts\.googleapis\.com/[^)]*\)\s*;\s*$",
    re.MULTILINE,
)


def _font_face_css() -> str:
    """@font-face rules pointing at the vendored Courier Prime files.

    Absolute file:// URLs so WeasyPrint resolves them without a base_url.
    If the font files are missing (stripped or non-filesystem install) we
    return nothing and let the font-family fallback chains carry the page.
    """
    rules: list[str] = []
    fonts = resources.files("morning_paper").joinpath("resources", "fonts")
    for filename, weight, font_style in _VENDORED_FONT_FACES:
        font_path = Path(str(fonts.joinpath(filename)))
        if not font_path.is_file():
            return ""
        rules.append(
            "@font-face { font-family: 'Courier Prime'; "
            f"font-style: {font_style}; font-weight: {weight}; "
            f"src: url('{font_path.resolve().as_uri()}') format('truetype'); }}"
        )
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


def compose_css(style: str = "typewriter", palette: str = "mono") -> str:
    """Palette tokens first, then the style sheet that consumes them.

    Google Fonts @import lines in the shipped sheets are stripped and replaced
    with @font-face rules over the vendored files: no network at render time.
    """
    style_pack = get_style(style)
    palette_pack = get_palette(palette)
    css = _resource_text(palette_pack.css_resource) + "\n" + _resource_text(style_pack.css_resource)
    css = _GOOGLE_FONTS_IMPORT.sub("", css)
    return _font_face_css() + css
