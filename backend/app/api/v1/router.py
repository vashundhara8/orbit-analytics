"""API v1 master router."""

from __future__ import annotations

from fastapi import APIRouter

from backend.app.api.v1.endpoints.auth import router as auth_router
from backend.app.api.v1.endpoints.churn import router as churn_router
from backend.app.api.v1.endpoints.cohorts import router as cohorts_router
from backend.app.api.v1.endpoints.experiments import router as experiments_router
from backend.app.api.v1.endpoints.funnel import router as funnel_router
from backend.app.api.v1.endpoints.health import router as health_router

api_v1_router = APIRouter()
api_v1_router.include_router(health_router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(funnel_router)
api_v1_router.include_router(cohorts_router)
api_v1_router.include_router(experiments_router)
api_v1_router.include_router(churn_router)
