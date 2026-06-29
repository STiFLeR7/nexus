# Development Guide

How to set up, run, and work on Nexus locally. For testing specifics see
[TESTING.md](TESTING.md); for contribution rules see [CONTRIBUTING.md](CONTRIBUTING.md).

---

## 1. Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.12+ | The project targets 3.12 (`requires-python = ">=3.12"`). |
| [uv](https://docs.astral.sh/uv/) | latest | Dependency manager + runner. Installs Python, syncs the locked env, runs tools. |
| Git | any recent | Line endings are normalized to LF via `.gitattributes`. |
| `make` | optional | Convenience task runner. Not required — every target is a thin `uv run` wrapper you can call directly. |

## 2. One-time setup

```bash
git clone https://github.com/STiFLeR7/nexus.git
cd nexus

# Install all dependencies (runtime + dev) from the lockfile, and register hooks.
make install
# equivalently, without make:
#   uv sync
#   uv run pre-commit install
```

That is the entire onboarding. `uv sync` provisions the interpreter and the exact
locked dependency set; `pre-commit install` wires the local quality gate so it
runs automatically on every commit.

## 3. Repository layout (relevant to development)

```
nexus_core/        Phase 1 foundation — frozen contracts, immutable domain
                   models, validation, registry/event/persistence interfaces,
                   state primitives. THIS is the engineering baseline.
nexus/             Legacy v1 application package (separate CI in ci.yml).
tests/unit/nexus_core/   Unit tests for the foundation.
docs/v2/           Frozen architecture (specs).
adr/               Ratified Architecture Decision Records (frozen).
contracts/         Frozen logical contract specs.
blueprint/v2/      Engineering blueprints / roadmap.
```

`nexus_core` is **additive** and never imports from `nexus/`. Its dependency
direction is one-way and acyclic: `contracts → domain → {validation, events,
registries, persistence, state}`. Nothing in it imports a web framework, ORM,
database, or runtime.

## 4. Daily workflow

```bash
make test          # fast inner loop — run the core suite
make check         # full local gate before pushing (lint+format+types+cov)
```

A typical change:

1. Make your edit (respecting the frozen architecture — see CONTRIBUTING.md).
2. `make test` for fast feedback.
3. `make check` to run the complete gate locally.
4. Commit — pre-commit hooks run automatically and may auto-fix formatting.
5. Push and open a PR — Core CI re-runs the same gate.

## 5. Make targets

| Target | What it does |
|--------|--------------|
| `make install` | Sync deps + install pre-commit hooks |
| `make lint` | Ruff lint (no autofix) |
| `make format` | Ruff auto-format in place |
| `make format-check` | Verify formatting (CI mode) |
| `make typecheck` | MyPy strict on `nexus_core` |
| `make test` | Run the core test suite (fast) |
| `make test-cov` | Tests + coverage gate (term/xml/html) |
| `make check` | **Full gate** — lint, format-check, typecheck, test-cov |
| `make pre-commit` | Run all pre-commit hooks against all files |
| `make build` | Build sdist + wheel |
| `make clean` | Remove caches and generated reports |

## 6. Quality gates

The same four checks run locally (`make check`), in pre-commit, and in Core CI:

| Gate | Command | Rule |
|------|---------|------|
| Lint | `ruff check` | Configured in `ruff.toml` (single source of truth). |
| Format | `ruff format --check` | LF line endings, double quotes, 100 cols. |
| Types | `mypy nexus_core` | `--strict` + `pydantic.mypy` plugin. No `Any` leaks. |
| Tests + coverage | `pytest --cov-fail-under=95` | Branch coverage, ≥95% floor. |

These are **non-negotiable**: a future change cannot regress architectural
correctness or code quality without failing automated checks.

## 7. Tooling configuration map

| Concern | File |
|---------|------|
| Project metadata, deps, pytest, coverage, mypy | `pyproject.toml` |
| Ruff lint + format (authoritative) | `ruff.toml` |
| Pre-commit hooks | `.pre-commit-config.yaml` |
| Core CI pipeline | `.github/workflows/core-ci.yml` |
| Legacy v1 CI | `.github/workflows/ci.yml` |
| Line-ending normalization | `.gitattributes` |
| Task shortcuts | `Makefile` |

> **Ruff note:** Ruff reads `ruff.toml` exclusively when it exists; a
> `[tool.ruff]` block in `pyproject.toml` would be silently ignored, so it is
> intentionally omitted to prevent configuration drift.

## 8. Windows notes

The development shell is bash-compatible (Git Bash / WSL). `make` is optional —
if it is unavailable, run the underlying commands directly, e.g.:

```bash
uv run ruff check nexus_core tests/unit/nexus_core
uv run mypy nexus_core
uv run pytest tests/unit/nexus_core --cov=nexus_core --cov-fail-under=95
```

Line endings are LF-canonical; `.gitattributes` + the `mixed-line-ending` hook
keep the working tree consistent across platforms.
