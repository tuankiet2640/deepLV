# DeepLV — API Specification

**Base URL:** `http://localhost:8000/api/v1`
**Auth:** JWT Bearer token or `X-API-Key` header
**Content-Type:** `application/json`

---

## Translation

### POST /translate

Translate text between language pairs.

**Auth:** API Key required (`X-API-Key` header)

**Request:**
```json
{
  "text": "Hello, how are you?",
  "source_lang": "auto",
  "target_lang": "de"
}
```

| Field        | Type   | Required | Notes                                                |
|--------------|--------|----------|------------------------------------------------------|
| text         | string | yes      | 1-5000 characters                                     |
| source_lang  | string | yes      | ISO 639-1 code or "auto" for detection                |
| target_lang  | string | yes      | ISO 639-1 code                                        |

**Response (200):**
```json
{
  "translated_text": "Hallo, wie geht es Ihnen?",
  "source_lang": "en",
  "target_lang": "de",
  "detected_lang": true,
  "cached": false,
  "latency_ms": 342
}
```

**Errors:**
| Status | Condition                          |
|--------|------------------------------------|
| 400    | Empty text, unsupported language   |
| 401    | Missing or invalid API key         |
| 413    | Text exceeds 5000 characters       |
| 429    | Rate limit exceeded                |
| 503    | Model worker unavailable           |

### GET /languages

List supported languages.

**Auth:** none

**Response (200):**
```json
{
  "languages": [
    { "code": "en", "name": "English" },
    { "code": "de", "name": "German" },
    { "code": "fr", "name": "French" },
    { "code": "es", "name": "Spanish" },
    { "code": "zh", "name": "Chinese" },
    { "code": "ja", "name": "Japanese" },
    { "code": "vi", "name": "Vietnamese" },
    { "code": "ko", "name": "Korean" },
    { "code": "pt", "name": "Portuguese" },
    { "code": "ru", "name": "Russian" }
  ]
}
```

---

## Authentication

### POST /auth/register

**Auth:** none

**Request:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response (201):**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "created_at": "2026-04-22T10:00:00Z"
}
```

**Errors:** 400 (invalid email/password), 409 (email exists)

### POST /auth/login

**Auth:** none

**Request:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response (200):**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

**Errors:** 401 (invalid credentials)

---

## API Keys

### POST /keys

Create a new API key.

**Auth:** JWT Bearer token

**Request:**
```json
{
  "name": "my-app-key"
}
```

**Response (201):**
```json
{
  "id": "uuid",
  "name": "my-app-key",
  "key": "dlv_live_a1b2c3d4e5f6...",
  "created_at": "2026-04-22T10:00:00Z"
}
```

*Note: the full key is only returned once at creation time.*

**Errors:** 400 (name required), 409 (limit reached, max 5 keys)

### GET /keys

List API keys (key values are masked).

**Auth:** JWT Bearer token

**Response (200):**
```json
{
  "keys": [
    {
      "id": "uuid",
      "name": "my-app-key",
      "key_prefix": "dlv_live_a1b2...",
      "created_at": "2026-04-22T10:00:00Z",
      "last_used_at": "2026-04-22T12:30:00Z"
    }
  ]
}
```

### DELETE /keys/{key_id}

Revoke an API key.

**Auth:** JWT Bearer token

**Response:** 204 No Content

**Errors:** 404 (key not found)

---

## Usage

### GET /usage

Get translation usage statistics.

**Auth:** JWT Bearer token

**Query params:**
| Param  | Type   | Default  | Notes                    |
|--------|--------|----------|--------------------------|
| key_id | string | all keys | Filter to specific key   |
| days   | int    | 30       | Lookback period (1-90)   |

**Response (200):**
```json
{
  "total_requests": 1523,
  "total_characters": 284100,
  "cache_hit_rate": 0.34,
  "by_language_pair": {
    "en->de": { "requests": 800, "characters": 150000 },
    "en->fr": { "requests": 723, "characters": 134100 }
  },
  "daily": [
    { "date": "2026-04-22", "requests": 45, "characters": 8200 }
  ]
}
```

---

## System

### GET /health

**Auth:** none

**Response (200):**
```json
{
  "status": "healthy",
  "services": {
    "redis": "connected",
    "postgres": "connected",
    "model_worker": "connected"
  },
  "version": "1.0.0",
  "uptime_seconds": 3600
}
```

### GET /metrics

Prometheus-format metrics. Scraped by monitoring.

**Auth:** none
