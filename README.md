# DeepLV

Production-grade multi-provider translation platform. Translate text and documents across 10 languages using built-in models (free), your own API keys (BYOK), or admin-managed credits.

```
Client -> FastAPI Gateway -> Redis Cache -> Translation Providers
         (auth, rate limit)   (24h TTL)    ├── MarianMT Worker (local, free, CTranslate2 INT8)
                                           ├── OpenAI GPT (BYOK or credits)
                                           ├── HuggingFace Inference API (BYOK or credits)
                                           └── Google Cloud Translation (BYOK or credits)
```

## Features

- **Multi-provider translation** - Choose your translation engine per request
- **Document translation** - Upload DOCX, PPTX, XLSX, HTML, TXT or PDF and get the file back
  in the same format with its styling, images, tables and layout intact (PDF returns DOCX)
- **Bring Your Own Key (BYOK)** - Store your own API keys (encrypted at rest with Fernet/AES)
- **Credit system** - Admin-managed provider keys with pay-per-use credits
- **Admin dashboard** - User management, usage analytics, provider key management, pricing control
- **Full observability** - Prometheus metrics, Grafana dashboards, structured JSON logging
- **4-tier auth** - Public, API Key, JWT Bearer, Admin
- **10 languages** - en, de, fr, es, zh, ja, vi, ko, pt, ru
- **React frontend** - Landing page, auth flow, real-time translation, document upload, settings, admin panel

## Architecture

| Component | Tech | Purpose |
|-----------|------|---------|
| API Gateway | FastAPI + uvicorn | Auth, rate limiting, cache, provider routing |
| Model Worker | CTranslate2 + MarianMT | INT8 quantized local translation inference |
| Cache | Redis 7 | Translation cache (24h TTL) + rate limit counters |
| Database | PostgreSQL 16 (Supabase in prod) | Users, API keys, usage logs, credits, jobs |
| Frontend | React 18 + TypeScript + Vite + Tailwind | Full-featured translation UI |
| Monitoring | Prometheus + Grafana | Metrics collection and visualization |
| Tunnel | Cloudflare Tunnel (prod) | Zero-config HTTPS without opening ports |

## Quick Start

### Development (local only)

```bash
git clone https://github.com/tuankiet2640/deepLV.git && cd deepLV
docker compose up --build
```

Services:
- Frontend: http://localhost:3000
- API + Swagger: http://localhost:8000/docs
- Grafana: http://localhost:3001
- Prometheus: http://localhost:9090

### Production with Cloudflare Tunnel

```bash
cp .env.production .env
# Fill in: DOMAIN, DATABASE_URL, JWT_SECRET, ENCRYPTION_KEY, CLOUDFLARE_TUNNEL_TOKEN
docker compose -f docker-compose.prod.yml up -d
```

### Production with Port Forwarding (no Cloudflare)

```bash
cp .env.production .env
# Fill in: DOMAIN, DATABASE_URL, JWT_SECRET, ENCRYPTION_KEY
docker compose -f docker-compose.local.yml up -d
```

See [QUICKSTART.md](QUICKSTART.md) for detailed setup or [DEPLOYMENT.md](DEPLOYMENT.md) for production deployment guide.

### Download Models (first time only)

```bash
# For free built-in MarianMT translation
chmod +x scripts/download_models.sh
./scripts/download_models.sh
```

## API Usage

### Register and Login

```bash
# Register a new account
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "securepassword123"}'

# Login to get JWT token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "securepassword123"}'
# Returns: { "access_token": "eyJ..." }
```

### Create an API Key

```bash
curl -X POST http://localhost:8000/api/v1/keys \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "my-app-key"}'
# Returns: { "key": "dlv_live_..." }
```

### Translate Text

```bash
# Default provider (MarianMT - free)
curl -X POST http://localhost:8000/api/v1/translate \
  -H "X-API-Key: dlv_live_..." \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello, how are you?", "source_lang": "en", "target_lang": "de"}'
# Returns: { "translated_text": "Hallo, wie geht es Ihnen?", "latency_ms": 342, "cached": false }

# With a specific provider (e.g., OpenAI using BYOK)
curl -X POST http://localhost:8000/api/v1/translate \
  -H "X-API-Key: dlv_live_..." \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello world", "source_lang": "en", "target_lang": "fr", "provider": "openai", "provider_key_id": 1}'
```

### Upload a Document for Translation

```bash
curl -X POST http://localhost:8000/api/v1/documents/translate \
  -H "Authorization: Bearer <token>" \
  -F "file=@document.pdf" \
  -F "source_lang=en" \
  -F "target_lang=de" \
  -F "provider=marianmt"
# Returns: { "job_id": "...", "status": "pending" }

# Check job status
curl http://localhost:8000/api/v1/documents/jobs/<job_id> \
  -H "Authorization: Bearer <token>"

# Download translated document
curl http://localhost:8000/api/v1/documents/jobs/<job_id>/download \
  -H "Authorization: Bearer <token>" -o translated.txt
```

