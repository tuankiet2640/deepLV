# DeepLV — Infrastructure

## Docker Compose Services

```yaml
services:
  api:        # FastAPI gateway — port 8000
  worker:     # Model worker — port 8001 (internal)
  redis:      # Cache + rate limits — port 6379
  postgres:   # Persistent storage — port 5432
  frontend:   # React app — port 3000 (nginx)
```

## Container Specifications

### api (API Gateway)
- **Base image:** python:3.11-slim
- **Build:** multi-stage (builder for deps, slim runtime)
- **Exposed port:** 8000
- **Health check:** GET /health every 10s, 3 retries
- **Depends on:** redis, postgres, worker
- **Environment:** DATABASE_URL, REDIS_URL, MODEL_WORKER_URL, JWT_SECRET, LOG_LEVEL
- **Restart:** unless-stopped

### worker (Model Worker)
- **Base image:** python:3.11-slim
- **Build:** multi-stage, includes model conversion step
- **Exposed port:** 8001 (internal network only)
- **Health check:** GET /health every 10s, 5 retries (model load may be slow)
- **Volumes:** models:/app/models (persistent model cache)
- **Environment:** MODEL_CACHE_SIZE, LOG_LEVEL, MODEL_DIR
- **Restart:** unless-stopped
- **Memory limit:** 4GB (hard cap to prevent OOM killing host)

### redis
- **Image:** redis:7-alpine
- **Exposed port:** 6379 (internal)
- **Config:** maxmemory 512mb, maxmemory-policy allkeys-lru
- **Health check:** redis-cli ping every 5s
- **Volumes:** redis-data:/data (optional persistence)

### postgres
- **Image:** postgres:16-alpine
- **Exposed port:** 5432 (internal, 5433 on host for debug)
- **Health check:** pg_isready every 5s
- **Volumes:** pg-data:/var/lib/postgresql/data
- **Environment:** POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD

### frontend
- **Base image:** node:20-alpine (build) -> nginx:alpine (serve)
- **Build:** multi-stage — npm build, then copy dist/ to nginx
- **Exposed port:** 3000
- **Nginx config:** SPA fallback, proxy /api/* to api:8000

## Volumes

| Volume     | Purpose                               | Backup needed? |
|------------|---------------------------------------|----------------|
| models     | CTranslate2 model files              | No (re-downloadable) |
| pg-data    | PostgreSQL data directory             | Yes            |
| redis-data | Redis RDB snapshots                  | No (cache only) |

## Networks

```
deeplv-network (bridge)
  - api, worker, redis, postgres, frontend
  - worker not exposed to host (internal only)
```

## Environment Variables (.env)

```bash
# PostgreSQL
POSTGRES_DB=deeplv
POSTGRES_USER=deeplv
POSTGRES_PASSWORD=<generate-random>
DATABASE_URL=postgresql+asyncpg://deeplv:<password>@postgres:5432/deeplv

# Redis
REDIS_URL=redis://redis:6379/0

# API
JWT_SECRET=<generate-random-64-chars>
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=info
CORS_ORIGINS=http://localhost:3000

# Model Worker
MODEL_WORKER_URL=http://worker:8001
MODEL_CACHE_SIZE=6
MODEL_DIR=/app/models

# Frontend
VITE_API_URL=http://localhost:8000
```

## CI/CD (GitHub Actions)

```
on: [push, pull_request]

jobs:
  lint:     ruff check + ruff format --check
  test:     pytest with SQLite (no Docker needed)
  build:    docker compose build (verify images build)
  typecheck: mypy --strict on src/
```

## Monitoring Endpoints

| Endpoint         | Port | Purpose                     | Auth |
|------------------|------|-----------------------------|------|
| /health          | 8000 | Liveness + dependency check | none |
| /metrics         | 8000 | Prometheus scrape target    | none |
| /health          | 8001 | Model worker liveness       | none |
| /docs            | 8000 | Swagger UI                  | none |
| /redoc           | 8000 | ReDoc API docs              | none |

## Startup Order

```
1. postgres  (wait: pg_isready)
2. redis     (wait: redis-cli ping)
3. worker    (wait: GET /health returns 200)
4. api       (wait: GET /health returns 200)
5. frontend  (nginx serves immediately)
```

Docker Compose `depends_on` with `condition: service_healthy` enforces this.
