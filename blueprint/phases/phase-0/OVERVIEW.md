# Phase 0 — Project Foundation

Status: 🔲 Not Started
Start Date: TBD
Target Completion: TBD

---

## Goal

Create a production-ready project skeleton that proves the system can boot, test, and run — before any orchestration logic exists.

## Philosophy

Every line of code written in Phase 0 will live forever in the codebase. Set high standards from day one.

## Deliverables

- [ ] Repository structure and directory layout
- [ ] Python project setup (pyproject.toml, all dependencies)
- [ ] Configuration system (Pydantic Settings, YAML)
- [ ] Structured logging framework (structlog)
- [ ] Database setup (SQLAlchemy 2.0 async + SQLite + Alembic)
- [ ] Testing framework (pytest, async support, factories)
- [ ] Docker setup (Dockerfile, docker-compose)
- [ ] CI pipeline (GitHub Actions)
- [ ] Repository registry (config/repositories.yaml)
- [ ] FastAPI skeleton (health check, startup, shutdown lifecycle)
- [ ] Pi evaluation (parallel track — see ADR-003)
- [ ] Hermes investigation (parallel track)

## Action Points

| AP | Title | Status |
|---|---|---|
| AP-001 | Repository structure | 🔲 |
| AP-002 | Python project (pyproject.toml) | 🔲 |
| AP-003 | Configuration system | 🔲 |
| AP-004 | Structured logging | 🔲 |
| AP-005 | Database setup + migrations | 🔲 |
| AP-006 | Testing framework | 🔲 |
| AP-007 | Docker setup | 🔲 |
| AP-008 | CI pipeline | 🔲 |
| AP-009 | Repository registry | 🔲 |
| AP-010 | FastAPI skeleton | 🔲 |
| AP-011 | Pi evaluation (parallel) | 🔲 |
| AP-012 | Hermes investigation (parallel) | 🔲 |

## Exit Criteria

- [ ] `python -m nexus` boots without errors
- [ ] `pytest` runs and all tests pass
- [ ] Database initializes with Alembic migrations
- [ ] GitHub Actions CI passes on push
- [ ] `docker-compose up` starts the application
- [ ] `docs/` and `blueprint/` are populated
- [ ] Pi evaluation findings documented

## Decisions Made

See `blueprint/DECISIONS/` for all ADRs recorded during this phase.

## Implementation Notes

*(To be filled as implementation proceeds)*

## Blockers

- OQ-001: Tech stack confirmation pending
- OQ-005: Pi evaluation sequencing decision pending
- OQ-008: Secrets management approach pending
