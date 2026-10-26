"""Security test suite for Orbit Analysis API.

Verifies:
- Unauthenticated access rejection (401)
- Forged, tampered, and malformed JWT rejection (401)
- Expired and invalid timestamp JWT rejection (401)
- Role-based access control (RBAC) enforcement (403)
- Cross-tenant access and tenant identity spoofing prevention (403)
- Demo token restrictions and environment toggles (403)
- Production configuration validation and startup failure enforcement
- Security response headers
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time

import pytest
from fastapi.testclient import TestClient

from backend.app.auth.models import AuthenticatedUser, UserRole
from backend.app.auth.security import _base64url_encode, create_access_token
from backend.app.config import DEV_DEFAULT_SECRET, Settings, settings
from backend.app.main import app

client = TestClient(app)


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def viewer_token() -> str:
    user = AuthenticatedUser(
        user_id="usr_viewer_01",
        email="viewer@orbitanalytics.io",
        tenant_id=settings.default_tenant_id,
        role=UserRole.VIEWER,
        organization_name=settings.default_tenant_name,
    )
    return create_access_token(user)


@pytest.fixture
def analyst_token() -> str:
    user = AuthenticatedUser(
        user_id="usr_analyst_01",
        email="analyst@orbitanalytics.io",
        tenant_id=settings.default_tenant_id,
        role=UserRole.ANALYST,
        organization_name=settings.default_tenant_name,
    )
    return create_access_token(user)


@pytest.fixture
def admin_token() -> str:
    user = AuthenticatedUser(
        user_id="usr_admin_01",
        email="admin@orbitanalytics.io",
        tenant_id=settings.default_tenant_id,
        role=UserRole.ADMIN,
        organization_name=settings.default_tenant_name,
    )
    return create_access_token(user)


# ── 1. Unauthenticated Access Tests ──────────────────────────────────────────


@pytest.mark.parametrize(
    "method,endpoint",
    [
        ("GET", "/api/v1/funnel"),
        ("GET", "/api/v1/cohorts"),
        ("GET", "/api/v1/experiments"),
        ("GET", "/api/v1/experiments/onboarding_v2"),
        ("GET", "/api/v1/experiments/onboarding_v2/revenue"),
        ("GET", "/api/v1/churn/summary"),
        ("GET", "/api/v1/churn/accounts"),
        ("GET", "/api/v1/onboarding/status"),
        ("POST", "/api/v1/onboarding/upload"),
    ],
)
def test_endpoints_reject_unauthenticated_requests(method: str, endpoint: str):
    """Verify that all sensitive endpoints return 401 Unauthorized when Authorization header is absent."""
    response = client.get(endpoint) if method == "GET" else client.post(endpoint)

    assert response.status_code == 401
    assert "Authorization header" in response.json()["detail"]


@pytest.mark.parametrize(
    "invalid_header",
    [
        "Basic dXNlcjpwYXNz",
        "Token some_random_token",
        "Bearer",
        "Bearer token_part_one token_part_two",
        "Bearer12345",
    ],
)
def test_endpoints_reject_malformed_authorization_headers(invalid_header: str):
    """Verify rejection of improperly structured Authorization headers."""
    response = client.get("/api/v1/funnel", headers={"Authorization": invalid_header})
    assert response.status_code == 401
    assert "Invalid authorization format" in response.json()["detail"]


# ── 2. Forged, Tampered, and Malformed Token Tests ────────────────────────────


def test_reject_token_signed_with_wrong_secret():
    """Verify rejection of a JWT signed by an untrusted or forged secret."""
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    payload = {
        "sub": "attacker",
        "email": "attacker@evil.com",
        "tenant_id": settings.default_tenant_id,
        "role": "admin",
        "org_name": settings.default_tenant_name,
        "iat": now,
        "exp": now + 3600,
    }
    enc_h = _base64url_encode(json.dumps(header).encode())
    enc_p = _base64url_encode(json.dumps(payload).encode())
    forged_input = f"{enc_h}.{enc_p}".encode()

    # Sign with attacker's secret
    forged_sig = _base64url_encode(
        hmac.new(b"attacker_malicious_secret_key_1234", forged_input, hashlib.sha256).digest()
    )
    forged_token = f"{enc_h}.{enc_p}.{forged_sig}"

    response = client.get("/api/v1/funnel", headers={"Authorization": f"Bearer {forged_token}"})
    assert response.status_code == 401
    assert "Invalid, expired, or tampered" in response.json()["detail"]


def test_reject_tampered_payload_claims():
    """Verify that tampering with any character in payload invalidates HMAC signature."""
    user = AuthenticatedUser(
        user_id="usr_analyst_01",
        email="analyst@orbitanalytics.io",
        tenant_id=settings.default_tenant_id,
        role=UserRole.ANALYST,
        organization_name=settings.default_tenant_name,
    )
    valid_token = create_access_token(user)
    parts = valid_token.split(".")

    # Tamper payload by altering a single character
    tampered_payload = parts[1][:-1] + ("A" if parts[1][-1] != "A" else "B")
    tampered_token = f"{parts[0]}.{tampered_payload}.{parts[2]}"

    response = client.get("/api/v1/funnel", headers={"Authorization": f"Bearer {tampered_token}"})
    assert response.status_code == 401
    assert "Invalid, expired, or tampered" in response.json()["detail"]


def test_reject_algorithm_none_and_unsupported_algorithms():
    """Verify algorithm confusion guard: 'none' and asymmetric algorithms are rejected."""
    for bad_alg in ("none", "HS512", "RS256", "ES256"):
        header = {"alg": bad_alg, "typ": "JWT"}
        now = int(time.time())
        payload = {
            "sub": "attacker",
            "email": "attacker@evil.com",
            "tenant_id": settings.default_tenant_id,
            "role": "analyst",
            "exp": now + 3600,
        }
        enc_h = _base64url_encode(json.dumps(header).encode())
        enc_p = _base64url_encode(json.dumps(payload).encode())
        token = f"{enc_h}.{enc_p}." if bad_alg == "none" else f"{enc_h}.{enc_p}.invalidsig"

        response = client.get("/api/v1/funnel", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401


# ── 3. Expired & Clock Skew Token Tests ──────────────────────────────────────


def test_reject_expired_access_token():
    """Verify that expired tokens are immediately rejected."""
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    payload = {
        "sub": "usr_expired",
        "email": "expired@orbitanalytics.io",
        "tenant_id": settings.default_tenant_id,
        "role": "analyst",
        "org_name": settings.default_tenant_name,
        "iat": now - 7200,
        "exp": now - 3600,  # Expired 1 hour ago
    }
    enc_h = _base64url_encode(json.dumps(header).encode())
    enc_p = _base64url_encode(json.dumps(payload).encode())
    signing_input = f"{enc_h}.{enc_p}".encode()
    sig = _base64url_encode(
        hmac.new(settings.secret_key.encode(), signing_input, hashlib.sha256).digest()
    )
    expired_token = f"{enc_h}.{enc_p}.{sig}"

    response = client.get("/api/v1/funnel", headers={"Authorization": f"Bearer {expired_token}"})
    assert response.status_code == 401
    assert "Invalid, expired, or tampered" in response.json()["detail"]


def test_reject_far_future_dated_iat_tokens():
    """Verify rejection of tokens issued far in the future (> 300s)."""
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    payload = {
        "sub": "usr_future",
        "email": "future@orbitanalytics.io",
        "tenant_id": settings.default_tenant_id,
        "role": "analyst",
        "org_name": settings.default_tenant_name,
        "iat": now + 600,  # 10 minutes in future
        "exp": now + 7200,
    }
    enc_h = _base64url_encode(json.dumps(header).encode())
    enc_p = _base64url_encode(json.dumps(payload).encode())
    signing_input = f"{enc_h}.{enc_p}".encode()
    sig = _base64url_encode(
        hmac.new(settings.secret_key.encode(), signing_input, hashlib.sha256).digest()
    )
    future_token = f"{enc_h}.{enc_p}.{sig}"

    response = client.get("/api/v1/funnel", headers={"Authorization": f"Bearer {future_token}"})
    assert response.status_code == 401


# ── 4. Role-Based Access Control (RBAC) Tests ────────────────────────────────


def test_viewer_role_forbidden_from_customer_data_upload(viewer_token: str):
    """Verify that VIEWER role is rejected with 403 Forbidden on data ingestion."""
    csv_payload = b"user_id,event_name,event_timestamp\nu1,signup,2025-01-01 10:00:00\n"
    response = client.post(
        "/api/v1/onboarding/upload",
        files={"file": ("data.csv", csv_payload, "text/csv")},
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 403
    assert "not authorized" in response.json()["detail"].lower()


def test_analyst_and_admin_roles_permitted_to_upload(analyst_token: str, admin_token: str):
    """Verify that ANALYST and ADMIN roles can access data ingestion."""
    csv_payload = (
        b"user_id,event_name,event_timestamp,acquisition_channel\n"
        b"u1,signup,2025-01-01 10:00:00,Organic\n"
        b"u1,workspace_created,2025-01-01 10:15:00,Organic\n"
        b"u1,invite_sent,2025-01-02 09:30:00,Organic\n"
        b"u1,first_project,2025-01-03 14:00:00,Organic\n"
        b"u1,paid,2025-01-05 16:45:00,Organic\n"
    )

    # Analyst role succeeds
    res_analyst = client.post(
        "/api/v1/onboarding/upload",
        files={"file": ("analyst_data.csv", csv_payload, "text/csv")},
        headers={"Authorization": f"Bearer {analyst_token}"},
    )
    assert res_analyst.status_code == 200
    assert res_analyst.json()["status"] in ("success", "warning")

    # Admin role succeeds
    res_admin = client.post(
        "/api/v1/onboarding/upload",
        files={"file": ("admin_data.csv", csv_payload, "text/csv")},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res_admin.status_code == 200
    assert res_admin.json()["status"] in ("success", "warning")


# ── 5. Cross-Tenant Access & Isolation Boundary Tests ────────────────────────


def test_reject_tokens_for_inactive_or_nonexistent_tenants():
    """Verify that tokens referencing unregistered tenants are rejected with 403 Forbidden."""
    user = AuthenticatedUser(
        user_id="usr_ghost",
        email="ghost@phantom.io",
        tenant_id="org_nonexistent_ghost_corp",
        role=UserRole.ANALYST,
        organization_name="Phantom Corp",
    )
    ghost_token = create_access_token(user)

    response = client.get("/api/v1/funnel", headers={"Authorization": f"Bearer {ghost_token}"})
    assert response.status_code == 403
    assert "inactive or does not exist" in response.json()["detail"]


def test_login_endpoint_rejects_cross_tenant_spoofing():
    """Verify that a user from org_acme_corp cannot login claiming org_orbit_demo."""
    response = client.post(
        "/api/v1/auth/token",
        json={
            "email": "analyst@acme.com",
            "password": "any_password",
            "tenant_id": settings.default_tenant_id,  # Attempting to access Orbit Demo
        },
    )
    assert response.status_code == 403
    assert "Cross-tenant access denied" in response.json()["detail"]


# ── 6. Demo Token Restrictions ───────────────────────────────────────────────


def test_demo_token_rejects_arbitrary_unapproved_tenant():
    """Verify that /demo-token rejects arbitrary tenant IDs."""
    response = client.get("/api/v1/auth/demo-token?tenant_id=org_malicious_attacker")
    assert response.status_code == 403
    assert "arbitrary tenant" in response.json()["detail"]


def test_demo_token_never_grants_admin_role():
    """Verify that demo token always issues unprivileged ANALYST role, never ADMIN."""
    response = client.get("/api/v1/auth/demo-token?tenant_id=org_orbit_demo")
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["role"] == "analyst"
    assert data["user"]["role"] != "admin"


# ── 7. Production Configuration Failures ──────────────────────────────────────


def test_production_startup_fails_with_default_secret():
    """Verify that Settings validation fails startup when production uses dev default secret."""
    with pytest.raises(ValueError, match="CRITICAL SECURITY CONFIGURATION FAILURE"):
        Settings(
            environment="production",
            secret_key=DEV_DEFAULT_SECRET,
        )


def test_production_startup_fails_with_short_secret():
    """Verify that Settings validation fails startup when production secret is < 32 characters."""
    with pytest.raises(ValueError, match="CRITICAL SECURITY CONFIGURATION FAILURE"):
        Settings(
            environment="production",
            secret_key="short_secret_under_32_chars",
        )


def test_production_startup_succeeds_with_strong_secret():
    """Verify that Settings validation succeeds in production with a 32+ char strong secret."""
    prod_settings = Settings(
        environment="production",
        secret_key="a" * 32,
    )
    assert prod_settings.environment == "production"
    assert prod_settings.enable_demo_auth is False  # Automatically disabled in production


# ── 8. Security Response Headers ─────────────────────────────────────────────


def test_security_headers_present_on_all_responses():
    """Verify defensive HTTP security headers are returned on all API responses."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "geolocation=()" in response.headers.get("Permissions-Policy", "")
