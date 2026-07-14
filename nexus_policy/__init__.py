"""``nexus_policy`` — the constitutional Policy Engine (P2).

The **single** owner of governance decisions (INV-28): given a
:class:`~nexus_policy.model.DecisionRequest` the :class:`~nexus_policy.engine.PolicyEngine`
returns an immutable :class:`~nexus_policy.model.PolicyEvaluation` from the closed
:class:`~nexus_core.contracts.enums.PolicyDecision` set. It *decides*; it performs no
action (INV-29). Every governed action with no matching policy is denied (INV-30,
fail-closed). Every decision is deterministic, explainable (INV-31), and recorded as a
correlated ``policy.evaluated`` event (INV-39) that replays without re-inference (INV-17).

The engine consumes the frozen ``policy`` contract (``contracts/policy.md`` /
``nexus_core.domain.Policy``) and reuses the Phase 2 / P1 substrate unchanged: durable
persistence (ADR-007) is transparent through :func:`~nexus_policy.composition.build_policy`.
This layer evaluates policy *only* — it never plans, executes, validates, recovers,
orchestrates, or interacts with humans.
"""

from __future__ import annotations

from nexus_policy.composition import PolicyContext, build_policy
from nexus_policy.conditions import MalformedConditionError, matches, specificity
from nexus_policy.defaults import (
    ALLOWED_RUNTIMES,
    DEFAULT_POLICY,
    EXECUTION_ACTION_CLASS,
    GLOBAL_COMMAND_BLACKLIST,
    REQUIRED_RUNTIME_POLICY,
    v1_seed_policies,
)
from nexus_policy.engine import PolicyEngine
from nexus_policy.events import POLICY_EVALUATED, POLICY_REGISTERED
from nexus_policy.model import DecisionRequest, PolicyEvaluation, PolicyRef
from nexus_policy.observability import PolicyObservability
from nexus_policy.precedence import resolve, version_key
from nexus_policy.registry import InMemoryPolicyRegistry

__all__ = [
    "ALLOWED_RUNTIMES",
    "DEFAULT_POLICY",
    "EXECUTION_ACTION_CLASS",
    "GLOBAL_COMMAND_BLACKLIST",
    "POLICY_EVALUATED",
    "POLICY_REGISTERED",
    "REQUIRED_RUNTIME_POLICY",
    "DecisionRequest",
    "InMemoryPolicyRegistry",
    "MalformedConditionError",
    "PolicyContext",
    "PolicyEngine",
    "PolicyEvaluation",
    "PolicyObservability",
    "PolicyRef",
    "build_policy",
    "matches",
    "resolve",
    "specificity",
    "v1_seed_policies",
    "version_key",
]
