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
class ContributorConfig:
    email: str
    name: str = ""


@dataclass(slots=True)
class InboxConfig:
    """The contributor inbox — "the masthead".

    People the reader trusts email articles; they land in tomorrow's staging
    queue. The contributors list is an allowlist and the only gate: mail from
    anyone else is never staged. The IMAP password is NEVER stored in config —
    it is read from the MORNING_PAPER_IMAP_PASSWORD environment variable
    (MORNING_PAPER_SMTP_PASSWORD when the reply credential is distinct).
    """

    enabled: bool = False
    imap_host: str = ""
    imap_user: str = ""
    mailbox: str = "INBOX"
    # only mail whose subject contains this tag is staged; "" disables the filter
    subject_tag: str = "paper"
    contributors: list[ContributorConfig] = field(default_factory=list)
    reply: bool = True
    # for confirmations; default derived from the imap values when omitted
    smtp_host: str = ""
    smtp_user: str = ""


@dataclass(slots=True)
class OutputsConfig:
    directory: Path = DEFAULT_OUTPUT_DIR
    renderer: str = "typewriter"
    # broadsheet/color is the product's visual identity — the same look the demo sells
    style: str = "broadsheet"
    palette: str = "color"
    # multiplies each style's base body size; 1.0 is the designed scale
    font_scale: float = 1.0
    pdf: bool = True
    html: bool = True
    markdown: bool = True
    json: bool = True


@dataclass(slots=True)
class MorningPaperConfig:
    name: str = "Morning Paper"
    timezone: str = "America/Los_Angeles"
    profile: str = ""
    article_extractor: str = "local"
    page_budget: int = 20
    sources: SourcesConfig = field(default_factory=SourcesConfig)
    outputs: OutputsConfig = field(default_factory=OutputsConfig)
    inbox: InboxConfig = field(default_factory=InboxConfig)


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


def _validate_style(value: str) -> str:
    from .styles import STYLES, resolve_style_name

    # deprecated 0.4.x names (editorial, flow, ops-card, magazine, typewriter)
    # are accepted for one release and stored as their canonical successors;
    # resolve_style_name prints the deprecation warning
    resolved = resolve_style_name(value)
    if resolved not in STYLES:
        raise ConfigError(f"outputs.style must be one of: {', '.join(sorted(STYLES))}")
    return resolved


def _validate_palette(value: str) -> str:
    from .styles import PALETTES

    if value not in PALETTES:
        raise ConfigError(f"outputs.palette must be one of: {', '.join(sorted(PALETTES))}")
    return value


def _validate_font_scale(value: float) -> float:
    from .styles import FONT_SCALE_MAX, FONT_SCALE_MIN

    if not FONT_SCALE_MIN <= value <= FONT_SCALE_MAX:
        raise ConfigError(
            f"outputs.font_scale must be between {FONT_SCALE_MIN} and {FONT_SCALE_MAX} (got {value})"
        )
    return value


def _validate_article_extractor(value: str) -> str:
    if value not in {"local", "jina"}:
        raise ConfigError("article_extractor must be one of: local, jina")
    return value


