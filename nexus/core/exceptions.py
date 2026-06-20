"""Nexus exception hierarchy.

All Nexus-specific errors derive from ``NexusError`` so callers can
catch a single base class when desired.  Subsystem errors are grouped
by domain to enable targeted error handling.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nexus.core.types import EventType

# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------


class NexusError(Exception):
    """Root exception for all Nexus-specific errors."""

    def __init__(self, message: str = "", *, detail: str | None = None) -> None:
        self.detail = detail
        super().__init__(message)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


class ConfigurationError(NexusError):
    """Raised when application configuration is invalid or missing."""


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------


class DatabaseError(NexusError):
    """Raised on database connectivity or query failures."""


# ---------------------------------------------------------------------------
# Event gateway
# ---------------------------------------------------------------------------


class EventGatewayError(NexusError):
    """Raised when the event gateway cannot dispatch an event."""


# ---------------------------------------------------------------------------
# Task engine
# ---------------------------------------------------------------------------


class TaskEngineError(NexusError):
    """Raised on task lifecycle violations or failures."""


# ---------------------------------------------------------------------------
# Approval engine
# ---------------------------------------------------------------------------


class ApprovalEngineError(NexusError):
    """Raised on approval workflow violations or failures."""


# ---------------------------------------------------------------------------
# Execution engine
# ---------------------------------------------------------------------------


class ExecutionEngineError(NexusError):
    """Raised on execution runner failures."""


class ExecutionTimeoutError(ExecutionEngineError):
    """Raised when an execution exceeds its timeout threshold."""


# ---------------------------------------------------------------------------
# Agent router
# ---------------------------------------------------------------------------


class AgentRouterError(NexusError):
    """Raised when the agent router encounters a problem."""

    def __init__(
        self,
        message: str = "",
        *,
        event_type: EventType | None = None,
        detail: str | None = None,
    ) -> None:
        self.event_type = event_type
        super().__init__(message, detail=detail)


class UnroutableEventError(AgentRouterError):
    """Raised when no agent can handle a given event type."""


# ---------------------------------------------------------------------------
# Model router
# ---------------------------------------------------------------------------


class ModelRouterError(NexusError):
    """Raised when the LLM model router cannot fulfil a request."""


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------


class UnauthorizedActionError(NexusError):
    """Raised when a caller lacks permission for an action."""


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------


class RepositoryNotRegisteredError(NexusError):
    """Raised when referencing an unregistered repository."""


# ---------------------------------------------------------------------------
# Communication
# ---------------------------------------------------------------------------


class CommunicationError(NexusError):
    """Base for communication subsystem errors."""


class DiscordError(CommunicationError):
    """Raised on Discord API or bot failures."""


class EmailError(CommunicationError):
    """Raised on email / SMTP delivery failures."""
