.PHONY: help up down build logs ps shell migrate migration rollback test lint health metrics clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-18s\033[0m %s\n", $$1, $$2}'

up: ## Start all services
	docker compose up -d --build

down: ## Stop all services
	docker compose down

build: ## Build the app image
	docker compose build app

logs: ## Follow app logs
	docker compose logs -f app

ps: ## List running services
	docker compose ps

shell: ## Open a shell in the app container
	docker compose exec app sh

migrate: ## Run Alembic migrations
	docker compose exec app alembic upgrade head

migration: ## Create a migration (msg="...")
	docker compose exec app alembic revision --autogenerate -m "$(msg)"

rollback: ## Downgrade one migration
	docker compose exec app alembic downgrade -1

test: ## Run tests with coverage
	cd app && pytest tests/ -v --cov=. --cov-report=term-missing

lint: ## Run flake8
	flake8 app/ --max-line-length=100 --exclude=app/tests,app/migrations

health: ## Curl /health
	curl -s http://localhost:8000/health | python3 -m json.tool

metrics: ## Show app metrics
	curl -s http://localhost:9090/metrics 2>/dev/null | head -20 || \
		curl -s http://localhost:8000/metrics | head -20

clean: ## Remove containers and volumes
	docker compose down -v --remove-orphans
