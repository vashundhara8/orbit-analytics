"""Application configuration for Orbit Analysis backend."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Self

from pydantic import BaseModel, Field, model_validator

DEV_DEFAULT_SECRET = "orbit_analytics_dev_secret_key_change_in_production_32chars"
MIN_SECRET_LENGTH = 32


class Settings(BaseModel):
    app_name: str = "Orbit Analysis API"
    app_version: str = "0.2.0"
    api_v1_prefix: str = "/api/v1"
    environment: str = Field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    secret_key: str = Field(
        default_factory=lambda: os.getenv("SECRET_KEY", DEV_DEFAULT_SECRET)
    )
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24 hours

    # Security: Demo mode configuration
    enable_demo_auth: bool = Field(
        default_factory=lambda: os.getenv("ENABLE_DEMO_AUTH", "true").lower() in ("true", "1")
    )

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

    @model_validator(mode="after")
    def validate_security_configuration(self) -> Self:
        """Enforce strict production secret configuration and demo authentication boundaries."""
        is_production = self.environment.lower() in ("production", "prod")

        if is_production:
            if not self.secret_key or self.secret_key == DEV_DEFAULT_SECRET:
                raise ValueError(
                    "CRITICAL SECURITY CONFIGURATION FAILURE: Application startup aborted. "
                    "In production environment, SECRET_KEY must be explicitly set and cannot use the development default."
                )
            if len(self.secret_key.strip()) < MIN_SECRET_LENGTH:
                raise ValueError(
                    f"CRITICAL SECURITY CONFIGURATION FAILURE: Application startup aborted. "
                    f"SECRET_KEY must be at least {MIN_SECRET_LENGTH} characters long in production."
                )
            # In production, demo authentication must be disabled unless explicitly overridden
            if "ENABLE_DEMO_AUTH" not in os.environ:
                self.enable_demo_auth = False

        return self


settings = Settings()
