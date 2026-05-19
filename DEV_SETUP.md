# PortfolioAI — Local Development Setup

Complete guide to running PortfolioAI locally for development and testing.

## Prerequisites

Before starting, ensure you have:
- **Git** (for cloning repository)
- **Python 3.10+** (for backend)
- **Node.js 18+** (for frontend)
- **PostgreSQL 13+** (local database)
- **Redis 6+** (for caching and Celery)
- **Docker** (optional, for containerized setup)

### macOS Installation

```bash
# Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install dependencies
brew install python@3.11 postgresql redis node git

# Start PostgreSQL and Redis services
brew services start postgresql
brew services start redis
```

### Ubuntu/Debian

```bash
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv postgresql postgresql-contrib redis-server nodejs npm git
```

### Windows (WSL2 recommended)

```bash
# Install WSL2 first, then use Ubuntu guide above
wsl --install Ubuntu-22.04
```

---

## Quick Start (5 minutes)

```bash
# 1. Clone repository
git clone https://github.com/yourusername/portfolioai.git
cd portfolioai

# 2. Create Python virtual environment
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install backend dependencies
pip install -r requirements.txt

# 4. Setup environment variables
cp .env.example .env
# Edit .env with local values (see section below)

# 5. Initialize database
alembic upgrade head

# 6. Start backend
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# 7. (In new terminal) Setup frontend
cd frontend
npm install
npm run dev

# 8. Open browser
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

---

## Detailed Setup

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/portfolioai.git
cd portfolioai
```

### 2. Backend Setup

#### Create Virtual Environment

```bash
cd backend
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # macOS/Linux
# OR
venv\Scripts\activate  # Windows
```

#### Install Dependencies

```bash
pip install -r requirements.txt
```

#### Configure Environment Variables

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Edit `.env` with local values:

```bash
# Application
ENVIRONMENT=development
LOG_LEVEL=DEBUG
DEBUG=true

# Security & JWT
SECRET_KEY=your-super-secret-key-for-dev  # Use: python -c "import secrets; print(secrets.token_urlsafe(32))"
JWT_SECRET=your-jwt-secret-for-dev
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30

# Database (local PostgreSQL)
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/portfolioai
SQLALCHEMY_ECHO=true

# Redis (local)
REDIS_URL=redis://localhost:6379/0

# GitHub OAuth (get from https://github.com/settings/developers)
GITHUB_CLIENT_ID=your_github_oauth_client_id
GITHUB_CLIENT_SECRET=your_github_oauth_client_secret
GITHUB_WEBHOOK_SECRET=your_webhook_secret

# Google Gemini AI
GOOGLE_API_KEY=your_google_api_key

# Stripe (test keys from https://dashboard.stripe.com/test/keys)
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_test_...
STRIPE_PRODUCT_ID_PRO=price_test_pro
STRIPE_PRODUCT_ID_TEAM=price_test_team

# SendGrid Email (optional for local dev)
SENDGRID_API_KEY=SG.test_...
SENDGRID_FROM_EMAIL=noreply@portfolioai.local

# Cloudflare R2 (optional, or use local file storage)
R2_ACCOUNT_ID=your_account_id
R2_ACCESS_KEY_ID=your_access_key
R2_SECRET_ACCESS_KEY=your_secret_key
R2_BUCKET_NAME=portfolioai-dev
R2_PUBLIC_URL=https://portfolioai-dev.example.com

# Vercel (optional, for deploying portfolios)
VERCEL_TOKEN=your_vercel_token

# Feature Flags
FEATURE_EMAIL_NOTIFICATIONS=true
FEATURE_WEBHOOKS=true
REQUIRE_HTTPS=false
```

#### Initialize Database

```bash
# Create database (if not exists)
createdb portfolioai

# Run migrations
alembic upgrade head

# Verify tables
psql portfolioai -c "\dt"
```

Expected tables:
- `users`, `portfolios`, `build_jobs` (existing)
- `subscriptions`, `invoices`, `payment_methods`, `webhook_logs`, `stripe_products` (Phase 3)

#### Start Backend Server

```bash
# From backend directory with venv activated
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

Output should show:
```
Uvicorn running on http://0.0.0.0:8000
```

Visit http://localhost:8000/docs for interactive API documentation.

---

### 3. Frontend Setup

#### Install Dependencies

```bash
cd frontend  # From project root
npm install
```

#### Configure Environment Variables

Create `.env.local`:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...
```

#### Start Development Server

```bash
npm run dev
```

Output should show:
```
ready - started server on 0.0.0.0:3000
```

Visit http://localhost:3000 in your browser.

---

### 4. Database Management

#### View Database

```bash
# Connect to database
psql portfolioai

# List tables
\dt

# Describe a table
\d users

# Exit
\q
```

#### Reset Database (Development Only)

```bash
# Drop and recreate database
dropdb portfolioai
createdb portfolioai
alembic upgrade head
```

#### Seed Test Data (Optional)

Create `backend/seed.py`:

```python
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from api.models import User, Subscription
from api.config import Settings

async def seed_db():
    settings = Settings()
    engine = create_async_engine(settings.DATABASE_URL)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with AsyncSessionLocal() as session:
        # Create test user
        user = User(
            id="test_user_1",
            github_username="testuser",
            email="test@example.com",
            github_id=12345,
            avatar_url="https://avatars.githubusercontent.com/u/12345?v=4",
        )
        session.add(user)
        
        # Create test subscription
        sub = Subscription(
            id="sub_test_1",
            user_id="test_user_1",
            tier="pro",
            stripe_subscription_id="sub_test_123",
            status="active",
        )
        session.add(sub)
        
        await session.commit()
        print("✓ Database seeded with test data")

if __name__ == "__main__":
    asyncio.run(seed_db())
```

Run it:

```bash
python seed.py
```

---

## Development Workflows

### Testing an API Endpoint

Use curl or Postman:

```bash
# Signup
curl -X POST http://localhost:8000/api/auth/github/login \
  -H "Content-Type: application/json" \
  -d '{"code":"github_code"}'

# Get current user (replace TOKEN with access_token from above)
curl http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer TOKEN"

# Create portfolio
curl -X POST http://localhost:8000/api/portfolios \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Portfolio",
    "github_repo": "testuser/test-repo",
    "framework": "next.js"
  }'
```

Or use the interactive API docs: http://localhost:8000/docs

### Testing Stripe Webhooks Locally

Install Stripe CLI:

```bash
# macOS
brew install stripe/stripe-cli/stripe

# Or download from https://stripe.com/docs/stripe-cli
```

Forward Stripe events to local server:

```bash
stripe listen --forward-to http://localhost:8000/api/billing/webhook
```

Output will show a signing secret — copy it to `.env` as `STRIPE_WEBHOOK_SECRET`.

Trigger test events in another terminal:

```bash
# Test subscription created event
stripe trigger customer.subscription.created

# Test payment succeeded
stripe trigger invoice.payment_succeeded
```

Check logs in backend terminal to see webhook processing.

### Testing Email Locally

#### Option 1: Use SendGrid Sandbox Mode (Recommended)

Set a test email address in SendGrid:
1. Go to https://app.sendgrid.com/settings/sender_authentication
2. Add your personal email as a test recipient
3. Emails will be delivered to that address

#### Option 2: Use MailHog (Mock Email Server)

```bash
# Install MailHog
brew install mailhog

# Start MailHog
mailhog
# Opens web UI at http://localhost:1025
# SMTP server at localhost:1025
```

Update `.env` to use MailHog:

```bash
SENDGRID_SMTP_HOST=localhost
SENDGRID_SMTP_PORT=1025
```

#### Option 3: Print to Logs

Update email functions to log instead of send:

```python
# In sendgrid_client.py
if not self.api_key:
    logger.info(f"[DEV MODE] Email would be sent:\nTo: {to_email}\nSubject: {subject}\nBody: {html_body}")
    return {"status": "dev_mode"}
```

### Running Tests

```bash
# Backend tests
cd backend
pytest

# With coverage
pytest --cov=api

# Frontend tests
cd frontend
npm test
```

### Code Formatting & Linting

