"""Application configuration for Orbit Analysis backend."""

from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel, Field


class Settings(BaseModel):
    app_name: str = "Orbit Analysis API"
    app_version: str = "0.2.0"
    api_v1_prefix: str = "/api/v1"
    environment: str = Field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    secret_key: str = Field(
        default_factory=lambda: os.getenv(
            "SECRET_KEY", "orbit_analytics_dev_secret_key_change_in_production_32chars"
        )
    )
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24 hours

    # Storage paths
    root_dir: Path = Field(default_factory=lambda: Path(__file__).resolve().parents[2])
    data_dir: Path = Field(default_factory=lambda: Path(__file__).resolve().parents[2] / "data")
    processed_dir: Path = Field(
        default_factory=lambda: Path(__file__).resolve().parents[2] / "data" / "processed"
    )
    raw_dir: Path = Field(
        default_factory=lambda: Path(__file__).resolve().parents[2] / "data" / "raw"
    )

    # Multi-tenant settings
    default_tenant_id: str = "org_orbit_demo"
    default_tenant_name: str = "Orbit Reference SaaS Corp"


settings = Settings()
