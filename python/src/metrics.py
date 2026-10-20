"""Reusable KPI calculation helpers."""

from __future__ import annotations

import pandas as pd


def safe_rate(numerator: int | float, denominator: int | float) -> float:
    """Compute a rate, returning 0.0 when denominator is zero."""
    return float(numerator / denominator) if denominator else 0.0


def format_pct(value: float, decimals: int = 1) -> str:
    return f"{value * 100:.{decimals}f}%"


def format_currency(value: float) -> str:
    return f"${value:,.0f}"


def compute_rolling_avg(series: pd.Series, window: int = 7) -> pd.Series:
    """Return a rolling average, filling leading NaNs with the raw values."""
    rolling = series.rolling(window, min_periods=1).mean()
    return rolling
