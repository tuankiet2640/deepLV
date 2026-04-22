# DeepLV — Task Breakdown

## Milestone 1: Core Translation Pipeline

- [ ] Create project directory structure
- [ ] Set up Python project with pyproject.toml and dependency management
- [ ] Implement model worker service (FastAPI on port 8001)
  - [ ] CTranslate2 model loader with LRU cache (max 6 models)
  - [ ] /translate endpoint (accepts text, source_lang, target_lang)
  - [ ] /health endpoint
  - [ ] Model download/conversion script
- [ ] Implement API gateway service (FastAPI on port 8000)
  - [ ] /api/v1/translate endpoint
  - [ ] Language detection with fasttext
  - [ ] Redis cache check/write logic
  - [ ] Forward to model worker on cache miss
  - [ ] /health endpoint
- [ ] Redis configuration
- [ ] Docker Compose with api, worker, redis services
- [ ] End-to-end smoke test (curl translate request)

## Milestone 2: Auth, Rate Limiting, Persistence

- [ ] PostgreSQL service in Docker Compose
- [ ] SQLAlchemy async models (User, APIKey, UsageLog)
- [ ] Alembic migration setup + initial migration
- [ ] POST /api/v1/auth/register
- [ ] POST /api/v1/auth/login (returns JWT)
- [ ] POST /api/v1/keys (create API key)
- [ ] GET /api/v1/keys (list keys)
- [ ] DELETE /api/v1/keys/:id (revoke key)
- [ ] JWT middleware (verify on protected routes)
- [ ] API key auth middleware (X-API-Key header)
- [ ] Rate limiter middleware (Redis sliding window)
- [ ] Usage logging (async write to PG after each translation)
- [ ] GET /api/v1/usage (usage stats per key)
- [ ] Structured logging setup (structlog)

## Milestone 3: Frontend

- [ ] Scaffold React + Vite + TypeScript project
- [ ] TailwindCSS setup
- [ ] TranslationPage component (split-pane layout)
- [ ] SourcePanel (textarea + language dropdown)
- [ ] TargetPanel (readonly output + language dropdown)
- [ ] useTranslation hook (debounced API call, 300ms)
- [ ] Language swap button
- [ ] Auto-detect indicator
- [ ] Loading shimmer on target panel
- [ ] Error toast/banner
- [ ] Responsive breakpoints (mobile stacks vertical)
- [ ] Nginx config for production serving

## Milestone 4: Production Polish

- [ ] Prometheus metrics (request count, latency histogram, cache hit rate, model load time)
- [ ] Correlation ID middleware (X-Request-ID)
- [ ] Graceful shutdown (drain connections, unload models)
- [ ] Text splitting (sentence boundary detection)
- [ ] Input validation (5000 char limit, empty text, unsupported pairs)
- [ ] CORS middleware
- [ ] Docker health checks on all services
- [ ] docker-compose.yml restart policies
- [ ] README.md with architecture, quickstart, API reference
- [ ] .env.example with documented variables
