from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


DEFAULT_CONFIG_DIR = Path.home() / ".config" / "morning-paper"
DEFAULT_CONFIG_PATH = DEFAULT_CONFIG_DIR / "config.yaml"
DEFAULT_OUTPUT_DIR = Path.home() / ".local" / "share" / "morning-paper"


@dataclass(slots=True)
class HackerNewsConfig:
    enabled: bool = True
    limit: int = 20


@dataclass(slots=True)
class RssFeedConfig:
    name: str
    url: str
    limit: int = 5


@dataclass(slots=True)
class SourcesConfig:
    hacker_news: HackerNewsConfig = field(default_factory=HackerNewsConfig)
    rss: list[RssFeedConfig] = field(default_factory=list)


@dataclass(slots=True)
class OutputsConfig:
    directory: Path = DEFAULT_OUTPUT_DIR
    pdf: bool = True
    html: bool = True
    markdown: bool = True
    json: bool = True


@dataclass(slots=True)
class MorningPaperConfig:
    name: str = "Morning Paper"
    timezone: str = "America/Los_Angeles"
    profile: str = ""
    sources: SourcesConfig = field(default_factory=SourcesConfig)
    outputs: OutputsConfig = field(default_factory=OutputsConfig)


def _expand_path(raw: str | Path | None, *, default: Path) -> Path:
    if not raw:
        return default
    return Path(raw).expanduser().resolve()


def load_config(path: Path) -> MorningPaperConfig:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    sources = data.get("sources") or {}
    outputs = data.get("outputs") or {}
    hn = sources.get("hacker_news") or {}
    rss_feeds = [
        RssFeedConfig(
            name=str(feed["name"]),
            url=str(feed["url"]),
            limit=int(feed.get("limit", 5)),
        )
        for feed in (sources.get("rss") or [])
        if feed.get("name") and feed.get("url")
    ]
    return MorningPaperConfig(
        name=str(data.get("name", "Morning Paper")),
        timezone=str(data.get("timezone", "America/Los_Angeles")),
        profile=str(data.get("profile", "")).strip(),
        sources=SourcesConfig(
            hacker_news=HackerNewsConfig(
                enabled=bool(hn.get("enabled", True)),
                limit=int(hn.get("limit", 20)),
            ),
            rss=rss_feeds,
        ),
        outputs=OutputsConfig(
            directory=_expand_path(outputs.get("directory"), default=DEFAULT_OUTPUT_DIR),
            pdf=bool(outputs.get("pdf", True)),
            html=bool(outputs.get("html", True)),
            markdown=bool(outputs.get("markdown", True)),
            json=bool(outputs.get("json", True)),
        ),
    )


def render_default_config() -> str:
    return """name: Morning Paper
timezone: America/Los_Angeles
profile: |
  Add a short note about who this paper is for and what should matter most.
  Example: early-stage AI tools, operator software, media, and founder signal.

sources:
  hacker_news:
    enabled: true
    limit: 20
  rss:
    - name: Simon Willison
      url: https://simonwillison.net/atom/everything/
      limit: 5
    - name: Lenny's Newsletter
      url: https://www.lennysnewsletter.com/feed
      limit: 5

outputs:
  directory: ~/.local/share/morning-paper
  pdf: true
  html: true
  markdown: true
  json: true
"""
