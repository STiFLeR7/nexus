"""Unit tests for the Repository Governance Layer (GovernanceManager)."""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nexus.execution.governance import GovernanceManager, RepositoryGovernanceError
from nexus.memory.models import (
    ApprovalRecord,
    RepositoryRegistryRecord,
    TaskRecord,
)


@pytest.mark.asyncio
async def test_governance_invalid_runtime(db_session: AsyncSession) -> None:
    """Ensure that validation fails for unapproved runtimes."""
    gov = GovernanceManager(db_session)
    task_id = uuid.uuid4()

    with pytest.raises(
        RepositoryGovernanceError, match="Runtime 'invalid_runtime' is not approved"
    ):
        await gov.validate_execution(
            task_id=task_id,
            working_dir=".",
            command="echo 'test'",
            runtime="invalid_runtime",
        )


@pytest.mark.asyncio
async def test_governance_missing_task(db_session: AsyncSession) -> None:
    """Ensure validation fails if the task record does not exist."""
    gov = GovernanceManager(db_session)
    task_id = uuid.uuid4()

    with pytest.raises(RepositoryGovernanceError, match=f"Task with ID {task_id} not found"):
        await gov.validate_execution(
            task_id=task_id,
            working_dir=".",
            command="echo 'test'",
            runtime="gemini",
        )


@pytest.mark.asyncio
async def test_governance_missing_approval(db_session: AsyncSession) -> None:
    """Ensure validation fails if task has no approved record."""
    gov = GovernanceManager(db_session)

    # Create task
    task = TaskRecord(
        id=uuid.uuid4(),
        title="Test Task",
        description="echo 'test'",
        status="created",
        priority=2,
    )
    db_session.add(task)
    await db_session.flush()

    with pytest.raises(
        RepositoryGovernanceError, match="Execution lacks active approval authorization"
    ):
        await gov.validate_execution(
            task_id=task.id,
            working_dir=".",
            command="echo 'test'",
            runtime="gemini",
        )


@pytest.mark.asyncio
async def test_governance_unapproved_status(db_session: AsyncSession) -> None:
    """Ensure validation fails if the task approval is rejected."""
    gov = GovernanceManager(db_session)

    task = TaskRecord(
        id=uuid.uuid4(),
        title="Test Task",
        description="echo 'test'",
        status="created",
        priority=2,
    )
    db_session.add(task)
    await db_session.flush()

    approval = ApprovalRecord(
        id=uuid.uuid4(),
        task_id=task.id,
        status="rejected",
        requested_at=datetime.now(UTC),
        decided_by="111222333",
        decision_reason="Rejection test",
    )
    db_session.add(approval)
    await db_session.flush()

    with pytest.raises(
        RepositoryGovernanceError, match="Execution lacks active approval authorization"
    ):
        await gov.validate_execution(
            task_id=task.id,
            working_dir=".",
            command="echo 'test'",
            runtime="gemini",
        )


@pytest.mark.asyncio
async def test_governance_unregistered_working_dir(db_session: AsyncSession) -> None:
    """Ensure validation fails if the working directory is not registered."""
    # Temporarily remove registered repositories for this test
    stmt = select(RepositoryRegistryRecord)
    res = await db_session.execute(stmt)
    records = res.scalars().all()
    for rec in records:
        await db_session.delete(rec)
    await db_session.flush()

    gov = GovernanceManager(db_session)

    task = TaskRecord(
        id=uuid.uuid4(),
        title="Test Task",
        description="echo 'test'",
        status="created",
        priority=2,
    )
    db_session.add(task)
    await db_session.flush()

    approval = ApprovalRecord(
        id=uuid.uuid4(),
        task_id=task.id,
        status="approved",
        requested_at=datetime.now(UTC),
        decided_by="111222333",
        decision_reason="Approved",
    )
    db_session.add(approval)
    await db_session.flush()

    # Using an unregistered directory path like /some/random/path
    unregistered_dir = os.path.abspath("unregistered_directory_test_path")
    with pytest.raises(
        RepositoryGovernanceError, match="is not registered under any approved repository"
    ):
        await gov.validate_execution(
            task_id=task.id,
            working_dir=unregistered_dir,
            command="echo 'test'",
            runtime="gemini",
        )


@pytest.mark.asyncio
async def test_governance_blacklisted_command(db_session: AsyncSession) -> None:
    """Ensure validation fails if command contains blacklisted patterns."""
    gov = GovernanceManager(db_session)

    task = TaskRecord(
        id=uuid.uuid4(),
        title="Test Task",
        description="echo 'test'",
        status="created",
        priority=2,
    )
    db_session.add(task)
    await db_session.flush()

    approval = ApprovalRecord(
        id=uuid.uuid4(),
        task_id=task.id,
        status="approved",
        requested_at=datetime.now(UTC),
        decided_by="111222333",
        decision_reason="Approved",
    )
    db_session.add(approval)
    await db_session.flush()

    # rm -rf / is blacklisted
    with pytest.raises(
        RepositoryGovernanceError, match="Command contains forbidden string pattern: 'rm -rf /'"
    ):
        await gov.validate_execution(
            task_id=task.id,
            working_dir=".",
            command="rm -rf / && echo 'cleanup'",
            runtime="gemini",
        )


@pytest.mark.asyncio
async def test_governance_happy_path(db_session: AsyncSession) -> None:
    """Verify that a correct runtime, task, approval, repository, and command passes validation."""
    gov = GovernanceManager(db_session)

    task = TaskRecord(
        id=uuid.uuid4(),
        title="Valid Task",
        description="echo 'all good'",
        status="created",
        priority=2,
    )
    db_session.add(task)
    await db_session.flush()

    approval = ApprovalRecord(
        id=uuid.uuid4(),
        task_id=task.id,
        status="approved",
        requested_at=datetime.now(UTC),
        decided_by="111222333",
        decision_reason="Approved",
    )
    db_session.add(approval)
    await db_session.flush()

    # The "." directory matches the seeded "workspace_root" from conftest db_session fixture
    registry_rec = await gov.validate_execution(
        task_id=task.id,
        working_dir=".",
        command="echo 'all good'",
        runtime="gemini",
    )
    assert registry_rec is not None
    assert registry_rec.name == "workspace_root"
