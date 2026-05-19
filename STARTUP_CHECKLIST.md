# PortfolioAI — Startup Checklist

Use this checklist to prepare PortfolioAI for production launch. Follow the order below.

## Pre-Launch (1-2 days before go-live)

### Infrastructure Setup
- [ ] **PostgreSQL Database**
  - [ ] Create production PostgreSQL instance (AWS RDS, Railway, Supabase, etc.)
  - [ ] Create database: `portfolioai`
  - [ ] Record connection string in secure vault
  - [ ] Ensure backups are enabled (daily minimum)
  - [ ] Test connection from application server

- [ ] **Redis Cache**
  - [ ] Create Redis instance (AWS ElastiCache, Railway, Upstash, etc.)
  - [ ] Verify connectivity
  - [ ] Configure persistence/snapshots
  - [ ] Record connection URL

- [ ] **Object Storage (Cloudflare R2 or AWS S3)**
  - [ ] Create bucket for portfolio sites
  - [ ] Configure CORS for portfolio delivery
  - [ ] Create access credentials (API token)
  - [ ] Record bucket name and public URL

### Secret Management
- [ ] **Create .env file** (never commit to git)
  - [ ] Copy `.env.example` to `.env`
  - [ ] Fill in all required secrets:
    - [ ] JWT_SECRET (use `python -c "import secrets; print(secrets.token_urlsafe(32))"`)
    - [ ] DATABASE_URL (production PostgreSQL)
    - [ ] REDIS_URL (production Redis)
    - [ ] GITHUB_CLIENT_ID / GITHUB_CLIENT_SECRET
    - [ ] GOOGLE_API_KEY (Gemini)
    - [ ] STRIPE_SECRET_KEY / STRIPE_WEBHOOK_SECRET
    - [ ] SENDGRID_API_KEY
    - [ ] R2_ACCESS_KEY_ID / R2_SECRET_ACCESS_KEY
    - [ ] VERCEL_TOKEN (optional, for portfolio deployment)
  - [ ] Store .env in secure vault (1Password, AWS Secrets Manager, etc.)
  - [ ] Verify no secrets in git history: `git log -p | grep -i "secret\|key\|token"`

- [ ] **Verify .env in .gitignore**
  ```bash
  grep "^\.env" .gitignore
  ```

### Stripe Configuration
- [ ] **Stripe Account Setup**
  - [ ] Create Stripe account at stripe.com
  - [ ] Complete identity verification
  - [ ] Switch to live mode (not test mode)
  - [ ] Generate live API keys

- [ ] **Create Products & Prices**
  - [ ] Create Pro plan product: $9/month recurring
    - [ ] Copy Price ID → STRIPE_PRODUCT_ID_PRO
  - [ ] Create Team plan product: $29/month recurring
    - [ ] Copy Price ID → STRIPE_PRODUCT_ID_TEAM
  - [ ] Create Free plan (no payment required, just for reference)

- [ ] **Configure Webhook Endpoint**
  - [ ] Go to **Developers → Webhooks**
  - [ ] Add endpoint: `https://api.portfolioai.app/api/billing/webhook`
  - [ ] Select events:
    - [ ] `customer.subscription.created`
    - [ ] `customer.subscription.updated`
    - [ ] `customer.subscription.deleted`
    - [ ] `invoice.payment_succeeded`
    - [ ] `invoice.payment_failed`
    - [ ] `charge.dispute.created`
  - [ ] Copy Webhook Signing Secret → STRIPE_WEBHOOK_SECRET
  - [ ] Test webhook with Stripe CLI: `stripe listen --forward-to localhost:8000/api/billing/webhook`

### SendGrid Configuration
- [ ] **SendGrid Account Setup**
  - [ ] Create SendGrid account at sendgrid.com
  - [ ] Verify sender email domain (DKIM/SPF)
  - [ ] Create API key → SENDGRID_API_KEY
  - [ ] Set SENDGRID_FROM_EMAIL to verified sender
  - [ ] Test sending email via API

