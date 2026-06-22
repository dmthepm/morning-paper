"""Editorial checkers — the copy desk's last read of a FINISHED edition.

`morning-paper review <edition>` is the editorial twin of `doctor`: where
`doctor` answers "does it render", `review` answers "is it good enough to run".
It reads the artifacts `build`/`render` already wrote (the composed markdown,
and the edition `.json` when present) and emits editorial WARNINGS — never hard
fails. The severity ladder tops out at `flag`; exit code is 0 by default
(a future `--strict` is the only way a flag becomes a nonzero exit). A cron
edition must never break because a headline ran long.

This module is layout-primitives' complement: the layout spec PREVENTS
structurally (orphans/widows, head-glue, fail-soft keeps live in _base.css);
`review` CATCHES the residue CSS cannot fix — a head that still wraps because
the WORDS are long, a starved section, a stale dateline, a duplicate story.
The two never overlap.

Phase 0 + Phase 1 only (per docs/editorial-checkers-spec.md): the verb, the
report model, the registry runner, and the eight TEXT-only checks. The
geometry checks (a render pass) and the learned `--learn` loop are deferred.
`preferences/checks.yaml`, when present, is READ for threshold overrides and
mutes — it is never written here.

Determinism: pure function of artifacts + prefs → report. No network, no clock
beyond the edition date already in the artifact.
"""

from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from difflib import SequenceMatcher
from pathlib import Path

import yaml

# ---------------------------------------------------------------------------
# Severity ladder — three rungs, all advisory. There is intentionally no
# `fail`: that word belongs to doctor's print-readiness gate.
# ---------------------------------------------------------------------------
SEVERITIES = ("info", "nudge", "flag")
_SEVERITY_RANK = {name: i for i, name in enumerate(SEVERITIES)}


@dataclass(slots=True)
class Finding:
    """One editorial finding. Flat dict — location / issue / why."""

    check: str
    severity: str
    location: dict[str, object]
    issue: str
    why: str
    measured: dict[str, object] = field(default_factory=dict)
    threshold: dict[str, object] = field(default_factory=dict)
    hint: str = ""
    source: str = "builtin"

    def to_dict(self) -> dict[str, object]:
        out: dict[str, object] = {
            "check": self.check,
            "severity": self.severity,
            "location": self.location,
            "issue": self.issue,
            "why": self.why,
        }
        if self.measured:
            out["measured"] = self.measured
        if self.threshold:
            out["threshold"] = self.threshold
        if self.hint:
            out["hint"] = self.hint
        out["source"] = self.source
        return out


# ---------------------------------------------------------------------------
# The parsed edition: everything the TEXT checks read, derived once.
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class Headline:
    text: str
    kind: str  # "headline"
    section: str
    deck: str = ""
    # role tells a TRUE headline (the lead/front head + article heads) apart
    # from a DECK / DEPARTMENT / SECTION LABEL that is long by design. The two
    # length checks (line-count, length) flag only true headlines; decks and
    # labels are intentionally multi-sentence summaries and must not trip them.
    # See HEADLINE_ROLE_* below for the class → role mapping. Verb-presence and
    # hed-dek-redundancy still read every head regardless of role.
    role: str = "headline"  # "headline" | "deck"


@dataclass(slots=True)
class Section:
    name: str
    item_count: int
    word_count: int
    has_content: bool


@dataclass(slots=True)
class ParsedEdition:
    style: str
    palette: str
    headlines: list[Headline]
    sections: list[Section]
    items: list[dict[str, object]]  # structured items from the .json, if any
    edition_date: str | None
    markdown_present: bool


