# Nexus

> **AI Orchestration Control Plane for Human-Governed Autonomous Execution**

[![Status](https://img.shields.io/badge/status-pre--alpha-orange)](blueprint/ROADMAP.md)
[![Version](https://img.shields.io/badge/version-0.1.0-blue)](CHANGELOG.md)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## What is Nexus?

Nexus is a **production-grade AI Orchestration Control Plane** designed to act as a persistent digital operations manager.

It is **not** a chatbot. It is **not** a Discord bot project. It is **not** a wrapper around an LLM.

Nexus is a deterministic, auditable, and recoverable orchestration system that coordinates:

- **Tasks** — creation, lifecycle, prioritization
- **Approvals** — governance workflows, audit trails
- **Agent Execution** — Gemini CLI, Claude Code, Hermes Agent
- **Research** — autonomous monitoring, paper tracking, AI news
- **Communication** — Discord, Email (future: WhatsApp, Slack)
- **Scheduling** — cron-based automation, reminders, escalations
- **Memory** — persistent state, workflow recovery, audit history

> **Conversation is a feature. Orchestration is the product.**

---

## Core Philosophy

```
AI should assist execution.
AI should not control execution.
Human governance remains the final authority.
All execution paths must remain observable, auditable, and interruptible.
```

- **Determinism over cleverness** — routing, workflows, and decisions are rule-based, not LLM-dependent
- **Persistence over convenience** — every important state must survive restarts
- **Governance over automation** — humans approve execution; Nexus coordinates it
- **Auditability over speed** — every action produces a traceable event

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
        │  Validate · Authenticate│
        └────────────┬────────────┘
                     │
                     ▼
        ┌─────────────────────────┐
        │      NEXUS CORE         │
        │  Task Engine            │
        │  Approval Engine        │
        │  Agent Router           │
        │  Rule Engine            │
        │  Workflow Orchestrator  │
        └──────┬──────┬──────┬────┘
               │      │      │
         Memory  Sched  Intel
               │      │      │
               ▼      ▼      ▼
        ┌─────────────────────────┐
        │    EXECUTION LAYER      │
        │  Gemini CLI │ Claude    │
        │  Hermes Agent │ ...     │
        └─────────────────────────┘
```

See [docs/01_ARCHITECTURE.md](docs/01_ARCHITECTURE.md) for the full architectural specification.

---

## Tech Stack

| Concern | Technology |
|---|---|
| Runtime | Python 3.11+ |
| API Framework | FastAPI |
| ORM | SQLAlchemy |
| Validation | Pydantic v2 |
| Database (MVP) | SQLite → PostgreSQL |
| Scheduler | APScheduler |
| Discord | discord.py |
| Email | SMTP via Python |
| LLM Gateway | OpenRouter |
| Logging | structlog |
| Testing | pytest |
| Containerization | Docker |
| CI | GitHub Actions |

---

## Project Structure

```
nexus/
├── docs/                    # Source of truth documentation
├── blueprint/               # Living memory: roadmap, decisions, progress
├── nexus/                   # Application source
│   ├── core/                # Nexus Core: orchestrator, engines, routers
│   ├── communication/       # Discord, Email adapters
│   ├── gateway/             # Event Gateway
│   ├── memory/              # Memory Layer: models, manager, repositories
│   ├── scheduling/          # APScheduler integration
│   ├── intelligence/        # Model Router, OpenRouter adapter
│   ├── execution/           # Execution Engine, runners
│   └── agents/              # Agent definitions (Research, Planning, Execution...)
├── tests/                   # Test suite
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── config/                  # Configuration files
│   ├── repositories.yaml    # Allowed repository registry
│   └── settings.yaml        # Environment configuration
├── templates/               # Email HTML templates
│   └── email/
├── scripts/                 # Utility scripts
├── docker/                  # Docker configuration
├── .github/                 # GitHub Actions CI
└── alembic/                 # Database migrations
```

---

## Development Status

| Phase | Name | Status |
|---|---|---|
| Phase 0 | Project Foundation | 🔲 Pending |
| Phase 1 | Core Infrastructure | 🔲 Pending |
| Phase 2 | Task Management | 🔲 Pending |
| Phase 3 | Approval Engine | 🔲 Pending |
| Phase 4 | Execution Runtime | 🔲 Pending |
| Phase 5 | Research Automation | 🔲 Pending |
| Phase 6 | Intelligence Reporting | 🔲 Pending |
| Phase 7 | Production Hardening | 🔲 Pending |

See [blueprint/ROADMAP.md](blueprint/ROADMAP.md) for the detailed phased execution plan.

---

## Getting Started

> ⚠️ Nexus is in pre-alpha. Setup instructions will be published when Phase 0 is complete.

### Prerequisites

- Python 3.11+
- Docker
- Discord Bot Token
- OpenRouter API Key
- SMTP credentials

### Quick Start

```bash
# Clone the repository
git clone https://github.com/hill-patel/nexus.git
cd nexus

# Create environment
cp config/settings.example.yaml config/settings.yaml
# Edit settings.yaml with your credentials

# Install dependencies
pip install -e ".[dev]"

# Initialize database
alembic upgrade head

# Run
python -m nexus
```

---

## Documentation

| Document | Purpose |
|---|---|
| [00_BRIEF.md](docs/00_BRIEF.md) | Executive summary and vision |
| [01_ARCHITECTURE.md](docs/01_ARCHITECTURE.md) | Full architectural specification |
| [02_TECH_STACK.md](docs/02_TECH_STACK.md) | Technology choices |
| [03_AGENT_DESIGN.md](docs/03_AGENT_DESIGN.md) | Agent taxonomy and design |
| [04_INTEGRATION_SPECS.md](docs/04_INTEGRATION_SPECS.md) | Integration contracts |
| [05_CRITICAL_CONSTRAINTS.md](docs/05_CRITICAL_CONSTRAINTS.md) | Non-negotiable constraints |
| [06_DEVELOPMENT_PHASES.md](docs/06_DEVELOPMENT_PHASES.md) | Implementation roadmap |
| [07_HERMES_AGENT.md](docs/07_HERMES_AGENT.md) | External references |
| [08_MEMORY_ARCHITECTURE.md](docs/08_MEMORY_ARCHITECTURE.md) | Memory system design |
| [RULES.md](docs/RULES.md) | Project rules and operating standards |

---

## Blueprint (Living Memory)

The `blueprint/` directory is the project's living memory system.

All phases, action points, decisions, architectural changes, and progress are tracked there.

See [blueprint/README.md](blueprint/README.md) for the blueprint structure.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.

See [docs/RULES.md](docs/RULES.md) for project rules and operating standards.

---

## Owner

**Hill Patel** — AI Engineer, Technical Operator, Builder

---

## North Star

> Nexus should eventually become a trusted operational control plane that continuously manages tasks, context, approvals, research, and execution while remaining transparent, recoverable, and governed by human intent.
