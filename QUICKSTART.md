# DeepLV — Quick Start Guide

Get DeepLV running in 5 minutes.

---

## Choose Your Deployment Mode

| Mode | Use when | Command |
|------|----------|---------|
| **Cloudflare Tunnel** | You want HTTPS without opening ports | `docker compose -f docker-compose.prod.yml up -d` |
| **Port Forwarding** | You want direct access / have your own domain + SSL | `docker compose -f docker-compose.local.yml up -d` |
| **Dev (local only)** | Testing on your machine | `docker compose up -d` |

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

## 6. User Flow (Register, Login, Translate)

Once deployed, here is the typical user flow:

### Via the Frontend (Web UI)

1. **Register** - Visit `/register` and create an account with email and password
2. **Login** - Visit `/login` to authenticate and receive a session
3. **Create API Key** - Go to `/api-keys` to generate a `dlv_live_...` key for programmatic access
4. **Translate** - Use `/translate` for real-time text translation with provider selection
5. **Documents** - Use `/documents` to upload PDF/DOCX/TXT files for background translation
6. **Settings** - Visit `/settings` to manage BYOK provider keys and view credit balance
7. **Admin** - If you are an admin user, `/admin` gives access to user management, analytics, and system settings

### Frontend Pages

| Route | Page | Auth Required |
|-------|------|---------------|
| `/` | Landing page (product marketing, pricing, features) | No |
| `/login` | Login with email/password | No |
| `/register` | Create a new account | No |
| `/translate` | Real-time translation with provider selector | No |
| `/documents` | Document upload, job tracking, download | No |
| `/settings` | BYOK key management, credits, provider keys | Yes (JWT) |
| `/api-keys` | Create and manage API keys | Yes (JWT) |
| `/admin` | Admin dashboard (users, analytics, keys, settings) | Yes (admin) |
| `/getting-started` | Getting started documentation | No |
| `/api-reference` | API reference documentation | No |
| `/architecture` | Architecture overview | No |
| `/status` | System status page | No |

### Via the API (programmatic)

```bash
# 1. Register
curl -X POST https://DOMAIN/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "securepassword123"}'

# 2. Login
curl -X POST https://DOMAIN/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "securepassword123"}'
# Returns: { "access_token": "eyJ..." }

# 3. Create API key
curl -X POST https://DOMAIN/api/v1/keys \
  -H "Authorization: Bearer eyJ..." \
  -H "Content-Type: application/json" \
  -d '{"name": "my-key"}'
# Returns: { "key": "dlv_live_..." }

# 4. Translate (with API key)
curl -X POST https://DOMAIN/api/v1/translate \
  -H "X-API-Key: dlv_live_..." \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello world", "source_lang": "en", "target_lang": "de"}'

# 5. Translate with a specific provider
curl -X POST https://DOMAIN/api/v1/translate \
  -H "X-API-Key: dlv_live_..." \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello world", "source_lang": "en", "target_lang": "fr", "provider": "openai"}'
```

---

## 7. (Optional) Download Local Translation Models

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

---

## Option B: Port Forwarding (No Cloudflare)

If you prefer to expose ports directly from your router instead of using Cloudflare Tunnel:

### 1. Configure

```bash
cp .env.production .env
```

Edit `.env` — same as above but change:
```bash
# Use your public IP or domain
DOMAIN=your-public-ip-or-domain.com
CORS_ORIGINS=http://your-public-ip-or-domain.com:3000
VITE_API_URL=http://your-public-ip-or-domain.com:3000

# Remove or leave blank (not needed)
CLOUDFLARE_TUNNEL_TOKEN=
```

### 2. Deploy with port-forwarding compose file

```bash
docker compose -f docker-compose.local.yml up --build -d
```

### 3. Configure your router

Forward these ports to your machine's LAN IP:

| External Port | Internal Port | Service |
|--------------|---------------|---------|
| 80 or 3000 | 3000 | Frontend + API |
| 9090 (optional) | 9090 | Prometheus |
| 3001 (optional) | 3001 | Grafana |

### 4. (Optional) Add SSL with Let's Encrypt

If you have a domain pointed at your public IP:

```bash
# Install certbot on your host
sudo apt install certbot

# Get certificate
sudo certbot certonly --standalone -d translate.yourdomain.com

# Mount certs into nginx (add to docker-compose.local.yml frontend volumes):
#   - /etc/letsencrypt/live/yourdomain.com:/etc/nginx/ssl:ro
```

Then update `frontend/nginx.prod.conf` to listen on 443 with the cert.

### 5. Access

| URL | What |
|-----|------|
| `http://YOUR_IP:3000` | Translation UI |
| `http://YOUR_IP:3000/docs` | API docs |
| `http://YOUR_IP:3001` | Grafana |
| `http://YOUR_IP:9090` | Prometheus |

### Port-forwarding commands

```bash
# Start
docker compose -f docker-compose.local.yml up -d

# Logs
docker compose -f docker-compose.local.yml logs -f

# Stop
docker compose -f docker-compose.local.yml down

# Restart
docker compose -f docker-compose.local.yml restart

# Change port (default 3000)
PORT=8080 docker compose -f docker-compose.local.yml up -d
```

### Find your IPs

```bash
# LAN IP
hostname -I | awk '{print $1}'

# Public IP
curl -s ifconfig.me
```