# ---------------------------------------------------------------------------
# Artifact resolution + parsing
# ---------------------------------------------------------------------------
# Headline ROLE vocabulary — the explicit, maintainable map from a head's CSS
# class to whether the LENGTH checks treat it as a real headline.
#
# TRUE HEADLINES (role "headline") — the lead/front head and per-article heads.
# These carry the news in a tight line and SHOULD flag when they run long:
#   .mg-title   broadsheet lead/front headline (demo.md: "The Lighthouse
#               Keeper Wants a Quieter Lamp" — a real, tight hed)
#   .article-title  a printed article's own headline (article_print.py)
#   .oc-title   field-card main title (its pack's headline)
#   plus markdown #/## headings, which double as the head in the simpler packs.
#
# DECKS / DEPARTMENT / SECTION LABELS (role "deck") — EXEMPT from the length
# checks. These are multi-sentence summaries or department names that are long
# BY DESIGN; flagging them is the 0.6.0 false positive that trained editors to
# ignore the gate (dogfood 2026-06-21). They are still parsed so verb-presence,
# hed-dek-redundancy, and duplicate-headline can read them — only the two
# LENGTH checks skip them:
#   .dept-title broadsheet DEPARTMENT title (15pt; the renderer emits it for
#               every read/dept/staged item — a deck, not a one-line hed)
#   .mg-dek     the deck (an explicit second-beat summary, always prose-length)
#   .dept-kicker / .mg-kicker  section labels / kickers
#
# A composed head wears one of these class names; plain markdown headings are
# heads too. The two regexes below split heads by role at parse time.
_TRUE_HEAD_CLASSES = ("mg-title", "article-title", "oc-title")
_DECK_HEAD_CLASSES = ("dept-title", "mg-dek")
_HEAD_DIV_RE = re.compile(
    r'<div[^>]*class="[^"]*\b(?:mg-title|article-title|oc-title)\b[^"]*"[^>]*>(.*?)</div>',
    re.IGNORECASE | re.DOTALL,
)
# Deck/department heads: parsed (so the non-length checks see them) but tagged
# role "deck" so the length checks skip them.
_DECK_HEAD_DIV_RE = re.compile(
    r'<div[^>]*class="[^"]*\b(?:dept-title)\b[^"]*"[^>]*>(.*?)</div>',
    re.IGNORECASE | re.DOTALL,
)
_DECK_DIV_RE = re.compile(
    r'<div[^>]*class="[^"]*\bmg-dek\b[^"]*"[^>]*>(.*?)</div>',
    re.IGNORECASE | re.DOTALL,
)
# Section labels: the kicker divs the renderer emits, plus h1.
_SECTION_DIV_RE = re.compile(
    r'<div[^>]*class="[^"]*\b(?:dept-kicker|mg-kicker)\b[^"]*"[^>]*>(.*?)</div>',
    re.IGNORECASE | re.DOTALL,
)
_ARTICLE_HEAD_RE = re.compile(
    r'<div[^>]*class="[^"]*\barticle-head\b[^"]*"[^>]*>(.*?)</div>\s*</div>',
    re.IGNORECASE | re.DOTALL,
)
_TAG_RE = re.compile(r"<[^>]+>")
_REFCODE_RE = re.compile(r'<span[^>]*class="[^"]*\bref-code\b[^"]*"[^>]*>.*?</span>', re.IGNORECASE | re.DOTALL)
_WORKSPACE_METADATA_STEMS = {
    "collector-report",
    "operator-answers",
    "queue-snapshot",
    "render-result",
    "review",
    "source-inventory",
}


def _strip_tags(value: str) -> str:
    """Plain text from an HTML fragment: drop ref-codes, tags, collapse space."""
    no_ref = _REFCODE_RE.sub(" ", value)
    text = _TAG_RE.sub(" ", no_ref)
    text = html.unescape(text)
    return " ".join(text.split())


def _split_frontmatter(document: str) -> tuple[dict[str, object], str]:
    # local copy of renderers._split_frontmatter (avoid importing the heavy
    # renderer module just for the YAML split)
    lines = document.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, document
    try:
        closing = lines[1:].index("---") + 1
    except ValueError:
        return {}, document
    meta = yaml.safe_load("\n".join(lines[1:closing])) or {}
    if not isinstance(meta, dict):
        meta = {}
    body = "\n".join(lines[closing + 1 :])
    return meta, body


def resolve_artifacts(path: Path) -> dict[str, Path]:
    """Find the .md and .json for an edition from a file or directory path.

    Accepts the composed markdown file directly, the edition JSON, or a
    directory holding either. Mirrors what build/render write.
    """
    found: dict[str, Path] = {}
    if path.is_dir():
        render_result = path / "render-result.json"
        if render_result.is_file():
            try:
                payload = json.loads(render_result.read_text(encoding="utf-8"))
            except Exception:
                payload = {}
            outputs = payload.get("outputs") if isinstance(payload, dict) else None
            if isinstance(outputs, dict):
                markdown = Path(str(outputs.get("markdown", ""))).expanduser()
                json_path = Path(str(outputs.get("json", ""))).expanduser()
                if markdown.is_file():
                    found["markdown"] = markdown
                if json_path.is_file():
                    found["json"] = json_path
                if found:
                    return found

        edition_dir = path / "edition"
        if edition_dir.is_dir():
            nested = resolve_artifacts(edition_dir)
            if nested:
                return nested

        mds = sorted(p for p in path.glob("*.md") if p.stem not in _WORKSPACE_METADATA_STEMS)
        jsons = sorted(p for p in path.glob("*.json") if p.stem not in _WORKSPACE_METADATA_STEMS)
        shared = sorted({p.stem for p in mds} & {p.stem for p in jsons})
        stem = "edition" if "edition" in shared else (shared[0] if shared else "")
        if stem:
            found["markdown"] = path / f"{stem}.md"
            found["json"] = path / f"{stem}.json"
        else:
            if mds:
                found["markdown"] = next((p for p in mds if p.stem == "edition"), mds[0])
            if jsons:
                found["json"] = next((p for p in jsons if p.stem == "edition"), jsons[0])
        return found
    if path.suffix == ".md":
        found["markdown"] = path
        sibling = path.with_suffix(".json")
        if sibling.is_file():
            found["json"] = sibling
    elif path.suffix == ".json":
        found["json"] = path
        sibling = path.with_suffix(".md")
        if sibling.is_file():
            found["markdown"] = sibling
    elif path.is_file():
        # unknown suffix but readable — treat as markdown
        found["markdown"] = path
    return found


