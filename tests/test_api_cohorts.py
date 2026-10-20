"""Integration tests for Cohort Retention API: metrics, maturity masking, and tenant isolation."""

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


def test_get_cohort_retention_success(demo_token: str):
    headers = {"Authorization": f"Bearer {demo_token}"}
    response = client.get("/api/v1/cohorts", headers=headers)
    assert response.status_code == 200

    data = response.json()
    assert data["tenant_id"] == settings.default_tenant_id
    assert data["max_weeks_horizon"] == 12
    assert data["num_cohorts_returned"] > 0
    assert len(data["cohorts"]) == data["num_cohorts_returned"]

    # Verify first cohort structure
    first_cohort = data["cohorts"][0]
    assert "cohort_week" in first_cohort
    assert first_cohort["cohort_size"] >= 500
    assert len(first_cohort["cells"]) == 13  # W0 through W12

    w0_cell = first_cohort["cells"][0]
    assert w0_cell["weeks_since_signup"] == 0
    assert w0_cell["active_users"] is not None
    assert 0.0 < w0_cell["retention_rate"] <= 1.0

    # Verify milestone averages
    milestones = data["milestones"]
    assert milestones["w1_retention_avg"] is not None
    assert 0.0 < milestones["w1_retention_avg"] <= 1.0
    assert milestones["w4_retention_avg"] is not None
    assert 0.0 < milestones["w4_retention_avg"] <= 1.0
    assert milestones["w8_retention_avg"] is not None
    assert milestones["w12_retention_avg"] is not None


def test_cohort_retention_horizon_filtering(demo_token: str):
    headers = {"Authorization": f"Bearer {demo_token}"}
    response = client.get("/api/v1/cohorts?max_weeks=4&num_cohorts=5", headers=headers)
    assert response.status_code == 200

    data = response.json()
    assert data["max_weeks_horizon"] == 4
    assert data["num_cohorts_returned"] == 5
    for cohort in data["cohorts"]:
        assert len(cohort["cells"]) == 5  # W0 through W4


def test_cohort_retention_invalid_params(demo_token: str):
    headers = {"Authorization": f"Bearer {demo_token}"}
    # num_cohorts out of bounds (< 1)
    response = client.get("/api/v1/cohorts?num_cohorts=0", headers=headers)
    assert response.status_code == 422


def test_unauthorized_cohorts_access():
    response = client.get("/api/v1/cohorts")
    assert response.status_code == 401


def test_tenant_isolation_cohorts(acme_token: str):
    headers = {"Authorization": f"Bearer {acme_token}"}
    response = client.get("/api/v1/cohorts", headers=headers)
    assert response.status_code == 200

    data = response.json()
    assert data["tenant_id"] == "org_acme_corp"
    assert data["num_cohorts_returned"] == 0
    assert len(data["cohorts"]) == 0
    assert data["milestones"]["w1_retention_avg"] is None
