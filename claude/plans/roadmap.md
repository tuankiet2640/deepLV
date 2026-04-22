# DeepLV — Roadmap

## Milestone 1: Core Translation Pipeline
**Goal:** text in, translation out, end-to-end via API

- Model worker service with CTranslate2 inference
- API gateway with /translate endpoint
- Language detection (fasttext)
- Redis translation cache
- Docker Compose for all services
- Health check endpoints

## Milestone 2: Auth, Rate Limiting, Persistence
**Goal:** production access control and observability

- PostgreSQL schema + Alembic migrations
- User registration and JWT auth
- API key management (create, revoke, list)
- Per-key rate limiting via Redis
- Usage logging (characters translated, cache hits)
- Structured logging (structlog)

## Milestone 3: Frontend
**Goal:** DeepL-style web translation interface

- React + Vite + TypeScript project
- Split-pane translation layout
- Language selector with auto-detect and swap
- Debounced translate-as-you-type
- Loading states and error handling
- Responsive design

## Milestone 4: Production Polish
**Goal:** the details that separate portfolio from toy

- Prometheus metrics endpoint (/metrics)
- Request tracing (correlation IDs)
- Graceful shutdown handling
- API versioning (v1 prefix)
- OpenAPI docs customization
- Multi-sentence text splitting and reassembly
- Input sanitization and character limit enforcement
- CORS configuration
- Docker health checks and restart policies
- README with architecture diagram and quickstart
