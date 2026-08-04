# Deploy DeepLV on Railway (Free)

Get a live URL in 5 minutes.

## What You Get

- Full translation API + React frontend at `https://deeplv-xxx.up.railway.app`
- Supabase for database (free tier)
- Optional Redis (Railway add-on, free)
- All API providers work (OpenAI, HuggingFace, Google via BYOK)
- MarianMT works too, but needs a **separate worker service** (see
  [Optional: Deploy the MarianMT Worker](#optional-deploy-the-marianmt-worker) below) —
  the free tier's 512MB RAM is tight for it, and API providers are simpler to start with

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
RESEND_API_KEY=re_your_key
EMAIL_FROM_ADDRESS=onboarding@resend.dev
FRONTEND_URL=https://YOUR_APP.up.railway.app
```

> Replace `YOUR_APP` with your actual Railway domain after first deploy.
>
> `MODEL_WORKER_URL=http://localhost:8001` is a placeholder for when you're
> **not** running the MarianMT worker — with no worker listening, MarianMT
> requests fail cleanly (a translation error) rather than doing anything
> silently wrong. If you do deploy the worker (see below), point this at
> its Railway-internal URL instead.
>
> `RESEND_API_KEY` is optional too — leave it unset and the app still
> works, it just logs verification codes and password reset links instead
> of emailing them (fine for testing, not for real users). Get a key at
> [resend.com](https://resend.com); the sandbox sender
> `onboarding@resend.dev` only delivers to the account owner's own inbox,
> so verify a real sending domain before inviting other users. Set
> `FRONTEND_URL` to your actual Railway domain (not `localhost`) so links
> in those emails point somewhere real.

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
4. Try translating (with just `Dockerfile.railway` deployed, MarianMT has no
   worker to talk to — use OpenAI/HuggingFace/Google with BYOK, or deploy the
   worker per the section below)

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

## Optional: Deploy the MarianMT Worker

The main service (`Dockerfile.railway`) is API + frontend only — it has
nowhere to run MarianMT inference itself. To actually serve MarianMT
translations, deploy the worker as a **second Railway service** in the same
project:

1. In your Railway project, click **"+ New"** → **"GitHub Repo"** → pick
   `tuankiet2640/deepLV` again (a second service from the same repo).
2. Under that service's **Settings** → **Build**, set the Dockerfile path to
   `Dockerfile.railway-worker` (Railway won't auto-detect this one, since
   `railway.toml` at the repo root points at the main API service).
3. The worker's build step downloads and converts the model pairs listed in
   `scripts/download_models.py` (currently `en<->{de,fr,es,zh,ja,vi}`) —
   expect a slower first build than the main service.
4. Once deployed, copy the worker service's **internal** Railway URL
   (Settings → Networking) and set it as `MODEL_WORKER_URL` on the **main**
   API service, then redeploy the main service to pick up the change.

**RAM**: `Dockerfile.railway-worker` sets `MODEL_CACHE_SIZE=6`, meaning up to
6 CTranslate2 models can be loaded (and held in memory) at once, on top of
the base Python/PyTorch footprint. That's a real squeeze against Railway's
free-tier 512MB — a paid plan with more RAM is the realistic path to running
this reliably, not a hard requirement to try it.

**Pivot quality**: the worker only has direct models for pairs involving
English (`en<->de`, `en<->vi`, etc.). Any other pair (e.g. `vi->fr`) pivots
through English as two chained translations, which measurably degrades
quality on formal or technical text — the UI now warns about this when you
pick MarianMT for such a pair. For anything you need to be accurate (a
contract, HR paperwork, anything someone might sign), use an API provider
for non-English-pair translations regardless of whether the worker is
running.

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
- MarianMT worker is a tight fit on 512MB with `MODEL_CACHE_SIZE=6` — a paid
  plan is the realistic way to run it reliably; API providers are the easier
  default on the free tier
- Redis may not be available (app works without it, just no caching)

## Custom Domain

1. Railway Settings → Networking → Custom Domain
2. Add CNAME record: `your-domain.com` → `your-app.up.railway.app`
3. Update `CORS_ORIGINS` variable to match
