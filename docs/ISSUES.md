# DeepLV — GitHub Issues Tracking

These are the issues that should be created on GitHub for this project. The features in PR #1 address issues 1-5. Issues 6-8 are follow-up improvements identified during code review.

---

## Feature Issues (Implemented in PR #1)

### Issue #1: Multi-Provider Translation Engine
**Labels:** `enhancement`, `core`

Implement a flexible multi-provider translation engine giving users autonomous choice:
- **MarianMT (built-in, free)** — Local CTranslate2 inference
- **OpenAI** — GPT-based translation via user's API key or admin credits
- **HuggingFace** — Inference API via user's key or admin credits
- **Google Translate** — Cloud Translation API via user's key

User options:
1. Free tier — Built-in MarianMT models
2. BYOK (Bring Your Own Key) — User supplies their own API key
3. Pay with credits — Use admin-managed premium keys

Technical: Provider abstraction layer, Fernet encryption at rest, atomic credit deduction.

---

### Issue #2: Document Upload & AI Translation
**Labels:** `enhancement`, `core`

Upload documents (PDF, DOCX, TXT up to 10MB) and translate them using any available provider:
- Smart text chunking (paragraph → sentence → hard split at 5000 chars)
- Background translation with async job tracking
- Progress reporting and download of translated documents
- Credit reservation BEFORE translation begins
- Startup sweep for orphaned jobs

---

### Issue #3: Admin Dashboard
**Labels:** `enhancement`, `admin`

Full admin panel for managing the DeepLV platform:
- User management (list, view, suspend)
- Usage analytics (translations per day, popular language pairs)
- Provider key management (add/rotate admin API keys)
- System settings (rate limits, pricing, credits per character)
- Admin role enforcement middleware

---

### Issue #4: Full Observability Stack (Prometheus + Grafana)
**Labels:** `enhancement`, `infrastructure`

Production observability:
- Prometheus scraping API + worker metrics
- Grafana with pre-built dashboard (8 panels)
- Metrics: request latency, cache hits, provider usage, document jobs, credits spent
- Structured JSON logging with correlation IDs
- Docker Compose services for prometheus (port 9090) and grafana (port 3001)

---

### Issue #5: Frontend - Document Upload & Settings Pages
**Labels:** `enhancement`, `frontend`

New frontend pages:
- Document upload with drag-and-drop, provider selection, job status tracking
- Settings page for BYOK key management and credit balance
- Provider selector integrated into text translate page
- Updated navigation

---

## Follow-up Issues (From Code Review)

### Issue #6: Fix non-atomic credit purchase endpoint
**Labels:** `bug`, `security`

The `purchase_credits` endpoint uses `user.credits_balance += req.amount` which is not atomic. Two concurrent purchases can lose one addition (last-write-wins). Fix: use `UPDATE users SET credits_balance = credits_balance + :amount` like the deduction path.

---

### Issue #7: Cache Fernet instance in encryption module
**Labels:** `performance`, `tech-debt`

`_get_fernet()` in `src/api/services/encryption.py` re-instantiates `APISettings()` on every call, re-reading env vars. Cache the Fernet instance at module level or use `@lru_cache`.

---

### Issue #8: Add background task exception tracking
**Labels:** `reliability`, `observability`

`asyncio.create_task(...)` in document upload handler doesn't store the task reference. Unhandled exceptions outside the inner try/except vanish silently. Store task refs and add `task.add_done_callback` to log failures.

---

## How to Create These on GitHub

```bash
# After merging PR #1, create issues:
gh issue create --title "feat: Multi-provider translation engine" --body "..." --label enhancement
gh issue create --title "feat: Document upload & AI translation" --body "..." --label enhancement
gh issue create --title "feat: Admin dashboard" --body "..." --label enhancement
gh issue create --title "feat: Observability stack (Prometheus + Grafana)" --body "..." --label enhancement,infrastructure
gh issue create --title "feat: Frontend document upload & settings pages" --body "..." --label enhancement,frontend
gh issue create --title "fix: Non-atomic credit purchase endpoint" --body "..." --label bug
gh issue create --title "perf: Cache Fernet instance in encryption module" --body "..." --label performance
gh issue create --title "fix: Background task exception tracking" --body "..." --label reliability
```
