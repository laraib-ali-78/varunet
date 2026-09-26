"""
VaruNet FastAPI Application
Multi-model AI-NWP forecast blending, deterministic verification, and alerting service.
Automatic OpenAPI documentation available at /docs.
Custom JWT authentication with Role-Based Access Control (RBAC).
Prometheus metrics instrumentation exposed at /metrics.
"""

import asyncio
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

logger = logging.getLogger("varunet.ingestion")

from backend.app.routers.forecasts import router as forecasts_router
from backend.app.routers.skill_scores import router as skill_scores_router
from backend.app.routers.blend import router as blend_router
from backend.app.routers.alerts import router as alerts_router
from backend.app.auth.router import router as auth_router

app = FastAPI(
    title="VaruNet API",
    description=(
        "Hybrid AI–NWP Multi-Model Forecast Blending System for Smart India Hackathon SIH26081. "
        "Provides raw ingestion retrieval, deterministic skill-scoring, dynamic XGBoost forecast blending, "
        "TreeSHAP explainability, multi-sector hazard alerting, and role-based access control (RBAC)."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Enable CORS for React frontend dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instrument Prometheus metrics: request latency and request count
instrumentator = Instrumentator(
    should_group_status_codes=False,
    should_ignore_untemplated=True,
    should_respect_env_var=False,
    excluded_handlers=["/metrics"],
)
instrumentator.instrument(app).expose(app, endpoint="/metrics", tags=["Monitoring"])

# Include Authentication router
app.include_router(auth_router)

# Include Core Forecast, Skill, Blend, and Alert routers
app.include_router(forecasts_router)
app.include_router(skill_scores_router)
app.include_router(blend_router)
app.include_router(alerts_router)


# Scheduled background ingestion worker running inside the container
async def scheduled_ingestion_worker():
    """
    Ingestion scheduling worker running inside the backend container.
    Periodically ingests forecast frames using calibrated proxy feeds.
    """
    logger.info("VaruNet Ingestion Scheduler started inside backend container.")
    await asyncio.sleep(2)
    try:
        from backend.app.services.ingestion_service import ingest_forecast_cycle
        count = ingest_forecast_cycle()
        logger.info("Initial ingestion cycle completed: Ingested %d forecast rows into database.", count)
    except Exception as e:
        logger.error("Initial ingestion cycle failed: %s", str(e))

    while True:
        await asyncio.sleep(3600)  # Next scheduled run
        try:
            from backend.app.services.ingestion_service import ingest_forecast_cycle
            count = ingest_forecast_cycle()
            logger.info("Scheduled ingestion run completed: Ingested %d forecast rows into database.", count)
        except Exception as e:
            logger.error("Scheduled ingestion cycle failed: %s", str(e))


@app.on_event("startup")
async def startup_ingestion_scheduler():
    asyncio.create_task(scheduled_ingestion_worker())


# Health check endpoint explicitly remains public without authentication
@app.get("/", tags=["Health"])
def health_check():
    """
    Health check endpoint returning service status.
    Explicitly unauthenticated per architectural hard rules.
    """
    return {
        "service": "VaruNet API",
        "status": "online",
        "docs": "/docs",
        "metrics": "/metrics",
        "auth": "Custom JWT (forecaster, admin, citizen)",
        "version": "1.0.0",
    }