def _section_word_counts(body: str, section_spans: list[tuple[str, int]]) -> list[Section]:
    """Count items/words between section markers in the composed body.

    A 'section' runs from one section marker to the next. Items are heads
    inside it (article heads + queue rows + table rows + list items); words are
    visible text tokens.
    """
    if not section_spans:
        return []
    sections: list[Section] = []
    for idx, (name, start) in enumerate(section_spans):
        end = section_spans[idx + 1][1] if idx + 1 < len(section_spans) else len(body)
        chunk = body[start:end]
        text = _strip_tags(chunk)
        words = len(text.split())
        # items: article heads, queue rows, table data rows, top-level list items
        item_count = (
            len(re.findall(r'class="[^"]*\b(?:article-head|q-row|bet|sig|card|read)\b', chunk))
            + len(re.findall(r"<tr\b", chunk, re.IGNORECASE))
            + len(re.findall(r"^\s*(?:[-*]|\d+\.)\s+\S", chunk, re.MULTILINE))
        )
        # content present? real words beyond a placeholder
        placeholder = bool(re.search(r"not-configured|No .*available|not configured", chunk, re.IGNORECASE))
        has_content = words > 3 and not (placeholder and words < 20)
        sections.append(
            Section(name=name, item_count=max(item_count, 0), word_count=words, has_content=has_content)
        )
    return sections


def parse_edition(artifacts: dict[str, Path]) -> ParsedEdition:
    style = palette = ""
    edition_date: str | None = None
    items: list[dict[str, object]] = []
    headlines: list[Headline] = []
    sections: list[Section] = []
    markdown_present = "markdown" in artifacts

    # JSON carries structured items + edition date + style/palette metadata
    if "json" in artifacts:
        try:
            payload = json.loads(artifacts["json"].read_text(encoding="utf-8"))
        except Exception:
            payload = {}
        if isinstance(payload, dict):
            edition_date = str(payload.get("date") or "") or None
            meta = payload.get("metadata")
            if isinstance(meta, dict):
                style = str(meta.get("style", "")) or style
                palette = str(meta.get("palette", "")) or palette
            raw_items = payload.get("items")
            if isinstance(raw_items, dict):
                for group in raw_items.values():
                    if isinstance(group, list):
                        items.extend(it for it in group if isinstance(it, dict))
            elif isinstance(raw_items, list):
                items.extend(it for it in raw_items if isinstance(it, dict))

    if markdown_present:
        document = artifacts["markdown"].read_text(encoding="utf-8")
        meta, body = _split_frontmatter(document)
        style = str(meta.get("style", "")) or style
        palette = str(meta.get("palette", "")) or palette

        # section markers, in document order
        section_spans: list[tuple[str, int]] = []
        for m in _SECTION_DIV_RE.finditer(body):
            section_spans.append((_strip_tags(m.group(1)), m.start()))
        # markdown ## / # headings are also sections
        for m in re.finditer(r"^(#{1,2})\s+(.+)$", body, re.MULTILINE):
            section_spans.append((m.group(2).strip(), m.start()))
        section_spans.sort(key=lambda t: t[1])

        # the section a position falls in (for headline location)
        def _section_at(pos: int) -> str:
            name = ""
            for sec_name, sec_pos in section_spans:
                if sec_pos <= pos:
                    name = sec_name
                else:
                    break
            return name

        # decks, keyed by position, so a head can pick up the deck right after it
        decks = [(m.start(), _strip_tags(m.group(1))) for m in _DECK_DIV_RE.finditer(body)]

        def _deck_near(pos: int, window: int = 400) -> str:
            for d_pos, d_text in decks:
                if pos <= d_pos <= pos + window:
                    return d_text
            return ""

        # TRUE headlines: lead/article head divs (.mg-title/.article-title/
        # .oc-title). These flag when they run long.
        for m in _HEAD_DIV_RE.finditer(body):
            text = _strip_tags(m.group(1))
            if text:
                headlines.append(
                    Headline(
                        text=text, kind="headline", section=_section_at(m.start()),
                        deck=_deck_near(m.start()), role="headline",
                    )
                )
        # DECK / DEPARTMENT heads: .dept-title — parsed so verb/redundancy/
        # duplicate checks still read them, but tagged role "deck" so the two
        # length checks skip them (they are long summaries by design).
        for m in _DECK_HEAD_DIV_RE.finditer(body):
            text = _strip_tags(m.group(1))
            if text:
                headlines.append(
                    Headline(
                        text=text, kind="headline", section=_section_at(m.start()),
                        deck=_deck_near(m.start()), role="deck",
                    )
                )
        # headlines: markdown ## / # headings double as both section and head
        # in the simpler packs (brief/zine). Treat them as true headlines.
        for m in re.finditer(r"^(#{1,2})\s+(.+)$", body, re.MULTILINE):
            text = m.group(2).strip()
            if text:
                headlines.append(
                    Headline(text=text, kind="headline", section=text, deck=_deck_near(m.start()), role="headline")
                )

        sections = _section_word_counts(body, section_spans)

    return ParsedEdition(
        style=style or "broadsheet",
        palette=palette or "color",
        headlines=headlines,
        sections=sections,
        items=items,
        edition_date=edition_date,
        markdown_present=markdown_present,
    )


