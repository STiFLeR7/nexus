"""Central Sandbox Manager coordinating providers and audits (AP-503)."""

from __future__ import annotations

import uuid
from typing import Any
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from nexus.execution.sandbox.audit import SandboxAuditIntegration
from nexus.execution.sandbox.provider import (
    DockerSandboxProvider,
    LocalSandboxProvider,
    MockSandboxProvider,
    SandboxPolicy,
    SandboxProcess,
    SandboxProvider,
)

logger = structlog.get_logger("nexus.execution.sandbox.manager")


class SandboxManager:
    """Orchestrates runtime execution sandboxing, applying resource limits and logging audits."""

    def __init__(self, db_session: AsyncSession, settings: Any = None):
        """Initialize the SandboxManager with DB session and configurations."""
        self.session = db_session
        self.settings = settings
        self.audit = SandboxAuditIntegration(db_session)
        self.provider = self._resolve_provider()

    def _resolve_provider(self) -> SandboxProvider:
        """Resolve the active SandboxProvider based on configuration settings."""
        from nexus.config import NexusSettings
        if not isinstance(self.settings, NexusSettings):
            return LocalSandboxProvider()

        if not self.settings.sandbox:
            return LocalSandboxProvider()

        cfg = self.settings.sandbox
        if not cfg.enabled:
            return LocalSandboxProvider()

        provider_name = cfg.provider.lower()
        if provider_name == "docker":
            return DockerSandboxProvider()
        elif provider_name == "mock":
            return MockSandboxProvider()
        else:
            return LocalSandboxProvider()

    async def execute(
        self,
        command: str,
        cwd: str = ".",
        timeout: int = 300,
        correlation_id: uuid.UUID | None = None,
    ) -> SandboxProcess:
        """Provision a sandbox, log creation audits, start the process, and return its handle.

        Args:
            command: The command execution string to launch.
            cwd: The workspace working directory path on the host.
            timeout: Maximum execution timeout in seconds.
            correlation_id: The trace ID (execution_id) correlating system events.

        Returns:
            A SandboxProcess wrapper handle.
        """
        sandbox_id = str(uuid.uuid4())

        # Resolve containment policies
        cpu_limit = 1.0
        memory_limit = "512m"
        network_policy = "none"
        filesystem_policy = "restricted"
        image = "python:3.12-slim"

        from nexus.config import NexusSettings
        if isinstance(self.settings, NexusSettings) and self.settings.sandbox:
            cfg = self.settings.sandbox
            cpu_limit = cfg.cpu_limit
            memory_limit = cfg.memory_limit
            network_policy = cfg.network_policy
            filesystem_policy = cfg.filesystem_policy
            image = cfg.image

        policy = SandboxPolicy(
            cpu_limit=cpu_limit,
            memory_limit=memory_limit,
            timeout=timeout,
            network_policy=network_policy,
            filesystem_policy=filesystem_policy,
            image=image,
        )

        # 1. Audit: SandboxCreated
        await self.audit.audit_event(
            event_type="sandbox.created",
            sandbox_id=sandbox_id,
            data={
                "command": command,
                "cwd": cwd,
                "policy": policy.model_dump(),
            },
            correlation_id=correlation_id,
        )

        # 2. Audit: SandboxStarted
        await self.audit.audit_event(
            event_type="sandbox.started",
            sandbox_id=sandbox_id,
            correlation_id=correlation_id,
        )

        try:
            process = await self.provider.spawn(command, policy, cwd, sandbox_id)
            original_communicate = process.communicate

            # Intercept communicate to record audit terminations or failures
            async def wrapped_communicate() -> Tuple[bytes, bytes]:
                try:
                    stdout, stderr = await original_communicate()
                    err_str = stderr.decode("utf-8", errors="replace")

                    if process.returncode != 0:
                        # Differentiate timeout vs failure
                        if "timeout" in err_str.lower() or process.returncode == -1:
                            await self.audit.audit_event(
                                event_type="sandbox.timeout",
                                sandbox_id=sandbox_id,
                                data={
                                    "exit_code": process.returncode,
                                    "stderr": err_str[:500],
                                },
                                correlation_id=correlation_id,
                            )
                        else:
                            await self.audit.audit_event(
                                event_type="sandbox.failure",
                                sandbox_id=sandbox_id,
                                data={
                                    "exit_code": process.returncode,
                                    "stderr": err_str[:500],
                                },
                                correlation_id=correlation_id,
                            )
                    else:
                        # Successful execution termination
                        await self.audit.audit_event(
                            event_type="sandbox.terminated",
                            sandbox_id=sandbox_id,
                            data={"exit_code": 0},
                            correlation_id=correlation_id,
                        )
                    return stdout, stderr
                except Exception as ex:
                    await self.audit.audit_event(
                        event_type="sandbox.failure",
                        sandbox_id=sandbox_id,
                        data={"error": str(ex)},
                        correlation_id=correlation_id,
                    )
                    raise ex

            process.communicate = wrapped_communicate
            return process

        except Exception as spawn_err:
            await self.audit.audit_event(
                event_type="sandbox.failure",
                sandbox_id=sandbox_id,
                data={"error": f"Failed to spawn: {spawn_err!s}"},
                correlation_id=correlation_id,
            )
            raise spawn_err
