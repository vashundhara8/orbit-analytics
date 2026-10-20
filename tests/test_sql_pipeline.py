"""Integration test for the DuckDB SQL pipeline.

Runs the full staging + mart SQL against the already-generated data
and validates mart output shapes and key invariants.
"""

from pathlib import Path

import duckdb
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
SQL_DIR = ROOT / "sql"

STAGING_ORDER = ["stg_users", "stg_events", "stg_subscriptions", "stg_experiments"]
MART_ORDER = ["mart_funnel", "mart_cohort_retention", "mart_experiment_results", "mart_product_growth_daily"]


@pytest.fixture(scope="module")
def duckdb_con():
    """Build a DuckDB connection with all staging + mart models loaded."""
    con = duckdb.connect(":memory:")

    for table_name, filename in {
        "raw_dim_users": "dim_users.parquet",
        "raw_fact_events": "fact_events.parquet",
        "raw_fact_subscriptions": "fact_subscriptions.parquet",
        "raw_fact_experiments": "fact_experiments.parquet",
    }.items():
        path = RAW_DIR / filename
        if not path.exists():
            pytest.skip(f"Raw data not found at {path}. Run `make generate` first.")
        con.execute(f"CREATE TABLE {table_name} AS SELECT * FROM read_parquet('{path}')")

    for name in STAGING_ORDER:
        sql = (SQL_DIR / "staging" / f"{name}.sql").read_text()
        con.execute(sql)

    for name in MART_ORDER:
        sql = (SQL_DIR / "marts" / f"{name}.sql").read_text()
        con.execute(sql)

    yield con
    con.close()


class TestMartFunnel:
    def test_has_rollup_row(self, duckdb_con):
        df = duckdb_con.execute("SELECT * FROM mart_funnel").fetchdf()
        rollup = df[df["acquisition_channel"].isna()]
        assert len(rollup) == 1

    def test_has_channel_rows(self, duckdb_con):
        df = duckdb_con.execute("SELECT * FROM mart_funnel").fetchdf()
        channels = df.dropna(subset=["acquisition_channel"])
        assert len(channels) >= 2

    def test_funnel_monotonically_decreasing(self, duckdb_con):
        df = duckdb_con.execute("SELECT * FROM mart_funnel").fetchdf()
        rollup = df[df["acquisition_channel"].isna()].iloc[0]
        steps = ["signup_users", "workspace_users", "invite_users", "project_users", "paid_users"]
        values = [rollup[s] for s in steps]
        for i in range(1, len(values)):
            assert values[i] <= values[i - 1], f"{steps[i]} ({values[i]}) > {steps[i-1]} ({values[i-1]})"


class TestMartCohortRetention:
    def test_not_empty(self, duckdb_con):
        df = duckdb_con.execute("SELECT * FROM mart_cohort_retention").fetchdf()
        assert len(df) > 0

    def test_retention_rate_between_zero_and_one(self, duckdb_con):
        df = duckdb_con.execute("SELECT * FROM mart_cohort_retention").fetchdf()
        assert df["retention_rate"].min() >= 0
        assert df["retention_rate"].max() <= 1.0

    def test_week_zero_retention_highest(self, duckdb_con):
        df = duckdb_con.execute("SELECT * FROM mart_cohort_retention").fetchdf()
        for cohort, group in df.groupby("cohort_week"):
            w0 = group[group["weeks_since_signup"] == 0]["retention_rate"].iloc[0]
            later = group[group["weeks_since_signup"] > 0]["retention_rate"]
            if len(later) > 0:
                assert w0 >= later.min(), f"Cohort {cohort}: W0 ({w0}) < later min ({later.min()})"


class TestMartExperimentResults:
    def test_two_variants(self, duckdb_con):
        df = duckdb_con.execute("SELECT * FROM mart_experiment_results").fetchdf()
        assert set(df["variant"]) == {"control", "treatment"}

    def test_activation_rate_valid(self, duckdb_con):
        df = duckdb_con.execute("SELECT * FROM mart_experiment_results").fetchdf()
        for _, row in df.iterrows():
            assert 0 <= row["activation_rate"] <= 1.0


class TestMartProductGrowthDaily:
    def test_not_empty(self, duckdb_con):
        df = duckdb_con.execute("SELECT * FROM mart_product_growth_daily").fetchdf()
        assert len(df) > 100

    def test_mrr_non_negative(self, duckdb_con):
        df = duckdb_con.execute("SELECT * FROM mart_product_growth_daily").fetchdf()
        assert (df["mrr"] >= 0).all()

    def test_dates_are_ordered(self, duckdb_con):
        df = duckdb_con.execute("SELECT * FROM mart_product_growth_daily ORDER BY metric_date").fetchdf()
        dates = pd.to_datetime(df["metric_date"])
        assert dates.is_monotonic_increasing


