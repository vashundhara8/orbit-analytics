"""Pydantic schemas for the Cohort Retention API."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field, model_validator


class CohortCellItem(BaseModel):
    weeks_since_signup: int
    active_users: int | None = None
    retention_rate: float | None = None


class CohortRowItem(BaseModel):
    cohort_week: str
    cohort_size: int
    cells: list[CohortCellItem]


class CohortMilestones(BaseModel):
    w1_retention_avg: float | None = None
    w4_retention_avg: float | None = None
    w8_retention_avg: float | None = None
    w12_retention_avg: float | None = None


class CohortRetentionParams(BaseModel):
    max_weeks: int = Field(
        12,
        ge=1,
        le=24,
        description="Maximum weeks elapsed since signup (horizon)",
        examples=[12],
    )
    num_cohorts: int = Field(
        15,
        ge=1,
        le=52,
        description="Number of recent weekly cohorts to retrieve",
        examples=[15],
    )
    min_cohort_size: int = Field(
        500,
        ge=0,
        description="Minimum starting cohort size threshold to filter out tiny cohorts",
        examples=[500],
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
    def validate_bounds(self) -> CohortRetentionParams:
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError(
                f"start_date ({self.start_date}) must not be later than end_date ({self.end_date})"
            )
        return self


class CohortRetentionResponse(BaseModel):
    tenant_id: str
    organization_name: str
    num_cohorts_returned: int
    max_weeks_horizon: int
    min_cohort_size_filter: int
    start_date: date | None = None
    end_date: date | None = None
    milestones: CohortMilestones
    cohorts: list[CohortRowItem]
