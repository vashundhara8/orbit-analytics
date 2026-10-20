"""Authentication and authorization models."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class UserRole(StrEnum):
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"


class TenantContext(BaseModel):
    tenant_id: str
    organization_name: str
    is_active: bool = True


class AuthenticatedUser(BaseModel):
    user_id: str
    email: str
    tenant_id: str
    role: UserRole
    organization_name: str


class TokenData(BaseModel):
    sub: str  # user_id
    email: str
    tenant_id: str
    role: UserRole
    org_name: str
    exp: int


class LoginRequest(BaseModel):
    email: str = Field(..., examples=["analyst@orbitanalytics.io"])
    password: str = Field(..., examples=["demo_secret"])
    tenant_id: str | None = Field(None, examples=["org_orbit_demo"])


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthenticatedUser
