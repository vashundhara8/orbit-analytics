"""Experimentation intelligence endpoints enforcing server-side tenant isolation."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path

from backend.app.auth.dependencies import get_current_tenant
from backend.app.auth.models import TenantContext
from backend.app.schemas.experiments import (
    ExperimentAnalysisResponse,
    ExperimentRevenueAnalysisResponse,
    ExperimentSummaryItem,
)
from backend.app.services.experiment_service import ExperimentService

router = APIRouter(prefix="/experiments", tags=["Experimentation Intelligence"])


@router.get("", response_model=list[ExperimentSummaryItem], summary="List Tenant Experiments")
async def list_experiments(
    tenant: Annotated[TenantContext, Depends(get_current_tenant)],
) -> list[ExperimentSummaryItem]:
    """List all experiments active or recorded for the authenticated tenant."""
    service = ExperimentService(tenant_id=tenant.tenant_id, org_name=tenant.organization_name)
    return service.list_experiments()


@router.get(
    "/{experiment_name}",
    response_model=ExperimentAnalysisResponse,
    summary="Get Detailed Experiment Inference & Diagnostics",
)
async def get_experiment_analysis(
    experiment_name: Annotated[str, Path(description="Name of the experiment to evaluate")],
    tenant: Annotated[TenantContext, Depends(get_current_tenant)],
) -> ExperimentAnalysisResponse:
    """Retrieve two-proportion z-test, confidence intervals, and SRM diagnostic for an experiment.

    Enforces server-side tenant isolation: experimental evaluation is strictly scoped
    to the authenticated tenant's data domain.
    """
    service = ExperimentService(tenant_id=tenant.tenant_id, org_name=tenant.organization_name)
    return service.get_experiment_analysis(experiment_name=experiment_name)


@router.get(
    "/{experiment_name}/revenue",
    response_model=ExperimentRevenueAnalysisResponse,
    summary="Get Downstream Revenue & Billing Intelligence",
)
async def get_experiment_revenue_analysis(
    experiment_name: Annotated[str, Path(description="Name of the experiment to evaluate")],
    tenant: Annotated[TenantContext, Depends(get_current_tenant)],
) -> ExperimentRevenueAnalysisResponse:
    """Evaluate downstream paid conversion, realized MRR, ARPU lift, and post-conversion churn.

    Performs point-in-time Intention-To-Treat analysis linking experiment assignments
    to subscription lifecycle events, enforcing server-side tenant isolation.
    """
    service = ExperimentService(tenant_id=tenant.tenant_id, org_name=tenant.organization_name)
    return service.get_experiment_revenue_analysis(experiment_name=experiment_name)