```bash
# Backend
cd backend
black api/  # Format Python code
flake8 api/  # Lint
mypy api/  # Type check

# Frontend
cd frontend
npm run lint  # Run ESLint
npm run format  # Format with Prettier
npm run typecheck  # TypeScript check
```

---

## Troubleshooting

### PostgreSQL Connection Error

```
Error: could not connect to server: No such file or directory
```

Solution:

```bash
# Check if PostgreSQL is running
brew services list

# Start PostgreSQL
brew services start postgresql

# Or, if using Docker:
docker run --name postgres -e POSTGRES_PASSWORD=postgres -d -p 5432:5432 postgres:15
```

### Port Already in Use

```
Port 8000 already in use
```

Solution:

```bash
# Kill process using port 8000
lsof -ti:8000 | xargs kill -9

# Or use different port
uvicorn api.main:app --port 8001
```

### Import Errors

```
ModuleNotFoundError: No module named 'api'
```

Solution:

```bash
# Ensure you're in backend directory with venv activated
cd backend
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Database Migration Errors

```
sqlalchemy.exc.ProgrammingError: table "users" already exists
```

Solution:

```bash
# Check current migration version
alembic current

# Downgrade if needed
alembic downgrade -1

# Or reset (development only)
dropdb portfolioai
createdb portfolioai
alembic upgrade head
```

### GitHub OAuth Not Working

Make sure your OAuth app is configured:

1. Go to https://github.com/settings/developers
2. Create OAuth App:
   - **Application name**: PortfolioAI Dev
   - **Homepage URL**: http://localhost:3000
   - **Authorization callback URL**: http://localhost:8000/api/auth/github/callback
3. Copy Client ID → `GITHUB_CLIENT_ID`
4. Generate Client Secret → `GITHUB_CLIENT_SECRET`

---

## Docker Setup (Optional)

For isolated, containerized development:

### docker-compose.yml

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: portfolioai
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7
    ports:
      - "6379:6379"

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://postgres:postgres@postgres:5432/portfolioai
      REDIS_URL: redis://redis:6379/0
    depends_on:
      - postgres
      - redis
    volumes:
      - ./backend:/app
    command: uvicorn api.main:app --host 0.0.0.0 --reload

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000
    volumes:
      - ./frontend:/app
    command: npm run dev
```

Start all services:

```bash
docker-compose up
```

Services available at:
- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- API Docs: http://localhost:8000/docs
- PostgreSQL: localhost:5432
- Redis: localhost:6379

---

## VS Code Extensions (Recommended)

- **Python**: ms-python.python
- **Pylance**: ms-python.vscode-pylance
- **PostgreSQL**: ckolkman.vscode-postgres
- **Thunder Client**: rangav.vscode-thunder-client (for API testing)
- **ES7+ React/Redux/React-Native**: dsznajder.es7-react-js-snippets
- **Prettier**: esbenp.prettier-vscode

---

## Environment Variables Cheat Sheet

### Required for Development

```bash
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/portfolioai
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=dev-secret-key
JWT_SECRET=dev-jwt-secret
GITHUB_CLIENT_ID=your_github_id
GITHUB_CLIENT_SECRET=your_github_secret
STRIPE_SECRET_KEY=sk_test_...
```

### Optional for Development

```bash
SENDGRID_API_KEY=  # Leave empty to skip email
GOOGLE_API_KEY=  # Leave empty to skip AI features
VERCEL_TOKEN=  # Leave empty to skip portfolio deployment
```

---

## Next Steps

After setup is complete:

1. **Explore the API**: http://localhost:8000/docs
2. **Try a GitHub login**: http://localhost:3000
3. **Create a portfolio** through the dashboard
4. **Read API_DOCS.md** for endpoint details
5. **Review code structure**:
   - `backend/api/` — Python backend
   - `frontend/src/` — Next.js frontend
   - `backend/migrations/` — Database migrations

---

## Questions?

- **Backend issues**: Check `backend/logs/` and backend terminal output
- **Frontend issues**: Check browser console (F12) and frontend terminal output
- **Database issues**: Use `psql portfolioai` to inspect database
- **Stripe issues**: Check Stripe dashboard for event history

Good luck! 🚀
