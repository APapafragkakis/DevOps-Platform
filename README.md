# DevOps Platform

Production-grade DevOps platform demonstrating end-to-end cloud-native system design and deployment.

Built as a real-world backend + DevOps project, this platform showcases hands-on experience with Kubernetes, Docker, CI/CD pipelines, Infrastructure as Code (Terraform on AWS), and distributed system design.

Designed and implemented by an MSc Computer Science student with a focus on Backend & DevOps engineering.

---

## Key Highlights

- End-to-end CI/CD pipeline (GitHub Actions → GHCR → Kubernetes)
- Kubernetes deployment on AWS EKS with Helm and HPA autoscaling
- Infrastructure provisioning with Terraform (VPC, EKS, RDS)
- Production-ready backend (FastAPI + PostgreSQL + Redis)
- Observability stack (Prometheus, Grafana, Jaeger)
- Load-tested system (k6, p95 < 500ms)

## Architecture

```
                         ┌──────────────────────────────────┐
                         │          GitHub Actions          │
                         │  lint → test → scan → build      │
                         │  → load test (k6) → deploy       │
                         └────────────┬─────────────────────┘
                                      │ push image
                                      ▼
                              ┌──────────────┐
                              │  GHCR Image  │
                              │  Registry    │
                              └──────┬───────┘
                                     │ helm upgrade
          ┌──────────────────────────▼────────────────────────────┐
          │                    AWS EKS Cluster                    │
          │   ┌──────────────────────────────────────────────┐    │
          │   │           devops-platform namespace          │    │
          │   │   ┌─────────┐  ┌─────────┐  ┌─────────┐      │    │
          │   │   │  Pod 1  │  │  Pod 2  │  │  Pod N  │      │    │
          │   │   │FastAPI  │  │FastAPI  │  │FastAPI  │      │    │
          │   │   └────┬────┘  └────┬────┘  └────┬────┘      │    │
          │   │        └───────────┬┘             │  HPA     │    │
          │   │               ┌───▼──────┐   min:2 max:6     │    │
          │   │               │ Service  │                   │    │
          │   │               └───┬──────┘                   │    │
          │   │               ┌───▼──────┐                   │    │
          │   │               │  Ingress │                   │    │
          │   └───────────────┴──────────┴───────────────────┘    │
          │         │                        │                    │
          │  ┌──────▼──────┐       ┌─────────▼──────┐             │
          │  │ RDS Postgres │      │ ElastiCache    │            │
          │  │ (private)    │      │ Redis          │            │
          │  └─────────────┘       └────────────────┘             │
          └───────────────────────────────────────────────────────┘
                                   │
                    ┌──────────────▼───────────────┐
                    │         Observability         │
                    │  Prometheus → Grafana :3000   │
                    │  Jaeger tracing   :16686      │
                    └──────────────────────────────┘
```

---

## Tech Stack

| Layer              | Technology                                              |
|--------------------|---------------------------------------------------------|
| Application        | Python 3.12 / FastAPI / SQLAlchemy                      |
| Authentication     | JWT (python-jose) + bcrypt password hashing             |
| Database           | PostgreSQL 16 + Alembic migrations                      |
| Caching            | Redis 7 (write-through, TTL 60s, graceful degradation)  |
| Rate Limiting      | slowapi (60 req/min reads, 30 req/min writes)           |
| Observability      | Prometheus metrics + Jaeger distributed tracing         |
| Containerization   | Docker (multi-stage build, non-root user)               |
| Local Dev          | Docker Compose (app + postgres + redis + jaeger + grafana) |
| CI/CD              | GitHub Actions (lint → test → scan → build → load test) |
| Load Testing       | k6 (smoke test in CI, p95 < 500ms threshold)            |
| Image Registry     | GitHub Container Registry (GHCR)                        |
| Infrastructure     | Terraform (AWS VPC + EKS + RDS)                         |
| Orchestration      | Kubernetes via Helm chart (HPA, rolling updates)        |
| Security Scanning  | Trivy (CRITICAL/HIGH CVEs)                              |

---

## Quick Start (Docker)

