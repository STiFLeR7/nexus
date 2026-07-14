# Contributing

Thanks for working on Nexus. This guide covers the workflow and the standards
your change must meet. See [DEVELOPMENT.md](DEVELOPMENT.md) for setup and
[TESTING.md](TESTING.md) for the test approach.

---

## 1. Golden rule — the architecture is frozen

`nexus_core` implements a **ratified, frozen** architecture. The specs in
`docs/v2/`, the decisions in `adr/`, the logical specs in `contracts/`, and the
invariants in `docs/v2/99_ARCHITECTURAL_INVARIANTS.md` are authoritative.

**Do not** redesign abstractions, invent new ones, merge responsibilities,
bypass contracts, or edit an ADR as part of a code change. If your
implementation appears to conflict with the architecture, **stop and document
the conflict** (open an issue / ADR proposal) — do not silently change the
design. Code follows the architecture, not the other way around.

## 2. Branching & commits

- Branch from the active planning branch (e.g. `v1.2.0-planning`); PRs target
  `master`.
- Use **Conventional Commits**:

  ```
  feat(core): add X primitive
  fix(validation): correct relationship check for Y
  docs(development): clarify coverage policy
  test(domain): cover illegal Z transition
  chore(ci): pin ruff-pre-commit
  ```

- Keep commits focused and atomic. Do not bundle unrelated refactors.

## 3. Coding standards

These are enforced by the gate; internalizing them avoids churn:

- **Immutable domain objects.** Every model is a frozen Pydantic `DomainObject`
  with `extra="forbid"`. Sequence fields are `tuple`, not `list`.
- **References over embedding.** By-id pointers use `Reference`
  (`target_type` + `identifier`). No embedded object copies.
- **One canonical schema per object.** Enums live once in `contracts/`; never
  redefine them.
- **Dependency inversion.** Registries, events, and persistence are `Protocol`s.
  Higher layers depend on abstractions; the domain layer imports only
  `contracts`.
- **No infrastructure coupling** in `nexus_core`: no web framework, ORM,
  database, scheduler, runtime, or network. No global state or service locators.
- **Strict typing.** `mypy --strict` clean, PEP 695 generics, no stray `Any`,
  no unjustified `# type: ignore`.
- **Fail fast, never silently correct.** Validation raises on bad input.

## 4. The gate your PR must pass

Run locally before pushing:

```bash
make check
```

This must be green:

| Check | Requirement |
|-------|-------------|
| Ruff lint | `ruff check` clean (rules in `ruff.toml`) |
| Ruff format | `ruff format --check` clean |
| MyPy | `mypy nexus_core` strict, no errors |
| Tests | all pass |
| Coverage | branch coverage ≥ 95% (no artificial inflation) |
| Build | `uv build` succeeds |

Core CI (`.github/workflows/core-ci.yml`) re-runs the identical gate on the PR.
A PR cannot merge with a red gate.

## 5. Definition of done

- [ ] Conforms to the frozen contracts / ADRs / invariants (no design drift).
- [ ] New/changed behavior is covered by meaningful tests (positive **and**
      negative cases).
- [ ] `make check` passes locally.
- [ ] Docs updated if the change affects developer workflow or public surface.
- [ ] Conventional-commit messages; no `# type: ignore` / `# noqa` without an
      inline justification.

## 6. Scope boundaries (Phase 1 foundation)

The following are **later phases** and must not be implemented against the
foundation in a quality/foundation PR: event bus, persistence backends,
orchestration, planning, runtime, and APIs. The foundation provides the
primitives those phases build on — it does not contain them.
