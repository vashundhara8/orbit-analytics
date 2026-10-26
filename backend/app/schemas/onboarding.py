"""Schemas for customer data onboarding, validation contracts, and quality reporting."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DataQualitySummary(BaseModel):
    total_rows: int = Field(..., description="Total rows in the uploaded CSV file")
    accepted_rows: int = Field(..., description="Valid rows accepted into tenant storage")
    rejected_rows: int = Field(..., description="Invalid or malformed rows rejected")
    duplicate_rows: int = Field(..., description="Duplicate event rows identified and excluded")
    total_unique_users: int = Field(..., description="Number of distinct user identifiers")
    date_range_start: str | None = Field(None, description="Earliest valid event timestamp")
    date_range_end: str | None = Field(None, description="Latest valid event timestamp")
    coverage_days: int = Field(0, description="Total days spanned by the event timestamps")
    is_window_complete: bool = Field(True, description="Whether observation window covers minimum expected period (>=14 days)")
    warnings: list[str] = Field(default_factory=list, description="Actionable data quality warnings")
    rejection_reasons: dict[str, int] = Field(
        default_factory=dict, description="Breakdown of rejection counts by reason"
    )
    rejection_samples: list[str] = Field(
        default_factory=list, description="Sanitized row-level sample errors for diagnostics"
    )


class IngestionStatusResponse(BaseModel):
    tenant_id: str
    organization_name: str
    has_data: bool
    last_ingested_at: str | None = None
    filename: str | None = None
    quality_summary: DataQualitySummary | None = None


class IngestionUploadResponse(BaseModel):
    status: str = Field(..., examples=["success", "warning"])
    message: str
    tenant_id: str
    quality_summary: DataQualitySummary
