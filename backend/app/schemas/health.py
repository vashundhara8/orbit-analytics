"""Health and readiness check schemas."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    app_name: str
    app_version: str
    environment: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    data_engine: str = "DuckDB / Columnar Parquet"
    tenancy_mode: str = "Isolated Tenant Workspaces"
