.PHONY: help up down build logs test lint clean ps shell migrate

# Default target
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ── Docker ──────────────────────────────────────────────────────────────────
up: ## Start all services (detached)
	docker compose up -d --build

down: ## Stop all services
	docker compose down

build: ## Build app image only
	docker compose build app

logs: ## Follow app logs
	docker compose logs -f app

ps: ## Show running containers
	docker compose ps

shell: ## Open shell in running app container
	docker compose exec app sh

# ── Database ─────────────────────────────────────────────────────────────────
migrate: ## Run Alembic migrations
	docker compose exec app alembic upgrade head

migration: ## Create a new migration (usage: make migration msg="add users table")
	docker compose exec app alembic revision --autogenerate -m "$(msg)"

rollback: ## Roll back last migration
	docker compose exec app alembic downgrade -1

# ── Testing ───────────────────────────────────────────────────────────────────
test: ## Run tests with coverage
	cd app && pytest tests/ -v --cov=. --cov-report=term-missing

lint: ## Run flake8 linter
	flake8 app/ --max-line-length=100 --exclude=app/tests,app/migrations

# ── Ops ───────────────────────────────────────────────────────────────────────
health: ## Check API health
	curl -s http://localhost:8000/health | python3 -m json.tool

metrics: ## Show Prometheus metrics (first 20 lines)
	curl -s http://localhost:9090/metrics 2>/dev/null | head -20 || \
		curl -s http://localhost:8000/metrics | head -20

clean: ## Remove volumes and containers
	docker compose down -v --remove-orphans

