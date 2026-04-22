# DeepLV — Constraints

## Latency Targets

| Operation                  | Target    | Acceptable | Notes                                    |
|----------------------------|-----------|------------|------------------------------------------|
| Cached translation         | <5ms      | <20ms      | Redis GET + JSON serialize               |
| Single sentence inference  | <500ms    | <1s        | CTranslate2 INT8, beam_size=4            |
| Long text (500 words)      | <2s       | <3s        | Split into sentences, translate in batch  |
| Language detection          | <10ms     | <50ms      | fasttext in-process, no network hop       |
| First request (cold model) | <8s       | <15s       | Model load from disk, one-time per pair   |
| API auth + rate limit      | <2ms      | <5ms       | Redis-backed, in hot path                 |

## Throughput

- **Target:** 50 concurrent translation requests on a single API + single model worker
- **Rate limit default:** 100 requests/minute per API key (configurable per tier)
- **Character limit per request:** 5,000 characters (prevents abuse, keeps inference bounded)

## Memory Budget

| Component      | Budget   | Notes                                              |
|----------------|----------|----------------------------------------------------|
| Model Worker   | 2-4 GB   | ~200-400MB per loaded model, LRU evicts to max 6   |
| API Gateway    | 512 MB   | Stateless, low memory footprint                     |
| Redis          | 512 MB   | ~1M cached translations at ~500 bytes avg           |
| PostgreSQL     | 256 MB   | Usage logs, users — small dataset                   |

## Simplifications (honest scope cuts)

These are deliberate choices for a portfolio project, not oversights:

1. **Pretrained models only** — MarianMT/Opus-MT from HuggingFace. No fine-tuning. Translation quality is "good" not "DeepL-quality." The system design is the showcase, not BLEU scores.

2. **CPU inference only** — CTranslate2 INT8 on CPU. No GPU requirement means `docker compose up` works on any machine. Production would use GPU for 10x throughput.

3. **10 language pairs via English pivot** — direct pairs where Opus-MT models exist (en<->de, en<->fr, en<->es, en<->zh, en<->ja, en<->vi, en<->ko, en<->pt, en<->ru). Non-English pairs (e.g., de->fr) pivot through English. This is how most production systems work at smaller scale.

4. **SQLite-compatible test mode** — PostgreSQL for Docker deployment, but tests can run with SQLite for CI speed.

5. **No GPU autoscaling** — Kubernetes manifests are conceptual. The system runs via Docker Compose.

6. **No WebSocket streaming** — translations return as complete responses, not token-streamed. Acceptable because translation latency is <1s for most inputs.

## Hard Limits

- Max input text: 5,000 characters (HTTP 413 beyond this)
- Max concurrent model loads: 6 language pairs in memory (LRU eviction)
- Max API keys per user: 5
- JWT token expiry: 24 hours
- Cache TTL: 24 hours
- Rate limit window: 60 seconds (sliding)
