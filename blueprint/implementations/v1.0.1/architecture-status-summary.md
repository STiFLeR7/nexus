# Architecture Status Summary (AP-104)

> **The single source of truth for subsystem status.** Every subsystem is classified with evidence.
> When any other document (README, STATUS) states a subsystem's status, it must agree with this file.
>
> **Basis:** Nexus v1.0.0 (tag) + v1.0.1 Alignment. Reality verified first-hand and cross-checked
> against the accepted onboarding audit (`blueprint/onboarding/`).

---

## Classification scale

| Class | Meaning |
|---|---|
| **Production Ready** | Built, tested, safe, and genuinely relied upon in the governed path |
| **Operational** | Built and working in-process; fit for attended/pilot use |
| **Experimental** | Built but unproven / unsafe-by-default / needs review before trust |
| **Stubbed** | Interface exists; concrete behavior is a generic placeholder |
| **Mocked** | Contains simulated/canned behavior in the production path |
| **Deferred** | Intentionally postponed within v1.0.x |
| **Future** | Genuinely not started; a later-milestone aspiration |

---

## Master status table

| Subsystem | Status | Evidence | Notes |
|---|---|---|---|
| **Approval System** | 🟢 Production Ready | `execution/service.py:43-45`, `approvals/service.py:85-181`; 12 governance tests | Un-bypassable DB-backed gate. **Now fail-closed** on empty `owner_ids` (A-001, `service.py:96-102`). |
| **Governance Layer (11-gate)** | 🟢 Production Ready | `execution/governance.py` | Best-tested code in repo; audits every decision. |
| **Memory System** | 🟢 Production Ready | `memory/manager.py:28-101`, `models.py:184-199` | Event-sourced immutable `audit_log` + checkpoint replay. |
| **Communication Outbox** | 🟢 Production Ready | `gateway/communication_outbox.py:79-243`; concurrency/lease tests | Lease-based, backoff+jitter, dead-letter, audited. |
| **Task Management** | 🟢 Production Ready | `task_service.py:25-38`; e2e `tests/e2e/test_mvp_workflow.py` | Guarded lifecycle, locking, Discord CRUD. |
| **Runtime Registry + adapter split** | 🟢 Operational | `runners/__init__.py`, `runners/base.py` | Excellent extensible abstraction; concrete runtimes vary (below). |
| **Execution timeouts** | 🟢 Operational | `runners/base.py:9-27` (`resolve_execution_timeout`, `hard_limit` clamp) | **Fixed** (A-002) to honor ADR-010 tiers. |
| **Scheduler Foundation** | 🟢 Operational | `scheduling/scheduler.py`, `jobs.py`; AP-103B reports | **New in v1.0.1.** 6 jobs, audited, single-node. Closes A-003. |
| **Metrics Persistence** | 🟢 Operational | `core/metrics.py`; `metrics_aggregation` job (5m) | Collection always worked; **aggregation+retention now actually scheduled** (was dormant in v1.0.0). |
| **Research Engine** | 🟡 Operational (latent) | research service; `research_collection` job (2h) | Engine production-grade; **now scheduled** but `research_feeds` empty by default → safely audited-skip until configured. RSS/Atom only. |
| **Daily Briefing Engine** | 🟡 Operational | briefing service; `daily_briefing` job (08:00 Asia/Kolkata) | **Now scheduled.** Note: default briefing path uses synchronous flush (per onboarding 07). |
| **Gemini Runtime** | 🟠 Stubbed | `runners/gemini.py` | Generic shell runner; no real `gemini` CLI binary invocation yet. |
| **Claude Runtime** | 🟠 Stubbed | `runners/claude.py` | Generic shell runner; no real `claude` CLI binary invocation yet. |
| **Hermes Runtime** | 🔴 Mocked (partial) | `runners/hermes.py` (AsyncMock branch, hardcoded plan/canned search) | Real loop scaffold + simulated branches in production. **Full ledger is AP-105.** Classified as Agent Runtime (`reports/hermes-runtime-classification.md`). |
| **Sandbox Isolation** | 🟠 Experimental (default-off) | `config.py:133-137` (`provider="local"`) | Default = **no isolation**; host execution guarded only by substring blacklist. **Review is A-006.** |
| **Health reporting** | 🟠 Experimental | `core/health.py:49-71`; `api.py` `/api/v1/status` returns `"stub"` | Boot-time boolean from `git --version`; not live-probed. Known gap. |
| **Alembic migrations** | 🟠 Experimental | `api.py` `create_all`; incomplete migrations | `create_all` is the real schema source; migrations incomplete/untested. Blocks PostgreSQL path. |
| **Distributed / multi-node scheduling** | ⚪ Future | `scheduler-future-scaling.md` | Lease model + PostgreSQL coordination designed, not built. |
| **PostgreSQL backend** | ⚪ Future | ADR-002 | SQLite/WAL today. |
| **Extra integrations (WhatsApp/Slack/GitHub)** | ⚪ Future | ROADMAP Phase 9 | Not started. |

---

## Status rollup

- **Production Ready (5):** Approval, Governance, Memory, Communication Outbox, Task Management.
- **Operational (5):** Runtime Registry, Execution timeouts, Scheduler, Metrics, (latent) Research / Briefing.
- **Stubbed (2):** Gemini, Claude runtimes.
- **Mocked (1):** Hermes runtime (full audit → AP-105).
- **Experimental (4):** Sandbox isolation, Health reporting, Alembic migrations.
- **Future (3):** Distributed scheduling, PostgreSQL, extra integrations.

## One-line truth

> Nexus v1.0.1 is a **production-grade governed-execution kernel** (approval + governance + memory +
> outbox) with an **operational single-node autonomy layer** (scheduler now drives research,
> briefing, approval-expiry, metrics, and health jobs), whose **concrete agent runtimes are still
> stubbed/mocked** and whose **default sandbox is unisolated** — honestly pilot-ready as an
> attended-to-lightly-autonomous single-operator control plane.

## Especially-watched subsystems (AP-104 mandate)

- **Hermes Runtime** — 🔴 Mocked. Do not represent as functional agent execution. AP-105 will produce
  the per-capability ledger.
- **Research Engine** — 🟡 built + scheduled, **but empty feeds by default**; not autonomous until configured.
- **Scheduler** — 🟢 Operational, **single-node only** (no cross-process lease yet).
- **Sandbox Layer** — 🟠 default-off isolation; treat host exposure as real until A-006.
- **Metrics Persistence** — 🟢 now aggregated on schedule (the v1.0.0 dormancy is resolved).
- **Outbox / Governance / Approval / Memory** — 🟢 the trustworthy core.