## Supported Languages

| Code | Language | Code | Language |
|------|----------|------|----------|
| en | English | ja | Japanese |
| de | German | vi | Vietnamese |
| fr | French | ko | Korean |
| es | Spanish | pt | Portuguese |
| zh | Chinese | ru | Russian |

Direct models exist for all `en <-> X` pairs. Non-English pairs (e.g., `de -> fr`) pivot through English automatically.

## Translation Providers

| Provider | Cost | Setup |
|----------|------|-------|
| **MarianMT** (built-in) | Free | Download models locally |
| **OpenAI GPT** | BYOK or credits | Store your API key or use admin credits |
| **HuggingFace** | BYOK or credits | Store your API key or use admin credits |
| **Google Cloud Translation** | BYOK or credits | Store your API key or use admin credits |

## API Endpoints (29 total)

### Public
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Register new user |
| POST | `/api/v1/auth/login` | Login, get JWT token |
| GET | `/health` | Health check |
| GET | `/metrics` | Prometheus metrics |
| GET | `/api/v1/languages` | List supported languages |

### API Key Required (X-API-Key header)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/translate` | Translate text |

### JWT Required (Bearer token)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/keys` | Create API key |
| GET | `/api/v1/keys` | List API keys |
| DELETE | `/api/v1/keys/{id}` | Delete API key |
| GET | `/api/v1/credits/balance` | Check credit balance |
| POST | `/api/v1/credits/purchase` | Purchase credits |
| GET | `/api/v1/credits/transactions` | Transaction history |
| POST | `/api/v1/providers/keys` | Store provider API key (BYOK) |
| GET | `/api/v1/providers/keys` | List stored provider keys |
| DELETE | `/api/v1/providers/keys/{id}` | Remove provider key |
| POST | `/api/v1/documents/translate` | Upload document for translation |
| GET | `/api/v1/documents/jobs` | List translation jobs |
| GET | `/api/v1/documents/jobs/{id}` | Job status |
| GET | `/api/v1/documents/jobs/{id}/download` | Download result |
| GET | `/api/v1/usage` | Usage statistics |

### Admin Only (is_admin=True)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/admin/users` | List all users |
| GET | `/api/v1/admin/users/{id}` | User detail |
| PATCH | `/api/v1/admin/users/{id}` | Update user (admin, credits) |
| GET | `/api/v1/admin/usage` | Global analytics |
| GET | `/api/v1/admin/provider-keys` | List admin provider keys |
| POST | `/api/v1/admin/provider-keys` | Add admin provider key |
| DELETE | `/api/v1/admin/provider-keys/{id}` | Remove admin key |
| PATCH | `/api/v1/admin/settings` | Update system settings |

## Frontend Pages

| Route | Page | Auth Required |
|-------|------|---------------|
| `/` | Landing page (product marketing) | No |
| `/login` | Login | No |
| `/register` | Register | No |
| `/translate` | Real-time text translation with provider selector | No |
| `/documents` | Document upload and translation job tracking | No |
| `/settings` | BYOK key management, credits | Yes |
| `/api-keys` | API key management | Yes |
| `/admin` | Admin dashboard (users, analytics, keys, settings) | Yes (admin) |
| `/getting-started` | Getting started guide | No |
| `/api-reference` | API documentation | No |
| `/architecture` | Architecture overview | No |
| `/status` | System status | No |

## Project Structure

