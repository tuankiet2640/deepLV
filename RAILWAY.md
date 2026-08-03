# Deploy DeepLV on Railway (Free)

Get a live URL in 5 minutes.

## What You Get

- Full translation API + React frontend at `https://deeplv-xxx.up.railway.app`
- Supabase for database (free tier)
- Optional Redis (Railway add-on, free)
- All API providers work (OpenAI, HuggingFace, Google via BYOK)
- MarianMT unavailable (needs too much RAM) — use API providers instead

## Steps

### 1. Create a Railway Account

Go to [railway.app](https://railway.app) and sign up with GitHub.

### 2. Create New Project from GitHub Repo

1. Click **"New Project"**
2. Select **"Deploy from GitHub Repo"**
3. Pick `tuankiet2640/deepLV`
4. Railway will auto-detect the `railway.toml` and use `Dockerfile.railway`

### 3. Add Redis (Optional but Recommended)

1. In your project, click **"+ New"** → **"Database"** → **"Redis"**
2. Railway auto-sets `REDIS_URL` — no config needed

### 4. Set Environment Variables

Go to your service → **Variables** tab → Add these:

```
DATABASE_URL=postgresql+asyncpg://postgres.odyncoxjkthuwhkrdawi:YOUR_PASSWORD@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres
JWT_SECRET=<run: openssl rand -hex 32>
ENCRYPTION_KEY=<run: openssl rand -hex 32>
CORS_ORIGINS=https://YOUR_APP.up.railway.app
LOG_LEVEL=info
RATE_LIMIT_REQUESTS=60
RATE_LIMIT_WINDOW_SECONDS=60
CREDIT_COST_PER_1K_CHARS=5.0
MODEL_WORKER_URL=http://localhost:8001
```

> Replace `YOUR_APP` with your actual Railway domain after first deploy.

### 5. Deploy

Railway auto-deploys on push. Or click **"Deploy"** manually.

First deploy takes ~3 minutes (building Docker image).

### 6. Get Your URL

Once deployed, go to **Settings** → **Networking** → **Generate Domain**.

Your app is live!

## After Deploy

1. Visit your URL → Landing page should load
2. Click **"Create Free Account"** → Register (first user = admin automatically)
3. Log in → Go to API Keys → Create a key
4. Try translating (MarianMT won't work — use OpenAI/HuggingFace/Google with BYOK)

## Adding Translation Providers

### Option A: Users bring their own keys (BYOK)
Users go to Settings → Provider Keys → Add their OpenAI/HuggingFace/Google key.

### Option B: You provide admin keys (users pay credits)
Add these to Railway Variables:
```
ADMIN_OPENAI_KEY=sk-...
ADMIN_HUGGINGFACE_KEY=hf_...
ADMIN_GOOGLE_KEY=AIza...
```

## Costs

| Service | Cost |
|---------|------|
| Railway | Free ($5/month credit) |
| Supabase | Free (500MB, pauses after 7 days idle) |
| Redis (Railway) | Free (included in $5 credit) |
| **Total** | **$0** |

## Limitations on Free Tier

- Railway: 512MB RAM, sleeps after 30 min inactive (cold starts take ~10s)
- Supabase: Pauses after 7 days idle (just visit dashboard to unpause)
- No MarianMT (needs 1-3GB RAM) — use API providers instead
- Redis may not be available (app works without it, just no caching)

## Custom Domain

1. Railway Settings → Networking → Custom Domain
2. Add CNAME record: `your-domain.com` → `your-app.up.railway.app`
3. Update `CORS_ORIGINS` variable to match