### GitHub OAuth Setup
- [ ] **GitHub OAuth Application**
  - [ ] Go to GitHub Settings → Developer settings → OAuth Apps
  - [ ] Create new OAuth App
  - [ ] Fill in:
    - [ ] Application name: `PortfolioAI`
    - [ ] Homepage URL: `https://portfolioai.app` (or your domain)
    - [ ] Authorization callback URL: `https://api.portfolioai.app/api/auth/github/callback`
  - [ ] Copy Client ID → GITHUB_CLIENT_ID
  - [ ] Generate Client Secret → GITHUB_CLIENT_SECRET
  - [ ] Create Webhook Secret (32+ random chars) → GITHUB_WEBHOOK_SECRET

## Database & Migrations (1 hour before go-live)

### Initialize Database
- [ ] **Run Migrations**
  ```bash
  cd backend
  alembic upgrade head
  ```
  This creates all tables:
  - users, portfolios, build_jobs
  - subscriptions, invoices, payment_methods, webhook_logs, stripe_products

- [ ] **Verify Tables Exist**
  ```bash
  psql $DATABASE_URL -c "\dt"
  ```
  Should show 8 tables (3 existing + 5 new subscription tables)

### Seed Data (Optional)
- [ ] Create test admin user (if needed for dashboard)
- [ ] Create StripeProduct records for Free/Pro/Team plans

## Application Deployment (30 mins before go-live)

### Backend Deployment
- [ ] **Choose Hosting** (one of):
  - [ ] Heroku (easiest, $7-50/mo)
  - [ ] Railway (modern, pay-per-use)
  - [ ] AWS (EC2/Lightsail)
  - [ ] DigitalOcean App Platform
  - [ ] Google Cloud Run
  - [ ] Your own VPS

- [ ] **Deploy Backend**
  - [ ] Connect git repository to hosting platform
  - [ ] Set environment variables (copy from .env)
  - [ ] Enable automatic deployments from `main` branch
  - [ ] Run build: `pip install -r requirements.txt`
  - [ ] Run migrations: `alembic upgrade head`
  - [ ] Start server: `uvicorn api.main:app --host 0.0.0.0 --port 8000`
  - [ ] Verify health: `curl https://api.portfolioai.app/docs`

- [ ] **Test Backend**
  - [ ] Ping health endpoint
  - [ ] Test GitHub OAuth flow
  - [ ] Test JWT token generation
  - [ ] Test Stripe checkout (test mode first)

### Frontend Deployment
- [ ] **Choose Hosting** (one of):
  - [ ] Vercel (recommended for Next.js, free tier available)
  - [ ] Netlify
  - [ ] Cloudflare Pages
  - [ ] AWS S3 + CloudFront

- [ ] **Deploy Frontend**
  - [ ] Connect git repository to hosting
  - [ ] Set environment variables:
    - [ ] NEXT_PUBLIC_API_URL=`https://api.portfolioai.app`
  - [ ] Enable automatic deployments from `main`
  - [ ] Run build: `npm run build`
  - [ ] Verify site loads: `https://portfolioai.app`

- [ ] **Test Frontend**
  - [ ] Test signup flow (GitHub OAuth)
  - [ ] Test pricing page
  - [ ] Test dashboard
  - [ ] Test checkout flow (Stripe test mode first)
  - [ ] Test cancel subscription

## Pre-Launch Testing (30 mins before go-live)

### End-to-End Scenarios
- [ ] **User Signup → Build → Payment → Email**
  1. [ ] Click "Connect GitHub"
  2. [ ] Authorize OAuth
  3. [ ] Create portfolio
  4. [ ] Trigger build
  5. [ ] Go to pricing
  6. [ ] Click "Upgrade to Pro"
  7. [ ] Enter test card: `4242 4242 4242 4242` (Stripe test card)
  8. [ ] Verify email received (check SendGrid dashboard)
  9. [ ] Check subscription in dashboard

- [ ] **Subscription Management**
  - [ ] Test upgrade: Free → Pro
  - [ ] Test cancel: Pro → Free (at end of period)
  - [ ] Test payment failure alert (use `4000 0000 0000 0002`)
  - [ ] Verify emails sent for each event

