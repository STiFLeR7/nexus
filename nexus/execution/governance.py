from __future__ import annotations

import fnmatch
import os
from typing import TYPE_CHECKING, Any

from sqlalchemy import select

from nexus.core.exceptions import ExecutionEngineError
from nexus.memory.models import (
    ApprovalRecord,
    AuditLogRecord,
    ExecutionRecord,
    RepositoryRegistryRecord,
)

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

    async def _write_audit(
        self,
        task_id: uuid.UUID,
        event_type: str,
        data: dict[str, Any],
    ) -> None:
        """Write an immutable audit log record to the database."""
        import uuid as uuid_pkg

        audit = AuditLogRecord(
            id=uuid_pkg.uuid4(),
            event_type=event_type,
            entity_type="task",
            entity_id=task_id,
            data=data,
            component="governance_engine",
            actor="system",
        )
        self.session.add(audit)
        await self.session.flush()

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
            await self._write_audit(
                task_id,
                "RuntimeRejected",
                {
                    "runtime": runtime,
                    "allowed_runtimes": list(allowed_runtimes),
                    "reason": "Runtime not approved in platform",
                },
            )
            raise RepositoryGovernanceError(f"Runtime '{runtime}' is not approved.")

        # Load task
        from nexus.memory.models import TaskRecord

        task_stmt = select(TaskRecord).where(TaskRecord.id == task_id)
        task_res = await self.session.execute(task_stmt)
        task = task_res.scalar_one_or_none()
        if not task:
            raise RepositoryGovernanceError(f"Task with ID {task_id} not found.")

        # 2. Runtime Policy Approved Check
        if task.runtime_policy != "approved":
            await self._write_audit(
                task_id,
                "PolicyViolation",
                {
                    "runtime_policy": task.runtime_policy,
                    "expected": "approved",
                    "reason": "Policy mismatch",
                },
            )
            raise RepositoryGovernanceError(
                f"Runtime policy is '{task.runtime_policy}', but 'approved' is required."
            )

        # 3. Approval Record Validation
        app_stmt = (
            select(ApprovalRecord)
            .where(ApprovalRecord.task_id == task_id)
            .order_by(ApprovalRecord.created_at.desc())
            .limit(1)
        )
        app_res = await self.session.execute(app_stmt)
        approval = app_res.scalar_one_or_none()
        if not approval or approval.status != "approved":
            await self._write_audit(
                task_id,
                "ExecutionBlocked",
                {
                    "reason": "Execution lacks active approval authorization",
                    "status": "no_approval",
                },
            )
            raise RepositoryGovernanceError("Execution lacks active approval authorization.")

        # 4. Approved Repository & Working Directory Validation
        # Find matching repository record by absolute path overlap
        repo_stmt = select(RepositoryRegistryRecord)
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
            await self._write_audit(
                task_id,
                "RepositoryValidated",
                {"status": "failed", "working_dir": working_dir, "reason": "Unknown repository"},
            )
            raise RepositoryGovernanceError(
                f"Working directory '{working_dir}' is not registered "
                f"under any approved repository."
            )

        # 5. Repository Active Check
        if matching_repo.status != "active" or not matching_repo.is_active:
            await self._write_audit(
                task_id,
                "RepositoryValidated",
                {
                    "status": "failed",
                    "repository_id": str(matching_repo.id),
                    "reason": "Repository disabled",
                },
            )
            raise RepositoryGovernanceError(f"Repository '{matching_repo.name}' is disabled.")

        # Log successful repository validation
        await self._write_audit(
            task_id,
            "RepositoryValidated",
            {"status": "passed", "repository_id": str(matching_repo.id)},
        )

        # 6. Runtime Allowed on Repo Check
        if matching_repo.allowed_runtimes:
            allowed_runtimes_lower = [r.lower() for r in matching_repo.allowed_runtimes]
            if runtime.lower() not in allowed_runtimes_lower:
                await self._write_audit(
                    task_id,
                    "RuntimeRejected",
                    {
                        "runtime": runtime,
                        "allowed_runtimes": matching_repo.allowed_runtimes,
                        "reason": "Runtime not allowed for repo",
                    },
                )
                raise RepositoryGovernanceError(
                    f"Runtime '{runtime}' is not allowed for repo '{matching_repo.name}'."
                )

        # Log successful runtime authorization
        await self._write_audit(
            task_id,
            "RuntimeAuthorized",
            {"runtime": runtime, "repository_id": str(matching_repo.id)},
        )

        # 7. Profile Allowed on Repo Check
        if (
            matching_repo.allowed_profiles
            and task.execution_profile not in matching_repo.allowed_profiles
        ):
                await self._write_audit(
                    task_id,
                    "PolicyViolation",
                    {
                        "profile": task.execution_profile,
                        "allowed_profiles": matching_repo.allowed_profiles,
                        "reason": "Profile not allowed for repo",
                    },
                )
                raise RepositoryGovernanceError(
                    f"Execution profile '{task.execution_profile}' is not allowed "
                    f"for repository '{matching_repo.name}'."
                )

        # 8. Owner Approved Check
        if matching_repo.owner:
            authorized_owners = [o.strip() for o in matching_repo.owner.split(",")]
            decided_by = str(approval.decided_by) if approval.decided_by is not None else ""
            if decided_by not in authorized_owners:
                await self._write_audit(
                    task_id,
                    "PolicyViolation",
                    {
                        "decided_by": decided_by,
                        "repo_owners": authorized_owners,
                        "reason": "Approval owner mismatch",
                    },
                )
                raise RepositoryGovernanceError(
                    f"Owner approval validation failed. Decided by '{decided_by}', "
                    f"but repo owner is '{matching_repo.owner}'."
                )

        # 9. Execution Limit Not Exceeded Check
        # Count active executions for this repository path
        active_stmt = select(ExecutionRecord).where(
            ExecutionRecord.repository == matching_repo.absolute_path,
            ExecutionRecord.completed_at.is_(None),
        )
        active_res = await self.session.execute(active_stmt)
        active_execs = active_res.scalars().all()
        # Set limit at 3
        if len(active_execs) >= 3:
            await self._write_audit(
                task_id,
                "ExecutionBlocked",
                {
                    "active_execution_count": len(active_execs),
                    "limit": 3,
                    "reason": "Repository execution limit exceeded",
                },
            )
            raise RepositoryGovernanceError(
                f"Execution limit exceeded for repository '{matching_repo.name}'. "
                f"Current active: {len(active_execs)}."
            )

        # 10. Branch Constraints (whitelisted branch checks on active repo)
        active_branch = None
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
        except Exception:
            pass

        if active_branch:
            # Blocked branches check
            if matching_repo.blocked_branches:
                blocked = any(
                    fnmatch.fnmatch(active_branch, pattern)
                    for pattern in matching_repo.blocked_branches
                )
                if blocked:
                    await self._write_audit(
                        task_id,
                        "BranchRejected",
                        {
                            "branch": active_branch,
                            "blocked_branches": matching_repo.blocked_branches,
                            "reason": "Branch is blocked",
                        },
                    )
                    raise RepositoryGovernanceError(
                        f"Branch '{active_branch}' is blocked for "
                        f"repository '{matching_repo.name}'."
                    )

            # Protected branches check
            if matching_repo.protected_branches:
                protected = any(
                    fnmatch.fnmatch(active_branch, pattern)
                    for pattern in matching_repo.protected_branches
                )
                if protected:
                    await self._write_audit(
                        task_id,
                        "BranchRejected",
                        {
                            "branch": active_branch,
                            "protected_branches": matching_repo.protected_branches,
                            "reason": "Branch is protected",
                        },
                    )
                    raise RepositoryGovernanceError(
                        f"Branch '{active_branch}' is protected for "
                        f"repository '{matching_repo.name}'."
                    )

            # Allowed branches check
            if matching_repo.allowed_branches:
                branches = matching_repo.allowed_branches
                branches_list = list(branches.keys()) if isinstance(branches, dict) else branches

                if "*" not in branches_list:
                    matched = any(
                        fnmatch.fnmatch(active_branch, pattern) for pattern in branches_list
                    )
                    if not matched:
                        await self._write_audit(
                            task_id,
                            "BranchRejected",
                            {
                                "branch": active_branch,
                                "allowed_branches": branches_list,
                                "reason": "Branch not whitelisted",
                            },
                        )
                        raise RepositoryGovernanceError(
                            f"Branch '{active_branch}' is not whitelisted for "
                            f"repository '{matching_repo.name}'."
                        )

        # 11. Command Filter Safety Constraints
        blacklisted_patterns = ["rm -rf /", "sudo ", "mv /etc", ":(){ :|:& };:"]
        for pattern in blacklisted_patterns:
            if pattern in command:
                await self._write_audit(
                    task_id,
                    "PolicyViolation",
                    {
                        "command": command,
                        "violation": pattern,
                        "reason": "Forbidden command pattern",
                    },
                )
                raise RepositoryGovernanceError(
                    f"Command contains forbidden string pattern: '{pattern}'"
                )

        return matching_repo
