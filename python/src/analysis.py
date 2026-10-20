"""Core analysis functions: funnel, cohort retention, A/B test, churn scoring.

Can be run standalone via `python -m python.src.analysis` to print summary results,
or imported by Streamlit pages for interactive rendering.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from statsmodels.stats.proportion import proportions_ztest

ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = ROOT / "data" / "processed"
RAW_DIR = ROOT / "data" / "raw"


# ── Funnel ───────────────────────────────────────────────────────────────────


def analyze_funnel(funnel_df: pd.DataFrame) -> pd.DataFrame:
    """Reshape mart_funnel into a step-by-step conversion table.

    Returns one row per funnel step with users, conversion rate, and drop-off.
    Uses the ROLLUP total row (acquisition_channel IS NULL) for overall numbers.
    """
    overall = funnel_df[funnel_df["acquisition_channel"].isna()].iloc[0]

    steps = ["signup", "workspace", "invite", "project", "paid"]
    columns = [
        "signup_users",
        "workspace_users",
        "invite_users",
        "project_users",
        "paid_users",
    ]

    rows = []
    for i, (step, col) in enumerate(zip(steps, columns, strict=True)):
        users = int(overall[col])
        prev_users = int(overall[columns[i - 1]]) if i > 0 else users
        rows.append(
            {
                "step": step,
                "users": users,
                "conversion_rate": users / int(overall["total_users"])
                if overall["total_users"]
                else 0,
                "step_rate": users / prev_users if prev_users else 0,
                "drop_off": 1 - (users / prev_users) if prev_users else 0,
            }
        )

    return pd.DataFrame(rows)


# ── Cohort retention ─────────────────────────────────────────────────────────


def build_cohort_heatmap(cohort_df: pd.DataFrame) -> pd.DataFrame:
    """Pivot mart_cohort_retention into a heatmap-ready matrix.

    Rows = cohort_week, columns = weeks_since_signup, values = retention_rate.
    """
    pivot = cohort_df.pivot_table(
        index="cohort_week",
        columns="weeks_since_signup",
        values="retention_rate",
        aggfunc="first",
    )
    pivot.index = pivot.index.astype(str)
    pivot.columns = [f"W{int(c)}" for c in pivot.columns]
    return pivot


# ── A/B test ─────────────────────────────────────────────────────────────────


def analyze_experiment(experiment_df: pd.DataFrame) -> pd.DataFrame:
    """Run a proportions z-test on experiment mart data.

    Returns a single-row DataFrame with control/treatment rates,
    absolute and relative lift, p-value, and significance flag.
    """
    control = experiment_df[experiment_df["variant"] == "control"].iloc[0]
    treatment = experiment_df[experiment_df["variant"] == "treatment"].iloc[0]

    successes = np.array([treatment["activated_users"], control["activated_users"]])
    observations = np.array([treatment["users"], control["users"]])

    z_stat, p_value = proportions_ztest(successes, observations)

    lift = treatment["activation_rate"] - control["activation_rate"]
    relative_lift = lift / control["activation_rate"] if control["activation_rate"] else 0

    return pd.DataFrame(
        {
            "control_users": [int(control["users"])],
            "treatment_users": [int(treatment["users"])],
            "control_rate": [control["activation_rate"]],
            "treatment_rate": [treatment["activation_rate"]],
            "absolute_lift": [round(lift, 4)],
            "relative_lift": [round(relative_lift, 4)],
            "z_statistic": [round(z_stat, 4)],
            "p_value": [round(p_value, 6)],
            "significant": [p_value < 0.05],
        }
    )


# ── Churn scoring ────────────────────────────────────────────────────────────


def score_churn_risk() -> pd.DataFrame:
    """Build churn features from raw data and score each user.

    Features: days_since_last_event, total_event_count, distinct_event_types.
    Target: subscription_status == 'churned' from subscriptions.
    Returns per-user churn probability.
    """
    users = pd.read_parquet(RAW_DIR / "dim_users.parquet")
    events = pd.read_parquet(RAW_DIR / "fact_events.parquet")
    subs = pd.read_parquet(RAW_DIR / "fact_subscriptions.parquet")

    reference_date = events["event_ts"].max()

    event_features = (
        events.groupby("user_id")
        .agg(
            last_event_ts=("event_ts", "max"),
            total_events=("event_id", "count"),
            distinct_events=("event_name", "nunique"),
        )
        .reset_index()
    )
    event_features["days_since_last_event"] = (
        reference_date - event_features["last_event_ts"]
    ).dt.total_seconds() / 86400

    subs["is_churned"] = (subs["cancel_date"].notna()).astype(int)
    labeled = subs[subs["paid_start_date"].notna()][["user_id", "is_churned"]]

    df = labeled.merge(
        event_features[["user_id", "days_since_last_event", "total_events", "distinct_events"]],
        on="user_id",
        how="left",
    )
    df = df.dropna()

    feature_cols = ["days_since_last_event", "total_events", "distinct_events"]
    features = df[feature_cols].values
    target = df["is_churned"].values

    scaler = StandardScaler()
    features_scaled = scaler.fit_transform(features)

    model = LogisticRegression(random_state=42, max_iter=500)
    model.fit(features_scaled, target)

    df["churn_probability"] = model.predict_proba(features_scaled)[:, 1]
    df["risk_tier"] = pd.cut(
        df["churn_probability"],
        bins=[0, 0.3, 0.6, 1.0],
        labels=["low", "medium", "high"],
    )

    return df[
        ["user_id", "churn_probability", "risk_tier", "days_since_last_event", "total_events"]
    ].merge(users[["user_id", "company_size", "industry"]], on="user_id", how="left")


# ── CLI entry point ──────────────────────────────────────────────────────────


def main() -> None:
    print("=" * 60)
    print("SaaS Growth Analytics — Analysis Results")
    print("=" * 60)

    funnel_df = pd.read_parquet(PROCESSED_DIR / "mart_funnel.parquet")
    funnel = analyze_funnel(funnel_df)
    print("\n── Funnel Conversion ──")
    print(funnel.to_string(index=False))

    cohort_df = pd.read_parquet(PROCESSED_DIR / "mart_cohort_retention.parquet")
    heatmap = build_cohort_heatmap(cohort_df)
    print("\n── Cohort Retention (first 5 cohorts) ──")
    print(heatmap.head().to_string())

    exp_df = pd.read_parquet(PROCESSED_DIR / "mart_experiment_results.parquet")
    exp_results = analyze_experiment(exp_df)
    print("\n── A/B Test: onboarding_v2 ──")
    print(exp_results.to_string(index=False))

    print("\n── Churn Risk Scoring ──")
    churn = score_churn_risk()
    print(churn["risk_tier"].value_counts().to_string())
    print(f"  Mean churn probability: {churn['churn_probability'].mean():.3f}")

    print("\nDone.")


if __name__ == "__main__":
    main()
