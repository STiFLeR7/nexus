"""Nexus FastAPI application.

Provides the ASGI application with:
- Lifespan-managed startup (logging, database, table creation) and shutdown.
- ``GET /health`` — liveness probe.
- ``GET /api/v1/status`` — system status overview.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import structlog
from fastapi import APIRouter, FastAPI, Request

from nexus import __version__
from nexus.config import NexusSettings, get_settings
from nexus.database import Base, async_session_factory, create_engine
from nexus.logging_config import setup_logging
from nexus.memory.schemas import HealthResponse

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

logger = structlog.get_logger("nexus.api")


# ---------------------------------------------------------------------------
# Application state container
# ---------------------------------------------------------------------------

class _AppState:
    """Holds runtime references shared across the application."""

    engine: AsyncEngine | None = None
    session_factory: async_sessionmaker | None = None  # type: ignore[type-arg]


_state = _AppState()


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown lifecycle."""
    settings = getattr(app.state, "settings", None) or get_settings()

    # --- Startup ---
    setup_logging(level=settings.logging.level, log_format=settings.logging.format)
    logger.info("nexus_starting", version=__version__, environment=settings.environment)

    _state.engine = create_engine(
        database_url=settings.database.url,
        echo=settings.database.echo,
    )
    _state.session_factory = async_session_factory(_state.engine)

    # Create all tables
    async with _state.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("database_tables_created")

    logger.info("nexus_ready")
    yield

    # --- Shutdown ---
    logger.info("nexus_shutting_down")
    if _state.engine is not None:
        await _state.engine.dispose()
        logger.info("database_engine_disposed")
    logger.info("nexus_stopped")


# ---------------------------------------------------------------------------
# Router definition
# ---------------------------------------------------------------------------

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["system"])
async def health_check() -> dict[str, Any]:
    """Liveness probe — returns healthy status, version, and timestamp."""
    return {
        "status": "healthy",
        "version": __version__,
        "timestamp": datetime.now(UTC),
    }


@router.get("/api/v1/status", tags=["system"])
async def system_status(request: Request) -> dict[str, Any]:
    """Return current system status overview."""
    settings = getattr(request.app.state, "settings", None) or get_settings()
    return {
        "status": "operational",
        "version": __version__,
        "environment": settings.environment,
        "timestamp": datetime.now(UTC),
        "database": {
            "connected": _state.engine is not None,
            "url": settings.database.url,
        },
        "subsystems": {
            "gateway": "stub",
            "communication": "stub",
            "intelligence": "stub",
            "execution": "stub",
            "agents": "stub",
            "scheduling": "stub",
        },
    }


# ---------------------------------------------------------------------------
# Application Factory
# ---------------------------------------------------------------------------

def create_app(settings: NexusSettings | None = None) -> FastAPI:
    """Create and configure the FastAPI application instance."""
    app = FastAPI(
        title="Nexus",
        description="AI Orchestration Control Plane",
        version=__version__,
        lifespan=lifespan,
    )
    app.state.settings = settings or get_settings()
    app.include_router(router)
    return app


app = create_app()