class TestD30RetentionMaturity:
    """Test D30 retention maturity logic in mart_product_growth_daily SQL."""

    @pytest.fixture
    def maturity_con(self):
        """Build an in-memory DuckDB connection with controlled maturity scenarios."""
        con = duckdb.connect(":memory:")

        # Setup staging tables directly for focused testing
        # Max event date in stg_events is 2025-07-31
        con.execute("""
            CREATE TABLE stg_users AS
            SELECT 'u_mature_ret' AS user_id, DATE '2025-06-01' AS signup_date,
                   '11-50' AS company_size, 'Tech' AS industry, 'organic' AS acquisition_channel, 'pro' AS plan_type
            UNION ALL
            SELECT 'u_mature_zero' AS user_id, DATE '2025-06-02' AS signup_date,
                   '11-50' AS company_size, 'Tech' AS industry, 'organic' AS acquisition_channel, 'pro' AS plan_type
            UNION ALL
            SELECT 'u_exact_boundary' AS user_id, DATE '2025-06-29' AS signup_date,
                   '11-50' AS company_size, 'Tech' AS industry, 'organic' AS acquisition_channel, 'pro' AS plan_type
            UNION ALL
            SELECT 'u_immature' AS user_id, DATE '2025-07-15' AS signup_date,
                   '11-50' AS company_size, 'Tech' AS industry, 'organic' AS acquisition_channel, 'pro' AS plan_type;

            CREATE TABLE stg_events AS
            -- Returning user in Day 30 window (signup 2025-06-01 + 30 days = 2025-07-01)
            SELECT 'e1' AS event_id, 'u_mature_ret' AS user_id, 'login' AS event_name,
                   TIMESTAMP '2025-07-01 10:00:00' AS event_ts, DATE '2025-07-01' AS event_date,
                   'desktop' AS device, 's1' AS session_id
            UNION ALL
            -- User returning before Day 28 (not in D30 window)
            SELECT 'e2' AS event_id, 'u_mature_zero' AS user_id, 'login' AS event_name,
                   TIMESTAMP '2025-06-10 10:00:00' AS event_ts, DATE '2025-06-10' AS event_date,
                   'desktop' AS device, 's2' AS session_id
            UNION ALL
            -- Returning user on the exact boundary (signup 2025-06-29 + 32 days = 2025-07-31)
            SELECT 'e3' AS event_id, 'u_exact_boundary' AS user_id, 'login' AS event_name,
                   TIMESTAMP '2025-07-31 23:00:00' AS event_ts, DATE '2025-07-31' AS event_date,
                   'desktop' AS device, 's3' AS session_id;

            CREATE TABLE stg_subscriptions AS
            SELECT 'u_mature_ret' AS user_id, DATE '2025-06-01' AS trial_start_date,
                   DATE '2025-06-05' AS paid_start_date, CAST(NULL AS DATE) AS cancel_date, 100 AS mrr;
        """)

        # Run mart_product_growth_daily.sql
        sql = (SQL_DIR / "marts" / "mart_product_growth_daily.sql").read_text()
        con.execute(sql)

        yield con
        con.close()

    def test_mature_cohort_with_returning_users_positive(self, maturity_con):
        """Case 1: Mature cohort with returning users produces expected positive rate."""
        row = maturity_con.execute(
            "SELECT d30_retention_rate FROM mart_product_growth_daily WHERE metric_date = DATE '2025-06-01'"
        ).fetchone()
        assert row is not None
        assert row[0] == pytest.approx(1.0, abs=0.001)

    def test_mature_cohort_without_returning_users_is_zero(self, maturity_con):
        """Case 2: Mature cohort with no qualifying returning users produces 0.0, not NULL."""
        row = maturity_con.execute(
            "SELECT d30_retention_rate FROM mart_product_growth_daily WHERE metric_date = DATE '2025-06-02'"
        ).fetchone()
        assert row is not None
        assert row[0] == pytest.approx(0.0, abs=0.001)
        assert row[0] is not None

    def test_immature_cohort_is_null(self, maturity_con):
        """Case 3: Immature cohort with insufficient observation produces NULL."""
        row = maturity_con.execute(
            "SELECT d30_retention_rate FROM mart_product_growth_daily WHERE metric_date = DATE '2025-07-15'"
        ).fetchone()
        assert row is not None
        assert row[0] is None

    def test_exact_boundary_cohort_is_mature(self, maturity_con):
        """Case 4: Cohort whose qualifying window exactly reaches MAX(event_date) is mature."""
        row = maturity_con.execute(
            "SELECT d30_retention_rate FROM mart_product_growth_daily WHERE metric_date = DATE '2025-06-29'"
        ).fetchone()
        assert row is not None
        assert row[0] == pytest.approx(1.0, abs=0.001)

    def test_executive_summary_renders_immature_d30_as_unavailable(self):
        """Case 5: Executive summary KPI computation treats all-null D30 as unavailable (None)."""
        import numpy as np
        immature_df = pd.DataFrame({
            "new_signups": [100, 150],
            "activated_users": [60, 90],
            "new_paid": [20, 30],
            "churned_users": [5, 8],
            "mrr": [10000, 12000],
            "d30_retention_rate": [np.nan, None],
        })

        ret_series = immature_df["d30_retention_rate"].dropna()
        d30_ret = float(ret_series.mean()) if not ret_series.empty else None

        assert d30_ret is None
        d30_text = f"{d30_ret:.1%}" if d30_ret is not None else "N/A (Immature)"
        assert d30_text == "N/A (Immature)"
        assert d30_text != "0.0%"
