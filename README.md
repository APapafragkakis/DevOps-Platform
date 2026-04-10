# DevOps Platform

A production-grade deployment platform for a FastAPI microservice, demonstrating
end-to-end DevOps practices: containerization, CI/CD, Infrastructure as Code,
Kubernetes orchestration, Redis caching, Alembic migrations, rate limiting,
structured logging, and observability.

---

## Architecture

```
                         ┌──────────────────────────────────┐
                         │          GitHub Actions           │
                         │  CI: lint → test → scan → build   │
                         │  CD: staging → approval → prod    │
                         └────────────┬─────────────────────┘
                                      │ push image
                                      ▼
                              ┌──────────────┐
                              │  GHCR Image  │
                              │  Registry    │
                              └──────┬───────┘
                                     │ kubectl set image
          ┌──────────────────────────▼───────────────────────────┐
          │                    AWS EKS Cluster                    │
          │   ┌──────────────────────────────────────────────┐    │
          │   │           devops-platform namespace          │    │
          │   │   ┌─────────┐  ┌─────────┐  ┌─────────┐     │    │
          │   │   │  Pod 1  │  │  Pod 2  │  │  Pod N  │     │    │
          │   │   │FastAPI  │  │FastAPI  │  │FastAPI  │     │    │
          │   │   └────┬────┘  └────┬────┘  └────┬────┘     │    │
          │   │        └───────────┬┘             │  HPA     │    │
          │   │               ┌───▼──────┐   min:2 max:6    │    │
          │   │               │ Service  │                   │    │
          │   │               └───┬──────┘                   │    │
          │   │               ┌───▼──────┐                   │    │
          │   │               │  Ingress │                   │    │
          │   └───────────────┴──────────┴───────────────────┘    │
          │         │                        │                     │
          │  ┌──────▼──────┐       ┌─────────▼──────┐             │
          │  │ RDS Postgres │       │ ElastiCache    │             │
          │  │ (private)    │       │ Redis          │             │
          │  └─────────────┘       └────────────────┘             │
          └──────────────────────────────────────────────────────┘
                                   │
                    ┌──────────────▼───────────────┐
                    │     Monitoring (local)        │
                    │  Prometheus → Grafana :3000   │
                    └──────────────────────────────┘
```

---

## Tech Stack

| Layer              | Technology                                      |
|--------------------|-------------------------------------------------|
| Application        | Python 3.12 / FastAPI / SQLAlchemy              |
| Database           | PostgreSQL 16 + Alembic migrations              |
| Caching            | Redis 7 (write-through, TTL 60s, graceful degradation) |
| Rate Limiting      | slowapi (60 req/min reads, 30 req/min writes)   |
| Observability      | Prometheus metrics + JSON structured logging    |
| Containerization   | Docker (multi-stage build, non-root user)       |
| Local Dev          | Docker Compose (app + postgres + redis + grafana) |
| CI/CD              | GitHub Actions                                  |
| Image Registry     | GitHub Container Registry (GHCR)                |
| Infrastructure     | Terraform (AWS VPC + EKS + RDS)                 |
| Orchestration      | Kubernetes (EKS, HPA, rolling updates)          |
| Security Scanning  | Trivy (CRITICAL/HIGH CVEs)                      |

---

## Quick Start (Docker)

Prerequisites: Docker + Docker Compose

```bash
git clone https://github.com/YOUR_USERNAME/DevOps-Platform
cd DevOps-Platform

# Start everything
make up

# Or without Make:
docker compose up -d --build
```

| Service    | URL                          |
|------------|------------------------------|
| API        | http://localhost:8000        |
| Swagger UI | http://localhost:8000/docs   |
| Metrics    | http://localhost:8000/metrics |
| Grafana    | http://localhost:3000 (admin/admin) |
| Prometheus | http://localhost:9090        |

---

## Make Commands

```bash
make help        # List all commands
make up          # Start all services
make down        # Stop all services
make logs        # Follow app logs
make test        # Run tests with coverage
make lint        # Run flake8
make migrate     # Run Alembic migrations
make migration msg="add users table"  # Generate new migration
make health      # Curl /health and pretty-print
make clean       # Remove containers + volumes
```

---

## CI/CD Flow

