"""Funnel analytics endpoints enforcing tenant-isolated analytical queries."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from backend.app.auth.dependencies import get_current_tenant
from backend.app.auth.models import TenantContext
from backend.app.schemas.funnel import FunnelAnalysisResponse, FunnelFilterParams
from backend.app.services.funnel_service import FunnelService

router = APIRouter(prefix="/funnel", tags=["Funnel Analytics"])


@router.get("", response_model=FunnelAnalysisResponse, summary="Get Five-Stage Conversion Funnel")
async def get_funnel_analytics(
    filters: Annotated[FunnelFilterParams, Query()],
    tenant: Annotated[TenantContext, Depends(get_current_tenant)],
) -> FunnelAnalysisResponse:
    """Retrieve the five-stage conversion funnel and acquisition benchmarks.

    Enforces server-side tenant isolation: analytical queries are strictly scoped
    to the authenticated tenant's data domain.
    """
    service = FunnelService(tenant_id=tenant.tenant_id, org_name=tenant.organization_name)
    return service.get_funnel_metrics(filters)
