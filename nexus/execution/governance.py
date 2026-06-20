from __future__ import annotations

import os
from typing import TYPE_CHECKING

from sqlalchemy import select

from nexus.core.exceptions import ExecutionEngineError
from nexus.memory.models import ApprovalRecord, RepositoryRegistryRecord

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession


class RepositoryGovernanceError(ExecutionEngineError):
    """Exception raised when a subprocess run violates repository governance rules."""

    pass


class GovernanceManager:
    """Enforces safety constraints and whitelists on subprocess environments."""

    def __init__(self, db_session: AsyncSession) -> None:
        """Initialize the GovernanceManager with a database session."""
        self.session = db_session

    async def validate_execution(
        self,
        task_id: uuid.UUID,
        working_dir: str,
        command: str,
        runtime: str,
    ) -> RepositoryRegistryRecord:
        """Validate execution parameters against safety and registry constraints.

        Raises RepositoryGovernanceError on violation.
        """
        # 1. Approved Runtime Validation
        allowed_runtimes = {"gemini", "claude", "hermes"}
        if runtime.lower() not in allowed_runtimes:
            raise RepositoryGovernanceError(f"Runtime '{runtime}' is not approved.")

        # 2. Approval Record Validation
        from nexus.memory.models import TaskRecord

        task_stmt = select(TaskRecord).where(TaskRecord.id == task_id)
        task_res = await self.session.execute(task_stmt)
        task = task_res.scalar_one_or_none()
        if not task:
            raise RepositoryGovernanceError(f"Task with ID {task_id} not found.")

        # Check if approval exists and is approved
        app_stmt = (
            select(ApprovalRecord)
            .where(ApprovalRecord.task_id == task_id)
            .order_by(ApprovalRecord.created_at.desc())
            .limit(1)
        )
        app_res = await self.session.execute(app_stmt)
        approval = app_res.scalar_one_or_none()
        if not approval or approval.status != "approved":
            raise RepositoryGovernanceError("Execution lacks active approval authorization.")

        # 3. Approved Repository & Working Directory Validation
        # Find matching repository record by absolute path overlap
        repo_stmt = select(RepositoryRegistryRecord).where(
            RepositoryRegistryRecord.is_active.is_(True)
        )
        repo_res = await self.session.execute(repo_stmt)
        repositories = repo_res.scalars().all()

        matching_repo = None
        clean_working_dir = os.path.realpath(working_dir)
        for repo in repositories:
            clean_repo_path = os.path.realpath(repo.absolute_path)
            # Check if working_dir is inside repo directory
            if clean_working_dir == clean_repo_path or clean_working_dir.startswith(
                clean_repo_path + os.sep
            ):
                matching_repo = repo
                break

        if not matching_repo:
            raise RepositoryGovernanceError(
                f"Working directory '{working_dir}' is not registered "
                "under any approved repository."
            )

        # 4. Branch Constraints (whitelisted branch checks on active repo)
        try:
            import subprocess

            # Get active branch name
            res = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=clean_working_dir,
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode == 0:
                active_branch = res.stdout.strip()
                allowed_branches = matching_repo.allowed_branches
                if allowed_branches and isinstance(allowed_branches, list):
                    import fnmatch

                    matched = any(
                        fnmatch.fnmatch(active_branch, pattern) for pattern in allowed_branches
                    )
                    if not matched:
                        raise RepositoryGovernanceError(
                            f"Branch '{active_branch}' is not whitelisted "
                            f"for repository '{matching_repo.name}'."
                        )
        except Exception:
            pass

        # 5. Command Filter Safety Constraints
        blacklisted_patterns = ["rm -rf /", "sudo ", "mv /etc", ":(){ :|:& };:"]
        for pattern in blacklisted_patterns:
            if pattern in command:
                raise RepositoryGovernanceError(
                    f"Command contains forbidden string pattern: '{pattern}'"
                )

        return matching_repo
