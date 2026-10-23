"""Integration and unit tests for Downstream Experiment Revenue Intelligence API.

Validates:
- Intention-To-Treat (ITT) eligible experiment population and denominators.
- 35-day post-assignment paid conversion observation window.
- Active Snapshot MRR from Experiment Cohort and Welch's two-sample t-test for ARPU.
- Post-conversion churn rates and cancelled subscription handling.
- Trial-eligible subpopulation secondary breakdown.
- Sample Ratio Mismatch (SRM) and data quality diagnostics.
- Duplicate assignment deduplication invariance.
- Date boundary enforcement (late conversions excluded from 35-day window).
- Missing subscription records handling ($0 revenue, non-converted).
- Strict server-enforced tenant isolation boundaries.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.app.auth.models import AuthenticatedUser, UserRole
from backend.app.auth.security import create_access_token
from backend.app.config import settings
from backend.app.main import app
from backend.app.services.experiment_service import ExperimentService

client = TestClient(app)


@pytest.fixture
def demo_token() -> str:
    user = AuthenticatedUser(
        user_id="usr_test_analyst",
        email="analyst@orbitanalytics.io",
        tenant_id=settings.default_tenant_id,
        role=UserRole.ANALYST,
        organization_name=settings.default_tenant_name,
    )
    return create_access_token(user)


@pytest.fixture
def acme_token() -> str:
    user = AuthenticatedUser(
        user_id="usr_acme_analyst",
        email="analyst@acme.com",
        tenant_id="org_acme_corp",
        role=UserRole.ANALYST,
        organization_name="Acme Technologies Inc.",
    )
    return create_access_token(user)


def test_get_experiment_revenue_analysis_onboarding_v2(demo_token: str):
    """Verify production revenue intelligence metrics on onboarding_v2 experiment."""
    headers = {"Authorization": f"Bearer {demo_token}"}
    response = client.get("/api/v1/experiments/onboarding_v2/revenue", headers=headers)
    assert response.status_code == 200

    data = response.json()
    assert data["tenant_id"] == settings.default_tenant_id
    assert data["experiment_name"] == "onboarding_v2"
    assert data["observation_window_days"] == 35
    assert "Intention-To-Treat" in data["evaluated_population"]

    # Verify variants
    variants = data["variants"]
    assert len(variants) == 2

    control = next(v for v in variants if v["variant"] == "control")
    treatment = next(v for v in variants if v["variant"] == "treatment")

    # Sample sizes & denominators
    assert control["assigned_users"] == 10095
    assert treatment["assigned_users"] == 9905

    # Paid conversions within 35-day window
    assert control["paid_conversions"] == 644
    assert treatment["paid_conversions"] == 634
    assert control["paid_conversion_rate"] == 0.0638
    assert treatment["paid_conversion_rate"] == 0.0640

    # 95% Wald CI for conversion rates
    assert control["ci95_conversion_low"] < control["paid_conversion_rate"] < control["ci95_conversion_high"]
    assert treatment["ci95_conversion_low"] < treatment["paid_conversion_rate"] < treatment["ci95_conversion_high"]

    # Active vs Churned subscribers
    assert control["active_subscribers"] == 533
    assert control["churned_subscribers"] == 111
    assert control["active_subscribers"] + control["churned_subscribers"] == 644
    assert control["post_conversion_churn_rate"] == 0.1724

    assert treatment["active_subscribers"] == 518
    assert treatment["churned_subscribers"] == 116
    assert treatment["active_subscribers"] + treatment["churned_subscribers"] == 634
    assert treatment["post_conversion_churn_rate"] == 0.1830

    # Active Snapshot MRR from Experiment Cohort & ARPU
    assert "Active Snapshot MRR from Experiment Cohort" in data["primary_metric"]
    assert control["total_mrr"] == 15457.0
    assert treatment["total_mrr"] == 15022.0
    assert control["arpu"] == 1.5312
    assert treatment["arpu"] == 1.5166
    assert control["arppu"] == 24.00
    assert treatment["arppu"] == 23.69

    # Lift metrics: conversion lift is neutral (+0.02 pp)
    lift = data["lift"]
    assert lift["absolute_conversion_lift_pp"] == 0.02
    assert lift["arpu_diff"] == -0.0146
    assert lift["ci95_conversion_diff_low_pp"] < 0 < lift["ci95_conversion_diff_high_pp"]
    assert lift["ci95_arpu_diff_low"] < 0 < lift["ci95_arpu_diff_high"]

    # Statistical significance: null hypothesis retained
    sig = data["significance"]
    assert sig["conversion_is_significant"] is False
    assert 0.05 < sig["conversion_z_stat"] < 0.10
    assert sig["conversion_p_value"] > 0.90  # p ~ 0.95
    assert sig["arpu_is_significant"] is False
    assert sig["arpu_p_value"] > 0.80  # p ~ 0.87

    # Trial subpopulation secondary breakdown
    trial = data["trial_subpopulation"]
    assert trial["control_trial_users"] == 5413
    assert trial["control_trial_conversions"] == 644
    assert trial["control_trial_conversion_rate"] == 0.1190
    assert trial["treatment_trial_users"] == 5358
    assert trial["treatment_trial_conversions"] == 634
    assert trial["treatment_trial_conversion_rate"] == 0.1183
    assert trial["trial_conversion_is_significant"] is False

    # Diagnostics
    diag = data["diagnostics"]
    assert diag["has_srm"] is False
    assert diag["srm_p_value"] >= 0.01
    assert diag["duplicate_assignments_detected"] == 0
    assert diag["missing_subscription_records"] == 0
    assert diag["pre_assignment_conversions_detected"] == 0
    assert diag["observation_window_complete"] is True

    # Honest commercial advisory & causality disclosure
    assert "NEUTRAL REVENUE IMPACT" in data["decision_advisory"]
    assert "Audited Monomer Linkage Disclosure" in data["causality_disclosure"]


def test_experiment_revenue_tenant_isolation(acme_token: str):
    """Verify tenant isolation: tenants without provisioned experiments receive empty isolated response."""
    headers = {"Authorization": f"Bearer {acme_token}"}
    response = client.get("/api/v1/experiments/onboarding_v2/revenue", headers=headers)
    assert response.status_code == 200

    data = response.json()
    assert data["tenant_id"] == "org_acme_corp"
    assert len(data["variants"]) == 0
    assert data["lift"]["absolute_conversion_lift"] == 0.0
    assert data["significance"]["conversion_is_significant"] is False
    assert "Workspace is empty" in data["decision_advisory"]


def test_experiment_revenue_unknown_experiment(demo_token: str):
    """Verify querying nonexistent experiment returns safe empty response without crashing."""
    headers = {"Authorization": f"Bearer {demo_token}"}
    response = client.get("/api/v1/experiments/nonexistent_exp_123/revenue", headers=headers)
    assert response.status_code == 200

    data = response.json()
    assert len(data["variants"]) == 0
    assert data["lift"]["absolute_conversion_lift"] == 0.0


def test_experiment_revenue_dedup_invariance(monkeypatch, tmp_path: Path):
    """Verify duplicate assignments for a single user are deduplicated to earliest timestamp."""
    exp_rows = [
        # User 1 assigned twice to control at different times
        {"user_id": "u1", "experiment_name": "test_dedup", "variant": "control", "assigned_ts": pd.Timestamp("2024-01-01 10:00:00")},
        {"user_id": "u1", "experiment_name": "test_dedup", "variant": "control", "assigned_ts": pd.Timestamp("2024-01-02 10:00:00")},
    ]
    # Add 9 more control users and 10 treatment users
    for i in range(2, 11):
        exp_rows.append({"user_id": f"uc_{i}", "experiment_name": "test_dedup", "variant": "control", "assigned_ts": pd.Timestamp("2024-01-01 10:00:00")})
    for i in range(1, 11):
        exp_rows.append({"user_id": f"ut_{i}", "experiment_name": "test_dedup", "variant": "treatment", "assigned_ts": pd.Timestamp("2024-01-01 10:00:00")})

    exp_df = pd.DataFrame(exp_rows)

    subs_rows = [
        {"user_id": "u1", "trial_start_date": pd.Timestamp("2024-01-01"), "paid_start_date": pd.Timestamp("2024-01-15"), "cancel_date": None, "mrr": 29},
    ]
    for i in range(2, 11):
        subs_rows.append({"user_id": f"uc_{i}", "trial_start_date": pd.Timestamp("2024-01-01"), "paid_start_date": None, "cancel_date": None, "mrr": 0})
    for i in range(1, 11):
        subs_rows.append({"user_id": f"ut_{i}", "trial_start_date": pd.Timestamp("2024-01-01"), "paid_start_date": pd.Timestamp("2024-01-15") if i == 1 else None, "cancel_date": None, "mrr": 29 if i == 1 else 0})

    subs_df = pd.DataFrame(subs_rows)
    users_df = pd.DataFrame([{"user_id": row["user_id"], "plan_type": "trial"} for row in exp_rows])

    exp_df.to_parquet(tmp_path / "fact_experiments.parquet")
    subs_df.to_parquet(tmp_path / "fact_subscriptions.parquet")
    users_df.to_parquet(tmp_path / "dim_users.parquet")

    svc = ExperimentService(tenant_id="test_tenant", org_name="Test Org")
    monkeypatch.setattr(svc, "tenant_raw_dir", tmp_path)

    res = svc.get_experiment_revenue_analysis("test_dedup")
    control = next(v for v in res.variants if v.variant == "control")
    # Control has 10 distinct users (u1 + uc_2..uc_10), despite u1 having 2 assignment rows
    assert control.assigned_users == 10
    assert control.paid_conversions == 1
    assert res.diagnostics.duplicate_assignments_detected == 1


def test_experiment_revenue_date_boundary_enforcement(monkeypatch, tmp_path: Path):
    """Verify conversions occurring after the 35-day post-assignment window are excluded."""
    exp_rows = []
    subs_rows = []
    users_rows = []

    for i in range(1, 11):
        exp_rows.append({"user_id": f"uc_{i}", "experiment_name": "test_window", "variant": "control", "assigned_ts": pd.Timestamp("2024-01-01 10:00:00")})
        # Control user 1 converts on day 20 (within 35 days) -> COUNTED
        paid_dt = pd.Timestamp("2024-01-21") if i == 1 else None
        subs_rows.append({"user_id": f"uc_{i}", "trial_start_date": pd.Timestamp("2024-01-01"), "paid_start_date": paid_dt, "cancel_date": None, "mrr": 29 if i == 1 else 0})
        users_rows.append({"user_id": f"uc_{i}", "plan_type": "trial"})

    for i in range(1, 11):
        exp_rows.append({"user_id": f"ut_{i}", "experiment_name": "test_window", "variant": "treatment", "assigned_ts": pd.Timestamp("2024-01-01 10:00:00")})
        # Treatment user 1 converts on day 40 (after 35 days) -> EXCLUDED from 35d window
        paid_dt = pd.Timestamp("2024-02-15") if i == 1 else None
        subs_rows.append({"user_id": f"ut_{i}", "trial_start_date": pd.Timestamp("2024-01-01"), "paid_start_date": paid_dt, "cancel_date": None, "mrr": 29 if i == 1 else 0})
        users_rows.append({"user_id": f"ut_{i}", "plan_type": "trial"})

    exp_df = pd.DataFrame(exp_rows)
    subs_df = pd.DataFrame(subs_rows)
    users_df = pd.DataFrame(users_rows)

    exp_df.to_parquet(tmp_path / "fact_experiments.parquet")
    subs_df.to_parquet(tmp_path / "fact_subscriptions.parquet")
    users_df.to_parquet(tmp_path / "dim_users.parquet")

    svc = ExperimentService(tenant_id="test_tenant", org_name="Test Org")
    monkeypatch.setattr(svc, "tenant_raw_dir", tmp_path)

    res = svc.get_experiment_revenue_analysis("test_window")
    control = next(v for v in res.variants if v.variant == "control")
    treatment = next(v for v in res.variants if v.variant == "treatment")

    assert control.paid_conversions == 1
    assert treatment.paid_conversions == 0


def test_experiment_revenue_missing_subscription_handling(monkeypatch, tmp_path: Path):
    """Verify users completely missing from subscriptions table are counted as non-conversions ($0 mrr)."""
    exp_rows = []
    users_rows = []
    for i in range(1, 11):
        exp_rows.append({"user_id": f"uc_{i}", "experiment_name": "test_missing", "variant": "control", "assigned_ts": pd.Timestamp("2024-01-01 10:00:00")})
        users_rows.append({"user_id": f"uc_{i}", "plan_type": "free"})
    for i in range(1, 11):
        exp_rows.append({"user_id": f"ut_{i}", "experiment_name": "test_missing", "variant": "treatment", "assigned_ts": pd.Timestamp("2024-01-01 10:00:00")})
        users_rows.append({"user_id": f"ut_{i}", "plan_type": "free"})

    exp_df = pd.DataFrame(exp_rows)
    # Empty subscriptions table -> all 20 users missing
    subs_df = pd.DataFrame(columns=["user_id", "trial_start_date", "paid_start_date", "cancel_date", "mrr"])
    users_df = pd.DataFrame(users_rows)

    exp_df.to_parquet(tmp_path / "fact_experiments.parquet")
    subs_df.to_parquet(tmp_path / "fact_subscriptions.parquet")
    users_df.to_parquet(tmp_path / "dim_users.parquet")

    svc = ExperimentService(tenant_id="test_tenant", org_name="Test Org")
    monkeypatch.setattr(svc, "tenant_raw_dir", tmp_path)

    res = svc.get_experiment_revenue_analysis("test_missing")
    assert res.variants[0].paid_conversions == 0
    assert res.variants[1].paid_conversions == 0
    assert res.variants[0].total_mrr == 0.0
    assert res.variants[1].total_mrr == 0.0
    assert res.diagnostics.missing_subscription_records == 20


def test_experiment_revenue_snapshot_mrr_semantics(demo_token: str):
    """Verify that total_mrr strictly reflects active snapshot MRR, not cumulative cash collected."""
    headers = {"Authorization": f"Bearer {demo_token}"}
    response = client.get("/api/v1/experiments/exp_onboarding_v2/revenue", headers=headers)
    assert response.status_code == 200

    data = response.json()
    assert "Active Snapshot MRR from Experiment Cohort" in data["primary_metric"]

    for variant in data["variants"]:
        # Each active subscriber pays $29/mo (standard Pro plan)
        expected_mrr = variant["active_subscribers"] * 29.0
        assert variant["total_mrr"] == expected_mrr
        # Churned subscribers converted to paid during the 35d window, but contribute $0 to snapshot MRR
        assert variant["churned_subscribers"] > 0
        assert variant["paid_conversions"] == variant["active_subscribers"] + variant["churned_subscribers"]
        # ARPU is based on active snapshot MRR divided by all ITT assigned users
        assert round(variant["total_mrr"] / variant["assigned_users"], 4) == round(variant["arpu"], 4)
        # ARPPU is based on active snapshot MRR divided by total paid conversions
        assert round(variant["total_mrr"] / variant["paid_conversions"], 2) == round(variant["arppu"], 2)

