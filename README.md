# DevOps Platform

A FastAPI service with the full delivery setup around it: CI/CD on GitHub Actions, a Helm chart tested on Kubernetes in CI, Terraform for AWS, and metrics and tracing.

I built it as a hands-on backend and DevOps project during my MSc in Computer Science.

---

## What's in it

- CI on every push and PR: lint, tests on Postgres, migration checks, security scans, k6 load test, and a Kubernetes end-to-end test of the Helm chart on kind
- Images pushed to GHCR from `main` and from version tags, with a GitHub Release per tag
- CD workflow that deploys to staging and production with Helm and rolls back on failure (runs once the cluster secrets are set, see below)
- Terraform for an AWS setup (VPC, EKS, RDS), checked with `fmt` and `validate` in CI
- FastAPI + PostgreSQL + Redis backend with JWT auth, caching and rate limiting
- Prometheus metrics, Grafana, and OpenTelemetry tracing to Jaeger
- Dependabot for Python packages, GitHub Actions, the Docker base image and Terraform

## Architecture

Target AWS setup from `terraform/` and the Helm chart. It is not deployed anywhere right now, the chart is tested on kind in CI instead.

```
                         ┌──────────────────────────────────┐
                         │          GitHub Actions          │
                         │  lint → test → scan → load test  │
                         │  → kind e2e → build → deploy     │
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
          │  │ RDS Postgres │      │     Redis      │             │
          │  │ (private)    │      │                │             │
          │  └─────────────┘       └────────────────┘             │
          └───────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer              | Technology                                              |
|--------------------|---------------------------------------------------------|
| Application        | Python 3.12 / FastAPI / SQLAlchemy                      |
| Authentication     | JWT (PyJWT) + bcrypt password hashing                   |
| Database           | PostgreSQL 16 + Alembic migrations                      |
| Caching            | Redis 7 (cache-aside, TTL 60s, app keeps working without Redis) |
| Rate Limiting      | slowapi (60 req/min reads, 30 req/min writes)           |
| Observability      | Prometheus + Grafana, OpenTelemetry tracing to Jaeger   |
| Containerization   | Docker (multi-stage build, non-root user)               |
| Local Dev          | Docker Compose (app + postgres + redis + jaeger + prometheus + grafana) |
| CI/CD              | GitHub Actions                                          |
| Testing            | pytest on Postgres, k6 load test, Helm e2e on kind      |
| Security           | Trivy (dependencies and image), Dependabot              |
| Image Registry     | GitHub Container Registry (GHCR)                        |
| Infrastructure     | Terraform (AWS VPC + EKS + RDS)                         |
| Orchestration      | Kubernetes via Helm chart (HPA, rolling updates)        |

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

Grafana comes with Prometheus already added as a data source. Traces show up in Jaeger under the `devops-platform` service after a few requests.

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
make help        # List all commands
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
CI: push / PR (main, develop), tags v*
    │
    ├── lint         flake8
    ├── terraform    fmt -check + validate
    ├── test         Postgres service → alembic upgrade + alembic check → pytest (coverage ≥ 85%)
    ├── security     Trivy on Python dependencies
    ├── load-test    docker compose + k6 smoke test (p95 < 500ms, error rate < 1%)
    ├── e2e          build image → Trivy image scan → helm lint → kind cluster → helm install/upgrade → API smoke test
    ├── build        push image to GHCR (main and v* tags only)
    └── release      GitHub Release with generated notes (v* tags only)

CD: after CI succeeds on main, only if deploy settings exist
    ├── deploy staging   helm upgrade → smoke test /health → rollback on failure
    └── deploy prod      manual approval → helm upgrade → rollback on failure
```

Image tags: `sha-<short sha>` for every build, `latest` for `main`, and `X.Y.Z` / `X.Y` for version tags.

CD needs these repository settings:

- secrets `KUBE_CONFIG_STAGING`, `KUBE_CONFIG_PROD` (base64 kubeconfig, as repository secrets)
- variables `STAGING_URL`, `PROD_URL`
- environments `staging` and `production` (add required reviewers on `production`)

The release must be installed once with `helm upgrade --install` (see below) in the `devops-platform-staging` and `devops-platform` namespaces, CD only updates the image.

### Releases

```bash
git tag v3.0.0
git push origin v3.0.0
```

CI runs on the tag, pushes `ghcr.io/apapafragkakis/devops-platform:3.0.0` and creates the GitHub Release.

---

## Deploy with Helm

```bash
helm upgrade --install devops-platform ./helm/devops-platform \
  -n devops-platform --create-namespace \
  --set secrets.databaseUrl="postgresql://..." \
  --set secrets.secretKey="your-secret-key" \
  --set secrets.redisUrl="redis://..." \
  --set image.tag="sha-abc1234"
```

Pods run database migrations on start. A Postgres advisory lock makes sure only one pod migrates at a time.

To send traces, set `env.OTEL_EXPORTER_OTLP_ENDPOINT` to your OTLP HTTP collector.

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
pip install -r app/requirements-dev.txt
pytest app/tests/ -v --cov=app --cov-report=term-missing
```

Tests use SQLite by default. To run them on Postgres like CI does, set `DATABASE_URL`:

```bash
docker compose up -d postgres
export DATABASE_URL=postgresql://devops:devops@localhost:5432/devopsdb
(cd app && alembic upgrade head && alembic check)
pytest app/tests/ -v --cov=app
```

---

## Repository Structure

```
DevOps-Platform/
├── app/
│   ├── main.py              # routes, rate limiting, JWT protection
│   ├── auth.py              # JWT token creation and validation
│   ├── cache.py             # Redis layer with graceful degradation
│   ├── tracing.py           # OpenTelemetry setup (OTLP to Jaeger)
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
│       ├── test_main.py     # API tests
│       └── test_cache.py    # cache tests with fakeredis
├── helm/
│   └── devops-platform/     # Helm chart (Deployment, Service, Ingress, HPA, Secret)
├── k8s/
│   └── e2e-deps.yaml        # Postgres + Redis for the kind e2e job
├── load-tests/
│   └── smoke.js             # k6 load test (runs in CI)
├── monitoring/
│   ├── prometheus.yml
│   └── grafana/             # Grafana data source provisioning
├── terraform/               # AWS VPC + EKS + RDS
├── docker-compose.yml
├── Makefile
└── .github/
    ├── dependabot.yml
    └── workflows/
        ├── ci.yml           # lint, tests, scans, load test, e2e, build, release
        └── cd.yml           # staging → approval → production
```

---

## What I'd Add Next

- Deploy to a real cluster and turn on CD
- ArgoCD for GitOps-style delivery
- AWS Secrets Manager / External Secrets instead of Helm-managed secrets
- JWT refresh tokens
- Grafana dashboards as code

---

## License

MIT
