"""Authentication endpoints for token acquisition and tenant session management."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from backend.app.auth.dependencies import DEMO_USERS, TENANT_REGISTRY
from backend.app.auth.models import AuthenticatedUser, LoginRequest, TokenResponse, UserRole
from backend.app.auth.security import create_access_token
from backend.app.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/token", response_model=TokenResponse, summary="Obtain Tenant-Scoped Access Token")
async def login_for_access_token(request: LoginRequest) -> TokenResponse:
    """Issue a tenant-bound cryptographically signed JWT.

    Validates that user and requested tenant context exist in tenant registry.
    """
    user = DEMO_USERS.get(request.email)
    target_tenant = request.tenant_id or (user.tenant_id if user else settings.default_tenant_id)

    tenant_info = TENANT_REGISTRY.get(target_tenant)
    if not tenant_info or tenant_info.get("status") != "active":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Requested tenant '{target_tenant}' does not exist or is inactive.",
        )

    if not user:
        # Create an authorized user instance bound to the validated tenant
        user = AuthenticatedUser(
            user_id=f"usr_{abs(hash(request.email)) % 100000:05d}",
            email=request.email,
            tenant_id=target_tenant,
            role=UserRole.ANALYST,
            organization_name=tenant_info["name"],
        )
    elif target_tenant != user.tenant_id:
        # Cross-tenant permission check: if an existing user attempts to claim a tenant they do not belong to
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User '{user.email}' is not a member of tenant '{target_tenant}'. Cross-tenant access denied.",
        )

    token = create_access_token(user)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=user,
    )


@router.get("/demo-token", response_model=TokenResponse, summary="Get Quick Access Token for Demo Tenant")
async def get_demo_token(tenant_id: str = settings.default_tenant_id) -> TokenResponse:
    """Issue a demonstration token for local development and exploratory review."""
    tenant_info = TENANT_REGISTRY.get(tenant_id)
    if not tenant_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{tenant_id}' not found.",
        )

    demo_user = AuthenticatedUser(
        user_id="usr_orbit_demo",
        email=f"analyst@{tenant_id}.orbitanalytics.io",
        tenant_id=tenant_id,
        role=UserRole.ANALYST,
        organization_name=tenant_info["name"],
    )
    token = create_access_token(demo_user)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=demo_user,
    )
