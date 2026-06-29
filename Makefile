# =============================================================================
# Nexus — developer task runner
# =============================================================================
# Thin wrappers over `uv run` so local commands match CI exactly. Recipes assume
# a POSIX shell (Linux/macOS, or Git Bash / WSL on Windows). Windows users
# without `make` can run the underlying `uv run ...` commands directly — see
# docs/development/DEVELOPMENT.md.
# =============================================================================

# Packages and their tests (Phase 1 foundation + Phase 2 infrastructure).
PACKAGES := nexus_core nexus_infra
TESTS := tests/unit/nexus_core tests/unit/nexus_infra
COV_MIN := 95

.DEFAULT_GOAL := help
.PHONY: help install lint format format-check typecheck test test-cov \
        coverage-html check pre-commit build clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install: ## Install all dependencies + register pre-commit hooks
	uv sync
	uv run pre-commit install

lint: ## Ruff lint (no autofix)
	uv run ruff check $(PACKAGES) $(TESTS)

format: ## Ruff auto-format in place
	uv run ruff format $(PACKAGES) $(TESTS)

format-check: ## Verify formatting without writing
	uv run ruff format --check $(PACKAGES) $(TESTS)

typecheck: ## MyPy strict
	uv run mypy $(PACKAGES)

test: ## Run the test suite (fast)
	uv run pytest $(TESTS) -q

test-cov: ## Run tests with coverage gate (term + xml + html)
	uv run pytest $(TESTS) \
		--cov=nexus_core \
		--cov=nexus_infra \
		--cov-report=term-missing \
		--cov-report=xml \
		--cov-report=html \
		--cov-fail-under=$(COV_MIN)

coverage-html: test-cov ## Generate the HTML coverage report (htmlcov/index.html)
	@echo "Open htmlcov/index.html"

check: lint format-check typecheck test-cov ## Full local gate (matches CI)
	@echo "All quality gates passed."

pre-commit: ## Run every pre-commit hook against all files
	uv run pre-commit run --all-files

build: ## Build sdist + wheel
	uv build

clean: ## Remove caches and generated reports
	rm -rf .ruff_cache .mypy_cache .pytest_cache htmlcov coverage.xml dist
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
