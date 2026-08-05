# DeepLV — Task Breakdown

> Rewritten to reflect actual status. See `roadmap.md` for the milestone
> narrative — this file is the checklist view.

## Milestone 1: Core Translation Pipeline

- [x] Project directory structure
- [x] Python project with pyproject.toml (uv-managed) and dependency management
- [x] Model worker service (FastAPI on port 8001)
  - [x] CTranslate2 model loader with LRU cache (max 6 models, configurable)
  - [x] `/translate` endpoint (text, source_lang, target_lang)
  - [x] `/health` endpoint
  - [x] Model download/conversion script (`scripts/download_models.py`)
  - [x] Pivot translation through English for indirect pairs (e.g. vi→fr)
- [x] API gateway service (FastAPI on port 8000)
  - [x] `/api/v1/translate` endpoint (now routes through the multi-provider layer, not a direct worker passthrough — see Milestone 5)
  - [x] Language detection with fasttext
  - [x] Redis cache check/write logic
  - [x] Forward to model worker on cache miss
  - [x] `/health` endpoint (checks Redis, Postgres, worker)
- [x] Redis configuration
- [x] Docker Compose with api, worker, redis (+ postgres, frontend, prometheus, grafana)
- [x] End-to-end smoke test (curl translate request)

## Milestone 2: Auth, Rate Limiting, Persistence

- [x] PostgreSQL service in Docker Compose
- [x] SQLAlchemy async models (11 models today: User, APIKey, UsageLog, DocumentJob, DocumentResult, ProviderKey, AdminProviderKey, AdminSettings, CreditTransaction, PasswordResetToken, and more)
- [x] Alembic configured; migrations now auto-apply on startup (see Milestone 7)
- [x] POST /api/v1/auth/register (first user auto-promoted to admin)
- [x] POST /api/v1/auth/login (returns JWT)
- [x] Password reset flow (forgot/reset/change)
- [x] POST /api/v1/keys (create API key)
- [x] GET /api/v1/keys (list keys)
- [x] DELETE /api/v1/keys/:id (revoke key)
- [x] JWT middleware (verify on protected routes)
- [x] API key auth middleware (X-API-Key header), dual-mode with JWT fallback
- [x] Rate limiter middleware (Redis sliding window)
- [x] Usage logging (async write to PG after each translation)
- [x] GET /api/v1/usage + /usage/history (filtering/pagination)
- [x] Structured logging setup (structlog) with request-ID correlation

## Milestone 3: Frontend

- [x] Scaffold React + Vite + TypeScript project
- [x] TailwindCSS setup with dark mode
- [x] TranslationPage (split-pane layout)
- [x] Reusable TranslationPanel (editable vs read-only)
- [x] useTranslation hook (debounced API call, 300ms)
- [x] Language swap button
- [x] Auto-detect indicator
- [x] Loading state on target panel
- [x] Toast-based error handling (app-wide, not just translate)
- [x] Responsive breakpoints (mobile stacks vertical)
- [x] Nginx config for production serving
- [x] 13 additional pages beyond the original plan: document translate,
      history, settings, API keys, profile, admin, getting started,
      API reference, architecture, about, status, landing, 404

## Milestone 4: Production Polish

- [x] Prometheus metrics (request count, latency, cache hit rate, model load time)
- [x] Correlation ID middleware (X-Request-ID)
- [x] Text splitting (sentence/paragraph boundary detection, both worker- and document-level)
- [x] Input validation (5000 char limit, empty text, unsupported pairs)
- [x] CORS middleware
- [x] docker-compose.yml restart policies
- [x] README.md with architecture, quickstart, API reference
- [x] .env.example with documented variables (kept current as of this pass)
- [ ] Docker healthchecks on api/worker/frontend containers (`service_healthy`, not just `service_started`)
- [ ] Graceful shutdown (drain in-flight requests, unload models on SIGTERM)

## Milestone 5: Multi-Provider, BYOK & Monetization

- [x] Pluggable provider abstraction (`TranslationProvider` base + MarianMT/OpenAI/HuggingFace/Google implementations)
- [x] BYOK: encrypted provider key storage (Fernet), CRUD via /api/v1/providers/keys
- [x] Credit system: balance, atomic deduction, purchase, transaction history
- [x] Admin-owned provider keys as paid fallback when no BYOK key is stored
- [x] Admin dashboard: user management, usage analytics, system settings, admin-managed keys
- [x] Cost estimate widgets (pre-flight credit cost preview) for text and documents

## Milestone 6: Document Translation

- [x] Upload PDF/DOCX/TXT (10MB limit), background job processing
- [x] Job status polling, history, bulk/single deletion
- [x] Per-paragraph translation (bounded concurrency) instead of coarse chunking
- [x] DOCX format-preserving rebuild: body paragraphs, table cells, text box content
- [x] PDF format-preserving rebuild: pdfplumber block/font extraction → reportlab occlusion+redraw (shrink-to-fit) → pypdf composite; preserves embedded images
- [x] Vietnamese/Unicode-safe PDF text rendering (vendored DejaVu Sans font)
- [x] Graceful degradation: rebuild failure falls back to plain-text output, not a failed job

