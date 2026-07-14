"""Policy composition — dependency-injection wiring for the Policy Engine.

Mirrors ``build_validation`` / ``build_execution``: it **reuses** the Phase 2
infrastructure substrate unchanged — the emitter is the infrastructure context, the
policy read-model is its ``policies`` repository, the metrics sink is its
observability. Nothing in the infrastructure is modified. Durable persistence is
transparent: over a context from ``build_durable_infrastructure`` (ADR-007), policy
registrations and decision events flow to the durable log and the durable
``PolicyRepository`` with no policy-specific durable code.

Every dependency is overridable and there is no module-level singleton.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from nexus_infra import InfrastructureContext
from nexus_policy.defaults import v1_seed_policies
from nexus_policy.engine import PolicyEngine
from nexus_policy.observability import PolicyObservability
from nexus_policy.registry import InMemoryPolicyRegistry


@dataclass(frozen=True, slots=True)
class PolicyContext:
    """The wired policy layer (immutable wiring, stateful registry + engine)."""

    infrastructure: InfrastructureContext
    registry: InMemoryPolicyRegistry
    engine: PolicyEngine


def build_policy(
    infrastructure: InfrastructureContext,
    *,
    seed: bool = True,
    now: Callable[[], str] | None = None,
) -> PolicyContext:
    """Wire a policy context over an infrastructure context; all parts overridable.

    ``seed`` registers the v1-migrated governance defaults (ADR-004 §9) so the engine is
    verdict-parity with v1 out of the box; pass ``seed=False`` for an empty registry.
    """
    obs = PolicyObservability(infrastructure.observability)
    registry = InMemoryPolicyRegistry(
        emitter=infrastructure,
        repository=infrastructure.policies,
        observability=obs,
        now=now,
    )
    if seed:
        for policy in v1_seed_policies():
            registry.register(policy)
    engine = PolicyEngine(registry, emitter=infrastructure, observability=obs, now=now)
    return PolicyContext(infrastructure=infrastructure, registry=registry, engine=engine)
