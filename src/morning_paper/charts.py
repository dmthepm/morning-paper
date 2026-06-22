"""Inline SVG chart primitives for print.

WeasyPrint ignores CSS applied to inline-SVG content, so every presentation
property here is an SVG attribute. Colors come in as parameters (the style
layer maps palette -> ink/track); nothing depends on the host stylesheet.

Agents compose charts as fenced markdown directives; ``expand_chart_directives``
rewrites them to SVG before markdown rendering:

    ```mp-bars
    title: Yesterday's funnel
    Link clicks | 10 | 10 | 10 - CPC $3.09
    Landing views | 9 | 10 | LPV 90%
    Pixel leads | 0 | 10 | 0 - the unproven link
    ```

    ```mp-spark
    title: Leads, last 14 days
    3 5 2 8 9 4 6 7 2 1 5 9 12 11
    ```

    ```mp-stats
    Contacts (D1) | 14 | +2 / 24h
    Paid 7d | $300 | 3 lifetime
    ```

Degrade honestly: malformed lines render an em-dash placeholder block, never
invented data.
"""

from __future__ import annotations

import html
import math
import re


_FONT = "Courier New, Courier, monospace"
DEFAULT_INK = "#222222"
DEFAULT_TRACK = "#dddddd"
DEFAULT_TEXT = "#111111"
MAX_BAR_ROWS = 12
MAX_STAT_BLOCKS = 6
MAX_SPARK_VALUES = 90
MAX_LABEL_CHARS = 34
MAX_NOTE_CHARS = 42
MAX_TITLE_CHARS = 90


def _esc(value: str) -> str:
    return html.escape(value, quote=True)


def _clip_text(value: str, limit: int) -> str:
    value = " ".join(value.split())
    if len(value) <= limit:
        return value
    return value[: max(1, limit - 3)].rstrip() + "..."


def bar_row_chart(
    rows: list[tuple[str, float, float, str]],
    *,
    title: str = "",
    ink: str = DEFAULT_INK,
    track: str = DEFAULT_TRACK,
    text: str = DEFAULT_TEXT,
    width: int = 700,
    bar_width: int | None = None,
) -> str:
    """Horizontal labelled bars: (label, value, max, annotation) per row."""
    hidden = max(0, len(rows) - MAX_BAR_ROWS)
    rows = rows[:MAX_BAR_ROWS]
    row_h, gap = 17, 6
    bar_h = 7
    track_w = bar_width or width
    note_h = 10 if hidden else 0
    height = max(len(rows) * (row_h + gap) + 2 + note_h, row_h + 8)
    parts = [
        f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" font-family="{_FONT}">'
    ]
    y = 2
    for label, value, max_value, note in rows:
        label = _clip_text(label, MAX_LABEL_CHARS)
        note = _clip_text(note, MAX_NOTE_CHARS)
        label_y = y + 7
        bar_y = y + 10
        safe_max = max_value if max_value > 0 else 1.0
        fill_w = max(0.0, min(1.0, value / safe_max)) * track_w
        parts.append(
            f'<text x="0" y="{label_y}" font-size="8.5" fill="{text}">{_esc(label)}</text>'
        )
        if note:
            parts.append(
                f'<text x="{width}" y="{label_y}" text-anchor="end" font-size="8.5" font-weight="bold" fill="{text}">{_esc(note)}</text>'
            )
        parts.append(f'<rect x="0" y="{bar_y}" width="{track_w}" height="{bar_h}" fill="{track}"/>')
        if fill_w >= 0.5:
            parts.append(f'<rect x="0" y="{bar_y}" width="{fill_w:.1f}" height="{bar_h}" fill="{ink}"/>')
        y += row_h + gap
    if hidden:
        parts.append(
            f'<text x="0" y="{y + 5}" font-size="8" fill="{text}">+{hidden} row(s) not shown; split the chart or summarize.</text>'
        )
    parts.append("</svg>")
    svg = "".join(parts)
    return _wrap_chart(svg, title, "bars")


def sparkline(
    values: list[float],
    *,
    title: str = "",
    ink: str = DEFAULT_INK,
    track: str = DEFAULT_TRACK,
    text: str = DEFAULT_TEXT,
    width: int = 700,
    height: int = 60,
) -> str:
    """A single line with first/last value labels and a dot on the last point."""
    clean = [v for v in values if isinstance(v, (int, float)) and math.isfinite(v)]
    if len(clean) < 2:
        return _placeholder(title or "sparkline", "needs at least 2 finite values")
    if len(clean) > MAX_SPARK_VALUES:
        clean = clean[-MAX_SPARK_VALUES:]
    lo, hi = min(clean), max(clean)
    spread = (hi - lo) or 1.0
    pad_left, pad_right, pad_y = 28, 34, 8
    plot_w, plot_h = width - pad_left - pad_right, height - 2 * pad_y
    step = plot_w / (len(clean) - 1)
    points = [
        (pad_left + i * step, pad_y + plot_h - ((v - lo) / spread) * plot_h)
        for i, v in enumerate(clean)
    ]
    path = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    last_x, last_y = points[-1]
    parts = [
        f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" font-family="{_FONT}">',
        f'<line x1="{pad_left}" y1="{pad_y + plot_h}" x2="{pad_left + plot_w}" y2="{pad_y + plot_h}" stroke="{track}" stroke-width="1"/>',
        f'<polyline points="{path}" fill="none" stroke="{ink}" stroke-width="1.6"/>',
        f'<circle cx="{last_x:.1f}" cy="{last_y:.1f}" r="2.4" fill="{ink}"/>',
        f'<text x="{pad_left - 6}" y="{points[0][1] + 3:.1f}" text-anchor="end" font-size="9" fill="{text}">{_fmt_num(clean[0])}</text>',
        f'<text x="{last_x + 8:.1f}" y="{last_y + 3:.1f}" font-size="9" font-weight="bold" fill="{text}">{_fmt_num(clean[-1])}</text>',
        "</svg>",
    ]
    return _wrap_chart("".join(parts), title, "spark")