# ---------------------------------------------------------------------------
# checks.yaml — READ ONLY (thresholds + mutes). No learn loop, no writes.
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class Preferences:
    thresholds: dict[str, dict[str, object]] = field(default_factory=dict)
    mutes: list[dict[str, object]] = field(default_factory=list)

    def threshold(self, check: str, key: str, default: object, *, pack: str | None = None) -> tuple[object, str]:
        """Resolve a threshold value and its provenance (default|pack|user)."""
        entry = self.thresholds.get(check)
        if not isinstance(entry, dict):
            return default, "default"
        # per-pack override wins when present. Two accepted shapes, both from
        # the spec: `per_pack: { zine: 3 }` (a scalar that overrides the key
        # being asked for) or `per_pack: { zine: { warn_at_lines: 3 } }`.
        per_pack = entry.get("per_pack")
        if pack and isinstance(per_pack, dict) and pack in per_pack:
            sub = per_pack[pack]
            if isinstance(sub, dict):
                if key in sub:
                    return sub[key], "user"
            elif key in entry:
                # scalar per-pack value overrides the key the entry already
                # tunes (the spec's single-threshold `per_pack: { zine: 3 }`)
                return sub, "user"
        if key in entry:
            return entry[key], "user"
        return default, "default"

    def is_muted(self, check: str, *, section: str = "") -> bool:
        for rule in self.mutes:
            if not isinstance(rule, dict) or rule.get("check") != check:
                continue
            scope = rule.get("scope")
            when = rule.get("when")
            if scope == "global" or when is None:
                return True
            if isinstance(when, dict):
                want = str(when.get("section", "")).strip().lower()
                if want and want == section.strip().lower():
                    return True
        return False


def load_preferences(start: Path | None) -> Preferences:
    """Read preferences/checks.yaml if present near the edition or cwd.

    Searches the edition's directory and its ancestors for a
    `preferences/checks.yaml` (the newsroom layout), then the cwd. Absent or
    malformed → empty preferences (review still runs).
    """
    candidates: list[Path] = []
    seen: set[Path] = set()

    def _add_tree(base: Path) -> None:
        for parent in [base, *base.parents]:
            cand = parent / "preferences" / "checks.yaml"
            if cand not in seen:
                seen.add(cand)
                candidates.append(cand)

    if start is not None:
        _add_tree(start if start.is_dir() else start.parent)
    _add_tree(Path.cwd())

    for cand in candidates:
        if cand.is_file():
            try:
                data = yaml.safe_load(cand.read_text(encoding="utf-8")) or {}
            except Exception:
                return Preferences()
            if not isinstance(data, dict):
                return Preferences()
            thresholds = data.get("thresholds")
            mutes = data.get("mute")
            return Preferences(
                thresholds=thresholds if isinstance(thresholds, dict) else {},
                mutes=[m for m in (mutes or []) if isinstance(m, dict)],
            )
    return Preferences()


# ---------------------------------------------------------------------------
# Headline measure: chars-per-line proxy from the pack's headline geometry.
# Width-aware, not raw chars (spec #1). Numbers are the pack's headline
# font-size + the usable column width; both are read once from the pack CSS
# semantics (kept as a small table — deterministic, no render).
# ---------------------------------------------------------------------------
# usable text width (inches) ≈ page width − margins; headline pt size per pack.
_PACK_MEASURE = {
    # pack: (usable_width_in, headline_pt)
    "broadsheet": (6.6, 23.0),   # 8.5in − ~0.9in margins; .mg-title 23pt
    "brief": (7.5, 11.0),        # 8.5 − 0.5*2; h1 11pt
    "field-card": (7.5, 16.0),   # .oc-title 16pt
    "zine": (4.6, 14.5),         # half-letter 5.5in − margins; h1 14.5pt
}


def _chars_per_line(pack: str) -> float:
    width_in, pt = _PACK_MEASURE.get(pack, _PACK_MEASURE["broadsheet"])
    # average glyph advance ≈ 0.5 × font-size for proportional display faces.
    # pt → inches: /72. cpl = column width / glyph advance.
    glyph_in = (pt * 0.5) / 72.0
    if glyph_in <= 0:
        return 60.0
    return width_in / glyph_in


