# Nexus

> **AI Orchestration Control Plane for Human-Governed Autonomous Execution**

[![Status](https://img.shields.io/badge/status-released%20(pilot)-brightgreen)](blueprint/STATUS.md)
[![Version](https://img.shields.io/badge/release-v1.0.0%20%2B%20v1.0.1%20alignment-blue)](CHANGELOG.md)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

> **Release status:** Nexus is **released as v1.0.0** ("Operational Intelligence", git tag `v1.0.0`)
> and is currently in the **v1.0.1 "Alignment"** line — a correctness/safety/operational-completeness
> pass (no new features). It is **pilot-ready as an attended, single-operator governed-execution
> console**, with a now-operational single-node autonomy layer. For the authoritative, per-subsystem
> status see **[architecture-status-summary.md](blueprint/implementations/v1.0.1/architecture-status-summary.md)**.

---

## What is Nexus?

Nexus is an **AI Orchestration Control Plane** that acts as a persistent, governed digital operations
manager.

It is **not** a chatbot. It is **not** a Discord bot project. It is **not** a wrapper around an LLM.

Nexus is a deterministic, auditable, and recoverable orchestration system that coordinates:

- **Tasks** — creation, lifecycle, prioritization (✅ production-ready)
- **Approvals** — un-bypassable, DB-backed governance workflows with audit trails (✅ production-ready)
- **Agent Execution** — runtime registry over Gemini / Claude / Nexus adapters (🟡 governed core ready; Gemini/Claude stubbed, Nexus Experimental)
- **Research** — autonomous monitoring (✅ engine built, now scheduled; activates when feeds are configured)
- **Communication** — Discord, Email (future: WhatsApp, Slack)
- **Scheduling** — APScheduler-driven jobs for research, briefings, expiry sweeps, metrics, health (✅ single-node, new in v1.0.1)
- **Memory** — event-sourced persistent state, checkpoint replay, immutable audit history (✅ production-ready)

> **Conversation is a feature. Orchestration is the product.**

---

## What problem does it solve?

It de-fragments AI operations. Instead of chatting in one tool, tracking tasks in another, approving
actions manually, and running agents from terminals with no audit trail, Nexus centralizes that
surface so one operator can delegate work, approve privileged actions in Discord, run agents against
allow-listed repositories, and keep a complete, recoverable record — all under continuous human
governance.

---

## Core Philosophy

```
AI should assist execution.
AI should not control execution.
Human governance remains the final authority.
All execution paths must remain observable, auditable, and interruptible.
```

- **Determinism over cleverness** — routing, workflows, and decisions are rule-based, not LLM-dependent
- **Persistence over convenience** — every important state survives restarts (event-sourced)
- **Governance over automation** — humans approve execution; Nexus coordinates it
- **Auditability over speed** — every action produces a traceable, immutable event

---

## Architecture Overview

```
          User (Director / Operator)
                     │
                     ▼
        ┌─────────────────────────┐
        │   COMMUNICATION LAYER   │
        │  Discord │ Email │ ...  │
        └────────────┬────────────┘
                     │
                     ▼
        ┌─────────────────────────┐
        │     EVENT GATEWAY       │
        │  Normalize · Route ·    │
        │  Transactional Outbox   │
        └────────────┬────────────┘
                     │
                     ▼
        ┌─────────────────────────┐
        │      NEXUS CORE         │
        │  Task Engine            │
        │  Approval Engine (gate) │
        │  Runtime Governance     │
        │  Workflow Orchestrator  │
        └──────┬──────┬──────┬────┘
               │      │      │
           Memory  Scheduler Intel
        (event-   (APSched)  (OpenRouter)
         sourced)    │
               │     ▼ jobs: research · briefing · approval-expiry
               │       · metrics-aggregation · outbox/checkpoint health
               ▼      ▼      ▼
        ┌─────────────────────────┐
        │    EXECUTION LAYER      │
        │  Runtime Registry +     │
        │  Adapters: Gemini /     │
        │  Claude / Nexus        │
        │  (11-gate governance)   │
        └─────────────────────────┘
```

See [docs/01_ARCHITECTURE.md](docs/01_ARCHITECTURE.md) for the design specification, and
[architecture-status-summary.md](blueprint/implementations/v1.0.1/architecture-status-summary.md) for
the **current built status** of every subsystem.

---

## Major Capabilities (current status)

| Capability | Status | Notes |
|---|---|---|
| Task management | ✅ Production Ready | Guarded lifecycle, locking, Discord CRUD, full audit |
| Approval workflows | ✅ Production Ready | Un-bypassable DB gate; **fail-closed** owner auth (v1.0.1) |
| Runtime governance (11-gate) | ✅ Production Ready | Audits every execution decision |
| Memory (event-sourced) | ✅ Production Ready | Immutable `audit_log` + checkpoint replay |
| Communication outbox | ✅ Production Ready | Lease-based, backoff, dead-letter, audited |
| Scheduler (single-node) | ✅ Operational | 6 audited jobs; **new in v1.0.1** |
| Metrics persistence | ✅ Operational | Collection + **scheduled aggregation/retention** (v1.0.1) |
| Research engine | 🟡 Operational (latent) | Built + scheduled; activates once `research_feeds` configured |
| Daily briefing engine | 🟡 Operational | Built + scheduled 08:00 (Asia/Kolkata) |
| Gemini / Claude runtimes | 🟠 Stubbed | Generic shell runners; real CLI binary integration pending |
| Nexus runtime | 🟠 Experimental | Honest: no prod mock, provider-backed search (`SearchProvider` DI), goal-derived planning, structured tool-calls, truthful outcomes (v1.1.0 H-2). Lifecycle safety (terminate/resume) = Pilot/H-4 |
| Sandbox isolation | 🟢 Pilot Safe | **Default-secure fail-closed** + boot-validated + workspace-confined (v1.1.0 Track S). Isolation opt-in (`provider=docker`); residual R-04/R-08/R-09 |

---

## Runtime Support

Execution flows through a **Runtime Registry** with a CLI/Agent **adapter split** and an 11-gate
governance layer that authorizes every run:

- **Gemini** (`gemini`) — CLI adapter (currently a governed generic shell runner).
- **Claude** (`claude`) — CLI adapter (currently a governed generic shell runner).
- **Nexus** — Agent adapter (autonomous loop). **Experimental** (v1.1.0 H-2): real model decisions via
  structured tool-calls, provider-backed search, goal-derived planning, truthful exit status. Not yet
  lifecycle-safe (no terminate/resume) — that is the Pilot bar (H-4).

The governance abstraction and registry are production-quality; the **concrete runtime behaviors are
still stubbed/mocked** and must not be represented as full CLI/agent integrations.

## Governance Model

Every governed execution must pass an **un-bypassable, database-backed approval gate**
(`nexus/execution/service.py`) and the **11-gate runtime governance** checks
(`nexus/execution/governance.py`), each decision written to the immutable `audit_log`. As of v1.0.1,
owner authorization **fails closed**: if no `discord.owner_ids` are configured, the application
**refuses to start** (no fail-open, no degraded mode).

## Research Engine

A production-grade crawl→dedup→summarize→persist pipeline with resumable runs. It is now driven by the
scheduler (`research_collection`, every 2h) but ships with **empty `research_feeds`**, so it safely
audited-skips until an operator configures feeds. Currently RSS/Atom only.

## Briefing Engine

Generates and dispatches the daily operational briefing, scheduled at **08:00 Asia/Kolkata**
(`daily_briefing`).

## Scheduler

APScheduler-backed, single-node, behind a replaceable `SchedulerPort`. Jobs invoke services only
(no business logic in jobs), every fire is audited (`SCHEDULER_JOB_STARTED/COMPLETED/FAILED/SKIPPED`):
`research_collection` · `daily_briefing` · `approval_expiration_sweep` · `metrics_aggregation` ·
`outbox_health` (read-only) · `checkpoint_health` (read-only). Multi-node coordination is designed but
future (see [scheduler-future-scaling.md](blueprint/implementations/v1.0.1/scheduler-future-scaling.md)).

## Sandboxing

Execution sandbox is configurable (`docker` / `local` / `mock`) and is **default-secure** as of
v1.1.0 Track S (**Pilot Safe**, `ADR-sandbox-pilot-safe`):

- **Fails closed by default.** With sandboxing disabled or an unrecognized provider, the manager
  **refuses to execute** rather than silently running on the host (no fail-open).
- **Boot-validated.** Startup aborts on an incoherent sandbox config or an unavailable
  policy-enforcing provider (Docker availability is probed at boot).
- **Honest enforcement.** Each execution is audited with whether the provider actually enforces the
  policy (`policy_enforced`); a host run is declared, never pretended.
- **Workspace-confined file tools.** Agent `read_file`/`write_file` are confined to the approved
  workspace (path traversal / absolute / symlink escapes fail closed).

Container isolation remains **opt-in**: set `sandbox.enabled=true`, `sandbox.provider=docker` (Docker
present), and ideally `filesystem_policy=readonly` before running untrusted commands. Running on the
host (`provider=local`) is possible only as a deliberate, startup-warned, audited choice. Residual
items: command-blacklist robustness (R-04, governance-owned), shell exec surface (R-08), and the
non-readonly default mount (R-09).

---

## Tech Stack

| Concern | Technology |
|---|---|
| Runtime | Python 3.12+ |
| API Framework | FastAPI (ASGI) |
| ORM | SQLAlchemy 2.x (async, aiosqlite) |
| Validation | Pydantic v2 / Pydantic Settings |
| Database | SQLite (WAL) → PostgreSQL (future) |
| Scheduler | APScheduler (AsyncIOScheduler) |
| Discord | discord.py |
| Email | SMTP / Resend |
| LLM Gateway | OpenRouter |
| Logging | structlog |
| Testing | pytest / pytest-asyncio |
| Tooling | ruff, mypy (strict), uv |
| Containerization | Docker |
| CI | GitHub Actions |

---

## Project Structure

```
nexus/
├── docs/                    # Design-intent documentation (target architecture)
├── blueprint/               # Living memory: status, roadmap, decisions, audits, implementations
│   ├── STATUS.md            # Current project status (authoritative)
│   ├── ROADMAP.md           # Reconstructed history + forward direction
│   ├── DECISIONS/           # 21 ADRs
│   ├── onboarding/          # Accepted v1.0.0 onboarding audit (reality source)
│   ├── implementations/     # Per-release implementation reports (incl. v1.0.1/)
│   ├── architecture/        # Architecture & design records
│   └── reports/             # Reviews, gap analyses, classifications
├── nexus/                   # Application source
│   ├── api.py               # FastAPI app + lifespan (DB, outbox, metrics, scheduler, Discord)
│   ├── core/                # types/events, exceptions, metrics, health
│   ├── approvals/           # Approval engine (fail-closed owner auth)
│   ├── execution/           # Approval gate, 11-gate governance, runners/
│   ├── gateway/             # Event gateway, outbox(es), outbox_health
│   ├── memory/              # Event-sourced manager, models, checkpoint_health
│   ├── intelligence/        # OpenRouter client / model routing
│   ├── communication/       # Discord, Email adapters
│   ├── scheduling/          # APScheduler foundation: scheduler, jobs, orchestrator
│   └── agents/              # Agent definitions
├── tests/                   # unit / integration / e2e
├── config/                  # repositories.yaml, settings.yaml
├── alembic/                 # Migrations (incomplete; create_all is current schema source)
└── .github/                 # CI
```

---

## Development Status

| Phase / Release | Status |
|---|---|
| Phase 0 — Project Foundation | ✅ Complete |
| Phase 1 — Core Infrastructure | ✅ Complete |
| Phase 2 — Task Management / MVP | ✅ Complete |
| Phase 3 — Execution Runtime, Registry & Governance | ✅ Complete |
| Phase 8 — Pi Evaluation (parallel) | ✅ Complete (ADR-003: custom orchestration) |
| **v1.0.0 — "Operational Intelligence"** | ✅ Released (tag `v1.0.0`) |
| **v1.0.1 — "Alignment"** | 🔄 In progress (A-001/A-002/A-003 done; A-004 this doc; A-005/A-006 pending) |
| Future — distributed scheduling, PostgreSQL, extra integrations | ⚪ Future |

See [blueprint/ROADMAP.md](blueprint/ROADMAP.md) for the full reconstructed history and direction.

---

## Getting Started

### Prerequisites

- Python 3.12+
- (Optional) Docker — required for sandbox isolation and the documented PostgreSQL path
- Discord Bot Token **and at least one owner ID** (the app fails closed without owners)
- OpenRouter API Key
- SMTP / Resend credentials (for email)

### Quick Start

```bash
# Clone
git clone https://github.com/hill-patel/nexus.git
cd nexus

# Install (editable, with dev extras)
pip install -e ".[dev]"        # or: uv pip install -e ".[dev]"

# Configure
cp config/settings.example.yaml config/settings.yaml   # edit credentials
# REQUIRED: set discord.owner_ids (or DISCORD_OWNERS) — startup fails closed if empty

# Run
python -m nexus
```

> **Note:** the schema is currently created at startup via `create_all`; Alembic migrations are
> incomplete. `alembic upgrade head` is not yet the authoritative path.

---

## Documentation

| Document | Purpose |
|---|---|
| [blueprint/STATUS.md](blueprint/STATUS.md) | **Current** project status (authoritative) |
| [architecture-status-summary.md](blueprint/implementations/v1.0.1/architecture-status-summary.md) | **Per-subsystem built status** (single source of truth) |
| [blueprint/ROADMAP.md](blueprint/ROADMAP.md) | Reconstructed history + forward direction |
| [NEXUS_FIRST_IMPRESSION.md](NEXUS_FIRST_IMPRESSION.md) | Accepted v1.0.0 onboarding audit summary |
| [blueprint/DECISIONS/](blueprint/DECISIONS/) | 21 Architectural Decision Records |
| [docs/00_BRIEF.md](docs/00_BRIEF.md) | Executive summary and vision |
| [docs/01_ARCHITECTURE.md](docs/01_ARCHITECTURE.md) | Architectural design specification |
| [docs/RULES.md](docs/RULES.md) | Project rules and operating standards |

> The numbered `docs/` are **design-intent** documents (target architecture). For what is **actually
> built today**, always defer to `architecture-status-summary.md`.

---

## Blueprint (Living Memory)

The `blueprint/` directory is the project's living memory and the **authoritative record** of status,
decisions, audits, and implementation history. See [blueprint/README.md](blueprint/README.md).

---

## Owner

**Hill Patel** — AI Engineer, Technical Operator, Builder

---

## North Star

> Nexus should become a trusted operational control plane that continuously manages tasks, context,
> approvals, research, and execution while remaining transparent, recoverable, and governed by human
> intent.