- [ ] **Build Limits**
  - [ ] Free user: Try 4th build (should fail with 429)
  - [ ] Pro user: Try 51st build (should fail)
  - [ ] Team user: Build unlimited (should succeed)

### Security Validation
- [ ] **HTTPS Enforced**
  ```bash
  curl -I https://api.portfolioai.app
  ```
  Should return 301 redirect for HTTP

- [ ] **CORS Configured**
  - [ ] Test cross-origin request from frontend
  - [ ] Should return `Access-Control-Allow-Origin` header

- [ ] **Secrets Not in Logs**
  ```bash
  grep -r "sk_test_\|SG\.\|pk_test_" logs/
  ```
  Should return nothing

- [ ] **JWT Validation**
  - [ ] Test expired token (should return 401)
  - [ ] Test malformed token (should return 401)
  - [ ] Test valid token (should return 200)

## Go-Live Checklist (Day of launch)

- [ ] **Switch to Live Stripe Mode**
  - [ ] Update STRIPE_SECRET_KEY to live key (sk_live_xxx)
  - [ ] Update STRIPE_WEBHOOK_SECRET to live webhook secret
  - [ ] Update STRIPE_PRODUCT_ID_PRO to live price ID
  - [ ] Update STRIPE_PRODUCT_ID_TEAM to live price ID
  - [ ] Redeploy backend with new secrets

- [ ] **Enable Production Logging**
  - [ ] Set LOG_LEVEL=INFO (not DEBUG)
  - [ ] Set ENVIRONMENT=production
  - [ ] Configure Sentry for error tracking (optional but recommended)

- [ ] **Enable Feature Flags**
  - [ ] FEATURE_EMAIL_NOTIFICATIONS=true
  - [ ] FEATURE_WEBHOOKS=true
  - [ ] REQUIRE_HTTPS=true (production)

- [ ] **Final Smoke Tests**
  - [ ] Signup with real GitHub account
  - [ ] Build portfolio
  - [ ] Upgrade to real payment (small test charge, then refund)
  - [ ] Verify receipt email arrives
  - [ ] Check subscription in dashboard

- [ ] **Announce to Users**
  - [ ] Tweet/announce on social media
  - [ ] Send email to waitlist
  - [ ] Post on ProductHunt, HackerNews (optional)
  - [ ] Update website with feature list

## Post-Launch (Day 1-7)

- [ ] **Monitor Errors**
  - [ ] Check Sentry daily for errors
  - [ ] Review logs for failed builds or payments
  - [ ] Monitor database performance

- [ ] **Track Metrics**
  - [ ] Users signed up
  - [ ] Portfolios built
  - [ ] Stripe revenue (MRR)
  - [ ] Churn rate (cancellations)

- [ ] **Respond to Feedback**
  - [ ] Check email for user support requests
  - [ ] Fix critical bugs immediately
  - [ ] Defer non-critical requests to backlog

- [ ] **Backup Verification**
  - [ ] Verify daily database backups are running
  - [ ] Test restore from backup (on staging)
  - [ ] Document recovery procedure

## Ongoing Maintenance

- [ ] **Weekly**
  - [ ] Review error logs
  - [ ] Check payment success rate
  - [ ] Monitor uptime (set up UptimeRobot or similar)

- [ ] **Monthly**
  - [ ] Review usage metrics
  - [ ] Check for security updates to dependencies
  - [ ] Test disaster recovery plan

- [ ] **Quarterly**
  - [ ] Review and optimize database
  - [ ] Analyze churn patterns
  - [ ] Plan next phase features

---

## Quick Links

- **Stripe Dashboard**: https://dashboard.stripe.com
- **SendGrid Dashboard**: https://app.sendgrid.com
- **GitHub Settings**: https://github.com/settings/developers
- **Stripe CLI**: https://stripe.com/docs/stripe-cli
- **Alembic Docs**: https://alembic.sqlalchemy.org
- **PostgreSQL Docs**: https://www.postgresql.org/docs

---

**Estimated Time to Launch**: 2-3 days (infrastructure + config + testing)
**Estimated Cost (first month)**: $50-200 (database, hosting, Redis, storage)

Good luck! 🚀
