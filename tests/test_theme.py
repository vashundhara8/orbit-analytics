"""Tests for Orbit Design System theme helpers in streamlit_app/utils/theme.py."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_app.utils.theme import (
    BG_BASE,
    BG_SURFACE,
    CHART_COLORS,
    HEATMAP_COLORSCALE,
    TEXT_PRIMARY,
    apply_orbit_chart_theme,
    build_kpi_card_html,
    format_date_window_caption,
    format_delta,
    format_kpi_value,
    get_orbit_css,
    render_kpi_card,
)


class TestFormatKpiValue:
    def test_currency(self):
        assert format_kpi_value(318485, "currency") == "$318,485"
        assert format_kpi_value(0, "currency") == "$0"

    def test_percent(self):
        assert format_kpi_value(0.634, "percent", decimals=1) == "63.4%"
        assert format_kpi_value(0.1578, "percent", decimals=2) == "15.78%"
        assert format_kpi_value(0, "percent") == "0.0%"

    def test_integer(self):
        assert format_kpi_value(100000, "integer") == "100,000"
        assert format_kpi_value(1453089, "integer") == "1,453,089"

    def test_default_number(self):
        assert format_kpi_value(3.14159, "number", decimals=2) == "3.14"


class TestFormatDelta:
    def test_positive_percent(self):
        text, is_pos = format_delta(0.032, "percent")
        assert text == "+3.2%"
        assert is_pos is True

    def test_negative_percent(self):
        text, is_pos = format_delta(-0.014, "percent")
        assert text == "-1.4%"
        assert is_pos is False

    def test_zero_percent(self):
        text, is_pos = format_delta(0.0, "percent")
        assert text == "0.0%"
        assert is_pos is True

    def test_currency_deltas(self):
        pos_text, pos_flag = format_delta(1500, "currency")
        assert pos_text == "+$1,500"
        assert pos_flag is True

        neg_text, neg_flag = format_delta(-2500, "currency")
        assert neg_text == "-$2,500"
        assert neg_flag is False


class TestApplyOrbitChartTheme:
    def test_chart_layout_properties(self):
        fig = go.Figure(data=[go.Bar(x=["A", "B"], y=[10, 20])])
        styled = apply_orbit_chart_theme(
            fig,
            height=350,
            show_legend=False,
            xaxis_title="Category",
            yaxis_title="Count",
        )

        assert styled.layout.paper_bgcolor == "rgba(0,0,0,0)"
        assert styled.layout.plot_bgcolor == "rgba(0,0,0,0)"
        assert styled.layout.height == 350
        assert styled.layout.showlegend is False
        assert styled.layout.font.color == TEXT_PRIMARY
        assert styled.layout.xaxis.title.text == "Category"
        assert styled.layout.yaxis.title.text == "Count"

    def test_color_constants_defined(self):
        assert isinstance(CHART_COLORS, list)
        assert len(CHART_COLORS) >= 5
        assert isinstance(HEATMAP_COLORSCALE, list)
        assert HEATMAP_COLORSCALE[0][1] == BG_SURFACE


class TestGetOrbitCss:
    def test_css_contains_expected_classes(self):
        css = get_orbit_css()
        assert isinstance(css, str)
        assert ".orbit-card" in css
        assert ".orbit-kpi-value" in css
        assert ".orbit-kpi-label" in css
        assert ".orbit-badge" in css
        assert BG_BASE in css or BG_SURFACE in css


class TestRenderKpiCard:
    """Regression tests for KPI card markup generation and CommonMark safety."""

    def test_basic_card(self):
        html = build_kpi_card_html(label="Tracked Accounts", value="100,000")
        assert "Tracked Accounts" in html
        assert "100,000" in html
        assert "orbit-card" in html
        assert "orbit-kpi-delta" not in html
        assert "orbit-subtext" not in html
        for line in html.splitlines():
            assert line.strip() != "", "HTML should not contain blank lines"
            assert not line.startswith("    "), "No line should have 4+ space indent"

    def test_subtext_only(self):
        html = build_kpi_card_html(
            label="Week 1 Retention",
            value="34.2%",
            subtext="Initial onboarding retention",
        )
        assert "Week 1 Retention" in html
        assert "34.2%" in html
        assert "Initial onboarding retention" in html
        assert "orbit-subtext" in html
        assert "orbit-kpi-delta" not in html
        for line in html.splitlines():
            assert line.strip() != "", "HTML should not contain blank lines"
            assert not line.startswith("    "), "No line should have 4+ space indent"

    def test_delta_only(self):
        html = build_kpi_card_html(
            label="Active Run-Rate MRR",
            value="$1,053,102",
            delta="+$23,400",
            delta_positive=True,
        )
        assert "Active Run-Rate MRR" in html
        assert "$1,053,102" in html
        assert "+$23,400" in html
        assert "orbit-delta-positive" in html
        assert "orbit-subtext" not in html
        for line in html.splitlines():
            assert line.strip() != "", "HTML should not contain blank lines"
            assert not line.startswith("    "), "No line should have 4+ space indent"

    def test_delta_plus_subtext(self):
        html = build_kpi_card_html(
            label="Activation Rate",
            value="42.5%",
            delta="+1.2 pp",
            delta_positive=True,
            subtext="1,200 of 2,820 signups",
        )
        assert "Activation Rate" in html
        assert "42.5%" in html
        assert "+1.2 pp" in html
        assert "orbit-delta-positive" in html
        assert "1,200 of 2,820 signups" in html
        assert "orbit-subtext" in html
        for line in html.splitlines():
            assert line.strip() != "", "HTML should not contain blank lines"
            assert not line.startswith("    "), "No line should have 4+ space indent"

    def test_render_kpi_card_invokes_markdown(self, monkeypatch):
        captured = []

        def mock_markdown(body, unsafe_allow_html=False):
            captured.append((body, unsafe_allow_html))

        monkeypatch.setattr(st, "markdown", mock_markdown)
        render_kpi_card(
            label="Test Metric",
            value="99.9%",
            delta="+0.5%",
            delta_positive=True,
            subtext="Test subtext",
        )

        assert len(captured) == 1
        body, unsafe = captured[0]
        assert unsafe is True
        assert "Test Metric" in body
        assert "99.9%" in body
        assert "+0.5%" in body
        assert "Test subtext" in body


class TestFormatDateWindowCaption:
    def test_active_period_only_when_comparison_disabled(self):
        start = pd.Timestamp("2025-05-31")
        end = pd.Timestamp("2025-06-29")
        caption = format_date_window_caption(
            start_date=start,
            end_date=end,
            period_days=30,
            compare_enabled=False,
            comparison_msg="",
        )
        assert caption == "Active Period: May 31, 2025 - Jun 29, 2025 (30 days)"
        assert "Comparison" not in caption

    def test_active_and_comparison_period_when_enabled(self):
        start = pd.Timestamp("2025-05-31")
        end = pd.Timestamp("2025-06-29")
        msg = "Comparison Period: May 01, 2025 - May 30, 2025 (30 days)"
        caption = format_date_window_caption(
            start_date=start,
            end_date=end,
            period_days=30,
            compare_enabled=True,
            comparison_msg=msg,
        )
        assert "Active Period: May 31, 2025 - Jun 29, 2025 (30 days)" in caption
        assert "Comparison Period: May 01, 2025 - May 30, 2025 (30 days)" in caption
        assert "•" in caption

    def test_partial_comparison_message(self):
        start = pd.Timestamp("2024-01-10")
        end = pd.Timestamp("2024-01-20")
        msg = "Partial Comparison: Jan 01, 2024 - Jan 09, 2024 (9 of 11 days available)"
        caption = format_date_window_caption(
            start_date=start,
            end_date=end,
            period_days=11,
            compare_enabled=True,
            comparison_msg=msg,
        )
        assert "Active Period: Jan 10, 2024 - Jan 20, 2024 (11 days)" in caption
        assert "Partial Comparison" in caption

    def test_all_preset_window_durations(self):
        max_date = pd.Timestamp("2025-06-29")
        min_date = pd.Timestamp("2024-01-01")

        presets = {
            "Last 7 Days": (max_date - pd.Timedelta(days=6), max_date, 7),
            "Last 30 Days": (max_date - pd.Timedelta(days=29), max_date, 30),
            "Last 90 Days": (max_date - pd.Timedelta(days=89), max_date, 90),
            "Year-to-Date (2025)": (pd.Timestamp("2025-01-01"), max_date, 180),
            "All Time (546 Days)": (min_date, max_date, 546),
        }

        for name, (start, end, expected_days) in presets.items():
            actual_days = (end - start).days + 1
            assert actual_days == expected_days, f"Failed on {name}"
            # Verify previous period boundary is contiguous
            prev_end = start - pd.Timedelta(days=1)
            prev_start = prev_end - pd.Timedelta(days=expected_days - 1)
            prev_days = (prev_end - prev_start).days + 1
            assert prev_days == expected_days, f"Previous period duration mismatch on {name}"
            assert prev_end < start, f"Previous period overlaps active window on {name}"
