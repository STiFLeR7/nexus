"""Policy composition wiring (``nexus_policy.composition``).

``build_policy`` reuses the infrastructure substrate unchanged, seeds the v1-migrated
governance defaults, and produces an engine whose decisions land in the infrastructure
event store. It never modifies the infrastructure.
"""

from __future__ import annotations

from nexus_infra import build_infrastructure
from nexus_policy import DecisionRequest, build_policy
from nexus_policy.events import POLICY_EVALUATED, POLICY_REGISTERED


def test_build_policy_seeds_the_v1_defaults() -> None:
    ctx = build_policy(build_infrastructure(), now=lambda: "t")
    identities = {p.identity for p in ctx.registry.enabled()}
    assert "policy.execution.allow-baseline" in identities
    assert "policy.execution.deny-unapproved-runtime" in identities


def test_build_policy_without_seed_is_empty() -> None:
    ctx = build_policy(build_infrastructure(), seed=False, now=lambda: "t")
    assert ctx.registry.enabled() == ()
    # A governed request against an empty registry fails closed (INV-30).
    e = ctx.engine.evaluate(DecisionRequest(action_class="execution", correlation_identifier="c"))
    assert e.default_applied is True


def test_registrations_and_decisions_are_persisted_to_the_shared_log() -> None:
    infra = build_infrastructure()
    ctx = build_policy(infra, now=lambda: "t")
    ctx.engine.evaluate(
        DecisionRequest(
            action_class="execution",
            correlation_identifier="cor",
            attributes={"runtime": "claude", "command": "ls", "runtime_policy": "approved"},
        )
    )
    types = [e.type for e in infra.event_store.read_all()]
    assert types.count(POLICY_REGISTERED) == 4  # the four seed policies
    assert types.count(POLICY_EVALUATED) == 1


def test_policies_persist_through_the_infrastructure_repository() -> None:
    infra = build_infrastructure()
    build_policy(infra, now=lambda: "t")
    # The shared PolicyRepository read-model holds the seed policies (projection, not authority).
    assert infra.policies.get("policy.execution.allow-baseline") is not None
