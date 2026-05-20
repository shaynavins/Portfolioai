# PortfolioAI v1.0.0 — Production-Ready Launch

**Release Date**: May 2025

We're thrilled to announce PortfolioAI v1.0.0, a **production-ready, monetizable SaaS platform** for generating and hosting AI-powered portfolios! This release includes complete authentication, payments, email, and deployment infrastructure.

---

## What's New

### Phase 1: Auth & Security ✅

**Secure, scalable user authentication system with JWT token pairs and comprehensive security.**

- **JWT Token-Pair Authentication**: 15-minute access tokens + 30-day refresh tokens for secure sessions
- **Password Security**: bcrypt hashing with configurable rounds, no plaintext storage
- **GitHub OAuth Integration**: Sign up/login with GitHub in 2 clicks
- **Rate Limiting**: Redis-backed per-user request limits (5 auth, 100 general, 10 build per hour)
- **Security Headers**: CORS, HSTS, X-Frame-Options, X-Content-Type-Options
- **Input Validation**: Pydantic schemas for all endpoints, SQL injection prevention
- **HTTPS Enforcement**: All production endpoints require HTTPS
- **Configuration System**: 60+ environment variables, organized by feature

**Files Added**:
- `backend/api/auth/` — GitHub OAuth routes
- `backend/api/security.py` — JWT, token validation, security headers
- `backend/api/validation.py` — Pydantic models

---

### Phase 2: Stripe Integration ✅

**Complete payment infrastructure with tier-based build limits and webhook handling.**

- **Subscription Models**:
  - **Free Plan**: 3 builds/month, limited features
  - **Pro Plan**: $9/month, 50 builds/month, advanced analytics
  - **Team Plan**: $29/month, unlimited builds, admin controls
- **Stripe Checkout**: Seamless checkout experience with Stripe's hosted UI
- **Webhook Handling**: Automatic subscription, payment, and dispute event processing
- **Build Limits Enforcement**: Per-plan limits checked on each build request
- **Subscription Management**: Cancel, upgrade, downgrade capabilities
- **Invoice History**: Track all payments with hosted invoice URLs
- **Idempotent Migrations**: Safe, repeatable database setup

**Database Models** (5 new tables):
- `subscriptions` — User subscription status, tier, stripe IDs
- `invoices` — Invoice records with amounts and payment status
- `payment_methods` — Stored payment methods
- `webhook_logs` — Audit trail of Stripe webhook events
- `stripe_products` — Product/price mapping (Free, Pro, Team)

**Files Added**:
- `backend/api/integrations/stripe_client.py` — Stripe API wrapper
- `backend/api/routes/billing.py` — All billing endpoints (checkout, webhook, status, cancel, invoices, usage)
- `backend/api/models/billing_models.py` — Database models
- `backend/migrations/versions/001_add_subscription_tables.py` — Database migration

---

### Phase 3: Frontend & Email & Billing Dashboard ✅

**User-friendly pricing, checkout, and subscription management with transactional emails.**

#### 3A: Frontend Pricing & Checkout
- **Pricing Page** (`/pricing`):
  - 3-tier pricing table with feature comparison
  - FAQ section
  - CTAs to upgrade or start free
  - Responsive design (mobile, tablet, desktop)
- **Checkout Page** (`/checkout`):
  - Order summary with selected plan
  - Redirect to Stripe checkout
  - Success/cancel handling
- **Dashboard Updates**:
  - Billing card showing current subscription status
  - Renewal dates and billing period
  - Upgrade, downgrade, cancel buttons
  - Usage statistics for build limit

#### 3B: Email Integration
- **SendGrid Integration**: 4 transactional email templates
- **Email Templates**:
  - Welcome email (new user signup)
  - Payment success (subscription activated)
  - Payment failure (card declined, action required)
  - Cancellation confirmation (subscription ended)
- **Event Hooks**: Emails automatically sent on Stripe webhook events
- **Graceful Fallback**: Works without SendGrid (logs email content if API key missing)

#### 3C: Billing Dashboard
- **Invoices Endpoint** (`GET /api/billing/invoices`):
  - Invoice history with amounts, dates, status
  - Links to hosted invoice URLs on Stripe
  - Pagination support
- **Usage Endpoint** (`GET /api/billing/usage`):
  - Current month's build consumption vs tier limit
  - Remaining quota calculation
  - Percentage usage indicator
  - Billing period dates

**Files Added**:
- `frontend/src/app/pricing/page.tsx` (370 lines) — Pricing page with feature comparison
- `frontend/src/app/checkout/page.tsx` (145 lines) — Checkout handoff to Stripe
- `backend/api/routes/billing.py` (585 lines) — All billing endpoints
- `backend/api/integrations/sendgrid_client.py` (225 lines) — Email service
- `backend/.env.example` (132 lines) — Configuration template

---

## New Endpoints

### Authentication
- `POST /api/auth/github/login` — GitHub OAuth login
- `POST /api/auth/refresh` — Refresh access token
- `POST /api/auth/logout` — Logout user
- `GET /api/auth/me` — Get current user

