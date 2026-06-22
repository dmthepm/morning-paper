from __future__ import annotations

from morning_paper.charts import bar_row_chart, sparkline


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