Prerequisites: Docker + Docker Compose

```bash
git clone https://github.com/APapafragkakis/DevOps-Platform
cd DevOps-Platform

docker compose up -d --build
```

| Service    | URL                            |
|------------|--------------------------------|
| API docs   | http://localhost:8000/docs     |
| Metrics    | http://localhost:8000/metrics  |
| Grafana    | http://localhost:3000 (admin/admin) |
| Prometheus | http://localhost:9090          |
| Jaeger UI  | http://localhost:16686         |

---

## Authentication Flow

All `/items` endpoints require a JWT token.

```bash
# 1. Register
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "alex", "password": "secret"}'

# 2. Login — get token
curl -X POST http://localhost:8000/auth/token \
  -d "username=alex&password=secret"

# 3. Use token
curl http://localhost:8000/items \
  -H "Authorization: Bearer <token>"
```

Or use the **Authorize** button in Swagger UI at `/docs`.

---

## Make Commands

```bash
make up          # Start all services
make down        # Stop all services
make logs        # Follow app logs
make test        # Run tests with coverage
make lint        # Run flake8
make migrate     # Run Alembic migrations
make migration msg="add users table"
make health      # Curl /health
make clean       # Remove containers + volumes
```

---

## CI/CD Flow

```
git push (main)
    │
    ├── lint         flake8
    ├── test         pytest + coverage (SQLite in CI)
    ├── security     Trivy — CRITICAL/HIGH CVEs
    ├── build        Docker multi-stage → push to GHCR
    ├── load-test    k6 smoke test (p95 < 500ms, error rate < 1%)
    ├── deploy staging   helm upgrade → smoke test /health
    └── deploy prod      manual approval → helm upgrade → auto-rollback
```

---

## Deploy with Helm

```bash
helm upgrade --install devops-platform ./helm/devops-platform \
  --set secrets.databaseUrl="postgresql://..." \
  --set secrets.secretKey="your-secret-key" \
  --set secrets.redisUrl="redis://..." \
  --set image.tag="sha-abc1234"
```

---

## Deploy Infrastructure (Terraform)

```bash
cd terraform
terraform init
terraform plan  -var="environment=staging" -var="db_password=SECRET"
terraform apply -var="environment=staging" -var="db_password=SECRET"

aws eks update-kubeconfig --name $(terraform output -raw eks_cluster_name)
```

> **Cost note:** EKS (~$0.10/hr) + RDS. Run `terraform destroy` when done.

---

## Run Tests

```bash
cd app
pip install -r requirements.txt
pytest tests/ -v --cov=. --cov-report=term-missing
```


## Repository Structure

```
DevOps-Platform/
├── app/
│   ├── main.py              # routes, rate limiting, JWT protection
│   ├── auth.py              # JWT token creation and validation
│   ├── cache.py             # Redis layer with graceful degradation
│   ├── tracing.py           # OpenTelemetry / Jaeger setup
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── crud.py
│   ├── Dockerfile           # multi-stage, non-root, healthcheck
│   ├── migrations/
│   │   └── versions/
│   │       ├── 0001_initial_items_table.py
│   │       └── 0002_add_users_table.py
│   └── tests/
│       └── test_main.py     # 11 tests, SQLite in-memory
├── helm/
│   └── devops-platform/     # Helm chart (Deployment, Service, HPA, Secret)
├── load-tests/
│   └── smoke.js             # k6 load test (runs in CI)
├── docker-compose.yml       # app + postgres + redis + jaeger + grafana
├── Makefile
├── monitoring/
│   └── prometheus.yml
├── k8s/                     # raw manifests (superseded by Helm chart)
├── terraform/               # AWS VPC + EKS + RDS
└── .github/
    └── workflows/
        ├── ci.yml           # lint → test → security → build → load-test
        └── cd.yml           # staging → approval → production
```

---

## What I'd Add Next

- ArgoCD for GitOps-style continuous delivery
- AWS Secrets Manager integration
- Alembic migrations in the CD pipeline
- JWT refresh tokens
- Grafana dashboards as code

---

## License

MIT

