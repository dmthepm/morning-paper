from __future__ import annotations

from morning_paper.charts import expand_chart_directives, bar_row_chart, sparkline


def test_bar_chart_uses_full_measure() -> None:
    html = bar_row_chart(
        [("09:00", 38, 40, "peak - queue to the door")],
        title="Saturday at the bakery counter, by hour",
    )

    assert 'class="mp-chart mp-chart-bars"' in html
    assert '<rect x="0" y="12" width="700" height="7"' in html
    assert '<rect x="0" y="12" width="665.0" height="7"' in html
    assert 'x="700" y="9" text-anchor="end"' in html


def test_sparkline_keeps_small_print_gutters() -> None:
    html = sparkline([4, 6, 5, 7, 9, 8, 8, 11, 10, 9, 12, 14, 13, 15])

    assert 'class="mp-chart mp-chart-spark"' in html
    assert '<line x1="28" y1="52" x2="666" y2="52"' in html
    assert 'points="28.0,52.0' in html
    assert '666.0,8.0"' in html


def test_bar_chart_caps_rows_and_clips_long_labels() -> None:
    rows = [(f"Very long bakery counter label number {i}", i, 20, f"annotation {i}") for i in range(15)]
    html = bar_row_chart(rows)

    assert "+3 row(s) not shown" in html
    assert "Very long bakery counter label..." in html
    assert "Very long bakery counter label number 14" not in html


def test_stats_caps_blocks_with_honest_note() -> None:
    markdown = """```mp-stats
One | 1 | ok
Two | 2 | ok
Three | 3 | ok
Four | 4 | ok
Five | 5 | ok
Six | 6 | ok
Seven | 7 | ok
Eight | 8 | ok
```"""

    html = expand_chart_directives(markdown)

    assert "+2" in html
    assert "not shown" in html
    assert "Eight" not in html


def test_sparkline_caps_large_value_series() -> None:
    values = " ".join(str(i) for i in range(120))
    html = expand_chart_directives(f"```mp-spark\n{values}\n```")

    assert ">0<" not in html
    assert ">30<" in html
    assert ">29<" not in html
    assert "119" in html
