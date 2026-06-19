# Nexus Blueprint

> The living memory system for the Nexus project.

---

## Purpose

The `blueprint/` directory is the **single source of truth for project execution**.

Every implementation decision, architectural change, phase status, action point, bug, and resolution is recorded here.

**Documentation is not optional. Documentation is part of implementation.**

---

## Structure

```
blueprint/
├── README.md                  # This file
├── ROADMAP.md                 # Phased execution plan (canonical)
├── STATUS.md                  # Current project status snapshot
├── DECISIONS/                 # Architectural Decision Records (ADRs)
│   ├── ADR-001-tech-stack.md
│   ├── ADR-002-database-choice.md
│   └── ADR-003-pi-evaluation.md
├── GAPS_AND_RISKS.md          # Identified gaps, risks, and open questions
├── phases/                    # Phase-by-phase implementation memory
│   ├── phase-0/
│   │   ├── OVERVIEW.md
│   │   └── AP-001/
│   │       ├── SPEC.md
│   │       ├── IMPLEMENTATION.md
│   │       ├── DECISIONS.md
│   │       └── STATUS.md
│   ├── phase-1/
│   └── ...
└── references/                # Evaluated external references
    ├── pi-evaluation.md
    ├── hermes-evaluation.md
    ├── gemini-cli-evaluation.md
    └── claude-code-evaluation.md
```

---

## How to Use

### Recording a Decision

Create or update a file under `blueprint/DECISIONS/ADR-NNN-title.md`.

Use the ADR template:

```markdown
# ADR-NNN: Title

Date: YYYY-MM-DD
Status: Proposed | Accepted | Superseded
Supersedes: ADR-NNN (if applicable)

## Context
What situation prompted this decision?

## Decision
What was decided?

## Consequences
What are the trade-offs and implications?
```

### Recording Phase Progress

Each phase has its own directory under `blueprint/phases/phase-N/`.

Each Action Point (AP) within a phase has its own directory.

Template for AP status:

```markdown
# AP-NNN: Title

Phase: N
Status: Not Started | In Progress | Complete | Blocked

## Objective
...

## Implementation Notes
...

## Tests
...

## Decisions Made
...

## Open Questions
...
```

### Recording a Risk or Gap

Add to `blueprint/GAPS_AND_RISKS.md`:

```markdown
## GAP-NNN: Title

Category: Missing Spec | Architectural Risk | Integration Gap | ...
Severity: Critical | High | Medium | Low
Status: Open | Resolved | Accepted

### Description
...

### Impact
...

### Resolution
...
```

---

## Memory Rules

1. **Never delete** — archive instead
2. **Always date** — every document has a date
3. **Always link** — cross-reference related APs and decisions
4. **Always resolve** — open questions must eventually close
5. **Always commit** — blueprint changes committed with implementation

---

## Current Status

See [STATUS.md](STATUS.md) for the current project snapshot.

See [ROADMAP.md](ROADMAP.md) for the full execution plan.

See [GAPS_AND_RISKS.md](GAPS_AND_RISKS.md) for identified risks.
