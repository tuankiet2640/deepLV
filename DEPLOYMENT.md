# DeepLV — Production Deployment Guide

Deploy DeepLV on your laptop, Raspberry Pi, or any machine with Docker, using Supabase for the database and Cloudflare Tunnel for public HTTPS access.

## Architecture (Production)

```
Internet → Cloudflare Tunnel → nginx (port 80 internal)
                                  ├── /        → React SPA (static files)
                                  ├── /api/    → FastAPI Gateway
                                  ├── /grafana → Grafana dashboards
                                  └── /metrics → Prometheus (internal only)

FastAPI Gateway → Redis (local, cache + rate limits)
               → Supabase PostgreSQL (external, managed)
               → Model Worker (local, MarianMT inference)
               → External APIs (OpenAI, HuggingFace, Google — via BYOK or admin keys)
```

## Prerequisites

- Docker & Docker Compose v2+
- A [Supabase](https://supabase.com) project (free tier works)
- A [Cloudflare](https://cloudflare.com) account with a domain
- 8GB RAM recommended (4GB minimum — reduces model cache to 2)

## Quick Start (5 minutes)

### 1. Clone & configure

```bash
git clone https://github.com/tuankiet2640/deepLV.git
cd deepLV
cp .env.production .env
```

### 2. Fill in your .env

Edit `.env` with your actual values:

```bash
# Generate secrets
openssl rand -hex 32  # Use for JWT_SECRET
openssl rand -hex 32  # Use for ENCRYPTION_KEY
```

Required values to set:
| Variable | Where to get it |
|----------|----------------|
| `DOMAIN` | Your domain (e.g., `translate.mydomain.com`) |
| `DATABASE_URL` | Supabase Dashboard → Settings → Database → Connection string (use Pooler URI, port 6543) |
| `JWT_SECRET` | `openssl rand -hex 32` |
| `ENCRYPTION_KEY` | `openssl rand -hex 32` |
| `CLOUDFLARE_TUNNEL_TOKEN` | Cloudflare Zero Trust → Networks → Tunnels → Create |
| `GRAFANA_ADMIN_PASSWORD` | Your choice |

### 3. Set up Cloudflare Tunnel

1. Go to [Cloudflare Zero Trust Dashboard](https://one.dash.cloudflare.com)
2. Navigate to **Networks → Tunnels**
3. Click **Create a tunnel**
4. Name it (e.g., `deeplv`)
5. Copy the tunnel token → paste into `.env` as `CLOUDFLARE_TUNNEL_TOKEN`
6. Add a **Public Hostname**:
   - Subdomain: `translate` (or whatever you want)
   - Domain: `yourdomain.com`
   - Service: `http://frontend:80`
   - (Under "Additional settings" → set "No TLS Verify" to ON since it's HTTP internally)

### 4. Set up Supabase

1. Create a new project at [supabase.com](https://supabase.com)
2. Go to **Settings → Database**
3. Copy the **Connection string** (URI format)
4. Important: Use the **Transaction pooler** connection (port `6543`), not the direct connection
5. Format for `.env`:
   ```
   DATABASE_URL=postgresql+asyncpg://postgres.XXXXX:YOUR_PASSWORD@aws-0-us-east-1.pooler.supabase.com:6543/postgres?prepared_statement_cache_size=0
   ```

> **Note:** The `?prepared_statement_cache_size=0` parameter is added automatically by the app when it detects Supabase. You don't need it in the URL, but it doesn't hurt.

### 5. Deploy

```bash
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

### 6. (Optional) Download translation models

For local MarianMT translation (free, no API key needed):

```bash
chmod +x scripts/download_models.sh
./scripts/download_models.sh
```

Without models, the built-in MarianMT provider will return a 503. Users can still use OpenAI/HuggingFace/Google via BYOK keys or admin credits.

## Memory Usage Guide

| Service | Memory | Notes |
|---------|--------|-------|
| Worker (MarianMT) | 1-3 GB | Each model pair ~200-400MB. `MODEL_CACHE_SIZE=3` keeps 3 loaded |
| API Gateway | ~200 MB | Lightweight FastAPI |
| Redis | ~256 MB | Capped at 256MB with LRU eviction |
| Frontend (nginx) | ~30 MB | Static files |
| Cloudflared | ~50 MB | Tunnel agent |
| Prometheus | ~200 MB | 15-day retention, 1GB cap |
| Grafana | ~200 MB | Dashboard renderer |
| **Total** | **~4.5 GB** | Fits in 8GB with headroom |

### For 4GB machines (Raspberry Pi)

In `.env`, reduce:
```bash
MODEL_CACHE_SIZE=2       # Keep only 2 models loaded
```

Or disable MarianMT entirely and rely on API providers:
```bash
MODEL_CACHE_SIZE=1       # Minimal
```

## Changing Your Domain

1. Update `.env`:
   ```bash
   DOMAIN=newdomain.example.com
   CORS_ORIGINS=https://newdomain.example.com
   VITE_API_URL=https://newdomain.example.com
   ```
2. Update Cloudflare Tunnel public hostname
3. Rebuild frontend (domain is baked into the build):
   ```bash
   docker compose -f docker-compose.prod.yml build frontend
   docker compose -f docker-compose.prod.yml up -d frontend
   ```

## Translation Providers

Users have 3 ways to translate:

| Method | Cost to User | Setup Needed |
|--------|-------------|--------------|
| **MarianMT (built-in)** | Free | Download models |
| **BYOK (Bring Your Own Key)** | User pays their provider directly | User adds their API key in Settings |
| **Admin Credits** | Credits (you set pricing) | You add admin keys in `.env` or Admin Dashboard |

### Adding admin provider keys

Either set in `.env`:
```bash
ADMIN_OPENAI_KEY=sk-...
ADMIN_HUGGINGFACE_KEY=hf_...
ADMIN_GOOGLE_KEY=AIza...
```

Or via the Admin Dashboard UI (Settings → Provider Keys).

## Monitoring

- **Grafana**: `https://yourdomain.com/grafana/` (login with GRAFANA_ADMIN_USER/PASSWORD)
- **Prometheus**: Internal only (port 9090, not exposed publicly)
- **Health check**: `https://yourdomain.com/health`
- **API docs**: `https://yourdomain.com/docs`

## Updating

```bash
git pull
./scripts/deploy.sh
```

## Troubleshooting

### "Connection refused" to Supabase
- Ensure you're using port `6543` (pooler), not `5432` (direct)
- Check that your Supabase project isn't paused (free tier pauses after 1 week of inactivity)

### Worker "Model not found"
- Run `./scripts/download_models.sh` to download model pairs
- Or set `MODEL_CACHE_SIZE=0` and rely on API providers only

### Cloudflare Tunnel not connecting
- Verify the token: `docker compose -f docker-compose.prod.yml logs cloudflared`
- Ensure the public hostname is set to `http://frontend:80` (not HTTPS internally)

### High memory usage
- Reduce `MODEL_CACHE_SIZE` in `.env`
- Models are loaded on-demand and evicted LRU-style

### "Prepared statement already exists" error
- This means you're connecting to Supabase's PgBouncer in transaction mode
- The app auto-detects Supabase and disables prepared statement caching
- If using a custom pooler, add `?prepared_statement_cache_size=0` to DATABASE_URL
