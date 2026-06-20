from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseRuntimeAdapter(ABC):
    """Abstract base class defining the standard execution runtime adapter contract."""

    stdout_log: str
    stderr_log: str

    @abstractmethod
    async def initialize(self) -> None:
        """Verify runtime environment settings and installation files."""
        pass

    @abstractmethod
    async def validate(self, repository_path: str, command: str) -> None:
        """Execute pre-run governance checks (repository, branch, command safety)."""
        pass

    @abstractmethod
    async def execute(self, command: str) -> dict[str, Any]:
        """Launch runner subprocess, track stdout/stderr, and update metrics."""
        pass

    @abstractmethod
    async def heartbeat(self) -> None:
        """Update last_heartbeat timestamp in database to prevent task timeout."""
        pass

    @abstractmethod
    async def checkpoint(self, step_name: str, state: dict[str, Any]) -> None:
        """Persist intermediate task checkpoint metadata to SQLite."""
        pass

    @abstractmethod
    async def terminate(self) -> None:
        """Gracefully terminate or force-kill the subprocess execution container."""
        pass

    @abstractmethod
    async def summarize(self) -> str:
        """Generate a structured markdown summary of the execution outputs."""
        pass

    @abstractmethod
    async def persist(self) -> None:
        """Commit all logs, steps, and artifacts to the database."""
        pass
