.PHONY: help up down build logs test lint clean ps shell migrate

help:
    @grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
        awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-18s\033[0m %s\n", $$1, $$2}'

up:
    docker compose up -d --build

down:
    docker compose down

build:
    docker compose build app

logs:
    docker compose logs -f app

ps:
    docker compose ps

shell:
    docker compose exec app sh

migrate:
    docker compose exec app alembic upgrade head

migration:
    docker compose exec app alembic revision --autogenerate -m "$(msg)"

rollback:
    docker compose exec app alembic downgrade -1

test:
    cd app && pytest tests/ -v --cov=. --cov-report=term-missing

lint:
    flake8 app/ --max-line-length=100 --exclude=app/tests,app/migrations

health:
    curl -s http://localhost:8000/health | python3 -m json.tool

metrics:
    curl -s http://localhost:9090/metrics 2>/dev/null | head -20 || \
        curl -s http://localhost:8000/metrics | head -20

clean:
    docker compose down -v --remove-orphans