def stat_row(stats: list[tuple[str, str, str]]) -> str:
    """Big-number blocks: (label, value, delta) each. Pure HTML; styled by the pack."""
    hidden = max(0, len(stats) - MAX_STAT_BLOCKS)
    stats = stats[:MAX_STAT_BLOCKS]
    blocks = [
        '<div class="mp-stat">'
        f'<div class="mp-stat-value">{_esc(_clip_text(value, MAX_LABEL_CHARS))}</div>'
        f'<div class="mp-stat-delta">{_esc(_clip_text(delta, MAX_NOTE_CHARS))}</div>'
        f'<div class="mp-stat-label">{_esc(_clip_text(label, MAX_LABEL_CHARS))}</div>'
        "</div>"
        for label, value, delta in stats
    ]
    if hidden:
        blocks.append(
            '<div class="mp-stat mp-stat-note">'
            f'<div class="mp-stat-value">+{hidden}</div>'
            '<div class="mp-stat-delta">not shown</div>'
            '<div class="mp-stat-label">split or summarize</div>'
            "</div>"
        )
    return '<div class="mp-stats">' + "".join(blocks) + "</div>"


def _fmt_num(value: float) -> str:
    return f"{value:g}"


def _wrap_chart(svg: str, title: str, kind: str) -> str:
    title_html = f'<div class="mp-chart-title">{_esc(_clip_text(title, MAX_TITLE_CHARS))}</div>' if title else ""
    return f'<div class="mp-chart mp-chart-{kind}">{title_html}{svg}</div>'


def _placeholder(name: str, reason: str) -> str:
    return (
        '<div class="mp-chart"><div class="mp-chart-title">'
        f"{_esc(name)} — not rendered ({_esc(reason)})</div></div>"
    )


_DIRECTIVE_RE = re.compile(r"```mp-(bars|spark|stats)\n(.*?)```", re.DOTALL)


def _parse_title(body: str) -> tuple[str, list[str]]:
    lines = [line.strip() for line in body.strip().splitlines() if line.strip()]
    title = ""
    if lines and lines[0].lower().startswith("title:"):
        title = lines[0].split(":", 1)[1].strip()
        lines = lines[1:]
    return title, lines


def _render_directive(kind: str, body: str, *, ink: str, track: str, text: str) -> str:
    title, lines = _parse_title(body)
    if kind == "bars":
        rows: list[tuple[str, float, float, str]] = []
        for line in lines:
            cells = [cell.strip() for cell in line.split("|")]
            if len(cells) < 3:
                return _placeholder(title or "mp-bars", f"bad row: {line[:40]}")
            try:
                rows.append((cells[0], float(cells[1]), float(cells[2]), cells[3] if len(cells) > 3 else ""))
            except ValueError:
                return _placeholder(title or "mp-bars", f"non-numeric row: {line[:40]}")
        if not rows:
            return _placeholder(title or "mp-bars", "no rows")
        return bar_row_chart(rows, title=title, ink=ink, track=track, text=text)
    if kind == "spark":
        try:
            values = [float(token) for line in lines for token in line.replace(",", " ").split()]
        except ValueError:
            return _placeholder(title or "mp-spark", "non-numeric values")
        if len(values) > MAX_SPARK_VALUES:
            title = title or "mp-spark"
        return sparkline(values, title=title, ink=ink, track=track, text=text)
    if kind == "stats":
        stats: list[tuple[str, str, str]] = []
        for line in lines:
            cells = [cell.strip() for cell in line.split("|")]
            if len(cells) < 2:
                return _placeholder(title or "mp-stats", f"bad row: {line[:40]}")
            stats.append((cells[0], cells[1], cells[2] if len(cells) > 2 else ""))
        if not stats:
            return _placeholder(title or "mp-stats", "no rows")
        return stat_row(stats)
    return _placeholder(kind, "unknown directive")


def expand_chart_directives(
    markdown: str,
    *,
    ink: str = DEFAULT_INK,
    track: str = DEFAULT_TRACK,
    text: str = DEFAULT_TEXT,
) -> str:
    """Rewrite ```mp-bars / ```mp-spark / ```mp-stats fences into inline SVG/HTML."""

    def _sub(match: re.Match[str]) -> str:
        return _render_directive(match.group(1), match.group(2), ink=ink, track=track, text=text)

    return _DIRECTIVE_RE.sub(_sub, markdown)
