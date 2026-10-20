"""Cohort retention endpoints enforcing server-side tenant isolation."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from backend.app.auth.dependencies import get_current_tenant
from backend.app.auth.models import TenantContext
from backend.app.schemas.cohorts import CohortRetentionParams, CohortRetentionResponse
from backend.app.services.cohort_service import CohortService

router = APIRouter(prefix="/cohorts", tags=["Cohort Retention"])


@router.get("", response_model=CohortRetentionResponse, summary="Get Weekly Cohort Retention Matrix")
async def get_cohort_retention(
    params: Annotated[CohortRetentionParams, Query()],
    tenant: Annotated[TenantContext, Depends(get_current_tenant)],
) -> CohortRetentionResponse:
    """Retrieve weekly cohort retention matrix, milestone benchmarks, and elapsed-period masking.

    Enforces server-side tenant isolation: analytical queries are strictly scoped
    to the authenticated tenant's data domain.
    """
    service = CohortService(tenant_id=tenant.tenant_id, org_name=tenant.organization_name)
    return service.get_cohort_retention(params)
