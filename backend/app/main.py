"""Main FastAPI entry point for Orbit Analysis."""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.api.v1.endpoints.health import health_check
from backend.app.api.v1.router import api_v1_router
from backend.app.config import settings

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Enterprise Multi-Tenant SaaS Growth Intelligence API: "
        "Funnel analytics, cohort retention, experimentation, and churn intelligence."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Cross-Origin Resource Sharing (CORS) for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root health check endpoint
app.add_api_route("/health", health_check, methods=["GET"], tags=["Health"])

# Register versioned API router
app.include_router(api_v1_router, prefix=settings.api_v1_prefix)


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Safe unhandled exception response to prevent credential or internal trace leakage."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred while processing the analytical request.",
            "path": request.url.path,
        },
    )
