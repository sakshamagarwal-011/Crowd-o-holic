from __future__ import annotations

"""
Main FastAPI application — Crowd Flow Optimiser backend.
"""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.core.exceptions import register_exception_handlers

# Configure logging first
configure_logging()
log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup/shutdown lifecycle."""
    log.info("=" * 60)
    log.info("Crowd Flow Optimiser Backend starting")
    log.info("Version: %s", settings.app_version)
    log.info("AI mode: %s", settings.effective_ai_mode)
    log.info("DB: %s", settings.database_url[:30] + "..." if len(settings.database_url) > 30 else settings.database_url)
    log.info("=" * 60)

    # Pre-warm AI provider
    from app.services.ai_service import get_ai_provider
    provider = get_ai_provider()
    log.info("AI provider ready: %s (available=%s)", provider.provider_name, provider.is_available)

    # Auto-create default simulation so frontend connects immediately
    from app.services.simulation_service import get_or_create_default
    from app.services.venue_service import get_venue_for_simulation
    graph = get_venue_for_simulation("venue-stadium-a")
    default_engine = get_or_create_default(graph, provider)
    log.info("Default simulation ready | id=%s", default_engine.simulation_id)

    yield

    log.info("Crowd Flow Optimiser Backend shutting down")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Crowd Flow Optimiser — Real-time crowd simulation, risk analysis, "
        "dynamic routing, and AI-powered safety analysis."
    ),
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Exception handlers ────────────────────────────────────────────────────────

register_exception_handlers(app)

# ── Routes ────────────────────────────────────────────────────────────────────

from app.api.routes.health import router as health_router
from app.api.routes.venues import router as venues_router
from app.api.routes.scenarios import router as scenarios_router
from app.api.routes.simulations import router as simulations_router
from app.api.routes.emergency import router as emergency_router
from app.api.routes.intelligence import router as intelligence_router
from app.api.websocket import router as ws_router

app.include_router(health_router)
app.include_router(venues_router)
app.include_router(scenarios_router)
app.include_router(simulations_router)
app.include_router(emergency_router)
app.include_router(intelligence_router)
app.include_router(ws_router)

# ── Root redirect ─────────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
async def root():
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
    }
