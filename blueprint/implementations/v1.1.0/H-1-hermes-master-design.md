# H-1 — Hermes Master Design (v1.1.0 "Containment")

> **Track H · Design only — no implementation, no code, no runtime change.** Integrating design for
> evolving the Hermes runtime **Prototype → Experimental → Pilot**. Every proposal traces to accepted
> v1.0.1 evidence (AP-105: `hermes-reality-audit.md`, `hermes-capability-ledger.md`,
> `hermes-gap-analysis.md`; `v1.0.1-risk-register.md`; `ADR-v1.0.1-alignment-release.md`).
>
> Branch `v1.1.0-planning`, off frozen `v1.0.1` (`ab5937b`). v1.0.1 is immutable history.

---

## 1. Mission & target

Move Hermes from **Prototype** (`ADR-hermes-reality-audit.md`) to **Experimental**, then **Pilot**, by
making its *intelligence honest* and its *lifecycle safe* — without redesigning the runtime abstraction,
governance, scheduler, memory, event, or approval architectures (Architecture Rules 1–10).

## 2. Starting evidence (what v1.0.1 proved, verbatim sources)

| Defect | Evidence | Ledger ref |
|---|---|---|
| AsyncMock in production path | `hermes.py:7,186-211` | Cap 4 (Mocked) |
| Decorative hardcoded planning | `hermes.py:147-151` | Cap 2 (Simulated) |
| Simulated `web_search` | `hermes.py:76-86` | Cap 8 (Simulated) |
| Exit status always `0` | `hermes.py:284-289` | Cap 18 (Simulated) |
| `terminate()` no-op, never invoked | `hermes.py:312-314`; `orchestrator.py:210-216` | Cap 14 (Not Present) |
| No resume (checkpoints write-only) | `hermes.py:138-139`, `301-310` | Cap 12 (Not Present) |

What is **already real** and must be preserved: governance-gated `validate_goal`, real
`agent_steps`/`checkpoint`/`heartbeat`/`artifact` persistence, real file/command tools, real
summarization, clean registry integration (AP-105 §4).

## 3. The five sub-designs (this track)

| Doc | Concern | Answers questions |
|---|---|---|
| `H-1-hermes-capability-model.md` | Per-capability current→target | Q3 planning, Q4 search, exit-status |
| `H-1-hermes-lifecycle-design.md` | Explicit state machine + cancellation | Q2 states, Q6 cancellation |
| `H-1-hermes-recovery-design.md` | Resume + checkpoint evolution | Q5 resume, Q7 checkpoints |
| `H-1-hermes-tooling-design.md` | Tool/search abstraction + structured calls | Q4 search, tooling |
| `../v1.1.0/R-05-shared-resolution.md` | File-tool containment (shared with Track S) | tooling∩sandbox |

## 4. Required questions — master answers (detail in sub-designs)

1. **What constitutes a real Hermes execution?** A run that: validates the goal through governance →
   derives a plan *from the goal* (not a literal) → iterates a loop where a **real** model selects the
   next action as a **structured tool-call** → executes a **real** tool (including real search) →
   observes the real result → persists the step + checkpoint + heartbeat → terminates on genuine
   completion, budget exhaustion, or cancellation → returns an **exit status reflecting the real
   outcome** → persists artifacts. **No mock branch, no canned observation, no always-`0` exit** in the
   production path.
2. **Missing lifecycle states?** Explicit `PLANNING`, `DECIDING`, `TOOL_EXECUTING`, `CHECKPOINTED`,
   `CANCELLING`/`CANCELLED`, `RESUMING`, and a `FAILED`/`TIMED_OUT` distinct from `COMPLETED`. Today all
   collapse to `COMPLETED` + exit `0`. (→ lifecycle-design.)
3. **Planning?** Goal-derived, advisory, revisable; the plan artifact becomes *real* (generated) not
   decorative. (→ capability-model.)
4. **Search?** Behind a `SearchProvider` abstraction (runtime-abstraction rule); the canned response
   becomes a **test double only**; production wires a real provider, subject to sandbox network policy
   (cross-track). (→ tooling-design.)
5. **Resume?** Reconstruct trajectory from the already-persisted `agent_steps` + last checkpoint, then
   continue — mirroring the existing `resume_research_run`/`resume_briefing_run` precedent. (→
   recovery-design.)
6. **Cancellation?** Cooperative: a cancellation signal observed at loop boundaries; `terminate()` sets
   it and is **wired into the orchestrator + timeout path**; in-flight subprocess killed via the sandbox.
   (→ lifecycle-design.)
7. **Checkpoints write-only → recoverable?** Define the recovery contract; resume reads the latest
   checkpoint for `workflow_id` for plan/cursor and `agent_steps` for trajectory (no schema change
   needed at design level). (→ recovery-design.)
8. **Experimental requires:** no prod mock; real exit status; real search; structured tool-calls;
   goal-derived plan; tests covering the real-LLM branch. (Honesty achieved; full lifecycle safety may
   still be partial.)
9. **Pilot requires:** Experimental **plus** wired+tested cancellation, working+tested resume,
   sandbox-confined file tools (R-05), fail-fast init, configurable step budget, and one audited real
   governed run producing genuine output. (Honest **and** lifecycle-safe **and** contained.)
10. **Intentionally deferred:** multi-agent/hierarchical coordination; dependency-graph/advanced
    replanning; new tools beyond the existing set; per-step Discord streaming; non-OpenRouter backends;
    full **Production Ready** status. v1.1.0 targets **Experimental→Pilot only**.

## 5. Design principles

- **Honesty before capability:** remove simulation from the prod path (P0) before adding sophistication.
- **Reuse existing primitives:** `agent_steps`, `workflow_checkpoints`, audit ledger, `EventGateway`,
  governance, sandbox — extend, don't replace (Rules 1–8).
- **Abstraction-respecting:** search/tools behind ports, like the runtime registry (Rule 2).
- **No hidden coupling:** Hermes consumes the sandbox boundary via the existing `SandboxManager`
  contract; it does not reach around it (Rule 9, R-05).

## 6. Promotion gates (evidence-defined)

| Gate | Condition (evidence required) |
|---|---|
| **Prototype → Experimental** | Q8 satisfied; AP-105 ledger Caps 2,3,4,8,18 reclassified ≥ Partially-Implemented with tests |
| **Experimental → Pilot** | Q9 satisfied; Caps 12,14 = Implemented; R-05 closed; one audited real run |

## 7. Out of scope (reject if proposed)

Anything in the v1.1.0 deferred list (PostgreSQL, distributed scheduling, runtime CLI integration,
health rework, version sync, multi-node, new agent types, features, UI, observability expansion) — and
anything that modifies governance/approval/scheduler/memory/event architecture beyond what a listed
Hermes gap strictly requires.

## 8. Status

Design only. No code, no commit, no migration. Sub-designs + `ADR-hermes-v1.1-foundation.md` accompany
this document for review. Implementation APs remain **gated** until the design is accepted.
