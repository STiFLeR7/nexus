"""Nexus FastAPI application.

Provides the ASGI application with:
- Lifespan-managed startup (logging, database, table creation) and shutdown.
- ``GET /health`` — liveness probe.
- ``GET /api/v1/status`` — system status overview.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import structlog
from fastapi import APIRouter, FastAPI, Request, Response, status

from nexus import __version__
from nexus.communication.discord import DiscordService, NexusBot, set_bot
from nexus.config import NexusSettings, get_settings
from nexus.database import Base, async_session_factory, create_engine
from nexus.gateway import EventGateway, publish_outbox_loop
from nexus.gateway.communication_outbox import run_communication_outbox_loop
from nexus.core.metrics import run_metrics_flush_loop
from nexus.intelligence import OpenRouterClient
from nexus.logging_config import setup_logging

from nexus.memory.schemas import HealthResponse
from nexus.scheduling import WorkflowOrchestrator

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
    discord_bot: NexusBot | None = None
    bot_task: asyncio.Task[Any] | None = None
    outbox_task: asyncio.Task[Any] | None = None
    comm_outbox_task: asyncio.Task[Any] | None = None
    metrics_flush_task: asyncio.Task[Any] | None = None



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

    # Run startup Git checks
    from nexus.core import health
    await health.run_git_startup_validation(_state.session_factory)

    # Perform startup policy auto-seeding (AP-317 / Baseline Action)
    from nexus.database import get_session
    from nexus.memory.policy_service import PolicyService
    async with get_session(_state.session_factory) as session:
        policy_service = PolicyService(session)
        await policy_service.seed_default_policies()

    # Initialize event gateway and client adaptors
    event_gateway = EventGateway()
    openrouter_client = OpenRouterClient(settings)

    # Boot Discord bot adapter
    discord_bot = NexusBot(settings, _state.session_factory, event_gateway)
    _state.discord_bot = discord_bot
    set_bot(discord_bot)
    discord_service = DiscordService(discord_bot)

    # Boot workflow orchestrator
    orchestrator = WorkflowOrchestrator(
        _state.session_factory, event_gateway, discord_service, openrouter_client
    )
    orchestrator.register_listeners()

    # Spawn transactional outbox publisher loop
    _state.outbox_task = asyncio.create_task(
        publish_outbox_loop(_state.session_factory, discord_service, poll_interval=2.0)
    )

    # Spawn communication outbox delivery loop
    _state.comm_outbox_task = asyncio.create_task(
        run_communication_outbox_loop(_state.session_factory, discord_service, email_service, poll_interval=2.0)
    )

    # Spawn metrics flusher loop
    _state.metrics_flush_task = asyncio.create_task(
        run_metrics_flush_loop(_state.session_factory, interval=5.0)
    )


    # Start Discord Bot thread client if credentials configured
    if settings.discord.token and settings.discord.token != "YOUR_DISCORD_BOT_TOKEN":
        _state.bot_task = asyncio.create_task(discord_bot.start(settings.discord.token))
        logger.info("discord_bot_task_spawned")
    else:
        logger.warning("discord_bot_skipped_empty_or_placeholder_token")

    logger.info("nexus_ready")
    yield

    # --- Shutdown ---
    logger.info("nexus_shutting_down")

    if _state.outbox_task:
        _state.outbox_task.cancel()
        logger.info("outbox_publisher_task_cancelled")

    if _state.comm_outbox_task:
        _state.comm_outbox_task.cancel()
        logger.info("communication_outbox_task_cancelled")

    if _state.metrics_flush_task:
        from nexus.core.metrics import flush_metrics_to_db
        try:
            await flush_metrics_to_db(_state.session_factory)
        except Exception as e:
            logger.error("error_flushing_metrics_on_shutdown", error=str(e))
        _state.metrics_flush_task.cancel()
        logger.info("metrics_flush_task_cancelled")

    if _state.bot_task:
        _state.bot_task.cancel()
        logger.info("discord_bot_task_cancelled")


    if _state.discord_bot:
        try:
            await _state.discord_bot.close()
            logger.info("discord_bot_connection_closed")
        except Exception as e:
            logger.error("error_closing_discord_bot", error=str(e))

    if _state.engine is not None:
        await _state.engine.dispose()
        logger.info("database_engine_disposed")

    logger.info("nexus_stopped")


# ---------------------------------------------------------------------------
# Router definition
# ---------------------------------------------------------------------------

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["system"])
async def health_check(response: Response) -> dict[str, Any]:
    """Liveness probe — returns healthy status, version, and timestamp."""
    from nexus.core import health

    is_ok = health.is_healthy()
    status_str = "healthy" if is_ok else "unhealthy"
    if not is_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": status_str,
        "version": __version__,
        "timestamp": datetime.now(UTC),
    }


@router.get("/api/v1/status", tags=["system"])
async def system_status(request: Request) -> dict[str, Any]:
    """Return current system status overview."""
    from nexus.core import health

    settings = getattr(request.app.state, "settings", None) or get_settings()
    is_ok = health.is_healthy()
    status_str = "operational" if is_ok else "unhealthy"

    return {
        "status": status_str,
        "health_reason": health.get_health_reason(),
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
