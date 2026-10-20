"""FastAPI dependencies for authentication and tenant isolation enforcement."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from backend.app.auth.models import AuthenticatedUser, TenantContext, UserRole
from backend.app.auth.security import verify_access_token
from backend.app.config import settings

# Pre-registered tenant catalog for multi-tenant simulation / operational validation
TENANT_REGISTRY: dict[str, dict[str, str]] = {
    settings.default_tenant_id: {
        "name": settings.default_tenant_name,
        "status": "active",
    },
    "org_acme_corp": {
        "name": "Acme Technologies Inc.",
        "status": "active",
    },
    "org_starlight_saas": {
        "name": "Starlight Cloud SaaS",
        "status": "active",
    },
}

DEMO_USERS: dict[str, AuthenticatedUser] = {
    "analyst@orbitanalytics.io": AuthenticatedUser(
        user_id="usr_orbit_01",
        email="analyst@orbitanalytics.io",
        tenant_id=settings.default_tenant_id,
        role=UserRole.ANALYST,
        organization_name=settings.default_tenant_name,
    ),
    "analyst@acme.com": AuthenticatedUser(
        user_id="usr_acme_01",
        email="analyst@acme.com",
        tenant_id="org_acme_corp",
        role=UserRole.ANALYST,
        organization_name="Acme Technologies Inc.",
    ),
    "analyst@starlight.io": AuthenticatedUser(
        user_id="usr_starlight_01",
        email="analyst@starlight.io",
        tenant_id="org_starlight_saas",
        role=UserRole.ANALYST,
        organization_name="Starlight Cloud SaaS",
    ),
}


async def get_current_user(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> AuthenticatedUser:
    """Extract and authenticate the user from Authorization Bearer header.

    Rejects requests with missing, malformed, or expired credentials.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header. Bearer token required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization format. Expected 'Bearer <token>'.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1]
    token_data = verify_access_token(token)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid, expired, or tampered access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return AuthenticatedUser(
        user_id=token_data.sub,
        email=token_data.email,
        tenant_id=token_data.tenant_id,
        role=token_data.role,
        organization_name=token_data.org_name,
    )


async def get_current_tenant(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> TenantContext:
    """Enforce tenant context derived server-side from verified user credentials.

    Ensures that active tenant boundaries cannot be spoofed by client headers or query params.
    """
    tenant_info = TENANT_REGISTRY.get(current_user.tenant_id)
    if not tenant_info or tenant_info.get("status") != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Tenant '{current_user.tenant_id}' is inactive or does not exist.",
        )

    return TenantContext(
        tenant_id=current_user.tenant_id,
        organization_name=tenant_info["name"],
        is_active=True,
    )