```
deepLV/
  src/
    api/                       # FastAPI gateway (port 8000)
      main.py                  # App entry, middleware, router registration
      database.py              # SQLAlchemy async engine + sessions
      metrics.py               # Prometheus counters + histograms
      models/                  # SQLAlchemy ORM models
        user.py                # User (email, password_hash, is_admin, credits)
        api_key.py             # API keys (dlv_live_... format)
        usage_log.py           # Translation usage tracking
        provider_key.py        # User BYOK keys (Fernet encrypted)
        admin_provider_key.py  # Admin-managed provider keys
        credit_transaction.py  # Credit purchase/debit ledger
        document_job.py        # Document translation jobs
        document_result.py     # Translated document content
        admin_settings.py      # Configurable system settings
      routers/                 # HTTP route handlers
        auth.py                # Register, login
        translate.py           # Text translation with provider selection
        keys.py                # API key CRUD
        providers.py           # BYOK provider key management
        credits.py             # Credit balance and transactions
        documents.py           # Document upload and job tracking
        admin.py               # Admin operations
        usage.py               # Usage statistics
        health.py              # Health checks
      services/                # Business logic
        auth.py                # JWT + password hashing
        cache.py               # Redis caching
        encryption.py          # Fernet encryption for stored keys
        provider_manager.py    # Provider resolution and routing
        document_format/       # Format-preserving extract + re-inject per file type
        text_chunker.py        # Splits oversized segments for provider limits
        document_translator.py # Async document translation
        language_detect.py     # Auto language detection
        providers/             # Translation provider implementations
          base.py              # Abstract TranslationProvider class
          marianmt.py          # Built-in MarianMT (via worker)
          openai_provider.py   # OpenAI GPT translation
          huggingface_provider.py  # HuggingFace Inference API
          google_provider.py   # Google Cloud Translation
      middleware/              # Request middleware
        dependencies.py        # Auth + rate limit dependencies
        admin.py               # Admin role enforcement
    worker/                    # Model worker (port 8001)
      main.py                  # FastAPI inference service + /metrics
      model_cache.py           # LRU cache for CTranslate2 models
      translator.py            # Translation logic + pivot handling
    shared/                    # Shared utilities
      config.py                # Pydantic Settings (env vars)
      logging.py               # Structured JSON logging
  frontend/                    # React + Vite + TailwindCSS
    src/
      pages/                   # Route pages (12 pages)
      components/              # Reusable UI components
        admin/                 # Admin-specific components
      hooks/                   # Custom React hooks
      contexts/                # Auth context provider
  monitoring/
    prometheus/prometheus.yml   # Scrape config for API + worker
    grafana/
      provisioning/            # Auto-provision datasources
      dashboards/              # Pre-built overview dashboard
  migrations/                  # Alembic database migrations
  scripts/                     # Utilities (deploy, model download)
  tests/                       # pytest test suite
  .github/workflows/ci.yml    # CI: lint, typecheck, test, build
  docker-compose.yml           # Dev (7 services)
  docker-compose.prod.yml      # Production + Cloudflare Tunnel (7 services)
  docker-compose.local.yml     # Production + port forwarding (6 services)
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DOMAIN` | Public domain for the app | `translate.yourdomain.com` |
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `REDIS_URL` | Redis connection string | `redis://redis:6379/0` |
| `JWT_SECRET` | Secret for signing JWT tokens | Required |
| `JWT_ALGORITHM` | JWT signing algorithm | `HS256` |
| `JWT_EXPIRE_MINUTES` | Token expiry in minutes | `1440` (24h) |
| `ENCRYPTION_KEY` | Fernet key for encrypting BYOK keys | Required |
| `MODEL_WORKER_URL` | Worker service URL | `http://worker:8001` |
| `MODEL_CACHE_SIZE` | Number of models to keep loaded | `3` |
| `RATE_LIMIT_REQUESTS` | Max requests per window | `60` |
| `RATE_LIMIT_WINDOW_SECONDS` | Rate limit window | `60` |
| `ADMIN_OPENAI_KEY` | Admin OpenAI API key | Empty |
| `ADMIN_HUGGINGFACE_KEY` | Admin HuggingFace key | Empty |
| `ADMIN_GOOGLE_KEY` | Admin Google Translation key | Empty |
| `CREDIT_COST_PER_1K_CHARS` | Credits charged per 1000 chars | `5.0` |
| `CLOUDFLARE_TUNNEL_TOKEN` | Tunnel token (prod only) | Required for prod |
| `GRAFANA_ADMIN_USER` | Grafana admin username | `admin` |
| `GRAFANA_ADMIN_PASSWORD` | Grafana admin password | Required |
| `VITE_API_URL` | Frontend API base URL | `https://DOMAIN` |
| `CORS_ORIGINS` | Allowed CORS origins | `https://DOMAIN` |

## Development

```bash
# Backend setup
pip install -e ".[dev]"

# Frontend setup
cd frontend && npm install

# Run tests
pytest tests/ -v

# Lint and format
ruff check src/ tests/
ruff format --check src/ tests/

# Type check (Python)
mypy src/

# Frontend build
cd frontend && npm run build

# Validate docker-compose
docker compose config
```

## Key Metrics (Prometheus)

- `deeplv_http_requests_total` - Request count by method/endpoint/status
- `deeplv_http_request_duration_seconds` - Latency histogram
- `deeplv_translations_total` - Translations by language pair and cache status
- `deeplv_cache_hits_total` / `deeplv_cache_misses_total` - Cache effectiveness
- `deeplv_provider_translations_total` - Translations by provider
- `deeplv_document_jobs_total` - Document jobs by status
- `deeplv_credits_spent_total` - Total credits consumed
- `deeplv_active_provider_keys_gauge` - Active BYOK keys count

## Security

- **Passwords**: bcrypt hashed
- **JWT tokens**: HS256, configurable expiry (default 24h)
- **API keys**: `dlv_live_...` format, SHA256 hashed in database
- **BYOK keys**: Fernet encrypted at rest (AES-128-CBC)
- **Rate limiting**: Redis sliding window per API key
- **Admin access**: Role-based (`is_admin` flag on user)

## License

MIT