```
git push (main)
    │
    ├── lint         flake8
    ├── test         pytest + coverage (SQLite in CI — no external DB)
    ├── security     Trivy scans for CRITICAL/HIGH CVEs
    ├── build        Docker multi-stage → push to GHCR
    ├── deploy staging   kubectl rolling update → smoke test /health
    └── deploy prod      Manual approval → rolling update → smoke test → auto-rollback
```

---

## Run Tests Locally

```bash
cd app
pip install -r requirements.txt
pytest tests/ -v --cov=. --cov-report=term-missing
```

Tests use SQLite in-memory — zero external dependencies.

---

## Deploy Infrastructure (Terraform)

```bash
cd terraform
terraform init
terraform plan  -var="environment=staging" -var="db_password=SECRET"
terraform apply -var="environment=staging" -var="db_password=SECRET"

# Configure kubectl
aws eks update-kubeconfig --name $(terraform output -raw eks_cluster_name)
```

> **Cost note:** EKS (~$0.10/hr) + RDS. Run `terraform destroy` when done.

---

## Deploy to Kubernetes

```bash
kubectl apply -f k8s/
kubectl rollout status deployment/devops-platform -n devops-platform
kubectl get pods -n devops-platform -w
```

---

## Database Migrations (Alembic)

```bash
# Apply all pending migrations
make migrate

# Generate a migration from model changes
make migration msg="add users table"

# Roll back one migration
make rollback
```

---

## Engineering Decisions

**Why Redis caching with graceful degradation?**
The cache layer wraps every Redis call in try/except and returns `None` on failure.
The app continues serving requests from PostgreSQL if Redis is unavailable —
no cascading failure from a cache outage.

**Why rate limiting?**
Unprotected APIs are a common attack surface. `slowapi` adds per-IP rate limits
(60/min reads, 30/min writes) with zero application logic changes — it's
decorator-based middleware.

**Why structured JSON logging?**
Log aggregators (CloudWatch, Datadog, Loki) ingest JSON natively.
Every log line is machine-parseable with consistent fields,
making alerting and dashboards trivial to build.

**Why Alembic instead of `create_all`?**
`create_all` is fine for local dev but unsuitable for production:
it can't alter existing tables, has no rollback, and doesn't track
schema history. Alembic gives us versioned, reversible migrations
that run automatically on container startup.

**Why `maxUnavailable: 0` in rolling updates?**
With 2 replicas, allowing 1 unavailable = 50% capacity loss during deploy.
`maxUnavailable: 0` + `maxSurge: 1` brings up the new pod before
terminating the old one — zero-downtime deployment.

**Why soft delete?**
Hard deletes make production debugging much harder.
`is_active = false` means we can always audit what happened.

---

## Repository Structure

```
DevOps-Platform/
├── app/
│   ├── main.py              # FastAPI app, routes, rate limiting
│   ├── database.py          # SQLAlchemy engine (env-aware)
│   ├── models.py            # ORM models
│   ├── schemas.py           # Pydantic schemas
│   ├── crud.py              # DB operations
│   ├── cache.py             # Redis cache layer (graceful degradation)
│   ├── logging_config.py    # Structured JSON logging
│   ├── requirements.txt
│   ├── Dockerfile           # Multi-stage, non-root, healthcheck
│   ├── alembic.ini
│   ├── migrations/
│   │   ├── env.py
│   │   └── versions/
│   │       └── 0001_initial_items_table.py
│   └── tests/
│       └── test_main.py
├── docker-compose.yml       # app + postgres + redis + prometheus + grafana
├── Makefile                 # Developer shortcuts
├── monitoring/
│   └── prometheus.yml
├── k8s/
│   ├── namespace.yaml
│   ├── deployment.yaml      # Rolling update, probes, resource limits
│   └── service-ingress-hpa.yaml
├── terraform/
│   ├── main.tf              # VPC + EKS + RDS
│   ├── variables.tf
│   └── outputs.tf
└── .github/
    └── workflows/
        ├── ci.yml           # lint → test → security → build
        └── cd.yml           # staging → approval → production
```

---

## What I'd Add Next

- Helm chart to replace raw Kubernetes manifests
- ArgoCD for GitOps-style continuous delivery
- AWS Secrets Manager / Vault integration
- JWT authentication with refresh tokens
- k6 load testing in the CD pipeline
- Distributed tracing with OpenTelemetry

---

## License

MIT
