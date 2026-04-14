from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml


DEFAULT_CONFIG_DIR = Path.home() / ".config" / "morning-paper"
DEFAULT_CONFIG_PATH = DEFAULT_CONFIG_DIR / "config.yaml"
DEFAULT_OUTPUT_DIR = Path.home() / ".local" / "share" / "morning-paper"


class ConfigError(ValueError):
    pass


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
    renderer: str = "typewriter"
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


def _validate_timezone(value: str) -> str:
    try:
        ZoneInfo(value)
    except Exception as exc:
        raise ConfigError(f"invalid timezone: {value}") from exc
    return value


def _validate_limit(value: int, *, label: str) -> int:
    if not 1 <= value <= 100:
        raise ConfigError(f"{label} must be between 1 and 100")
    return value


def _validate_output_directory(path: Path) -> Path:
    try:
        path.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        raise ConfigError(f"cannot create output directory: {path}") from exc
    if not path.is_dir():
        raise ConfigError(f"output directory is not a directory: {path}")
    if not os.access(path, os.W_OK):
        raise ConfigError(f"output directory is not writable: {path}")
    return path


def _validate_renderer(value: str) -> str:
    if value not in {"typewriter", "portable"}:
        raise ConfigError("outputs.renderer must be one of: typewriter, portable")
    return value


def load_config(path: Path) -> MorningPaperConfig:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    sources = data.get("sources") or {}
    outputs = data.get("outputs") or {}
    hn = sources.get("hacker_news") or {}
    rss_feeds = [
        RssFeedConfig(
            name=str(feed["name"]),
            url=str(feed["url"]),
            limit=_validate_limit(int(feed.get("limit", 5)), label=f"rss limit for {feed['name']}"),
        )
        for feed in (sources.get("rss") or [])
        if feed.get("name") and feed.get("url")
    ]
    return MorningPaperConfig(
        name=str(data.get("name", "Morning Paper")),
        timezone=_validate_timezone(str(data.get("timezone", "America/Los_Angeles"))),
        profile=str(data.get("profile", "")).strip(),
        sources=SourcesConfig(
            hacker_news=HackerNewsConfig(
                enabled=bool(hn.get("enabled", True)),
                limit=_validate_limit(int(hn.get("limit", 20)), label="hacker_news.limit"),
            ),
            rss=rss_feeds,
        ),
        outputs=OutputsConfig(
            directory=_validate_output_directory(
                _expand_path(outputs.get("directory"), default=DEFAULT_OUTPUT_DIR)
            ),
            renderer=_validate_renderer(str(outputs.get("renderer", "typewriter"))),
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
  renderer: typewriter
  pdf: true
  html: true
  markdown: true
  json: true
"""
