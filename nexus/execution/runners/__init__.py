"""Execution runners for executing tools and scripts."""

from __future__ import annotations

import uuid
from typing import Any

from nexus.execution.runners.base import BaseRuntimeAdapter
from nexus.execution.runners.gemini import GeminiRuntimeAdapter


def get_runtime_adapter(
    runner_name: str,
    db_session: Any,
    execution_id: uuid.UUID,
    event_gateway: Any = None,
    openrouter_client: Any = None,
    settings: Any = None,
) -> BaseRuntimeAdapter:
    """Resolve and instantiate the correct execution adapter by runner name."""
    clean_runner = runner_name.lower().replace("_", "").replace("-", "")
    if clean_runner in ("gemini", "claudecode", "claude"):
        return GeminiRuntimeAdapter(
            db_session, execution_id, event_gateway, openrouter_client, settings
        )
    else:
        raise ValueError(f"Unknown execution runner: {runner_name}")