def _estimate_lines(text: str, pack: str) -> int:
    cpl = _chars_per_line(pack)
    return max(1, -(-len(text) // max(1, int(round(cpl)))))  # ceil


# small finite-verb heuristic (POS-lite, stdlib only) for headline-verb-presence
_FINITE_VERBS = {
    "is", "are", "was", "were", "be", "been", "being", "am",
    "has", "have", "had", "do", "does", "did", "will", "would",
    "can", "could", "shall", "should", "may", "might", "must",
    "wants", "want", "needs", "need", "says", "say", "said",
    "makes", "make", "made", "takes", "take", "took", "gets", "get",
    "got", "goes", "go", "went", "comes", "come", "came", "sees", "see",
    "saw", "knows", "know", "knew", "finds", "find", "found", "gives",
    "give", "gave", "tells", "tell", "told", "calls", "call", "called",
    "keeps", "keep", "kept", "leaves", "leave", "left", "shows", "show",
    "showed", "breaks", "break", "broke", "builds", "build", "built",
    "wins", "win", "won", "loses", "lose", "lost", "buys", "buy",
    "bought", "sells", "sell", "sold", "runs", "run", "ran",
    "opens", "open", "closes", "close", "rises", "rise", "rose",
    "falls", "fall", "fell", "cuts", "cut", "adds", "add", "drops",
    "drop", "hits", "hit", "plans", "plan", "files", "file", "votes",
    "vote", "votes", "asks", "ask", "asked", "turns", "turn",
}
# common base-form verbs that carry no inflection (the -s/-ed/-ing fallback
# can't catch these, so name the frequent ones); kept small and stdlib-only
_BASE_VERBS = {
    "debate", "weigh", "back", "fund", "plan", "vote", "file", "seek",
    "urge", "push", "warn", "claim", "deny", "delay", "halt", "block",
    "boost", "name", "pick", "set", "let", "put", "cut", "hit", "win",
    "lose", "buy", "sell", "rise", "fall", "drop", "add", "ban", "face",
    "near", "eye", "spark", "fuel", "draw", "lead", "hold", "stand",
    "approve", "reject", "launch", "unveil", "reveal", "report", "say",
}
_VERB_SUFFIX_RE = re.compile(r"^[A-Za-z']+(?:s|es|ed|ing)$", re.IGNORECASE)
# obvious plural nouns / non-verbs that end in -s but aren't verbs in a head
_NON_VERB_S = {
    "news", "numbers", "notes", "reads", "signals", "series", "press",
    "business", "process", "across", "loss", "gas", "bus", "thanks",
    "yes", "this", "his", "its", "us", "plus", "minus", "status",
}
_WORD_RE = re.compile(r"[A-Za-z']+")
_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "of", "to", "in", "on", "for",
    "with", "at", "by", "from", "as", "is", "are", "was", "were", "be",
    "this", "that", "it", "its", "their", "his", "her", "they", "we",
}


def _has_finite_verb(headline: str) -> bool:
    """POS-lite: does the headline contain anything that reads as a verb?

    Conservative by design — it would rather miss a label head than flag a good
    one. A head counts as having a verb if any word is a known finite/base verb
    or carries a verb inflection (-s/-es/-ed/-ing), excluding obvious plural
    nouns. 'Delivery Truth' and 'The Q3 Numbers' have none and get flagged.
    """
    words = _WORD_RE.findall(headline)
    if not words:
        return False
    for w in words:
        lw = w.lower().strip("'")
        if lw in _STOPWORDS:
            continue
        if lw in _FINITE_VERBS or lw in _BASE_VERBS:
            return True
        if lw in _NON_VERB_S:
            continue
        if lw.endswith("ing") and len(lw) > 4:
            return True
        if lw.endswith("ed") and len(lw) > 3:
            return True
        if _VERB_SUFFIX_RE.match(lw) and (lw.endswith("s") or lw.endswith("es")):
            # an -s/-es word that isn't a known plural noun reads as a verb
            # ('approves', 'ships', 'wins') — the common headline pattern
            if len(lw) > 3:
                return True
    return False


def _content_words(text: str) -> set[str]:
    return {w.lower() for w in _WORD_RE.findall(text) if w.lower() not in _STOPWORDS and len(w) > 2}


def _normalize_title(title: str) -> str:
    return " ".join(_WORD_RE.findall(title.lower()))


def _trunc(text: str, length: int = 54) -> str:
    text = text.strip()
    return text if len(text) <= length else text[: length - 1].rstrip() + "…"


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    return ordered[mid] if n % 2 else (ordered[mid - 1] + ordered[mid]) / 2


# ---------------------------------------------------------------------------
# The eight TEXT-only checks. Each returns a list[Finding].
# Signature: (edition, prefs) -> list[Finding].
# ---------------------------------------------------------------------------
def check_headline_line_count(ed: ParsedEdition, prefs: Preferences) -> list[Finding]:
    warn_at, src = prefs.threshold("headline-line-count", "warn_at_lines", 3, pack=ed.style)
    strong_at, _ = prefs.threshold("headline-line-count", "strong_at_lines", 4, pack=ed.style)
    warn_at = int(warn_at)
    strong_at = int(strong_at)
    out: list[Finding] = []
    for h in ed.headlines:
        # only TRUE headlines wrap-flag; decks/department titles run long by
        # design (dogfood 2026-06-21 — the 0.6.0 false positive).
        if h.role != "headline":
            continue
        lines = _estimate_lines(h.text, ed.style)
        if lines < warn_at:
            continue
        severity = "flag" if lines >= strong_at else "flag"  # 3+ lines is a flag (the seed)
        out.append(
            Finding(
                check="headline-line-count",
                severity=severity,
                location={"section": h.section, "kind": "headline", "ref": _trunc(h.text)},
                issue=f"Headline estimated to wrap to {lines} lines at this measure.",
                why="Multi-line heads on the page read as body text and bury the lede; a desk aims for 1–2.",
                measured={"lines": lines, "chars": len(h.text)},
                threshold={"warn_at_lines": warn_at, "source": src},
                hint="Cut to a tighter line or promote to a wider column.",
            )
        )
    return out


def check_headline_length(ed: ParsedEdition, prefs: Preferences) -> list[Finding]:
    nudge_at, src = prefs.threshold("headline-length", "nudge_at", 60, pack=ed.style)
    nudge_at = int(nudge_at)
    out: list[Finding] = []
    for h in ed.headlines:
        # only TRUE headlines nudge on length; decks/department titles are
        # intentionally long summaries (dogfood 2026-06-21).
        if h.role != "headline":
            continue
        if len(h.text) <= nudge_at:
            continue
        out.append(
            Finding(
                check="headline-length",
                severity="nudge",
                location={"section": h.section, "kind": "headline", "ref": _trunc(h.text)},
                issue=f"Headline is {len(h.text)} characters (over ~{nudge_at}).",
                why="Long heads read flabby even when they fit; print convention is roughly 55–65 characters.",
                measured={"chars": len(h.text)},
                threshold={"nudge_at": nudge_at, "source": src},
                hint="Trim modifiers; lead with the verb and the news.",
            )
        )
    return out


def check_headline_verb_presence(ed: ParsedEdition, prefs: Preferences) -> list[Finding]:
    out: list[Finding] = []
    for h in ed.headlines:
        # skip very short section-style labels (1–2 words) — those are kickers,
        # not news heads, and a verb check on them is noise
        if len(h.text.split()) < 3:
            continue
        if _has_finite_verb(h.text):
            continue
        out.append(
            Finding(
                check="headline-verb-presence",
                severity="flag",
                location={"section": h.section, "kind": "headline", "ref": _trunc(h.text)},
                issue="Headline has no finite verb (reads as a label, not news).",
                why="A verb is what makes a headline report something; label heads ('The Q3 Numbers') stall the reader.",
                measured={"words": len(h.text.split())},
                threshold={"source": "default"},
                hint="Make a claim with a verb: who did what.",
            )
        )
    return out


def check_hed_dek_redundancy(ed: ParsedEdition, prefs: Preferences) -> list[Finding]:
    overlap_at, src = prefs.threshold("hed-dek-redundancy", "overlap_ratio", 0.5, pack=ed.style)
    overlap_at = float(overlap_at)
    out: list[Finding] = []
    for h in ed.headlines:
        if not h.deck:
            continue
        hed_words = _content_words(h.text)
        dek_words = _content_words(h.deck)
        if not dek_words:
            continue
        overlap = len(hed_words & dek_words) / len(dek_words)
        if overlap < overlap_at:
            continue
        out.append(
            Finding(
                check="hed-dek-redundancy",
                severity="nudge",
                location={"section": h.section, "kind": "headline", "ref": _trunc(h.text)},
                issue=f"Deck repeats {overlap:.0%} of the headline's words instead of advancing it.",
                why="The deck should add a second beat of information, not echo the head.",
                measured={"overlap_ratio": round(overlap, 2)},
                threshold={"overlap_ratio": overlap_at, "source": src},
                hint="Make the deck say something the headline did not.",
            )
        )
    return out


def check_section_balance(ed: ParsedEdition, prefs: Preferences) -> list[Finding]:
    multiple, src = prefs.threshold("section-balance", "max_ratio", 2.5, pack=ed.style)
    lonely_median, _ = prefs.threshold("section-balance", "lonely_when_median", 4, pack=ed.style)
    multiple = float(multiple)
    lonely_median = int(lonely_median)
    real = [s for s in ed.sections if s.has_content]
    if len(real) < 3:
        return []
    # measure on item count when sections carry countable items; otherwise fall
    # back to word count (plain-prose sections have no item markers but real
    # mass). The spec measures "item/word count" — pick the signal with spread.
    item_median = _median([s.item_count for s in real])
    use_words = item_median <= 0
    measure = (lambda s: s.word_count) if use_words else (lambda s: s.item_count)
    unit = "words" if use_words else "items"
    median = _median([measure(s) for s in real])
    if median <= 0:
        return []
    out: list[Finding] = []
    for s in real:
        value = measure(s)
        if value > median * multiple:
            out.append(
                Finding(
                    check="section-balance",
                    severity="nudge",
                    location={"section": s.name, "kind": "section", "ref": s.name},
                    issue=f"Section carries {value} {unit} — over {multiple:g}× the median of {median:g}.",
                    why="A section that dwarfs its siblings makes the rest of the paper feel thin.",
                    measured={unit: value, "median": median},
                    threshold={"max_ratio": multiple, "source": src},
                    hint="Move the weakest material to another day or section.",
                )
            )
        elif not use_words and s.item_count <= 1 and median >= lonely_median:
            out.append(
                Finding(
                    check="section-balance",
                    severity="nudge",
                    location={"section": s.name, "kind": "section", "ref": s.name},
                    issue=f"One item carries the whole section (median is {median:g}).",
                    why="A lonely section reads as an afterthought next to a fat one.",
                    measured={"items": s.item_count, "median": median},
                    threshold={"lonely_when_median": lonely_median, "source": src},
                    hint="Fill it out or fold it into a neighbor.",
                )
            )
    return out


def check_empty_or_sparse_section(ed: ParsedEdition, prefs: Preferences) -> list[Finding]:
    out: list[Finding] = []
    for s in ed.sections:
        if s.has_content:
            continue
        out.append(
            Finding(
                check="empty-or-sparse-section",
                severity="nudge",
                location={"section": s.name, "kind": "section", "ref": s.name},
                issue="Section heading sits over no real content.",
                why="A heading above 'not configured' or empty space is dead air on the page.",
                measured={"words": s.word_count},
                threshold={"source": "default"},
                hint="Drop the heading or give it material.",
            )
        )
    return out


def check_duplicate_headline(ed: ParsedEdition, prefs: Preferences) -> list[Finding]:
    near, src = prefs.threshold("duplicate-headline", "ratio", 0.9, pack=ed.style)
    near = float(near)
    out: list[Finding] = []
    # collect candidate (title, url) from both the markdown heads and JSON items
    titles: list[tuple[str, str, str]] = []  # (norm_title, raw_title, url)
    for h in ed.headlines:
        titles.append((_normalize_title(h.text), h.text, ""))
    seen_urls: dict[str, str] = {}
    for it in ed.items:
        title = str(it.get("title", ""))
        url = str(it.get("url", ""))
        titles.append((_normalize_title(title), title, url))
        if url:
            if url in seen_urls:
                out.append(
                    Finding(
                        check="duplicate-headline",
                        severity="nudge",
                        location={"section": "", "kind": "headline", "ref": _trunc(title or url)},
                        issue="Same story appears twice (identical URL).",
                        why="A story surfacing twice (e.g. HN and RSS) is the classic aggregator embarrassment.",
                        measured={"url": url},
                        threshold={"source": "default"},
                        hint="Keep the stronger placement; cut the duplicate.",
                    )
                )
            seen_urls[url] = title
    # near-duplicate titles
    reported: set[tuple[int, int]] = set()
    for i in range(len(titles)):
        for j in range(i + 1, len(titles)):
            a, j_raw = titles[i][0], titles[j][1]
            b = titles[j][0]
            if not a or not b:
                continue
            if a == b or SequenceMatcher(None, a, b).ratio() >= near:
                key = (i, j)
                if key in reported:
                    continue
                reported.add(key)
                out.append(
                    Finding(
                        check="duplicate-headline",
                        severity="nudge",
                        location={"section": "", "kind": "headline", "ref": _trunc(titles[i][1])},
                        issue="Two headlines are the same or near-identical.",
                        why="Repeating a story reads as an editing miss; one strong placement beats two weak ones.",
                        measured={"ratio": round(SequenceMatcher(None, a, b).ratio(), 2), "other": _trunc(j_raw)},
                        threshold={"ratio": near, "source": src},
                        hint="Cut the duplicate; keep the stronger headline.",
                    )
                )
    return out


def check_stale_dateline(ed: ParsedEdition, prefs: Preferences) -> list[Finding]:
    max_age, src = prefs.threshold("stale-dateline", "lead_max_age_days", 3, pack=ed.style)
    max_age = int(max_age)
    if not ed.items or not ed.edition_date:
        return []
    try:
        edition_day = date.fromisoformat(ed.edition_date[:10])
    except ValueError:
        return []
    # the lead item = highest score (matches the banner selection)
    def _score(it: dict[str, object]) -> float:
        try:
            return float(it.get("score", 0) or 0)
        except (TypeError, ValueError):
            return 0.0

    lead = max(ed.items, key=_score)
    published = str(lead.get("published_at", "") or "")
    if not published:
        return []
    try:
        pub_day = datetime.fromisoformat(published.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            pub_day = date.fromisoformat(published[:10])
        except ValueError:
            return []
    age = (edition_day - pub_day).days
    if age <= max_age:
        return []
    return [
        Finding(
            check="stale-dateline",
            severity="info",
            location={"section": "", "kind": "edition", "ref": _trunc(str(lead.get("title", "lead item")))},
            issue=f"Lead item is {age} days old for a {ed.edition_date} edition.",
            why="A 'morning' paper running week-old news as its lead undercuts the daily promise.",
            measured={"age_days": age, "published_at": published[:10]},
            threshold={"lead_max_age_days": max_age, "source": src},
            hint="Lead with something fresher, or note the age on the page.",
        )
    ]


# ---------------------------------------------------------------------------
# The registry (§4.3). Adding a builtin = adding one entry; the runner never
# changes. tier is 'text' for all Phase-1 checks.
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class Check:
    id: str
    tier: str
    fn: object  # Callable[[ParsedEdition, Preferences], list[Finding]]


REGISTRY: list[Check] = [
    Check("headline-line-count", "text", check_headline_line_count),
    Check("headline-length", "text", check_headline_length),
    Check("headline-verb-presence", "text", check_headline_verb_presence),
    Check("hed-dek-redundancy", "text", check_hed_dek_redundancy),
    Check("section-balance", "text", check_section_balance),
    Check("empty-or-sparse-section", "text", check_empty_or_sparse_section),
    Check("duplicate-headline", "text", check_duplicate_headline),
    Check("stale-dateline", "text", check_stale_dateline),
]


def run_review(path: Path, *, prefs: Preferences | None = None) -> dict[str, object]:
    """Run every registered check and assemble the report envelope (§2.3)."""
    artifacts = resolve_artifacts(path)
    if prefs is None:
        prefs = load_preferences(path)
    ed = parse_edition(artifacts)

    checks_run: list[str] = []
    checks_skipped: list[dict[str, object]] = []
    findings: list[Finding] = []

    for check in REGISTRY:
        # text checks need the markdown (or, for dup/stale, the JSON items)
        needs_markdown = check.id not in {"duplicate-headline", "stale-dateline"}
        if needs_markdown and not ed.markdown_present:
            checks_skipped.append({"check": check.id, "reason": "no markdown artifact; text checks unavailable"})
            continue
        if check.id == "stale-dateline" and (not ed.items or not ed.edition_date):
            checks_skipped.append(
                {"check": check.id, "reason": "no edition JSON with dated items; dateline unavailable"}
            )
            continue
        checks_run.append(check.id)
        for finding in check.fn(ed, prefs):  # type: ignore[operator]
            section = str(finding.location.get("section", ""))
            if prefs.is_muted(check.id, section=section):
                continue
            findings.append(finding)

    summary = {sev: sum(1 for f in findings if f.severity == sev) for sev in SEVERITIES}
    summary["sections_reviewed"] = len([s for s in ed.sections if s.has_content])

    if summary["flag"]:
        status = "review"
    elif summary["nudge"] or summary["info"]:
        status = "notes"
    else:
        status = "clean"

    edition_info: dict[str, object] = {
        "date": ed.edition_date,
        "style": ed.style,
        "palette": ed.palette,
        "artifacts": {k: str(v) for k, v in artifacts.items()},
    }

    # findings sorted: flags first, then nudge, then info — stable within rung
    findings.sort(key=lambda f: _SEVERITY_RANK.get(f.severity, 99), reverse=True)

    return {
        "edition": edition_info,
        "checks_run": checks_run,
        "checks_skipped": checks_skipped,
        "findings": [f.to_dict() for f in findings],
        "summary": summary,
        "status": status,
    }


# ---------------------------------------------------------------------------
# Human renderer (§2.4) — desk-sheet voice, flags first, quiet when clean.
# ---------------------------------------------------------------------------
def render_human(report: dict[str, object], *, verbose: bool = False) -> str:
    ed = report["edition"]
    summary = report["summary"]  # type: ignore[assignment]
    status = report["status"]
    date_str = ed.get("date") or "—"
    head = f"review: {date_str} · {ed.get('style')}/{ed.get('palette')}"

    findings = report["findings"]  # type: ignore[assignment]
    if status == "clean":
        return f"{head}\nreview: clean — nothing to flag.   status: clean"

    lines = [head, ""]
    by_sev = {sev: [f for f in findings if f["severity"] == sev] for sev in SEVERITIES}

    label = {"flag": "FLAG", "nudge": "NUDGE", "info": "INFO"}
    shown_info_nudge = verbose
    for sev in ("flag", "nudge", "info"):
        group = by_sev[sev]
        if not group:
            continue
        if sev in ("info", "nudge") and not shown_info_nudge and sev != "flag":
            # default view shows flags fully; nudges/info collapse to a count
            # unless --verbose. But the spec shows nudges in the example, so we
            # surface nudges by default and hide only info.
            if sev == "info":
                continue
        lines.append(f"{label[sev]} ({len(group)})")
        for f in group:
            loc = f["location"]
            section = loc.get("section") or loc.get("ref") or ""
            kind = loc.get("kind", "")
            ref = loc.get("ref", "")
            head_line = f"  {section} › {kind}".rstrip(" ›")
            lines.append(head_line)
            if ref and ref != section:
                lines.append(f'  "{ref}"')
            lines.append(f"  {f['issue']}")
            lines.append(f"  → {f['why']}")
            if f.get("hint"):
                lines.append(f"    fix: {f['hint']}")
            lines.append("")

    info_count = summary.get("info", 0)
    if info_count and not verbose:
        lines.append(f"{info_count} info hidden (--verbose to show).   status: {status}")
    else:
        lines.append(f"status: {status}")
    return "\n".join(lines).rstrip() + "\n"


def explain(report: dict[str, object], check_id: str) -> str:
    """`--explain CHECK`: the threshold math + provenance for matching findings."""
    lines = [f"explain: {check_id}"]
    matched = [f for f in report["findings"] if f["check"] == check_id]  # type: ignore[index]
    if not matched:
        if check_id not in {c.id for c in REGISTRY}:
            return f"explain: unknown check '{check_id}'\n"
        return f"explain: {check_id} — no findings on this edition.\n"
    for f in matched:
        measured = f.get("measured", {})
        threshold = f.get("threshold", {})
        src = threshold.get("source", "default")
        lines.append(f"  {f['location'].get('ref', '')}")
        lines.append(f"    measured: {measured}")
        lines.append(f"    threshold: {threshold} (source: {src})")
    return "\n".join(lines) + "\n"
