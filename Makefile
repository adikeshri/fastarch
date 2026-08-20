.PHONY: install dev test test-unit test-integration test-e2e test-architecture \
        lint lint-arch format typecheck migrate migration docker-up docker-down \
        docker-build worker precommit clean

install: ## Install all dependencies (including dev tools) with uv
	uv sync

dev: ## Run the API with autoreload
	uv run uvicorn app.main:app --reload --app-dir src

worker: ## Run the arq background-job worker
	uv run arq app.infrastructure.background_jobs.worker.WorkerSettings

test: ## Run the full test suite (unit + integration + e2e + architecture)
	uv run pytest

test-unit: ## Domain + application tests only — no infrastructure required
	uv run pytest tests/unit -m unit

test-integration: ## Repository/UoW/outbox/cache tests against real Postgres+Redis (testcontainers)
	uv run pytest tests/integration -m integration

test-e2e: ## Full HTTP-through-Postgres flows
	uv run pytest tests/e2e -m e2e

test-architecture: ## Dependency-rule / layering tests
	uv run pytest tests/architecture -m architecture

lint: ## Ruff lint + format check
	uv run ruff check .
	uv run ruff format --check .

lint-arch: ## Enforce the Clean Architecture dependency rules (import-linter)
	uv run lint-imports

format: ## Auto-fix lint issues and reformat
	uv run ruff check --fix .
	uv run ruff format .

typecheck: ## mypy strict type checking
	uv run mypy src

migrate: ## Apply all pending migrations
	uv run alembic upgrade head

migration: ## Autogenerate a new migration: make migration name="add foo"
	uv run alembic revision --autogenerate -m "$(name)"

docker-build: ## Build the application image
	docker compose build

docker-up: ## Start Postgres, Redis, the API, and the worker
	docker compose up -d --build

docker-down: ## Stop and remove the local stack
	docker compose down -v

precommit: ## Install git hooks
	uv run pre-commit install

clean: ## Remove caches and build artifacts
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage dist build

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
