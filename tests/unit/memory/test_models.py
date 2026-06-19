"""Unit tests for SQLAlchemy models in the memory layer.
"""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import pytest

from nexus.memory.models import (
    ApprovalRecord,
    AuditLogRecord,
    ExecutionRecord,
    KnowledgeItemRecord,
    ResearchItemRecord,
    TaskRecord,
    WorkflowCheckpointRecord,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_task_record_creation(db_session: AsyncSession) -> None:
    """Verify that a TaskRecord can be created and saved in the DB."""
    task = TaskRecord(
        title="Test task",
        description="A task description",
        status="created",
        priority=2,
    )
    db_session.add(task)
    await db_session.flush()

    assert task.id is not None
    assert isinstance(task.id, uuid.UUID)
    assert task.title == "Test task"
    assert task.description == "A task description"
    assert task.status == "created"
    assert task.priority == 2
    assert task.created_at is not None
    assert task.updated_at is not None
    assert task.is_archived is False


def test_audit_log_is_append_only() -> None:
    """Verify that AuditLogRecord is immutable and append-only.

    It must inherit from AuditMixin (no updated_at or is_archived columns).
    """
    assert not hasattr(AuditLogRecord, "updated_at")
    assert not hasattr(AuditLogRecord, "is_archived")
    # Should still have id and created_at
    assert hasattr(AuditLogRecord, "id")
    assert hasattr(AuditLogRecord, "created_at")


def test_all_models_have_id() -> None:
    """Verify that all ORM models defined in models.py have an id attribute."""
    models = [
        TaskRecord,
        ApprovalRecord,
        ExecutionRecord,
        AuditLogRecord,
        ResearchItemRecord,
        KnowledgeItemRecord,
        WorkflowCheckpointRecord,
    ]
    for model in models:
        assert hasattr(model, "id")
        # Ensure it is a mapping/mapped attribute or class property
        assert hasattr(model, "__tablename__")
