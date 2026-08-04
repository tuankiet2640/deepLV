# DeepLV — Roadmap

> Rewritten to reflect what's actually shipped, not the original MVP plan.
> The project outgrew that plan early — Milestones 5-7 below were never in
> the original scope at all.

## Milestone 1: Core Translation Pipeline — ✅ Shipped
**Goal:** text in, translation out, end-to-end via API

- Model worker service with CTranslate2 (INT8) inference
- API gateway with `/translate`, pivot-through-English for indirect pairs
- Language detection (fasttext)
- Redis translation cache
- Docker Compose for all services
- Health check endpoints

## Milestone 2: Auth, Rate Limiting, Persistence — ✅ Shipped
**Goal:** production access control and observability

- PostgreSQL schema (Alembic configured; see Milestone 7 on migration history)
- User registration and JWT auth, first user auto-promoted to admin
- API key management (create, revoke, list, dual auth alongside JWT)
- Per-key rate limiting via Redis sliding window
- Usage logging (characters translated, cache hits, latency)
- Structured logging (structlog) with request-ID correlation

## Milestone 3: Frontend — ✅ Shipped
**Goal:** DeepL-style web translation interface

Went well past "one translate page" — 18 routes exist today: translate,
document translate, history, settings, API keys, profile, admin dashboard,
login/register/forgot/reset password, getting started, API reference,
architecture, about, status, landing, and 404.

- React + Vite + TypeScript, TailwindCSS with dark mode
- Split-pane translation layout, debounced translate-as-you-type
- Language selector with auto-detect and swap
- Loading states, toast-based error handling, responsive design

## Milestone 4: Production Polish — 🟡 Mostly shipped
**Goal:** the details that separate portfolio from toy

- ✅ Prometheus metrics endpoint (`/metrics`)
- ✅ Request correlation IDs (structlog contextvars)
- ✅ API versioning (`/api/v1` prefix)
- ✅ Multi-sentence text splitting/reassembly, per-paragraph document chunking
- ✅ Input validation (5000-char limit, empty/oversized checks, unsupported pairs)
- ✅ CORS configuration
- ✅ Docker restart policies
- ✅ README with architecture diagram and quickstart
- ❌ **Docker healthchecks for `api`/`worker`/`frontend`** — only Postgres/Redis
  have them; app containers rely on `depends_on: service_started`, not
  `service_healthy`
- ❌ **Graceful shutdown** — no SIGTERM draining of in-flight requests/model
  unload; just a log line today

## Milestone 5: Multi-Provider, BYOK & Monetization — ✅ Shipped
**Goal:** not just MarianMT — let users bring real translation quality, and
pay for it if they want to

Never in the original plan; added because MarianMT alone isn't
production-relevant translation quality.

- Pluggable provider abstraction (MarianMT, OpenAI, HuggingFace, Google)
- BYOK: users store their own provider keys, encrypted at rest (Fernet)
- Credit system: balance, atomic deduction, purchase, transaction history
- Admin-owned provider keys as a paid fallback when a user has no BYOK key
- Admin dashboard: user management, usage analytics, system settings

## Milestone 6: Document Translation — ✅ Shipped
**Goal:** translate whole files, not just pasted text

- Upload PDF/DOCX/TXT, background job processing, cost estimation pre-flight
- Format-preserving rebuild:
  - **DOCX**: paragraphs, table cells, and text box content (`w:txbxContent`)
    all translated in place, preserving styles/images/layout
  - **PDF**: occlusion-and-redraw (pdfplumber for block/font extraction,
    reportlab for redraw with shrink-to-fit, pypdf to composite) — preserves
    images and approximate layout instead of flattening to plain text
  - **TXT**: unchanged, flat text
- Graceful degradation: a rebuild failure falls back to plain-text output
  rather than failing the job

## Milestone 7: Production Hardening — 🟡 In progress
**Goal:** the gap between "runs" and "trustworthy in production" — this is
the current focus, driven by real incidents after deploy, not a pre-planned
checklist

- ✅ Alembic migrations auto-apply on startup (the project's first migration
  shipped alongside — schema had relied entirely on `create_all()` before)
- ✅ Fixed: non-ASCII filenames crashing document downloads (RFC 5987 header encoding)
- ✅ Fixed: usage logging silently failing on every request (session/transaction bug)
- ✅ Fixed: a stale localStorage value silently dropping a valid session JWT
- ✅ Fixed: DOCX tables/text boxes left untranslated (extraction gaps)
- ✅ Fixed: PDF translation destroying layout/images (full rewrite, see Milestone 6)
- ✅ UI warns when MarianMT will pivot through English for a language pair
  (known quality ceiling on formal/technical text, not a bug)
- ❌ Docker healthchecks + graceful shutdown (carried over from Milestone 4)
- ❌ **Row Level Security disabled on all Supabase tables** — flagged by
  Supabase's advisor, not yet addressed. Real exposure if the anon key is
  ever public; not yet assessed for this app's actual usage pattern (direct
  `asyncpg` connection, not Supabase's REST/PostgREST layer)
- ✅ `.env.example` / `RAILWAY.md` kept in sync as new env vars ship (ongoing;
  most recently for Milestone 8's Resend variables)

## Milestone 8: Account Hardening — ✅ Shipped
**Goal:** auth was looser than a product with real user accounts should
have — no email verification, no working password-reset email, and an
almost-empty profile page

- Email verification via a 6-digit OTP code on signup (hashed at rest,
  15-minute expiry, 5-attempt lockout, rate-limited resend/verify
  endpoints); login is blocked until verified
- Fixed: `forgot-password` used to return the raw reset token directly in
  the API JSON response (and the frontend displayed it on screen) instead
  of emailing it — now sends a real reset link
- Email delivery via Resend's HTTP API (`src/api/services/email.py`),
  with a graceful log-instead-of-send fallback when unconfigured (no
  Resend account needed for local dev)
- Richer profile: avatar upload (stored as bytes in Postgres, same
  no-external-storage approach as document results), display name,
  default source/target language + theme preferences (synced
  cross-device on login), account activity stats (member since, last
  login, translation count)
- Google OAuth login was scoped out of this pass (explicit choice — email
  verification and profile enrichment first)

## Milestone 9: Anonymous Translate Tier — ✅ Shipped
**Goal:** `/translate` was reachable while signed out (not behind
`ProtectedRoute`), but every request 401'd — a dead-end UI for anyone
trying the product before creating an account

- New `get_optional_user` auth dependency: resolves API key/JWT like the
  existing one, but returns `(None, None)` instead of raising when no
  credential is present
- `/translate` now serves anonymous requests for `provider: "marianmt"`
  only (free, local, no cost) — every other provider still requires
  sign-in. Anonymous requests are rate-limited at 20/hour per IP
  (`X-Forwarded-For`-aware), separate from the per-account limiter;
  usage logging is skipped (no account to attribute it to)
- Frontend: `ProviderSelector` marks non-MarianMT providers "sign in
  required" when signed out; `TranslatePage` shows a free-tier banner
  linking to `/register` and falls back to MarianMT if a session ends
  mid-selection
- Documented in the README, Getting Started, and API Reference pages
