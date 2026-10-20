"""Generate synthetic SaaS product analytics data.

Produces four Parquet tables in data/raw/ and CSV samples in data/sample/.
Uses a fixed seed for reproducibility. Events, subscriptions, and experiments
are correlated so downstream funnel and A/B analyses produce realistic results.
"""

from __future__ import annotations

import uuid
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
SAMPLE_DIR = ROOT / "data" / "sample"

SEED = 42
NUM_USERS = 100_000
rng = np.random.default_rng(SEED)

INDUSTRIES = [
    "Technology",
    "Healthcare",
    "Finance",
    "Education",
    "Retail",
    "Manufacturing",
    "Media",
    "Professional Services",
]
COMPANY_SIZES = ["startup", "smb", "mid-market", "enterprise"]
CHANNELS = ["organic", "paid_search", "referral", "partner"]
PLAN_TYPES = ["free", "trial", "pro", "enterprise"]
DEVICES = ["desktop", "mobile", "tablet"]

FUNNEL_STEPS = [
    "signup",
    "workspace_created",
    "invite_sent",
    "first_project",
]

# Step-to-step conversion probability
STEP_CONVERSION = {
    "signup": 1.0,
    "workspace_created": 0.72,
    "invite_sent": 0.67,
    "first_project": 0.69,
}

MRR_BY_PLAN = {"free": 0, "trial": 0, "pro": 29, "enterprise": 199}


def _generate_users() -> pd.DataFrame:
    start = pd.Timestamp("2024-01-01")
    end = pd.Timestamp("2025-06-30")
    days_range = (end - start).days

    signup_offsets = rng.integers(0, days_range, size=NUM_USERS)
    signup_dates = pd.to_datetime(start) + pd.to_timedelta(signup_offsets, unit="D")

    size_weights = np.array([0.35, 0.30, 0.20, 0.15])
    channel_weights = np.array([0.40, 0.25, 0.20, 0.15])
    plan_weights = np.array([0.30, 0.35, 0.20, 0.15])

    return pd.DataFrame(
        {
            "user_id": [f"u_{i:06d}" for i in range(NUM_USERS)],
            "signup_date": signup_dates,
            "company_size": rng.choice(COMPANY_SIZES, NUM_USERS, p=size_weights),
            "industry": rng.choice(INDUSTRIES, NUM_USERS),
            "acquisition_channel": rng.choice(CHANNELS, NUM_USERS, p=channel_weights),
            "plan_type": rng.choice(PLAN_TYPES, NUM_USERS, p=plan_weights),
        }
    )


def _simulate_funnel(users: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, set[str]]]:
    """Walk each user through the funnel, tracking which steps they reach.

    Returns (events_df, reached_dict) where reached_dict maps
    step_name -> set of user_ids who reached that step.
    """
    records: list[dict] = []
    reached: dict[str, set[str]] = {step: set() for step in FUNNEL_STEPS}
    session_counter = 0

    for _, user in users.iterrows():
        uid = user["user_id"]
        signup_ts = pd.Timestamp(user["signup_date"])
        hour_offset = 0

        for step in FUNNEL_STEPS:
            if step != "signup" and rng.random() > STEP_CONVERSION[step]:
                break

            reached[step].add(uid)
            session_counter += 1
            hour_offset += int(rng.integers(1, 72))

            records.append(
                {
                    "event_id": str(uuid.uuid4()),
                    "user_id": uid,
                    "event_name": step,
                    "event_ts": signup_ts + pd.Timedelta(hours=hour_offset),
                    "device": rng.choice(DEVICES),
                    "session_id": f"s_{session_counter:08d}",
                }
            )

        extra = rng.poisson(12)
        for _ in range(extra):
            session_counter += 1
            offset_days = rng.integers(0, 180)
            records.append(
                {
                    "event_id": str(uuid.uuid4()),
                    "user_id": uid,
                    "event_name": rng.choice(
                        ["feature_used", "page_view", "settings_changed", "export"]
                    ),
                    "event_ts": signup_ts + pd.Timedelta(days=int(offset_days)),
                    "device": rng.choice(DEVICES),
                    "session_id": f"s_{session_counter:08d}",
                }
            )

    return pd.DataFrame(records), reached


