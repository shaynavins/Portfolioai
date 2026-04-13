# PortfolioAI 🚀

**Agentic portfolio builder** — connect GitHub + upload your resume, and an AI agent builds, deploys, and **auto-maintains** a live portfolio site at `username.portfolioai.app`.

## How It Works

1. User signs in via GitHub OAuth
2. LangGraph agent analyzes repos, scores them, writes bios and project descriptions
3. Portfolio site is generated and deployed to Vercel Pages
4. A GitHub webhook triggers automatic re-generation on every push

## Tech Stack

| Layer | Technology |
|---|---|
| Agent Orchestration | LangGraph (Python) |
| LLM | OpenAI GPT-4.1 mini |
| GitHub Integration | GitHub OAuth App + REST/GraphQL API via MCP |
| Backend API | FastAPI + Celery workers |
| Frontend | Next.js 14 + Tailwind CSS |
| Database | PostgreSQL (Supabase free tier) |
| Queue | Redis (Upstash free tier) |
| Storage | Cloudflare R2 (free tier) |
| Hosting | Vercel (portfolio pages) |
| Deployment | Railway (backend) |

## Quick Start

### 1. Prerequisites
```bash
node >= 18
python >= 3.11
docker (for local postgres/redis)
```

### 2. Clone and install
```bash
git clone <your-repo>
cd portfolioai

# Backend
cd backend && pip install -r requirements.txt

# Frontend
cd ../frontend && npm install
```

### 3. Set environment variables
```bash
cp .env.example .env
# Fill in: GOOGLE_API_KEY, GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET,
# DATABASE_URL, REDIS_URL, R2_* keys, VERCEL_TOKEN
```

### 4. Run locally
```bash
# Terminal 1 — backend API
cd backend && uvicorn api.main:app --reload --port 8000

# Terminal 2 — Celery worker (runs the LangGraph agent)
cd backend && celery -A api.worker worker --loglevel=info

# Terminal 3 — frontend
cd frontend && npm run dev
```

## Monetization Plan

- **Free tier**: 1 portfolio, updates every 24h, `username.portfolioai.app`
- **Pro ($9/mo)**: Custom domain, instant updates, multiple portfolios, theme selector
- **Team ($29/mo)**: Company branding, white-label, priority queue, analytics

## Deployment to Production

See `infra/deploy.md` for Railway + Vercel setup instructions.
