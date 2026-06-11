from __future__ import annotations

from dataclasses import dataclass
from importlib import resources


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
    """Palette tokens first, then the style sheet that consumes them."""
    style_pack = get_style(style)
    palette_pack = get_palette(palette)
    return _resource_text(palette_pack.css_resource) + "\n" + _resource_text(style_pack.css_resource)