def _generate_subscriptions(users: pd.DataFrame, reached: dict[str, set[str]]) -> pd.DataFrame:
    """Generate subscriptions correlated with funnel progress.

    Only users who reached first_project can convert to paid.
    """
    project_users = reached["first_project"]
    records: list[dict] = []

    for _, user in users.iterrows():
        uid = user["user_id"]
        plan = user["plan_type"]
        signup_date = pd.Timestamp(user["signup_date"])

        trial_start = signup_date if plan in ("trial", "pro", "enterprise") else pd.NaT
        paid_start = pd.NaT
        cancel_date = pd.NaT
        mrr = 0

        can_convert = uid in project_users

        if plan in ("pro", "enterprise") and can_convert:
            paid_start = signup_date + pd.Timedelta(days=int(rng.integers(7, 30)))
            mrr = MRR_BY_PLAN[plan]
            if rng.random() < 0.15:
                cancel_date = paid_start + pd.Timedelta(days=int(rng.integers(30, 180)))
                mrr = 0
        elif plan == "trial" and can_convert and rng.random() < 0.35:
            paid_start = signup_date + pd.Timedelta(days=int(rng.integers(14, 35)))
            mrr = MRR_BY_PLAN["pro"]
            if rng.random() < 0.18:
                cancel_date = paid_start + pd.Timedelta(days=int(rng.integers(30, 150)))
                mrr = 0

        records.append(
            {
                "user_id": uid,
                "trial_start_date": trial_start,
                "paid_start_date": paid_start,
                "cancel_date": cancel_date,
                "mrr": mrr,
            }
        )

    return pd.DataFrame(records)


def _generate_experiments(
    users: pd.DataFrame, events_df: pd.DataFrame, reached: dict[str, set[str]]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Assign ~20K users to an experiment and bake in a treatment lift.

    Treatment group users who didn't originally reach workspace_created
    get a 15% chance of an extra workspace_created event (the lift).
    Returns (experiments_df, updated_events_df).
    """
    eligible = users[users["plan_type"].isin(["trial", "free"])].head(20_000)
    variants = rng.choice(["control", "treatment"], len(eligible))
    assigned_ts = pd.to_datetime(eligible["signup_date"]) + pd.to_timedelta(
        rng.integers(1, 48, size=len(eligible)), unit="h"
    )

    exp_df = pd.DataFrame(
        {
            "user_id": eligible["user_id"].values,
            "experiment_name": "onboarding_v2",
            "variant": variants,
            "assigned_ts": assigned_ts.values,
        }
    )

    # inject treatment lift: 15% of treatment users who hadn't activated now do
    treatment_users = set(exp_df[exp_df["variant"] == "treatment"]["user_id"])
    already_activated = reached["workspace_created"]
    lift_candidates = treatment_users - already_activated

    extra_events = []
    session_base = events_df["session_id"].str.extract(r"(\d+)").astype(int).max().iloc[0] + 1

    for uid in lift_candidates:
        if rng.random() < 0.15:
            signup_ts = users.loc[users["user_id"] == uid, "signup_date"].iloc[0]
            session_base += 1
            extra_events.append(
                {
                    "event_id": str(uuid.uuid4()),
                    "user_id": uid,
                    "event_name": "workspace_created",
                    "event_ts": pd.Timestamp(signup_ts)
                    + pd.Timedelta(hours=int(rng.integers(2, 48))),
                    "device": rng.choice(DEVICES),
                    "session_id": f"s_{session_base:08d}",
                }
            )

    if extra_events:
        events_df = pd.concat([events_df, pd.DataFrame(extra_events)], ignore_index=True)

    return exp_df, events_df


def _save(df: pd.DataFrame, name: str) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)

    df.to_parquet(RAW_DIR / f"{name}.parquet", index=False)
    df.head(100).to_csv(SAMPLE_DIR / f"{name}_sample.csv", index=False)
    print(f"  {name}: {len(df):,} rows")


def main() -> None:
    print("Generating synthetic SaaS data...\n")

    print("1/4  dim_users")
    users = _generate_users()
    _save(users, "dim_users")

    print("2/4  fact_events (with funnel simulation)")
    events, reached = _simulate_funnel(users)

    print("3/4  fact_experiments (injecting treatment lift)")
    experiments, events = _generate_experiments(users, events, reached)
    _save(events, "fact_events")
    _save(experiments, "fact_experiments")

    print("4/4  fact_subscriptions (correlated with funnel)")
    subs = _generate_subscriptions(users, reached)
    _save(subs, "fact_subscriptions")

    print(f"\nDone. Raw data in {RAW_DIR}, samples in {SAMPLE_DIR}")


if __name__ == "__main__":
    main()
