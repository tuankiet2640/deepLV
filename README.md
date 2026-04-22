# DeepLV

Production-grade machine translation system. Translate text across 10 languages with sub-second latency.

```
Client -> FastAPI Gateway -> Redis Cache -> Model Worker (CTranslate2/MarianMT) -> PostgreSQL
         (auth, rate limit)   (24h TTL)    (INT8 quantized inference)               (usage logs)
```

## Architecture

| Component       | Tech                         | Purpose                                    |
|-----------------|------------------------------|--------------------------------------------|
| API Gateway     | FastAPI + uvicorn            | Auth, rate limiting, cache, routing        |
| Model Worker    | CTranslate2 + MarianMT      | INT8 quantized translation inference       |
| Cache           | Redis 7                      | Translation cache + rate limit counters    |
| Database        | PostgreSQL 16                | Users, API keys, usage logs                |
| Frontend        | React 18 + TypeScript + Vite | DeepL-style translate-as-you-type UI       |

### Design Decisions

See [`claude/decisions/adr-001.md`](claude/decisions/adr-001.md) for detailed rationale on every technology choice.

## Quick Start

```bash
# Clone and start all services
git clone <repo-url> && cd deeplv
docker compose up --build

# Wait for services to be healthy (~30s first time, longer for model download)
# API:      http://localhost:8000
# Frontend: http://localhost:3000
# Swagger:  http://localhost:8000/docs
# Health:   http://localhost:8000/health
# Metrics:  http://localhost:8000/metrics
```

### Download Models (first time only)

```bash
# Inside the worker container, or locally with Python 3.11+
python scripts/download_models.py --output-dir ./models --pairs en-de de-en en-fr fr-en
```

## API Usage

```bash
# Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "securepassword123"}'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "securepassword123"}'
# -> returns { "access_token": "eyJ..." }

# Create API key
curl -X POST http://localhost:8000/api/v1/keys \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "my-key"}'
# -> returns { "key": "dlv_live_..." }

# Translate
curl -X POST http://localhost:8000/api/v1/translate \
  -H "X-API-Key: dlv_live_..." \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello, how are you?", "source_lang": "auto", "target_lang": "de"}'
# -> { "translated_text": "Hallo, wie geht es Ihnen?", "latency_ms": 342, "cached": false }
```

## Supported Languages

| Code | Language   |
|------|------------|
| en   | English    |
| de   | German     |
| fr   | French     |
| es   | Spanish    |
| zh   | Chinese    |
| ja   | Japanese   |
| vi   | Vietnamese |
| ko   | Korean     |
| pt   | Portuguese |
| ru   | Russian    |

Direct models exist for all `en <-> X` pairs. Non-English pairs (e.g., `de -> fr`) pivot through English automatically.

## Project Structure

```
deeplv/
  src/
    api/                  # FastAPI gateway (port 8000)
      main.py             # App entry point, middleware, routers
      database.py         # SQLAlchemy async engine + session
      metrics.py          # Prometheus counters + histograms
      models/             # SQLAlchemy ORM models
      routers/            # HTTP route handlers
      services/           # Auth, cache, language detection
      middleware/         # Rate limiter, auth dependencies
    worker/               # Model worker (port 8001)
      main.py             # FastAPI app for inference
      model_cache.py      # LRU cache for loaded CTranslate2 models
      translator.py       # Translation logic + pivot handling
    shared/               # Config + logging shared between services
  frontend/               # React + Vite + TailwindCSS
  migrations/             # Alembic database migrations
  scripts/                # Model download + conversion
  tests/                  # pytest test suite
  claude/                 # Architecture docs, ADRs, planning artifacts
  docker-compose.yml      # Full system orchestration
```

## Key Metrics (Prometheus)

- `deeplv_http_requests_total` — request count by method/endpoint/status
- `deeplv_http_request_duration_seconds` — latency histogram
- `deeplv_translations_total` — translations by language pair and cache status
- `deeplv_cache_hits_total` / `deeplv_cache_misses_total` — cache effectiveness

## Development

```bash
# Run tests
pip install -e ".[dev]"
pytest

# Lint
ruff check src/ tests/
ruff format --check src/ tests/

# Type check
mypy src/
```

## License

MIT
