# Nexus — Project Roadmap

Version: 0.1
Last Updated: 2026-06-19
Status: Active

---

## Vision

Nexus becomes a trusted operational control plane that continuously manages tasks, context, approvals, research, and execution while remaining transparent, recoverable, and governed by human intent.

---

## Release Strategy

| Release | Target | Scope |
|---|---|---|
| v0.1 | MVP | Foundation + Tasks + Approvals + Execution + Discord + Email + Memory |
| v0.5 | Operational | Research + Reporting + Reliability + Operational Maturity |
| v1.0 | Production | Persistent Memory + Advanced Governance + Extensible Integrations |

---

## Development Philosophy

Nexus is built **vertically**, not horizontally.

- Build one complete workflow → test it → validate it → expand
- Every phase must produce a usable, tested system
- No phase ends with partially integrated functionality
- Nothing progresses if the previous phase is unstable

---

## Phase Overview

```
Phase 0  →  Project Foundation
Phase 1  →  Core Infrastructure
Phase 2  →  Task Management
Phase 3  →  Approval Engine
Phase 4  →  Execution Runtime
Phase 5  →  Research Automation
Phase 6  →  Intelligence Reporting
Phase 7  →  Production Hardening
Phase 8  →  Pi Evaluation (Parallel)
Phase 9+ →  Extended Integrations (Post-MVP)
Phase 10 →  Advanced Memory (Future)
Phase 11 →  Multi-Agent Coordination (Future)
```

---

## Phase 0 — Project Foundation

**Goal:** Create production-ready project skeleton.

**Status:** ✅ Complete

### Action Points

| AP | Title | Status |
|---|---|---|
| AP-001 | Repository structure and directory layout | ✅ |
| AP-002 | Python project setup (pyproject.toml, dependencies) | ✅ |
| AP-003 | Configuration system (Pydantic settings, YAML config) | ✅ |
| AP-004 | Structured logging framework (structlog) | ✅ |
| AP-005 | Database setup (SQLAlchemy + SQLite + Alembic migrations) | ✅ |
| AP-006 | Testing framework (pytest, fixtures, factories) | ✅ |
| AP-007 | Docker setup (Dockerfile, docker-compose) | ✅ |
| AP-008 | CI pipeline (GitHub Actions) | ✅ |
| AP-009 | Repository registry (config/repositories.yaml) | ✅ |
| AP-010 | FastAPI skeleton (health check, startup, shutdown) | ✅ |

### Exit Criteria

- [x] Application boots successfully
- [x] Tests execute and pass
- [x] Database initializes with migrations
- [x] CI pipeline passes
- [x] Docker image builds
- [x] Documentation exists


---

## Phase 1 — Core Infrastructure

**Goal:** Build Nexus Core primitives.

**Status:** 🔲 Not Started

### Action Points

| AP | Title | Status |
|---|---|---|
| AP-101 | Event Gateway (normalization, validation, routing) | 🔲 |
| AP-102 | Nexus Event schema and type system | 🔲 |
| AP-103 | Memory Manager (central state controller) | 🔲 |
| AP-104 | Memory models (Task, Approval, Execution, Research, Audit) | 🔲 |
| AP-105 | Audit Layer (immutable event log) | 🔲 |
| AP-106 | Workflow Orchestrator skeleton | 🔲 |
| AP-107 | Task Engine (creation, lifecycle state machine) | 🔲 |
| AP-108 | Correlation ID propagation | 🔲 |

### Exit Criteria

- [ ] Tasks created programmatically
- [ ] Tasks persist across restart
- [ ] Events persist with full audit trail
- [ ] Audit records exist for all state transitions
- [ ] System survives restart without state loss

---

## Phase 2 — Task Management

**Goal:** Establish complete task lifecycle.

**Status:** 🔲 Not Started

### Action Points

| AP | Title | Status |
|---|---|---|
| AP-201 | Task lifecycle state machine (Created→Queued→Active→Blocked→Complete) | 🔲 |
| AP-202 | Task CRUD operations with persistence | 🔲 |
| AP-203 | Task priority system | 🔲 |
| AP-204 | Task history and timeline | 🔲 |
| AP-205 | Task query API | 🔲 |
| AP-206 | Task status tracking with audit trail | 🔲 |

### Exit Criteria

- [ ] Tasks persist across restarts
- [ ] Full task history exists
- [ ] Task audit trail is complete and queryable
- [ ] All lifecycle transitions are recorded

---

## Phase 3 — Approval Engine

**Goal:** Introduce governance through approval workflows.

**Status:** 🔲 Not Started

### Action Points

| AP | Title | Status |
|---|---|---|
| AP-301 | Approval Engine core (request, record, track) | 🔲 |
| AP-302 | Discord adapter (bot, channel routing, embeds) | 🔲 |
| AP-303 | Discord approval card (embed with Approve/Reject buttons) | 🔲 |
| AP-304 | Approval state persistence and recovery | 🔲 |
| AP-305 | Approval expiration policy | 🔲 |
| AP-306 | Approval audit trail | 🔲 |
| AP-307 | Discord failure handling (retry, reconnect, backoff) | 🔲 |
| AP-308 | Discord channel structure setup | 🔲 |

