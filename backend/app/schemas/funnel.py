"""Pydantic schemas for the Funnel Analytics API."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field, model_validator


class FunnelFilterParams(BaseModel):
    acquisition_channel: str | None = Field(
        None,
        description="Filter by acquisition channel: organic, paid_search, referral, partner",
        examples=["organic"],
    )
    start_date: date | None = Field(
        None,
        description="Inclusive signup start date (YYYY-MM-DD)",
        examples=["2024-01-01"],
    )
    end_date: date | None = Field(
        None,
        description="Inclusive signup end date (YYYY-MM-DD)",
        examples=["2025-06-29"],
    )

    @model_validator(mode="after")
    def validate_date_range(self) -> FunnelFilterParams:
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError(
                f"start_date ({self.start_date}) must not be later than end_date ({self.end_date})"
            )
        return self


class FunnelStageItem(BaseModel):
    step_order: int
    step_id: str
    name: str
    description: str
    entering_users: int
    step_conversion_rate: float
    drop_off_rate: float
    users_lost: int
    cumulative_conversion_rate: float


class ChannelBenchmarkItem(BaseModel):
    channel: str
    total_signups: int
    paid_customers: int
    conversion_rate: float
    variance_vs_benchmark: float


class FunnelFilterApplied(BaseModel):
    acquisition_channel: str | None
    start_date: date | None
    end_date: date | None


class FunnelAnalysisResponse(BaseModel):
    tenant_id: str
    organization_name: str
    filter_applied: FunnelFilterApplied
    cohort_size: int
    overall_conversion_rate: float
    stages: list[FunnelStageItem]
    channel_benchmarks: list[ChannelBenchmarkItem]
    available_channels: list[str]
