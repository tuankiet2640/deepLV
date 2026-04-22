# DeepLV — Data Pipeline

## Model Preparation Pipeline

```
HuggingFace Hub
    |
    v
[download_models.py]          # Downloads MarianMT models for each language pair
    |
    v
PyTorch checkpoints           # ~/.cache/huggingface/hub/
    |
    v
[convert_models.py]           # Converts to CTranslate2 format with INT8 quantization
    |
    v
CTranslate2 models            # /models/{src}-{tgt}/ (model.bin, vocabulary, config)
    |
    v
Docker volume mount            # Persisted across container restarts
```

### Supported Model Matrix

| Source | Target | HuggingFace Model ID             | Size (CT2 INT8) |
|--------|--------|----------------------------------|-----------------|
| en     | de     | Helsinki-NLP/opus-mt-en-de       | ~70MB           |
| de     | en     | Helsinki-NLP/opus-mt-de-en       | ~70MB           |
| en     | fr     | Helsinki-NLP/opus-mt-en-fr       | ~70MB           |
| fr     | en     | Helsinki-NLP/opus-mt-fr-en       | ~70MB           |
| en     | es     | Helsinki-NLP/opus-mt-en-es       | ~70MB           |
| es     | en     | Helsinki-NLP/opus-mt-es-en       | ~70MB           |
| en     | zh     | Helsinki-NLP/opus-mt-en-zh       | ~70MB           |
| zh     | en     | Helsinki-NLP/opus-mt-zh-en       | ~70MB           |
| en     | ja     | Helsinki-NLP/opus-mt-en-jap      | ~70MB           |
| ja     | en     | Helsinki-NLP/opus-mt-jap-en      | ~70MB           |
| en     | vi     | Helsinki-NLP/opus-mt-en-vi       | ~70MB           |
| vi     | en     | Helsinki-NLP/opus-mt-vi-en       | ~70MB           |
| en     | ko     | Helsinki-NLP/opus-mt-en-ko       | ~70MB           |
| ko     | en     | Helsinki-NLP/opus-mt-ko-en       | ~70MB           |
| en     | pt     | Helsinki-NLP/opus-mt-en-pt       | ~70MB           |
| pt     | en     | Helsinki-NLP/opus-mt-pt-en       | ~70MB           |
| en     | ru     | Helsinki-NLP/opus-mt-en-ru       | ~70MB           |
| ru     | en     | Helsinki-NLP/opus-mt-ru-en       | ~70MB           |

### Non-English Pivot Translation

For language pairs without a direct model (e.g., de -> fr):
```
Input (de) -> translate de->en -> translate en->fr -> Output (fr)
```

This doubles latency but covers all NxN combinations with only 2N models.

## Translation Cache (Redis)

### Key Format
```
translate:{sha256(source_lang + ":" + target_lang + ":" + normalized_text)}
```

### Normalization
- Strip leading/trailing whitespace
- Collapse internal whitespace to single space
- Lowercase for cache key computation (original case preserved in value)

### Value Format
```json
{
  "translated_text": "Hallo Welt",
  "source_lang": "en",
  "target_lang": "de",
  "model_id": "Helsinki-NLP/opus-mt-en-de",
  "created_at": "2026-04-22T10:00:00Z"
}
```

### Eviction Policy
- TTL: 24 hours per entry
- Redis maxmemory-policy: allkeys-lru
- Max memory: 512MB

## Usage Logging (PostgreSQL)

### Write Path (async)
After each translation response is sent to client:
```python
# Non-blocking — does not add to response latency
asyncio.create_task(log_usage(
    user_id=user.id,
    api_key_id=key.id,
    source_lang="en",
    target_lang="de",
    character_count=len(text),
    cached=False,
    latency_ms=342,
))
```

### Schema
```sql
CREATE TABLE usage_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    api_key_id UUID NOT NULL REFERENCES api_keys(id),
    source_lang VARCHAR(5) NOT NULL,
    target_lang VARCHAR(5) NOT NULL,
    character_count INTEGER NOT NULL,
    cached BOOLEAN NOT NULL DEFAULT FALSE,
    latency_ms INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_usage_logs_user_date ON usage_logs (user_id, created_at);
CREATE INDEX idx_usage_logs_key_date ON usage_logs (api_key_id, created_at);
```

## Model Worker Memory Management

### LRU Model Cache
```
Max loaded models: 6 (configurable via MODEL_CACHE_SIZE env var)
Eviction: least-recently-used when loading a new model and at capacity
Memory per model: ~200-400MB (varies by language pair)
Total budget: ~2-4GB for model cache
```

### Lifecycle
```
1. Request arrives for en->de translation
2. Check in-memory dict: models["en-de"]
3. MISS: load from disk (/models/en-de/)
   - If cache full: evict LRU model
   - Load CTranslate2 Translator object
   - Store in cache with access timestamp
4. HIT: update access timestamp, return Translator
5. Run translate_batch() on the Translator
```
