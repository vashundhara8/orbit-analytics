"""Integration tests for Experimentation Intelligence API: hypothesis tests, SRM, and tenant isolation."""

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


def test_list_experiments_success(demo_token: str):
    headers = {"Authorization": f"Bearer {demo_token}"}
    response = client.get("/api/v1/experiments", headers=headers)
    assert response.status_code == 200

    experiments = response.json()
    assert len(experiments) >= 1
    names = [e["experiment_name"] for e in experiments]
    assert "onboarding_v2" in names


def test_get_experiment_analysis_onboarding_v2(demo_token: str):
    headers = {"Authorization": f"Bearer {demo_token}"}
    response = client.get("/api/v1/experiments/onboarding_v2", headers=headers)
    assert response.status_code == 200

    data = response.json()
    assert data["experiment_name"] == "onboarding_v2"
    assert data["tenant_id"] == settings.default_tenant_id

    # Verify variants
    variants = data["variants"]
    assert len(variants) == 2

    control = next(v for v in variants if v["variant"] == "control")
    treatment = next(v for v in variants if v["variant"] == "treatment")

    assert control["users"] == 10095
    assert control["activated_users"] == 6791
    assert control["activation_rate"] == 0.6727

    assert treatment["users"] == 9905
    assert treatment["activated_users"] == 6986
    assert treatment["activation_rate"] == 0.7053

    # Verify lift metrics
    lift = data["lift"]
    assert lift["absolute_lift_pp"] == 3.26
    assert abs(lift["relative_lift"] - 0.0484) < 0.005  # ~ +4.84%

    # 95% Confidence Interval for difference strictly excludes zero
    assert lift["ci95_difference_low_pp"] > 1.5
    assert lift["ci95_difference_high_pp"] < 5.0
    assert lift["ci95_difference_low_pp"] < lift["ci95_difference_high_pp"]

    # Significance test
    sig = data["significance"]
    assert sig["is_significant"] is True
    assert sig["z_statistic"] > 4.5
    assert sig["p_value"] < 0.001

    # SRM check passes (expected 50/50, actual 50.5% vs 49.5%, p ~ 0.179 >= 0.01)
    srm = data["srm"]
    assert srm["has_srm"] is False
    assert srm["p_value"] >= 0.01
    assert "Sample Ratio Mismatch check passed" in srm["interpretation"]


def test_unknown_experiment_empty_response(demo_token: str):
    headers = {"Authorization": f"Bearer {demo_token}"}
    response = client.get("/api/v1/experiments/nonexistent_experiment_xyz", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["variants"]) == 0
    assert data["lift"]["absolute_lift"] == 0.0


def test_unauthorized_experiments_access():
    response = client.get("/api/v1/experiments")
    assert response.status_code == 401


def test_tenant_isolation_experiments(acme_token: str):
    headers = {"Authorization": f"Bearer {acme_token}"}
    response = client.get("/api/v1/experiments/onboarding_v2", headers=headers)
    assert response.status_code == 200

    data = response.json()
    assert data["tenant_id"] == "org_acme_corp"
    assert len(data["variants"]) == 0
    assert data["lift"]["absolute_lift"] == 0.0
