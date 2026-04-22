---
skill: devops
---

# DevOps / Infrastructure

- **Docker** — multi-stage builds, separate containers for API, model worker, Redis, PostgreSQL
- **Docker Compose** — local development orchestration with health checks and dependency ordering
- **Kubernetes (conceptual)** — HPA on model workers, separate node pools for GPU/CPU
- **CI/CD** — GitHub Actions for lint, test, build, push images
- **Observability** — structured logging (structlog), Prometheus metrics, health/readiness probes
- **Secrets management** — environment-based config, no hardcoded credentials
