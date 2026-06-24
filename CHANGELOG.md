# Changelog

All notable changes to Nexus will be documented in this file.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)

> Reconstructed in AP-104 (v1.0.1) from the git history and blueprint implementation reports, after the
> onboarding audit found the changelog had omitted the actual v1.0.0 release. See
> [release-history-reconstruction.md](blueprint/implementations/v1.0.1/release-history-reconstruction.md).

---

## [1.0.1] — Unreleased — "Alignment"

A correctness, safety, and operational-completeness release. **No new features.** Every change traces
to an accepted onboarding-audit finding (A-001…A-006).

### Fixed

- **A-001 — Fail-open owner authentication.** Approval authorization now **fails closed**: the
  application refuses to start when no `discord.owner_ids` are configured, and the approval engine
  rejects authorization when owners are unset. (AP-102: `nexus/api.py`, `nexus/approvals/service.py`.)
- **A-002 — Execution timeout mismatch.** Runtimes previously read a non-existent config field and
  silently fell back to 300s. Added `resolve_execution_timeout(...)` honoring the ADR-010 per-runtime
  tiers and clamping to `execution.hard_limit`. (AP-102: `nexus/execution/runners/`.)

### Added

- **A-003 — Scheduler foundation.** APScheduler-backed, single-node scheduler behind a replaceable
  `SchedulerPort`, with six audited jobs — `research_collection`, `daily_briefing`,
  `approval_expiration_sweep`, `metrics_aggregation`, `outbox_health` (read-only),
  `checkpoint_health` (read-only). New `SCHEDULER_JOB_STARTED/COMPLETED/FAILED/SKIPPED` events,
  additive `SchedulingConfig`, and read-only `OutboxHealthService` / `CheckpointHealthService`.
  (AP-103B: `nexus/scheduling/`, `nexus/gateway/outbox_health.py`, `nexus/memory/checkpoint_health.py`.)
- **A-004 — Documentation alignment.** Realigned `README.md`, `blueprint/STATUS.md`,
  `blueprint/ROADMAP.md`, this changelog, and the blueprint landing page to reality; added
  `repository-state-map.md`, `documentation-drift-analysis.md`, `architecture-status-summary.md`,
  `release-history-reconstruction.md`, and the alignment reports. (AP-104.)

### Pending

- **A-005** — Hermes runtime reality audit (AP-105).
- **A-006** — Sandbox safety review.

### Known issues / residual debt

- In-code version string (`nexus/__init__.py`, `pyproject.toml`) still reads `0.1.0` while the release
  tag is `v1.0.0` (source/config change, out of the documentation-only AP-104 scope).
- `/api/v1/status` reports subsystems as literal `"stub"`; health is a boot-time boolean, not live.
- Concrete Gemini/Claude runtimes are generic shell runners; Hermes contains simulated branches.
- Default sandbox `provider="local"` provides no isolation.
- Alembic migrations incomplete; `create_all` is the current schema source.

---

## [1.0.0] — 2026-06 — "Operational Intelligence"

> Git tag `v1.0.0` (`4566020`, `aa3e527`). The first released governed-execution control plane.

### Added

- **Approval system** — un-bypassable, database-backed approval gate fronting all execution, fully
  audited (`nexus/execution/service.py`, `nexus/approvals/service.py`).
- **Runtime governance** — 11-gate governance authorizing every execution decision
  (`nexus/execution/governance.py`).
- **Runtime registry + adapter split** — CLI/Agent adapters for Gemini, Claude, and Hermes runtimes
  (AP-301…AP-304; `nexus/execution/runners/`).
- **Event-sourced memory** — immutable `audit_log`, checkpoint replay, resumable context
  (`nexus/memory/`).
- **Transactional + communication outbox** — lease-based delivery with backoff, dead-lettering, and
  audit on success/failure (`nexus/gateway/`).
- **Research engine** — crawl→dedup→summarize→persist with resumable runs (RSS/Atom).
- **Daily briefing engine** — operational briefing generation and dispatch.
- **Metrics persistence** — metric collection and flush.
- **Task management** — full guarded lifecycle with Discord CRUD.
- **Discord + Email communication** adapters; OpenRouter intelligence gateway.
- Accepted onboarding audit (`blueprint/onboarding/`, `NEXUS_FIRST_IMPRESSION.md`), maturity 6.0/10.

### Known issues at release (addressed in v1.0.1)

- Fail-open owner authentication (A-001); execution-timeout field bug (A-002); **no scheduler** so
  research/briefing/metrics/expiry never fired autonomously (A-003); documentation drift (A-004);
  Hermes simulated behaviors (A-005); default-off sandbox isolation (A-006).

---

## [0.0.1] — 2026-06-19

### Added

- Repository initialized; `docs/` directory with foundational documents; initial `.git` repository.
