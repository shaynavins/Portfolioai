# PortfolioAI 🚀

**Agentic portfolio builder** — connect GitHub + upload your resume, and an AI agent builds, deploys, and **auto-maintains** a live portfolio site at `username.portfolioai.app`.

## How It Works

1. User signs in via GitHub OAuth
2. LangGraph agent analyzes repos, scores them, writes bios and project descriptions
3. Portfolio site is generated and published through the backend deployment layer
4. A GitHub webhook triggers automatic re-generation on every push

## Tech Stack

| Layer | Technology |
|---|---|
| Agent Orchestration | LangGraph (Python) |
| LLM | Gemini (`langchain-google-genai`) |
| GitHub Integration | GitHub OAuth App + REST/GraphQL API via MCP |
| Backend API | FastAPI + Celery workers |
| Frontend | Next.js 14 + Tailwind CSS |
| Database | PostgreSQL (Supabase free tier) |
| Queue | Redis (Upstash free tier) |
| Storage | Cloudflare R2 (free tier) |
| Hosting | Next.js frontend + FastAPI backend |
| Deployment | Railway (backend) |
| Payments | Razorpay |

## Quick Start

### 1. Prerequisites
```bash
node >= 18.17
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
# JWT_SECRET, DATABASE_URL, REDIS_URL, and optional R2 / Razorpay keys
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

## Current Plan Model

- **Free tier**: 1 build for evaluation
- **Pro (₹199 one-time)**: Publishing, editing, and ongoing use

## Deployment to Production

See `infra/deploy.md` and `DEPLOYMENT_GUIDE.md` for the current deployment flow.
