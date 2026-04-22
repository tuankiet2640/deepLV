# DeepLV — Product Definition

## What It Is

A production-grade machine translation API and web interface, modeled after DeepL.
Supports real-time text translation across multiple language pairs with sub-second latency.

## Users

1. **API consumers** — developers integrating translation into their applications via REST API with API key authentication
2. **Web users** — individuals using the browser-based translation interface for ad-hoc text translation
3. **Hiring panel reviewers** — engineers evaluating this as a systems-level portfolio piece (the system must be self-explanatory and inspectable)

## Core Features

- **Real-time translation** — translate text between supported language pairs (EN, DE, FR, ES, ZH, JA, VI, KO, PT, RU)
- **Auto-detect source language** — identify input language automatically when not specified
- **Translate-as-you-type** — debounced live translation in the web UI, no submit button
- **Translation caching** — identical inputs return cached results instantly
- **API key authentication** — JWT-based auth for API access, usage tracking per key
- **Rate limiting** — per-user request throttling to prevent abuse
- **Usage dashboard** — character count, request count, cache hit rate per API key
- **Multi-sentence handling** — split long text into sentences, translate individually, reassemble
- **Language pair validation** — reject unsupported pairs with clear error messages

## Non-Goals

- **No model training** — we use pretrained MarianMT/Opus-MT models. Training is out of scope.
- **No document upload** — text-only input. No PDF/DOCX parsing.
- **No glossary/terminology customization** — no user-defined translation rules.
- **No collaborative features** — single-user translation, no shared workspaces.
- **No billing/payment** — usage tracking exists but no payment integration.
- **No mobile app** — responsive web UI only, no native clients.
- **No speech-to-text** — text input only, no audio translation.

## Success Criteria

A hiring panel member should be able to:
1. Read the architecture docs and understand every design decision
2. `docker compose up` and have the full system running in under 2 minutes
3. Open the web UI and translate text with visible sub-second response
4. Hit the API with curl and get a clean JSON response
5. See metrics, logs, and health checks that prove this is production-aware
