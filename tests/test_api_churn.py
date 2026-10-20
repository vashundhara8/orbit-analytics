"""Integration tests for Point-in-Time Churn Intelligence API and tenant isolation."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app.auth.models import AuthenticatedUser, UserRole
from backend.app.auth.security import create_access_token
from backend.app.config import settings
from backend.app.main import app

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
    assert data["task_definition"]["feature_window_days"] == 30
    assert data["task_definition"]["prediction_window_days"] == 60

    # Verify out-of-sample performance metrics
    perf = data["performance"]
    assert 0.40 <= perf["roc_auc"] <= 0.60  # Evaluated without leakage on audited uniform synthetic target
    assert 0.05 <= perf["pr_auc"] <= 0.12   # Baseline churn prevalence ~ 7.0%
    assert 0.00 <= perf["brier_score"] <= 0.15
    assert perf["train_samples"] + perf["test_samples"] == 15674

    # Verify coefficients
    coeffs = data["coefficients"]
    assert len(coeffs) == 5
    feat_names = {c["feature_name"] for c in coeffs}
    assert "days_since_last_event_at_cutoff" in feat_names
    assert "events_in_30d" in feat_names

    # Verify risk distribution
    dist = data["risk_distribution"]
    assert dist["total_scored"] == 15674
    assert dist["low_count"] + dist["medium_count"] + dist["high_count"] == 15674
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
    assert data["total_matching"] == 15674

    account = data["accounts"][0]
    assert "u_" in account["user_id"]
    assert 0.0 <= account["churn_probability"] <= 1.0
    assert account["risk_tier"] in ("high", "medium", "low")
    assert len(account["recommended_action"]) > 0


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

    acc_res = client.get("/api/v1/churn/accounts", headers=headers)
    assert acc_res.status_code == 200
    assert acc_res.json()["total_matching"] == 0
    assert len(acc_res.json()["accounts"]) == 0
