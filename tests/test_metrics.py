"""Tests for python.src.metrics helper functions."""

import pandas as pd
import pytest

from python.src.metrics import compute_rolling_avg, format_currency, format_pct, safe_rate


class TestSafeRate:
    def test_normal_division(self):
        assert safe_rate(10, 100) == pytest.approx(0.1)

    def test_zero_denominator_returns_zero(self):
        assert safe_rate(10, 0) == 0.0

    def test_zero_numerator(self):
        assert safe_rate(0, 100) == 0.0

    def test_float_inputs(self):
        assert safe_rate(1.5, 3.0) == pytest.approx(0.5)


class TestFormatPct:
    def test_default_decimals(self):
        assert format_pct(0.7265) == "72.7%"

    def test_custom_decimals(self):
        assert format_pct(0.7265, decimals=2) == "72.65%"

    def test_zero(self):
        assert format_pct(0.0) == "0.0%"

    def test_one(self):
        assert format_pct(1.0) == "100.0%"


class TestFormatCurrency:
    def test_thousands(self):
        assert format_currency(1234.56) == "$1,235"

    def test_zero(self):
        assert format_currency(0) == "$0"

    def test_large_number(self):
        assert format_currency(1_500_000) == "$1,500,000"


class TestComputeRollingAvg:
    def test_rolling_window(self):
        s = pd.Series([10, 20, 30, 40, 50])
        result = compute_rolling_avg(s, window=3)
        assert result.iloc[0] == pytest.approx(10.0)
        assert result.iloc[2] == pytest.approx(20.0)
        assert result.iloc[4] == pytest.approx(40.0)

    def test_single_element(self):
        s = pd.Series([42])
        result = compute_rolling_avg(s, window=7)
        assert result.iloc[0] == pytest.approx(42.0)

    def test_min_periods_one(self):
        s = pd.Series([1, 2, 3])
        result = compute_rolling_avg(s, window=5)
        assert len(result.dropna()) == 3
