# DeepLV — Quick Start Guide

Get DeepLV running in 5 minutes.

---

## 1. Clone

```bash
git clone https://github.com/tuankiet2640/deepLV.git
cd deepLV
```

## 2. Configure

```bash
cp .env.production .env
```

Generate your secrets:
```bash
openssl rand -hex 32  # → paste as JWT_SECRET
openssl rand -hex 32  # → paste as ENCRYPTION_KEY
```

Edit `.env` and fill in these 5 things:

| Variable | Value |
|----------|-------|
| `DOMAIN` | `translate.yourdomain.com` |
| `DATABASE_URL` | From Supabase → Settings → Database → URI (use port `6543`) |
| `JWT_SECRET` | The first `openssl rand` output |
| `ENCRYPTION_KEY` | The second `openssl rand` output |
| `CLOUDFLARE_TUNNEL_TOKEN` | From Cloudflare Zero Trust → Tunnels → Create |

## 3. Cloudflare Tunnel Setup

1. Go to https://one.dash.cloudflare.com
2. **Networks → Tunnels → Create a tunnel**
3. Name it `deeplv`, copy the token → paste in `.env`
4. Add public hostname:
   - Subdomain: `translate`
   - Domain: `yourdomain.com`
   - Service type: `HTTP`
   - URL: `frontend:80`

## 4. Supabase Setup

1. Go to https://supabase.com → New Project
2. **Settings → Database → Connection string → URI**
3. Switch to **Transaction pooler** (port 6543)
4. Copy and paste into `.env` as `DATABASE_URL`

Format:
```
postgresql+asyncpg://postgres.XXXXX:PASSWORD@aws-0-us-east-1.pooler.supabase.com:6543/postgres
```

## 5. Deploy

```bash
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

Done. Your app is live at `https://translate.yourdomain.com`

---

## 6. (Optional) Download Local Translation Models

For free built-in MarianMT translation (no API key needed):

```bash
chmod +x scripts/download_models.sh
./scripts/download_models.sh
```

Without this, users can still translate via OpenAI / HuggingFace / Google with their own API keys.

---

## Quick Reference

| URL | What |
|-----|------|
| `https://DOMAIN/` | Translation UI |
| `https://DOMAIN/docs` | API documentation |
| `https://DOMAIN/grafana/` | Monitoring dashboards |
| `https://DOMAIN/health` | Health check |

## Commands

```bash
# View logs
docker compose -f docker-compose.prod.yml logs -f

# Restart everything
docker compose -f docker-compose.prod.yml restart

# Stop
docker compose -f docker-compose.prod.yml down

# Update (pull latest code + redeploy)
git pull && ./scripts/deploy.sh

# Change domain
# 1. Edit DOMAIN, CORS_ORIGINS, VITE_API_URL in .env
# 2. Update Cloudflare Tunnel hostname
# 3. Rebuild:
docker compose -f docker-compose.prod.yml build frontend
docker compose -f docker-compose.prod.yml up -d
```

## Add Translation Providers (Optional)

Add admin API keys so users can pay credits to translate:

```bash
# In .env:
ADMIN_OPENAI_KEY=sk-...
ADMIN_HUGGINGFACE_KEY=hf_...
ADMIN_GOOGLE_KEY=AIza...
```

Then restart: `docker compose -f docker-compose.prod.yml restart api`

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Supabase "connection refused" | Use port `6543` not `5432` |
| Supabase "prepared statement" error | Already handled — app auto-detects Supabase |
| Worker "model not found" | Run `./scripts/download_models.sh` |
| High memory | Lower `MODEL_CACHE_SIZE=2` in `.env`, restart |
| Tunnel not connecting | Check token: `docker compose -f docker-compose.prod.yml logs cloudflared` |
| Supabase project paused | Free tier pauses after 7 days idle — unpause in dashboard |
