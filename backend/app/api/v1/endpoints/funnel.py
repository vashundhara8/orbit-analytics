"""Funnel analytics endpoints enforcing tenant-isolated analytical queries."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

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


@router.get("/export", summary="Export Funnel Conversion Stages to CSV")
async def export_funnel_stages(
    filters: Annotated[FunnelFilterParams, Query()],
    tenant: Annotated[TenantContext, Depends(get_current_tenant)],
) -> Response:
    """Export funnel conversion stages as an authorized CSV download.

    Enforces server-side tenant isolation: exported stages represent exclusively
    the authenticated tenant's analytics partition.
    """
    service = FunnelService(tenant_id=tenant.tenant_id, org_name=tenant.organization_name)
    csv_data = service.export_funnel_csv(filters)
    filename = f"funnel_stages_{tenant.tenant_id}.csv"
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
