# DeepLV — Architecture

## System Diagram

```
                         +-----------+
                         |  React UI |
                         | (Vite+TS) |
                         +-----+-----+
                               |
                          HTTPS/REST
                               |
                   +-----------v-----------+
                   |     FastAPI Gateway    |
                   |  - auth (JWT)          |
                   |  - rate limiting        |
                   |  - input validation     |
                   |  - language detection   |
                   |  - cache check (Redis)  |
                   +-----+-----+-----+-----+
                         |     |     |
                    +----+  +--+--+  +----+
                    |       |     |       |
               +----v--+ +--v--+ +--v----+
               | Redis | | PG  | | Model |
               | Cache | | DB  | | Worker|
               +-------+ +-----+ +---+---+
                                      |
                               +------v------+
                               |  MarianMT   |
                               | (CTranslate2|
                               |  INT8 quant)|
                               +-------------+
```

## Services

### 1. API Gateway (FastAPI)
- **Port:** 8000
- **Responsibilities:** HTTP routing, JWT validation, rate limit enforcement, language detection, cache lookup/write, request logging
- **Stateless:** all state lives in Redis or PostgreSQL
- **Communicates with Model Worker** via internal HTTP (not queued — synchronous for latency)

### 2. Model Worker (FastAPI internal service)
- **Port:** 8001 (internal only, not exposed)
- **Responsibilities:** load MarianMT models, run inference, return translations
- **Isolation rationale:** model loading is memory-heavy (~200MB-1GB per language pair). Decoupling lets us scale model workers independently of API servers.
- **Model loading:** lazy — loads a language pair on first request, keeps in LRU memory cache
- **Inference:** CTranslate2 for INT8 quantized inference, ~2-5x faster than PyTorch default

### 3. Redis
- **Port:** 6379
- **Responsibilities:**
  - Translation cache: key = hash(source_lang, target_lang, text), value = translated text, TTL = 24h
  - Rate limit counters: sliding window per API key
  - Session data (if needed)

### 4. PostgreSQL
- **Port:** 5432
- **Responsibilities:**
  - User accounts and API keys
  - Translation usage logs (character count, timestamp, language pair, cache hit/miss)
  - Rate limit configuration per tier

### 5. React Frontend
- **Port:** 5173 (dev) / served via nginx in production
- **Responsibilities:** translation UI, language selection, debounced input

## Request Flow (translate API call)

```
1. Client sends POST /api/v1/translate
   { "text": "Hello world", "source_lang": "auto", "target_lang": "de" }

2. API Gateway:
   a. Validate JWT / API key
   b. Check rate limit (Redis INCR + EXPIRE)
   c. If source_lang == "auto": run fasttext language detection
   d. Compute cache key = sha256(source_lang + target_lang + normalized_text)
   e. Check Redis for cached translation
      - HIT:  return cached result (latency: <5ms)
      - MISS: continue to step 3

3. API Gateway -> Model Worker (internal HTTP POST):
   { "text": "Hello world", "source_lang": "en", "target_lang": "de" }

4. Model Worker:
   a. Check if en->de model is loaded in memory
      - Not loaded: load MarianMT en->de model (~2-5s first time, then cached)
   b. Tokenize input with SentencePiece
   c. Run CTranslate2 inference (beam_size=4)
   d. Decode tokens to text
   e. Return: { "translated_text": "Hallo Welt" }

5. API Gateway:
   a. Write result to Redis cache (SET with 24h TTL)
   b. Log usage to PostgreSQL (async, non-blocking)
   c. Return response to client:
      {
        "translated_text": "Hallo Welt",
        "source_lang": "en",
        "target_lang": "de",
        "cached": false,
        "latency_ms": 340
      }
```

## Scaling Strategy

| Component      | Scaling Approach                                              |
|----------------|---------------------------------------------------------------|
| API Gateway    | Horizontal — stateless, add replicas behind LB                |
| Model Worker   | Horizontal — each worker holds its own model LRU cache        |
| Redis          | Vertical first, then Redis Cluster for >64GB cache            |
| PostgreSQL     | Vertical first, read replicas for analytics queries           |
| Frontend       | CDN-served static assets, infinite scale                      |

## Key Architectural Decisions

1. **Synchronous model call (not queued)** — translation is latency-sensitive. Adding a message queue (Kafka/RabQ) would add 10-50ms and complexity for no benefit at this scale. If we needed to handle 10K+ concurrent translations, we'd add a queue with WebSocket push.

2. **Separate model worker process** — even though it adds a network hop (~1ms), it lets us restart/update models without downtime on the API, and scale GPU/CPU workers independently.

3. **CTranslate2 over raw PyTorch** — 2-5x inference speedup with INT8 quantization, lower memory footprint, production-proven.

4. **Redis over in-process cache** — survives API restarts, shared across API replicas, predictable memory management with TTL eviction.
