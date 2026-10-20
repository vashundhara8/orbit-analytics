"""Tests for python.src.analysis functions.

Uses small synthetic DataFrames so tests are fast and deterministic.
"""

import numpy as np
import pandas as pd
import pytest

from python.src.analysis import analyze_experiment, analyze_funnel, build_cohort_heatmap

# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def funnel_df() -> pd.DataFrame:
    """Minimal mart_funnel with one ROLLUP row and one channel row."""
    return pd.DataFrame(
        [
            {
                "acquisition_channel": None,
                "total_users": 1000,
                "signup_users": 1000,
                "workspace_users": 700,
                "invite_users": 400,
                "project_users": 200,
                "paid_users": 100,
                "signup_to_workspace_rate": 0.70,
                "workspace_to_invite_rate": 0.571,
                "invite_to_project_rate": 0.50,
                "project_to_paid_rate": 0.50,
                "overall_conversion_rate": 0.10,
            },
            {
                "acquisition_channel": "organic",
                "total_users": 500,
                "signup_users": 500,
                "workspace_users": 350,
                "invite_users": 200,
                "project_users": 100,
                "paid_users": 50,
                "signup_to_workspace_rate": 0.70,
                "workspace_to_invite_rate": 0.571,
                "invite_to_project_rate": 0.50,
                "project_to_paid_rate": 0.50,
                "overall_conversion_rate": 0.10,
            },
        ]
    )


@pytest.fixture
def cohort_df() -> pd.DataFrame:
    """Minimal cohort retention data for two cohorts over 3 weeks."""
    rows = []
    for week in ["2024-01-01", "2024-01-08"]:
        for w in range(3):
            rows.append(
                {
                    "cohort_week": week,
                    "weeks_since_signup": w,
                    "active_users": max(100 - w * 20, 10),
                    "cohort_size": 100,
                    "retention_rate": max(1.0 - w * 0.2, 0.1),
                }
            )
    return pd.DataFrame(rows)


@pytest.fixture
def experiment_df() -> pd.DataFrame:
    """Experiment mart with clear treatment lift."""
    return pd.DataFrame(
        [
            {
                "experiment_name": "onboarding_v2",
                "variant": "control",
                "users": 5000,
                "activated_users": 3000,
                "activation_rate": 0.60,
            },
            {
                "experiment_name": "onboarding_v2",
                "variant": "treatment",
                "users": 5000,
                "activated_users": 3500,
                "activation_rate": 0.70,
            },
        ]
    )


# ── Funnel tests ─────────────────────────────────────────────────────────────


class TestAnalyzeFunnel:
    def test_returns_five_steps(self, funnel_df):
        result = analyze_funnel(funnel_df)
        assert len(result) == 5
        assert list(result["step"]) == ["signup", "workspace", "invite", "project", "paid"]

    def test_first_step_has_all_users(self, funnel_df):
        result = analyze_funnel(funnel_df)
        assert result.iloc[0]["users"] == 1000

    def test_conversion_rate_is_fraction_of_total(self, funnel_df):
        result = analyze_funnel(funnel_df)
        paid = result[result["step"] == "paid"].iloc[0]
        assert paid["conversion_rate"] == pytest.approx(0.10)

    def test_step_rate_between_zero_and_one(self, funnel_df):
        result = analyze_funnel(funnel_df)
        for _, row in result.iloc[1:].iterrows():
            assert 0 <= row["step_rate"] <= 1.0

    def test_drop_off_complements_step_rate(self, funnel_df):
        result = analyze_funnel(funnel_df)
        for _, row in result.iloc[1:].iterrows():
            assert row["step_rate"] + row["drop_off"] == pytest.approx(1.0)

    def test_users_monotonically_decrease(self, funnel_df):
        result = analyze_funnel(funnel_df)
        users = result["users"].tolist()
        for i in range(1, len(users)):
            assert users[i] <= users[i - 1]


# ── Cohort tests ─────────────────────────────────────────────────────────────


class TestBuildCohortHeatmap:
    def test_output_shape(self, cohort_df):
        heatmap = build_cohort_heatmap(cohort_df)
        assert heatmap.shape == (2, 3)

    def test_column_names(self, cohort_df):
        heatmap = build_cohort_heatmap(cohort_df)
        assert list(heatmap.columns) == ["W0", "W1", "W2"]

    def test_week_zero_is_highest(self, cohort_df):
        heatmap = build_cohort_heatmap(cohort_df)
        for _, row in heatmap.iterrows():
            assert row["W0"] >= row["W2"]

    def test_values_between_zero_and_one(self, cohort_df):
        heatmap = build_cohort_heatmap(cohort_df)
        assert (heatmap.values >= 0).all()
        assert (heatmap.values <= 1.0).all()


# ── Experiment tests ─────────────────────────────────────────────────────────


class TestAnalyzeExperiment:
    def test_returns_single_row(self, experiment_df):
        result = analyze_experiment(experiment_df)
        assert len(result) == 1

    def test_has_expected_columns(self, experiment_df):
        result = analyze_experiment(experiment_df)
        expected = {
            "control_users", "treatment_users", "control_rate", "treatment_rate",
            "absolute_lift", "relative_lift", "z_statistic", "p_value", "significant",
        }
        assert set(result.columns) == expected

    def test_positive_lift_when_treatment_is_higher(self, experiment_df):
        result = analyze_experiment(experiment_df)
        assert result.iloc[0]["absolute_lift"] > 0

    def test_significant_with_large_difference(self, experiment_df):
        result = analyze_experiment(experiment_df)
        assert bool(result.iloc[0]["significant"]) is True
        assert result.iloc[0]["p_value"] < 0.05

    def test_not_significant_with_equal_rates(self):
        equal_df = pd.DataFrame(
            [
                {"experiment_name": "test", "variant": "control", "users": 100,
                 "activated_users": 50, "activation_rate": 0.50},
                {"experiment_name": "test", "variant": "treatment", "users": 100,
                 "activated_users": 51, "activation_rate": 0.51},
            ]
        )
        result = analyze_experiment(equal_df)
        assert result.iloc[0]["significant"] is np.bool_(False)

    def test_relative_lift_calculation(self, experiment_df):
        result = analyze_experiment(experiment_df)
        r = result.iloc[0]
        expected_relative = (r["treatment_rate"] - r["control_rate"]) / r["control_rate"]
        assert r["relative_lift"] == pytest.approx(expected_relative, abs=0.001)
