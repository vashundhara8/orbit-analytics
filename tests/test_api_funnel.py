"""Integration tests for Orbit Analysis FastAPI backend: Health, Auth, Funnel, and Tenant Isolation."""

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


# ── Health Checks ─────────────────────────────────────────────────────────────


def test_health_check_endpoints():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app_name"] == settings.app_name

    v1_response = client.get("/api/v1/health")
    assert v1_response.status_code == 200
    assert v1_response.json()["status"] == "ok"


# ── Authentication & Token Flow ───────────────────────────────────────────────


def test_demo_token_endpoint():
    response = client.get("/api/v1/auth/demo-token")
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["tenant_id"] == settings.default_tenant_id


def test_login_token_endpoint_success():
    payload = {
        "email": "analyst@orbitanalytics.io",
        "password": "any_password",
        "tenant_id": settings.default_tenant_id,
    }
    response = client.post("/api/v1/auth/token", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["email"] == "analyst@orbitanalytics.io"
    assert data["user"]["tenant_id"] == settings.default_tenant_id


def test_login_cross_tenant_rejection():
    # User belongs to Acme Corp but attempts to request Orbit Demo tenant token
    payload = {
        "email": "analyst@acme.com",
        "password": "any_password",
        "tenant_id": settings.default_tenant_id,
    }
    response = client.post("/api/v1/auth/token", json=payload)
    assert response.status_code == 403
    assert "Cross-tenant access denied" in response.json()["detail"]


# ── Funnel Analytics API ──────────────────────────────────────────────────────


def test_get_funnel_success(demo_token: str):
    headers = {"Authorization": f"Bearer {demo_token}"}
    response = client.get("/api/v1/funnel", headers=headers)
    assert response.status_code == 200

    data = response.json()
    assert data["tenant_id"] == settings.default_tenant_id
    assert data["cohort_size"] == 100000
    assert data["overall_conversion_rate"] == 0.1567

    stages = data["stages"]
    assert len(stages) == 5

    stage_names = [s["step_id"] for s in stages]
    assert stage_names == ["signup", "workspace", "invite", "project", "paid"]

    # Verify verified audited metrics
    assert stages[0]["entering_users"] == 100000
    assert stages[0]["step_conversion_rate"] == 1.0

    assert stages[1]["entering_users"] == 72426
    assert stages[1]["step_conversion_rate"] == 0.7243
    assert stages[1]["drop_off_rate"] == 0.2757
    assert stages[1]["users_lost"] == 27574

    assert stages[2]["entering_users"] == 48353
    assert stages[2]["step_conversion_rate"] == 0.6676

    assert stages[3]["entering_users"] == 33264
    assert stages[3]["step_conversion_rate"] == 0.6879

    assert stages[4]["entering_users"] == 15674
    assert stages[4]["step_conversion_rate"] == 0.4712

    # Verify channel benchmarks
    benchmarks = data["channel_benchmarks"]
    assert len(benchmarks) == 4
    channels = {b["channel"] for b in benchmarks}
    assert channels == {"organic", "paid_search", "referral", "partner"}


def test_funnel_channel_filter(demo_token: str):
    headers = {"Authorization": f"Bearer {demo_token}"}
    response = client.get("/api/v1/funnel?acquisition_channel=organic", headers=headers)
    assert response.status_code == 200

    data = response.json()
    assert data["cohort_size"] == 39909
    assert data["filter_applied"]["acquisition_channel"] == "organic"
    assert data["stages"][0]["entering_users"] == 39909
    assert data["stages"][4]["entering_users"] == 6240


def test_funnel_date_range_filter(demo_token: str):
    headers = {"Authorization": f"Bearer {demo_token}"}
    response = client.get(
        "/api/v1/funnel?start_date=2024-01-01&end_date=2024-06-30",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["filter_applied"]["start_date"] == "2024-01-01"
    assert data["filter_applied"]["end_date"] == "2024-06-30"
    assert data["cohort_size"] > 0
    assert len(data["stages"]) == 5


def test_funnel_invalid_date_range(demo_token: str):
    headers = {"Authorization": f"Bearer {demo_token}"}
    # start_date > end_date must fail validation with 422
    response = client.get(
        "/api/v1/funnel?start_date=2025-06-30&end_date=2024-01-01",
        headers=headers,
    )
    assert response.status_code == 422


# ── Tenant Isolation Negative Tests ───────────────────────────────────────────


def test_unauthorized_funnel_access():
    # Request without Authorization header must be rejected
    response = client.get("/api/v1/funnel")
    assert response.status_code == 401
    assert "Bearer token required" in response.json()["detail"]


def test_invalid_token_funnel_access():
    # Request with malformed or tampered token must be rejected
    headers = {"Authorization": "Bearer bad_signature_token_12345"}
    response = client.get("/api/v1/funnel", headers=headers)
    assert response.status_code == 401


def test_tenant_isolation_boundary(acme_token: str):
    # Acme Corp user requests funnel - must receive Acme's isolated space, not Orbit Demo's 100k users
    headers = {"Authorization": f"Bearer {acme_token}"}
    response = client.get("/api/v1/funnel", headers=headers)
    assert response.status_code == 200

    data = response.json()
    assert data["tenant_id"] == "org_acme_corp"
    assert data["organization_name"] == "Acme Technologies Inc."
    # Since Acme Corp has no data provisioned, cohort_size must be 0 (isolated empty state),
    # proving Orbit Demo data is NEVER leaked across tenant boundaries!
    assert data["cohort_size"] == 0
    assert data["stages"][0]["entering_users"] == 0
