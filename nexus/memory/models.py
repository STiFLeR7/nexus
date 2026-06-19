"""SQLAlchemy 2.x ORM models for the Nexus memory layer.

Every mutable table includes ``id``, ``created_at``, ``updated_at``, and
``is_archived``.  The ``audit_log`` table is intentionally immutable and
append-only — it omits ``updated_at`` and ``is_archived``.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nexus.database import AuditMixin, Base, TimestampMixin

# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

class TaskRecord(TimestampMixin, Base):
    """A unit of work tracked by the orchestration layer."""

    __tablename__ = "tasks"

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="created",
        index=True,
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=2)

    # Relationships
    approvals: Mapped[list[ApprovalRecord]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    executions: Mapped[list[ExecutionRecord]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


# ---------------------------------------------------------------------------
# Approvals
# ---------------------------------------------------------------------------

class ApprovalRecord(TimestampMixin, Base):
    """An approval gate guarding task execution."""

    __tablename__ = "approvals"

    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
        index=True,
    )
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    decided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    decided_by: Mapped[str | None] = mapped_column(String(200), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    task: Mapped[TaskRecord] = relationship(back_populates="approvals")
    executions: Mapped[list[ExecutionRecord]] = relationship(
        back_populates="approval",
        lazy="selectin",
    )


# ---------------------------------------------------------------------------
# Executions
# ---------------------------------------------------------------------------

class ExecutionRecord(TimestampMixin, Base):
    """A single execution run of a task by a runner backend."""

    __tablename__ = "executions"

    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    approval_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("approvals.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    runner: Mapped[str] = mapped_column(String(100), nullable=False)
    repository: Mapped[str | None] = mapped_column(String(500), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_heartbeat: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    timeout_threshold: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    exit_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    logs: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    task: Mapped[TaskRecord] = relationship(back_populates="executions")
    approval: Mapped[ApprovalRecord | None] = relationship(back_populates="executions")


# ---------------------------------------------------------------------------
# Audit log (immutable, append-only)
# ---------------------------------------------------------------------------

class AuditLogRecord(AuditMixin, Base):
    """Immutable, append-only audit trail of all system events.

    This table deliberately omits ``updated_at`` and ``is_archived``
    — records are never modified or soft-deleted.
    """

    __tablename__ = "audit_log"

    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    data: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # type: ignore[type-arg]
    correlation_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    component: Mapped[str | None] = mapped_column(String(100), nullable=True)
    actor: Mapped[str | None] = mapped_column(String(200), nullable=True)


# ---------------------------------------------------------------------------
# Research items
# ---------------------------------------------------------------------------

class ResearchItemRecord(TimestampMixin, Base):
    """A research finding or reference collected by a research agent."""

    __tablename__ = "research_items"

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    source: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True)  # type: ignore[type-arg]


# ---------------------------------------------------------------------------
# Knowledge items
# ---------------------------------------------------------------------------

class KnowledgeItemRecord(TimestampMixin, Base):
    """A distilled knowledge item in the persistent knowledge base."""

    __tablename__ = "knowledge_items"

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    source: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True)  # type: ignore[type-arg]


# ---------------------------------------------------------------------------
# Workflow checkpoints
# ---------------------------------------------------------------------------

class WorkflowCheckpointRecord(TimestampMixin, Base):
    """Checkpoint snapshot for resumable workflow state."""

    __tablename__ = "workflow_checkpoints"

    workflow_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    step_name: Mapped[str] = mapped_column(String(200), nullable=False)
    state: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # type: ignore[type-arg]
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