## Milestone 7: Production Hardening (current focus)

- [x] Alembic's first real migration + auto-apply on startup (idempotent, safe for both fresh and existing databases)
- [x] Fix: non-ASCII filenames crashing document downloads (RFC 5987 Content-Disposition encoding)
- [x] Fix: usage logging failing on ~every request (background task reusing a request-scoped DB session with an already-open transaction)
- [x] Fix: stale `localStorage` value silently shadowing a valid session JWT on translate requests
- [x] Fix: DOCX tables and text boxes left untranslated (extraction didn't reach them)
- [x] Fix: PDF translation destroying layout/images (see Milestone 6)
- [x] UI warning when MarianMT will pivot through English (quality ceiling on formal/technical text)
- [x] `.env.example` and `RAILWAY.md` reconciled with actual deployed behavior (ongoing, most recently for Resend)
- [ ] Docker healthchecks + graceful shutdown (see Milestone 4 — same items, still open)
- [ ] Row Level Security on Supabase tables (flagged by Supabase's advisor; not yet assessed/enabled — enabling without policies would lock out the app's own backend, so this needs real policy design, not a blind `ENABLE ROW LEVEL SECURITY`)
- [ ] Automated regression coverage for the session/transaction and auth-header bugs above (both were verified by hand against a live DB rather than locked in with a committed test)

## Milestone 8: Account Hardening

- [x] `User` model: `is_verified`, `display_name`, `avatar`/`avatar_content_type`, `default_source_lang`/`default_target_lang`, `theme_preference`, `last_login_at`
- [x] `EmailOTP` model + migration (hashed code, expiry, attempt counter, consumed flag)
- [x] `src/api/services/email.py`: Resend HTTP API via httpx, log-instead-of-send fallback when unconfigured
- [x] `src/api/services/otp.py`: generate/hash/create/verify with 15-min expiry and 5-attempt lockout
- [x] `POST /auth/verify-email` + `/auth/resend-verification`, both rate-limited
- [x] `login` blocks unverified accounts (403 `email_not_verified`); sets `last_login_at`
- [x] Fixed: `forgot-password` now emails a reset link instead of returning the token in the API response (and the frontend no longer displays a token)
- [x] New `users.py` router: `GET`/`PATCH /users/me`, avatar upload/get/delete
- [x] Frontend: `VerifyEmailPage`, updated Register/Login/ForgotPassword/ResetPassword flows, `AuthContext.refreshUser()`, expanded `ProfilePage` (avatar, display name, preferences, activity stats), cross-device theme sync
- [x] pytest-asyncio session-scoped event loop fix (`asyncio_default_fixture_loop_scope`/`asyncio_default_test_loop_scope`) — the module-level DB engine was breaking across function-scoped loops when tests ran against a real Postgres
- [ ] Google OAuth login (explicitly deferred to a follow-up pass)

## Milestone 9: Anonymous Translate Tier

- [x] `get_optional_user` dependency (`src/api/middleware/dependencies.py`) — returns `(None, None)` instead of raising when no credential is present
- [x] `/translate` accepts anonymous requests for `provider: "marianmt"` only; every other provider still 401s
- [x] IP-based rate limiting for anonymous requests (20/hour, `X-Forwarded-For`-aware), separate from the per-account limiter
- [x] Usage logging skipped for anonymous requests (`UsageLog.user_id` is a non-nullable FK)
- [x] `ProviderManager.resolve()` accepts `user: User | None`
- [x] Frontend: `ProviderSelector` "sign in required" badges, `TranslatePage` anon-tier banner + MarianMT fallback on session end
- [x] `tests/test_anonymous_translate.py` + updated `test_api.py`
- [x] README, Getting Started, and API Reference docs updated

## Milestone 10: Glossary / Custom Terminology

- [x] `GlossaryTerm` model + migration (indexed on `user_id, source_lang, target_lang`)
- [x] `src/api/services/glossary.py`: `substitute()`/`restore()` via stable-hash placeholders, longest-term-first, non-alphanumeric lookaround boundaries (not `\b` — confirmed broken for "C++"/"Acme Corp."/"AT&T"-style terms), `get_terms_for_pair()`
- [x] `/translate` integration: substitute before cache lookup/provider call, restore after either a cache hit or fresh call; cache stores placeholder-templated text only, never a resolved `target_term` — verified safe against the existing global (no-user_id) cache
- [x] Document translation integration: terms fetched once per job, both `_translate_paragraph` call sites (normal + oversized-chunk-split paths) wrapped
- [x] Full CRUD router (`/glossary`): create/list/patch/delete, ownership scoping, case-insensitive duplicate rejection (409), 500-term cap per account
- [x] Frontend: "Glossary" tab in Settings, mirrors the Provider Keys tab pattern exactly
- [x] `tests/test_glossary.py`: substitution/restoration unit tests (including the punctuation boundary cases), CRUD ownership/duplicate/cap tests, `/translate` integration test with a mocked provider, cache-sharing-safety test (two users, same raw input, different glossaries, each gets their own correct output)
