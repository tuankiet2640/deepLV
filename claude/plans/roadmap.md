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

## Milestone 10: Glossary / Custom Terminology — ✅ Shipped
**Goal:** a real product differentiator (matches DeepL Pro's glossary
feature) — force specific terms (product names, brand names) to always
translate a certain way, per language pair, regardless of which of the 4
providers is used

- Provider-agnostic **text substitution**, not prompt injection (only
  OpenAI accepts a system prompt; MarianMT/HuggingFace/Google don't):
  matching source terms are replaced with a stable placeholder before the
  provider call and restored to the user's target term after
  (`src/api/services/glossary.py`)
- Boundary matching uses explicit non-alphanumeric lookarounds, not `\b` —
  `\b` was confirmed broken for terms starting/ending on punctuation
  ("C++", "Acme Corp.", "AT&T" would silently never match)
- The existing translation cache (global, no user_id in its key) stays
  safe: substitution happens before the cache key is built, so a shared
  cache entry only ever holds placeholder-templated text — each request
  restores locally from its own stored terms, so one user's `target_term`
  choice can never leak into another user's response
- Applied uniformly to both `/translate` and document translation
  (fetched once per job, not per paragraph)
- New `GlossaryTerm` model/table, full CRUD (`/glossary`), 500-term cap
  per account, duplicate rejection
- Frontend: new "Glossary" tab in Settings, mirroring the existing
  Provider Keys tab's list/add/delete pattern — no per-translation
  selector needed, applied automatically
- Explicitly out of scope: a Redis-backed lookup cache for glossary terms
  (a single indexed query per request is cheap enough at this app's
  scale), multiple named glossaries per user (DeepL's actual model — this
  app uses one flat auto-applied list per language pair instead), and a
  "glossary applied" indicator in the translate UI

**Follow-up, same milestone: export/import + context metadata.** A user
asked how a Legal-vs-Marketing scenario works — glossaries are per-user,
so two *different* people already have independent glossaries with no
conflict, but there was no way to *share* one without re-entering every
term by hand, and no way to record *why* a term is translated a certain
way. Rather than building team/organization accounts (a much bigger
feature — no multi-user grouping exists anywhere in this app), the fix is
decentralized:
- `category` and `notes` fields on each term — descriptive only this
  round, don't filter which terms apply at translate time
- `GET /glossary/export?format=json|csv` and `POST /glossary/import` —
  export a glossary to a file, import it into *anyone's* account (verified
  end-to-end: a "Legal" account's term, with its category/notes, exported
  and imported into a "Marketing" account's glossary)
- Import is partial-success, never all-or-nothing: bad rows (invalid
  language, empty term, duplicate) are skipped and reported per-row, valid
  rows still get created; the existing 500-term cap is enforced by
  truncating the import rather than rejecting it outright
- Frontend: Export JSON/CSV buttons (blob-download) and an Import button
  next to Add Term in the Glossary tab
