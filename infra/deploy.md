# PortfolioAI — Production Deployment Guide

## Overview

| Service | Provider | Free tier |
|---|---|---|
| Backend API | Railway | $5 credit/mo (plenty for MVP) |
| Celery Worker | Railway | 2nd service same project |
| PostgreSQL | Supabase | 500MB free |
| Redis | Upstash | 10k commands/day free |
| Storage | Cloudflare R2 | 10GB free |
| Portfolio hosting | Vercel | Unlimited static deploys |
| Frontend | Vercel | Free |

---

## Step 1 — GitHub OAuth App

1. Go to https://github.com/settings/applications/new
2. Application name: `PortfolioAI`
3. Homepage URL: `https://your-frontend.vercel.app`
4. Authorization callback URL: `https://your-backend.railway.app/api/auth/github/callback`
5. Copy `Client ID` and `Client Secret` → set in env vars

---

## Step 2 — Supabase (PostgreSQL)

1. Create project at https://supabase.com
2. Go to Settings → Database → Connection string (URI)
3. Copy the connection string → set as `DATABASE_URL`
4. Replace `[YOUR-PASSWORD]` with your DB password

---

## Step 3 — Upstash Redis

1. Create database at https://upstash.com
2. Copy `UPSTASH_REDIS_REST_URL` format Redis URL → set as `REDIS_URL`

---

## Step 4 — Cloudflare R2

1. Log in to https://dash.cloudflare.com
2. R2 → Create bucket named `portfolioai-sites`
3. R2 → Manage R2 API tokens → Create token (Object Read & Write)
4. Copy Account ID, Access Key, Secret Key
5. Enable public access on the bucket → copy public URL

---

## Step 5 — Vercel Token (for portfolio deployment)

1. Go to https://vercel.com/account/tokens
2. Create token with name `PortfolioAI`
3. Copy → set as `VERCEL_TOKEN`

---

## Step 6 — Deploy Backend to Railway

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# From /backend directory
cd backend
railway init
railway up

# Add environment variables
railway variables set GOOGLE_API_KEY=your-google-api-key
railway variables set GITHUB_CLIENT_ID=...
railway variables set GITHUB_CLIENT_SECRET=...
railway variables set JWT_SECRET=$(openssl rand -hex 32)
railway variables set DATABASE_URL=postgresql://...
railway variables set REDIS_URL=redis://...
railway variables set R2_ACCOUNT_ID=...
railway variables set R2_ACCESS_KEY_ID=...
railway variables set R2_SECRET_ACCESS_KEY=...
railway variables set R2_BUCKET_NAME=portfolioai-sites
railway variables set R2_PUBLIC_URL=https://pub-xxx.r2.dev
railway variables set VERCEL_TOKEN=...
railway variables set ENVIRONMENT=production
railway variables set APP_URL=https://your-frontend.vercel.app
```

### Add Celery Worker as second service
In Railway dashboard → New Service → same repo → override start command:
```
celery -A api.worker worker --loglevel=info --concurrency=2 -Q builds
```

---

## Step 7 — Deploy Frontend to Vercel

```bash
cd frontend
npx vercel

# Set env vars in Vercel dashboard or CLI:
vercel env add NEXT_PUBLIC_API_URL production
# Enter: https://your-backend.railway.app

vercel env add NEXT_PUBLIC_GITHUB_CLIENT_ID production
# Enter: your GitHub Client ID
```

---

## Step 8 — Custom Domain (optional)

1. Buy domain (Namecheap, Porkbun, etc.)
2. Point DNS to Vercel for frontend
3. Add custom domain in Railway for backend (e.g. `api.portfolioai.app`)
4. Update `APP_URL` and `API_URL` env vars accordingly
5. Update GitHub OAuth app callback URL

---

## Monitoring

- Railway provides built-in logs and metrics
- Add Sentry for error tracking: `pip install sentry-sdk[fastapi]`
- Consider Plausible.io for analytics (privacy-friendly)

---

## Cost at Scale

At 1000 users:
- Railway: ~$10/mo (scale up dyno)
- Supabase: free → $25/mo at 8GB
- Upstash: free → $10/mo
- Vercel: free (static sites)
- Cloudflare R2: ~$1.50/mo per 100GB
- Gemini API: variable by model selection and token usage

**Total: ~$50/mo to serve 1000 users at Pro ($9/mo) = 1800% margin**