### Billing
- `POST /api/billing/checkout` — Create Stripe checkout session
- `POST /api/billing/webhook` — Stripe webhook handler (auto-called by Stripe)
- `GET /api/billing/status` — Get subscription status
- `POST /api/billing/cancel` — Cancel subscription
- `GET /api/billing/invoices` — Get invoice history
- `GET /api/billing/usage` — Get build usage and quota

### Enhanced
- `GET /api/portfolios/{id}/builds` — Build history with filtering
- Build endpoint now enforces subscription tier limits

---

## Documentation

We've created comprehensive guides for development and deployment:

- **API_DOCS.md** — Complete API reference with examples and error codes
- **DEPLOYMENT.md** — Production deployment guide (Railway, Heroku, AWS, DigitalOcean)
- **DEV_SETUP.md** — Local development setup (Python, Node.js, PostgreSQL, Redis)
- **STARTUP_CHECKLIST.md** — Pre-launch checklist (infrastructure, Stripe, email, testing)

---

## Technical Highlights

### Backend Stack
- **FastAPI** — Modern, async Python web framework
- **SQLAlchemy** + **Alembic** — Async ORM with safe migrations
- **PostgreSQL** — Reliable relational database
- **Redis** — Rate limiting, caching, job queues
- **Stripe SDK** — Production-ready payment handling
- **SendGrid SDK** — Reliable email delivery
- **Pydantic** — Input validation and serialization
- **Bcrypt** — Secure password hashing
- **python-jose** — JWT token generation and validation

### Frontend Stack
- **Next.js 14** — React framework with App Router
- **TypeScript** — Type-safe development
- **TailwindCSS** — Utility-first styling
- **Stripe.js** — Client-side payment integration
- **Axios** — HTTP client with interceptors

### Database
- **PostgreSQL 13+** — ACID-compliant relational database
- **Alembic** — Safe, version-controlled schema migrations
- **8 tables**: users, portfolios, build_jobs, subscriptions, invoices, payment_methods, webhook_logs, stripe_products

---

## Security Features

- ✅ JWT token-pair authentication (no session storage)
- ✅ Bcrypt password hashing (not salting)
- ✅ CORS properly configured (no wildcard)
- ✅ HTTPS required in production
- ✅ Rate limiting per user and endpoint
- ✅ SQL injection prevention (ORM parameterized queries)
- ✅ XSS prevention (Next.js escaping)
- ✅ CSRF protection via SameSite cookies
- ✅ Secrets never logged (environment variables)
- ✅ Webhook signature verification (Stripe)

---

## Breaking Changes

None — this is the initial v1.0.0 release. No previous versions to break from.

---

## Known Limitations

- Portfolio deployment to live environments requires GitHub OAuth (users must authenticate)
- Email templates are basic HTML (further customization available)
- Build limits reset on calendar month (not billing cycle)
- Stripe test mode required before live (flip secret keys for production)

---

## What's Coming Next

Planned for future phases:

- **Phase 4**: Analytics & Reporting (build times, deployment stats, user insights)
- **Phase 5**: Team Collaboration (shared portfolios, role-based access, audit logs)
- **Phase 6**: Advanced Theming (custom templates, color schemes, custom domains)
- **Phase 7**: Mobile App (React Native, push notifications, offline support)

---

## How to Get Started

### For Developers
1. Clone the repository: `git clone https://github.com/yourusername/portfolioai.git`
2. Follow **DEV_SETUP.md** to run locally
3. Explore the API at `http://localhost:8000/docs`
4. Read **API_DOCS.md** for endpoint details

### For Deploying
1. Choose a hosting platform (Railway recommended for simplicity)
2. Follow **DEPLOYMENT.md** for step-by-step instructions
3. Use **STARTUP_CHECKLIST.md** before going live
4. Configure Stripe, SendGrid, and GitHub OAuth

---

## Upgrading

If you're using an earlier version of PortfolioAI:

1. Pull latest code: `git pull origin main`
2. Install new dependencies: `pip install -r requirements.txt`
3. Run database migrations: `alembic upgrade head`
4. Update environment variables: Use updated `.env.example`
5. Restart your application

---

## Contributors

**Phase 1-3 Development**:
- Authentication & Security: Oz (AI Agent)
- Stripe Integration: Oz (AI Agent)
- Frontend & Email: Oz (AI Agent)

---

## Support

- 📖 **Documentation**: See the docs files above
- 🐛 **Issues**: Report bugs on GitHub Issues
- 💬 **Discussions**: Ask questions on GitHub Discussions
- 📧 **Email**: support@portfolioai.app

---

## License

MIT License — Free for personal and commercial use

---

## Changelog

### v1.0.0 (May 2025)
- **Phase 1**: JWT auth, OAuth, rate limiting, security headers
- **Phase 2**: Stripe payments, subscription tiers, build limits, webhooks
- **Phase 3**: Pricing UI, checkout flow, email templates, billing dashboard
- **Documentation**: Complete API, deployment, dev setup, startup guides

---

**Thank you for using PortfolioAI!** 🎉

We're excited to see what you build. If you have feedback or feature requests, please reach out!

---

**Ready to launch?** Start with [STARTUP_CHECKLIST.md](./STARTUP_CHECKLIST.md) → [DEPLOYMENT.md](./DEPLOYMENT.md) → Go Live! 🚀
