"""Integration tests for Point-in-Time Churn Intelligence API, population boundaries, and tenant isolation."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.app.auth.models import AuthenticatedUser, UserRole
from backend.app.auth.security import create_access_token
from backend.app.config import settings
from backend.app.main import app
from backend.app.services.churn_service import ChurnService

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


def test_get_churn_summary_success(demo_token: str):
    headers = {"Authorization": f"Bearer {demo_token}"}
    response = client.get("/api/v1/churn/summary", headers=headers)
    assert response.status_code == 200

    data = response.json()
    assert data["tenant_id"] == settings.default_tenant_id
    assert "Active paying subscribers" in data["task_definition"]["scoring_population"]
    assert "15,648 accounts" in data["task_definition"]["scoring_population"]
    assert data["task_definition"]["feature_window_days"] == 30
    assert data["task_definition"]["prediction_window_days"] == 60

    # Verify out-of-sample performance metrics
    perf = data["performance"]
    assert 0.40 <= perf["roc_auc"] <= 0.60  # Evaluated without leakage on audited uniform synthetic target
    assert 0.05 <= perf["pr_auc"] <= 0.12   # Baseline churn prevalence ~ 7.0%
    assert 0.00 <= perf["brier_score"] <= 0.15
    assert perf["train_samples"] + perf["test_samples"] == 15648
    assert perf["train_samples"] == 12518
    assert perf["test_samples"] == 3130

    # Verify dummy baseline comparison
    assert perf["baseline_model_name"] == "Prior Dummy Baseline"
    assert perf["baseline_roc_auc"] == 0.50
    assert round(perf["baseline_pr_auc"], 2) == round(perf["baseline_prevalence"], 2)
    assert 0.05 <= perf["baseline_brier_score"] <= 0.08
    assert "80/20 Stratified" in perf["evaluation_strategy"]
    assert "calibration" in perf["calibration_assessment"].lower()

    # Verify coefficients
    coeffs = data["coefficients"]
    assert len(coeffs) == 5
    feat_names = {c["feature_name"] for c in coeffs}
    assert "days_since_last_event_at_cutoff" in feat_names
    assert "events_in_30d" in feat_names
    assert "distinct_events_in_30d" in feat_names
    assert "feature_used_count" in feat_names
    assert "export_count" in feat_names

    # Verify risk distribution
    dist = data["risk_distribution"]
    assert dist["total_scored"] == 15648
    assert dist["low_count"] + dist["medium_count"] + dist["high_count"] == 15648
    assert dist["high_count"] > 0
    assert dist["medium_count"] > 0
    assert dist["low_count"] > 0

    # Verify honest provenance notes
    assert "Audited Synthetic Data Provenance Disclosure" in data["data_provenance_notes"]


def test_get_churn_accounts_success(demo_token: str):
    headers = {"Authorization": f"Bearer {demo_token}"}
    response = client.get("/api/v1/churn/accounts?limit=15", headers=headers)
    assert response.status_code == 200

    data = response.json()
    assert data["tenant_id"] == settings.default_tenant_id
    assert len(data["accounts"]) == 15
    assert data["total_matching"] == 15648

    account = data["accounts"][0]
    assert "u_" in account["user_id"]
    assert 0.0 <= account["churn_probability"] <= 1.0
    assert account["risk_tier"] in ("high", "medium", "low")
    assert "Exploratory Review:" in account["recommended_action"]
    assert len(account["prediction_cutoff"]) > 0
    assert len(account["exploratory_review_suggestion"]) > 0


def test_churn_accounts_filtering(demo_token: str):
    headers = {"Authorization": f"Bearer {demo_token}"}
    response = client.get("/api/v1/churn/accounts?risk_tier=high&limit=10", headers=headers)
    assert response.status_code == 200

    data = response.json()
    assert len(data["accounts"]) <= 10
    for acc in data["accounts"]:
        assert acc["risk_tier"] == "high"


def test_unauthorized_churn_access():
    response = client.get("/api/v1/churn/summary")
    assert response.status_code == 401


def test_tenant_isolation_churn(acme_token: str):
    headers = {"Authorization": f"Bearer {acme_token}"}
    response = client.get("/api/v1/churn/summary", headers=headers)
    assert response.status_code == 200

    data = response.json()
    assert data["tenant_id"] == "org_acme_corp"
    assert data["performance"]["train_samples"] == 0
    assert data["risk_distribution"]["total_scored"] == 0
    assert data["performance"]["baseline_roc_auc"] == 0.50

    acc_res = client.get("/api/v1/churn/accounts", headers=headers)
    assert acc_res.status_code == 200
    assert acc_res.json()["total_matching"] == 0
    assert len(acc_res.json()["accounts"]) == 0


def test_churn_population_boundary_rules(monkeypatch, tmp_path: Path):
    """Regression test verifying the exact inclusion and label boundaries for Day-30 churn prediction.

    Rules verified:
    1. Cancellation before Day 30 (e.g. Day 15): EXCLUDED from eligible population.
    2. Cancellation exactly on Day 30: EXCLUDED from eligible population.
    3. Cancellation after Day 30 but within 60-day horizon (Day 31 - Day 90): INCLUDED, churn_target = 1.
    4. Cancellation after horizon (Day 91): INCLUDED, churn_target = 0.
    5. Active subscription with no cancellation (cancel_date is NULL): INCLUDED, churn_target = 0.
    6. Non-subscriber or missing paid_start_date: EXCLUDED from eligible population.
    """
    users_data = [
        {"user_id": "u_cancel_day15", "plan_type": "pro", "company_size": "11-50", "industry": "SaaS"},
        {"user_id": "u_cancel_day30", "plan_type": "pro", "company_size": "11-50", "industry": "SaaS"},
        {"user_id": "u_cancel_day31", "plan_type": "pro", "company_size": "11-50", "industry": "SaaS"},
        {"user_id": "u_cancel_day90", "plan_type": "pro", "company_size": "11-50", "industry": "SaaS"},
        {"user_id": "u_cancel_day91", "plan_type": "pro", "company_size": "11-50", "industry": "SaaS"},
        {"user_id": "u_active_null", "plan_type": "pro", "company_size": "11-50", "industry": "SaaS"},
        {"user_id": "u_free_user", "plan_type": "free", "company_size": "11-50", "industry": "SaaS"},
    ]

    base_date = pd.Timestamp("2024-01-01 00:00:00")
    subs_data = [
        # 1. Cancelled before Day 30 (Day 15) -> Excluded
        {"user_id": "u_cancel_day15", "paid_start_date": base_date, "cancel_date": base_date + pd.Timedelta(days=15), "mrr": 0.0},
        # 2. Cancelled exactly on Day 30 -> Excluded
        {"user_id": "u_cancel_day30", "paid_start_date": base_date, "cancel_date": base_date + pd.Timedelta(days=30), "mrr": 0.0},
        # 3. Cancelled Day 31 -> Included, target = 1
        {"user_id": "u_cancel_day31", "paid_start_date": base_date, "cancel_date": base_date + pd.Timedelta(days=31), "mrr": 0.0},
        # 4. Cancelled Day 90 -> Included, target = 1
        {"user_id": "u_cancel_day90", "paid_start_date": base_date, "cancel_date": base_date + pd.Timedelta(days=90), "mrr": 0.0},
        # 5. Cancelled Day 91 -> Included, target = 0
        {"user_id": "u_cancel_day91", "paid_start_date": base_date, "cancel_date": base_date + pd.Timedelta(days=91), "mrr": 0.0},
        # 6. Active (null cancel) -> Included, target = 0
        {"user_id": "u_active_null", "paid_start_date": base_date, "cancel_date": None, "mrr": 29.0},
        # 7. Free user -> Excluded
        {"user_id": "u_free_user", "paid_start_date": None, "cancel_date": None, "mrr": 0.0},
    ]

    events_data = [
        {"event_id": "e_1", "user_id": "u_cancel_day31", "event_name": "feature_used", "event_ts": base_date + pd.Timedelta(days=5)},
        {"event_id": "e_2", "user_id": "u_active_null", "event_name": "export", "event_ts": base_date + pd.Timedelta(days=10)},
    ]

    pd.DataFrame(users_data).to_parquet(tmp_path / "dim_users.parquet")
    pd.DataFrame(subs_data).to_parquet(tmp_path / "fact_subscriptions.parquet")
    pd.DataFrame(events_data).to_parquet(tmp_path / "fact_events.parquet")

    service = ChurnService(tenant_id="test_tenant", org_name="Test Org")
    monkeypatch.setattr(service, "tenant_raw_dir", tmp_path)

    df = service._extract_point_in_time_dataset()
    user_ids = set(df["user_id"].tolist())

    # Verify exclusions:
    assert "u_cancel_day15" not in user_ids, "Users cancelled before Day 30 must be excluded from Day 30 population"
    assert "u_cancel_day30" not in user_ids, "Users cancelled exactly on Day 30 must be excluded from Day 30 population"
    assert "u_free_user" not in user_ids, "Free users without paid_start_date must be excluded"

    # Verify inclusions:
    assert "u_cancel_day31" in user_ids
    assert "u_cancel_day90" in user_ids
    assert "u_cancel_day91" in user_ids
    assert "u_active_null" in user_ids
    assert len(user_ids) == 4

    # Verify targets:
    user_target = df.set_index("user_id")["churn_target"].to_dict()
    assert user_target["u_cancel_day31"] == 1, "Cancelled between Day 30 and Day 90 must have churn_target = 1"
    assert user_target["u_cancel_day90"] == 1, "Cancelled on Day 90 boundary must have churn_target = 1"
    assert user_target["u_cancel_day91"] == 0, "Cancelled after Day 90 must have churn_target = 0"
    assert user_target["u_active_null"] == 0, "Active non-cancelled user must have churn_target = 0"
