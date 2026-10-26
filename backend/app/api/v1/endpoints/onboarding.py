"""Customer data onboarding and ingestion endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status

from backend.app.auth.dependencies import get_current_tenant, require_roles
from backend.app.auth.models import AuthenticatedUser, TenantContext, UserRole
from backend.app.schemas.onboarding import IngestionStatusResponse, IngestionUploadResponse
from backend.app.services.ingestion_service import IngestionService

router = APIRouter(prefix="/onboarding", tags=["Data Onboarding"])

CSV_TEMPLATE_CONTENT = """user_id,event_name,event_timestamp,acquisition_channel
usr_1001,signup,2025-01-01 10:00:00,Organic
usr_1001,workspace_created,2025-01-01 10:15:00,Organic
usr_1001,invite_sent,2025-01-02 09:30:00,Organic
usr_1001,first_project,2025-01-03 14:00:00,Organic
usr_1001,paid,2025-01-05 16:45:00,Organic
usr_1002,signup,2025-01-02 11:20:00,Paid Search
usr_1002,workspace_created,2025-01-02 11:35:00,Paid Search
usr_1002,invite_sent,2025-01-03 08:10:00,Paid Search
usr_1003,signup,2025-01-03 12:00:00,Referral
usr_1003,workspace_created,2025-01-03 12:45:00,Referral
usr_1004,signup,2025-01-04 15:30:00,Direct
"""


@router.get(
    "/template",
    summary="Download Sample Event Data CSV Template",
    description="Provides a documented CSV template demonstrating accepted event names, timestamp formats, and column names.",
)
async def download_csv_template() -> Response:
    """Return a downloadable sample CSV template for data onboarding."""
    return Response(
        content=CSV_TEMPLATE_CONTENT.strip() + "\n",
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=orbit_analytics_template.csv"},
    )


@router.get(
    "/status",
    response_model=IngestionStatusResponse,
    summary="Get Tenant Ingestion Status & Data Freshness",
    description="Returns data freshness, accepted/rejected counts, and observation window completeness for the authenticated tenant.",
)
async def get_ingestion_status(
    tenant: Annotated[TenantContext, Depends(get_current_tenant)],
) -> IngestionStatusResponse:
    """Retrieve tenant-scoped data freshness and ingestion history."""
    service = IngestionService(tenant.tenant_id, tenant.organization_name)
    return service.get_status()


@router.post(
    "/upload",
    response_model=IngestionUploadResponse,
    summary="Upload & Ingest Customer Event CSV",
    description="Validates schema contracts, identifies rejected rows/duplicates, isolates storage per tenant, and materializes funnel marts.",
)
async def upload_customer_data(
    file: Annotated[UploadFile, File(description="CSV dataset with user events")],
    tenant: Annotated[TenantContext, Depends(get_current_tenant)],
    user: Annotated[AuthenticatedUser, Depends(require_roles(UserRole.ADMIN, UserRole.ANALYST))],
) -> IngestionUploadResponse:
    """Validate and ingest customer event dataset into isolated tenant storage."""
    filename = file.filename or "uploaded_data.csv"
    if not filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file format. Only .csv files are supported.",
        )

    file_bytes = await file.read()
    service = IngestionService(tenant.tenant_id, tenant.organization_name)
    return service.validate_and_ingest_csv(file_bytes=file_bytes, filename=filename)
