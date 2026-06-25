# Changelog

All notable changes to Nexus will be documented in this file.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)

> Reconstructed in AP-104 (v1.0.1) from the git history and blueprint implementation reports, after the
> onboarding audit found the changelog had omitted the actual v1.0.0 release. See
> [release-history-reconstruction.md](blueprint/implementations/v1.0.1/release-history-reconstruction.md).

---

## [1.1.0] — 2026-06-25 — "Containment"

Pilot operational release. Validated through a **real operational bring-up** (no mocks) — boot,
onboarding, scheduler, email, research, briefing, runtime, recovery, and Discord all exercised on
real infrastructure (**9/9 stages live-validated**). Classified **Pilot Ready** (not Production
Ready). Full evidence in `blueprint/implementations/v1.1.0/`.

### Branding

- **Hermes → Nexus Agent.** The autonomous planning/research runtime is renamed throughout code,
  tests, ADRs, and documentation. Registry id is now `nexus`; runtime records persist `runtime="nexus"`.
  `nexus/execution/runners/hermes.py` → `nexus_agent.py` and `hermes_tools.py` → `nexus_agent_tools.py`
  (git history preserved). Third-party Nous Research / `hermes-agent` references and historical tags
  (`hermes-experimental`, `hermes-pilot`) were intentionally **not** renamed.

### Architecture

- No architectural changes. Runtime registry, governance gates, sandbox boundary, scheduler ports,
  and memory/event-sourcing boundaries preserved. ADR history intact.

### Runtime

- **Nexus Agent: Experimental → Pilot.** Fail-fast initialization (refuse to start without an LLM
  capability), operator-tunable `execution.agent_max_steps`, honest terminal lifecycle
  (`completed`/`failed`/`timed_out`/`cancelled`), cancellation wiring, and `resume_goal`
  checkpoint recovery (H-2/H-4).
- **Multi-provider LLM gateway** — Groq → Zenmux → OpenRouter (free models) fallback chain;
  resilient to single-provider 402/429 (`nexus/intelligence/openrouter.py`).
- Orchestrator exit-status finalization honors the agent's truthful terminal status
  (`resolve_exit_status`, H-4).

### Governance

- A-001 fail-closed owner authorization verified live at boot; `RepositoryValidated` /
  `RuntimeAuthorized` audited per execution. Config now also reads `DISCORD_OWNER_ID` (operator-
  friendly alias) for owner-id resolution.

### Sandbox

- **Pilot Safe** (Track S): default-secure (`enabled=False`, `provider=local`, `network=none`,
  `fs=restricted`), execution fails closed, S-3 startup gate enforced.

### Research

- Live-validated: 20 findings parsed from a live RSS feed, LLM-scored, and persisted
  (`research.completed`).

### Scheduler

- Live-validated: audited jobs executing (`scheduler.job.started:4` / `completed:4`) with metrics
  and failure isolation.

### Operational Validation

- New `python -m nexus onboard` — safe, read-only staged operator onboarding (`nexus/onboarding.py`).
- Email (SMTP) real delivery after a one-line double-STARTTLS fix
  (`nexus/communication/email/service.py`).
- Discord real gateway delivery (bot → guild → `#general`, message id confirmed).
- Recovery: interrupt → fresh-adapter resume → completion, no corruption, audit continuity.
- Config alignment: `NOTIFY_SMTP_*` / `NOTIFY_EMAIL_FROM` mapped into the email config so the
  existing SMTP service delivers without a parallel credential store. `.env` remained the single
  source of truth (never rewritten).

### Breaking Changes

- **None for persisted data or external APIs.** The runtime id `hermes` and runner type
  `hermes_agent` still resolve (registry alias + retained enum member). Source imports of
  `HermesRuntimeAdapter` still work via a module-level alias.
- Internal module paths changed: import the agent runtime from
  `nexus.execution.runners.nexus_agent` (the old `hermes` module path no longer exists).

### Migration Notes

- No database migration required. On a fresh deployment the schema is created from the current
  models (`create_all`); existing databases with the v1.1.0 task columns need no change.
- Operators using the singular `DISCORD_OWNER_ID` env key are now supported directly.
- LLM defaults changed to free OpenRouter models; set `GROQ_API_KEY` / `ZENMUX_API` to enable the
  full fallback chain, or supply a paid/BYOK OpenRouter key for sustained load.

### Known Issues

- Free-tier LLM rate-limits under sustained load (mitigated, not eliminated, by the fallback chain).
- `create_all`-only schema management; Alembic migrations incomplete (manual recreate handled drift).
- `.env` `DISCORD_*_CHANNEL` ids not yet read into `settings.discord.channels` (delivery works).
- Gemini / Claude runtimes remain generic shell runners (Experimental).
- No production web `SearchProvider` for agent tools.
- In-code version string (`nexus/__init__.py`, `pyproject.toml`) still reads `0.1.0` — pre-existing
  documented debt; source bump deferred to v1.2 (out of release-workstream scope).

---

## [1.0.1] — 2026-06-24 — "Alignment"

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

- **A-005** — Nexus runtime reality audit (AP-105).
- **A-006** — Sandbox safety review.

### Known issues / residual debt

- In-code version string (`nexus/__init__.py`, `pyproject.toml`) still reads `0.1.0` while the release
  tag is `v1.0.0` (source/config change, out of the documentation-only AP-104 scope).
- `/api/v1/status` reports subsystems as literal `"stub"`; health is a boot-time boolean, not live.
- Concrete Gemini/Claude runtimes are generic shell runners; Nexus contains simulated branches.
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
- **Runtime registry + adapter split** — CLI/Agent adapters for Gemini, Claude, and Nexus runtimes
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
  Nexus simulated behaviors (A-005); default-off sandbox isolation (A-006).

---

## [0.0.1] — 2026-06-19

### Added

- Repository initialized; `docs/` directory with foundational documents; initial `.git` repository.
