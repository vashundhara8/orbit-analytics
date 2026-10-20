"""Churn intelligence endpoints enforcing server-side tenant isolation."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from backend.app.auth.dependencies import get_current_tenant
from backend.app.auth.models import TenantContext
from backend.app.schemas.churn import ChurnAccountsResponse, ChurnSummaryResponse
from backend.app.services.churn_service import ChurnService

router = APIRouter(prefix="/churn", tags=["Churn Intelligence"])


@router.get("/summary", response_model=ChurnSummaryResponse, summary="Get Point-in-Time Churn Model Summary & Calibration")
async def get_churn_summary(
    tenant: Annotated[TenantContext, Depends(get_current_tenant)],
) -> ChurnSummaryResponse:
    """Retrieve point-in-time prediction task definition, out-of-sample metrics, coefficients, and risk tiers.

    Enforces server-side tenant isolation: model evaluation is strictly scoped
    to the authenticated tenant's data domain.
    """
    service = ChurnService(tenant_id=tenant.tenant_id, org_name=tenant.organization_name)
    return service.get_churn_summary()


@router.get("/accounts", response_model=ChurnAccountsResponse, summary="Get Prioritized At-Risk Accounts for Retention Outreach")
async def get_at_risk_accounts(
    tenant: Annotated[TenantContext, Depends(get_current_tenant)],
    risk_tier: Annotated[str | None, Query(description="Filter by risk tier: high, medium, low")] = None,
    industry: Annotated[str | None, Query(description="Filter by industry")] = None,
    plan_type: Annotated[str | None, Query(description="Filter by plan: pro, enterprise")] = None,
    limit: Annotated[int, Query(ge=1, le=500, description="Maximum number of accounts to return")] = 50,
) -> ChurnAccountsResponse:
    """Retrieve scored customer accounts sorted by predicted churn probability and days of inactivity.

    Enforces server-side tenant isolation: accounts returned belong strictly to the authenticated tenant.
    """
    service = ChurnService(tenant_id=tenant.tenant_id, org_name=tenant.organization_name)
    return service.get_at_risk_accounts(
        risk_tier=risk_tier,
        industry=industry,
        plan_type=plan_type,
        limit=limit,
    )