### Exit Criteria

- [ ] Approval state persists across restarts
- [ ] Approval audit is complete
- [ ] Execution cannot bypass approval check
- [ ] Discord disconnection does not lose approval state

---

## Phase 4 — Execution Runtime

**Goal:** Controlled, auditable agent execution.

**Status:** 🔲 Not Started

### Action Points

| AP | Title | Status |
|---|---|---|
| AP-401 | Execution Engine (runtime abstraction layer) | 🔲 |
| AP-402 | Gemini CLI Runner | 🔲 |
| AP-403 | Claude Code Runner | 🔲 |
| AP-404 | Repository validation (allow-list enforcement) | 🔲 |
| AP-405 | Execution audit trail (start, complete, fail events) | 🔲 |
| AP-406 | Execution result persistence | 🔲 |
| AP-407 | Hermes Agent evaluation and integration decision | 🔲 |

### Exit Criteria

- [ ] Gemini CLI executes with structured input
- [ ] Claude Code executes with structured input
- [ ] Results persist with full metadata
- [ ] Execution history is complete and auditable
- [ ] Non-approved repositories are rejected

---

## Phase 5 — Research Automation

**Goal:** Autonomous, unattended information gathering.

**Status:** 🔲 Not Started

### Action Points

| AP | Title | Status |
|---|---|---|
| AP-501 | Research Agent (OpenRouter-backed) | 🔲 |
| AP-502 | OpenRouter integration (model router, fallback) | 🔲 |
| AP-503 | Model Router (Nemotron → OwlAlpha → DeepSeek fallback) | 🔲 |
| AP-504 | Circuit breaker for OpenRouter | 🔲 |
| AP-505 | Scheduled research jobs (APScheduler) | 🔲 |
| AP-506 | Research storage (knowledge memory) | 🔲 |
| AP-507 | Research result persistence | 🔲 |

### Exit Criteria

- [ ] Research runs unattended on schedule
- [ ] Research persists with history
- [ ] Fallback model chain operates correctly
- [ ] Reports generate successfully

---

## Phase 6 — Intelligence Reporting

**Goal:** Operational awareness through automated reports.

**Status:** 🔲 Not Started

### Action Points

| AP | Title | Status |
|---|---|---|
| AP-601 | Daily Summary Engine | 🔲 |
| AP-602 | Email integration (SMTP, templates) | 🔲 |
| AP-603 | Email templates (daily_summary, research_digest, failure_alert, etc.) | 🔲 |
| AP-604 | Discord report delivery | 🔲 |
| AP-605 | Report persistence | 🔲 |
| AP-606 | Scheduler setup (daily trigger at configured time) | 🔲 |

### Exit Criteria

- [ ] Reports generate automatically on schedule
- [ ] Reports deliver via Discord and Email
- [ ] Reports persist with history
- [ ] Reports are auditable

---

## Phase 7 — Production Hardening

**Goal:** Production-ready reliability and observability.

**Status:** 🔲 Not Started

### Action Points

| AP | Title | Status |
|---|---|---|
| AP-701 | Retry policies for all critical operations | 🔲 |
| AP-702 | Circuit breakers (Discord, OpenRouter, Email) | 🔲 |
| AP-703 | Health check endpoints | 🔲 |
| AP-704 | Backup strategy for SQLite | 🔲 |
| AP-705 | Recovery procedures (runbook) | 🔲 |
| AP-706 | Metrics collection | 🔲 |
| AP-707 | Performance validation | 🔲 |
| AP-708 | Security review | 🔲 |

### Exit Criteria

- [ ] System tolerates all expected failure modes
- [ ] System recovers from restart correctly
- [ ] Health checks operational
- [ ] Monitoring operational

---

## Phase 8 — Pi Evaluation (Parallel Track)

**Goal:** Determine orchestration strategy before implementing custom orchestration.

**Status:** 🔲 Not Started (should run early)

### Action Points

| AP | Title | Status |
|---|---|---|
| AP-801 | Clone and analyze https://github.com/earendil-works/pi | 🔲 |
| AP-802 | Evaluate Pi against Nexus requirements | 🔲 |
| AP-803 | Document adoption decision (ADR) | 🔲 |

### Decision Outcomes

- Option A: Adopt Pi as orchestration layer
- Option B: Partial integration
- Option C: Custom orchestration

---

## Post-MVP Phases

| Phase | Name | Status |
|---|---|---|
| Phase 9 | Extended Integrations (WhatsApp, Slack, GitHub, etc.) | 🔲 Future |
| Phase 10 | Advanced Memory (PostgreSQL, Vector, Knowledge Graph) | 🔲 Future |
| Phase 11 | Multi-Agent Coordination (Hierarchical Agents) | 🔲 Future |

---

## Status Legend

| Symbol | Meaning |
|---|---|
| 🔲 | Not Started |
| 🔄 | In Progress |
| ✅ | Complete |
| ❌ | Blocked |
| ⚠️ | Needs Review |
