"""Knowledge composition -- dependency-injection wiring for the Knowledge Engine.

Mirrors ``build_validation`` / ``build_recovery`` / ``build_reflection``: it **reuses** the Phase 2
infrastructure substrate (the event emitter is the infrastructure context; the repositories are the
Phase 2 ``InMemoryRepository`` / ``KnowledgeRepository``; the metrics sink is its observability)
rather than inventing anything. The infrastructure is not modified. Every dependency is overridable
and there is no module-level singleton.
"""

from __future__ import annotations

from dataclasses import dataclass

from nexus_infra import InfrastructureContext
from nexus_knowledge.engine import KnowledgeEngine
from nexus_knowledge.observability import KnowledgeObservability
from nexus_knowledge.persistence import KnowledgeRepositories, build_knowledge_repositories
from nexus_knowledge.policy import DEFAULT_PERSISTENCE_POLICY, PersistencePolicy
from nexus_runtime.events import TimestampSource


@dataclass(frozen=True, slots=True)
class KnowledgeContextBundle:
    """The wired knowledge layer (immutable wiring, stateful engine + repositories)."""

    infrastructure: InfrastructureContext
    repositories: KnowledgeRepositories
    engine: KnowledgeEngine


def build_knowledge(
    infrastructure: InfrastructureContext,
    *,
    repositories: KnowledgeRepositories | None = None,
    timestamps: TimestampSource | None = None,
    policy: PersistencePolicy = DEFAULT_PERSISTENCE_POLICY,
) -> KnowledgeContextBundle:
    """Wire a knowledge context over an infrastructure context; all parts overridable."""
    obs = infrastructure.observability
    resolved = repositories or build_knowledge_repositories(obs)
    engine = KnowledgeEngine(
        infrastructure,
        repositories=resolved,
        observability=KnowledgeObservability(obs),
        timestamps=timestamps,
        policy=policy,
    )
    return KnowledgeContextBundle(
        infrastructure=infrastructure, repositories=resolved, engine=engine
    )