def _parse_inbox(data: dict) -> InboxConfig:
    # Security rule: credentials never live in config. Catch any attempt early
    # with the fix in the error, instead of silently ignoring a secret on disk.
    for key in data:
        if "password" in str(key).lower():
            raise ConfigError(
                f"inbox.{key}: passwords never go in config — "
                "set the MORNING_PAPER_IMAP_PASSWORD environment variable instead (see docs/inbox.md)"
            )
    contributors = []
    for raw in data.get("contributors") or []:
        if not isinstance(raw, dict) or not raw.get("email"):
            raise ConfigError("inbox.contributors entries must be {email, name} mappings")
        contributors.append(
            ContributorConfig(email=str(raw["email"]).strip(), name=str(raw.get("name", "")).strip())
        )
    raw_tag = data.get("subject_tag", "paper")
    inbox = InboxConfig(
        enabled=bool(data.get("enabled", False)),
        imap_host=str(data.get("imap_host", "")).strip(),
        imap_user=str(data.get("imap_user", "")).strip(),
        mailbox=str(data.get("mailbox", "INBOX")).strip() or "INBOX",
        subject_tag=str(raw_tag).strip() if raw_tag is not None else "",
        contributors=contributors,
        reply=bool(data.get("reply", True)),
        smtp_host=str(data.get("smtp_host", "")).strip(),
        smtp_user=str(data.get("smtp_user", "")).strip(),
    )
    if inbox.enabled:
        if not inbox.imap_host:
            raise ConfigError("inbox.imap_host is required when inbox.enabled is true")
        if not inbox.imap_user:
            raise ConfigError("inbox.imap_user is required when inbox.enabled is true")
        if not inbox.contributors:
            raise ConfigError(
                "inbox.contributors must list at least one {email, name} when inbox.enabled is true — "
                "the masthead is the allowlist; without it nothing may stage"
            )
    return inbox


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
    page_budget = int(data.get("page_budget", 20))
    if not 1 <= page_budget <= 200:
        raise ConfigError("page_budget must be between 1 and 200")
    return MorningPaperConfig(
        name=str(data.get("name", "Morning Paper")),
        timezone=_validate_timezone(str(data.get("timezone", "America/Los_Angeles"))),
        profile=str(data.get("profile", "")).strip(),
        article_extractor=_validate_article_extractor(str(data.get("article_extractor", "local"))),
        page_budget=page_budget,
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
            style=_validate_style(str(outputs.get("style", "broadsheet"))),
            palette=_validate_palette(str(outputs.get("palette", "color"))),
            font_scale=_validate_font_scale(float(outputs.get("font_scale", 1.0))),
            pdf=bool(outputs.get("pdf", True)),
            html=bool(outputs.get("html", True)),
            markdown=bool(outputs.get("markdown", True)),
            json=bool(outputs.get("json", True)),
        ),
        inbox=_parse_inbox(data.get("inbox") or {}),
    )


FALLBACK_TIMEZONE = "America/Los_Angeles"


def detect_system_timezone() -> str:
    """Best-effort IANA timezone name for this machine, without new dependencies.

    Resolves the /etc/localtime symlink (macOS and most Linux distros point it
    into a zoneinfo tree) and validates the result. Falls back to a fixed
    default rather than guessing.
    """
    try:
        parts = Path("/etc/localtime").resolve().parts
        if "zoneinfo" in parts:
            index = len(parts) - 1 - parts[::-1].index("zoneinfo")
            name = "/".join(parts[index + 1 :])
            if name:
                ZoneInfo(name)
                return name
    except Exception:
        pass
    return FALLBACK_TIMEZONE


def render_default_config() -> str:
    return f"""name: Morning Paper
# detected from this machine; change it if your mornings happen elsewhere
timezone: {detect_system_timezone()}
profile: |
  Add a short note about who this paper is for and what should matter most.
  Replace this with your own beat: the topics, projects, and people you follow.
# article extraction for `print`/`stage`: `local` fetches and parses on this
# machine (trafilatura) — URLs never leave your computer. `jina` sends each URL
# to the third-party r.jina.ai reader service; it remains available and is used
# automatically (with an honest note) when local extraction comes up short.
article_extractor: local
# target length for a full edition; `morning-paper queue` reports against this
page_budget: 20

sources:
  hacker_news:
    enabled: true
    limit: 20
  # sample feeds — replace with yours. Full-text feeds (those that ship the
  # whole article in `content:encoded`) print as real reads; the build JSON
  # carries the full article in each item's `body` field, with `summary` kept
  # as the short blurb. Summary-only feeds stay summary-only.
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
  # style: broadsheet | brief | field-card | zine    palette: mono | color
  # broadsheet/color is what the demo prints — the default recommendation
  style: broadsheet
  palette: color
  # body type scale for the whole paper: 0.8 (compact) to 1.5 (large print)
  font_scale: 1.0
  pdf: true
  html: true
  markdown: true
  json: true

# the contributor inbox ("the masthead"): people you trust email you articles
# and they land in tomorrow's staging queue. `contributors` is an allowlist —
# mail from anyone else is never staged. Your mail password NEVER goes in this
# file: set the MORNING_PAPER_IMAP_PASSWORD environment variable to an app
# password (Gmail/iCloud walkthrough: docs/inbox.md).
inbox:
  enabled: false
  imap_host: imap.example.com
  imap_user: you@example.com
  mailbox: INBOX
  # only mail whose subject contains this word is staged; set "" to take all
  subject_tag: paper
  # the masthead — who is allowed to feed your paper
  contributors:
    - email: someone-you-trust@example.com
      name: Sam
  # send a warm confirmation back from your own address when something stages
  reply: true
  # smtp_host/smtp_user default to the imap values (imap.* host becomes smtp.*)
"""
