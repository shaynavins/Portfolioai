# PortfolioAI — Production Deployment Guide

Complete guide to deploying PortfolioAI to production on AWS, Heroku, Railway, or DigitalOcean.

## Pre-Deployment Checklist

Before deploying, ensure:
- [ ] All environment variables are configured (see `.env.example`)
- [ ] Database migrations pass locally: `alembic upgrade head`
- [ ] Tests pass: `pytest` (backend) and `npm test` (frontend)
- [ ] Code is linted: `black`, `flake8`, `npm run lint`
- [ ] `.env` file is in `.gitignore` (never commit secrets)
- [ ] Stripe account is created with live API keys
- [ ] SendGrid account is set up with verified sender domain
- [ ] GitHub OAuth app is created with production URLs
- [ ] SSL certificates are ready (auto-renew recommended)

---

## Option 1: Railway (Recommended for Getting Started)

Railway is the easiest platform for deploying full-stack applications with minimal configuration.

### 1. Create Railway Account

1. Go to https://railway.app
2. Sign up with GitHub (easier for deployment)
3. Create new project

### 2. Connect GitHub Repository

1. Click "Deploy from GitHub"
2. Authorize Railway access to your repository
3. Select the portfolio AI repository
4. Railway auto-detects Python (backend) and Node.js (frontend)

### 3. Add PostgreSQL Database

1. In Railway dashboard, click "Add Service"
2. Select "PostgreSQL"
3. Railway auto-creates a `DATABASE_URL` environment variable

### 4. Add Redis Cache

1. Click "Add Service"
2. Select "Redis"
3. Railway auto-creates a `REDIS_URL` environment variable

### 5. Set Environment Variables

1. Go to Backend Service → Settings → Environment Variables
2. Add all variables from `.env.example`:

```
ENVIRONMENT=production
LOG_LEVEL=INFO
DEBUG=false

SECRET_KEY=<generate-random-string>
JWT_SECRET=<generate-random-string>

GITHUB_CLIENT_ID=<your-github-oauth-id>
GITHUB_CLIENT_SECRET=<your-github-oauth-secret>

GOOGLE_API_KEY=<your-gemini-api-key>

STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_live_...
STRIPE_PRODUCT_ID_PRO=price_live_...
STRIPE_PRODUCT_ID_TEAM=price_live_...

SENDGRID_API_KEY=SG.xxx
SENDGRID_FROM_EMAIL=noreply@portfolioai.app

R2_ACCOUNT_ID=<your-r2-account-id>
R2_ACCESS_KEY_ID=<your-access-key>
R2_SECRET_ACCESS_KEY=<your-secret-key>
R2_BUCKET_NAME=portfolioai
R2_PUBLIC_URL=https://cdn.portfolioai.app

VERCEL_TOKEN=<optional-vercel-token>

FEATURE_EMAIL_NOTIFICATIONS=true
FEATURE_WEBHOOKS=true
REQUIRE_HTTPS=true
```

### 6. Configure Deployment Settings

**Backend Service**:
1. Settings → Build Command: `pip install -r requirements.txt && alembic upgrade head`
2. Settings → Start Command: `uvicorn api.main:app --host 0.0.0.0 --port 8000`
3. Enable auto-deploy on main branch

**Frontend Service**:
1. Settings → Build Command: `npm install && npm run build`
2. Settings → Start Command: `npm start`
3. Environment variable: `NEXT_PUBLIC_API_URL=https://api.portfolioai.app`

### 7. Deploy

1. Push changes to `main` branch
2. Railway auto-deploys backend and frontend
3. Check deployment logs for errors

### 8. Configure Domain

1. Go to Backend Service → Settings → Domains
2. Add your domain (e.g., `api.portfolioai.app`)
3. Add CNAME record to your DNS provider
4. Railway provides free HTTPS via Let's Encrypt

---

## Option 2: Heroku (Classic, But Requires Paid Dyno)

**Note**: Heroku's free tier was discontinued. Cheapest option is $7/month (eco dyno).

### 1. Create Heroku Account

1. Go to https://heroku.com
2. Sign up
3. Install Heroku CLI: `brew install heroku/brew/heroku`

### 2. Create Apps

```bash
# Create backend app
heroku create portfolioai-backend

# Create frontend app  
heroku create portfolioai-frontend
```

### 3. Add PostgreSQL Add-on

```bash
heroku addons:create heroku-postgresql:standard-0 --app=portfolioai-backend
```

### 4. Add Redis Add-on

```bash
heroku addons:create heroku-redis:premium-0 --app=portfolioai-backend
```

### 5. Set Environment Variables

```bash
heroku config:set \
  ENVIRONMENT=production \
  SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))") \
  JWT_SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(32))") \
  GITHUB_CLIENT_ID=your_id \
  GITHUB_CLIENT_SECRET=your_secret \
  STRIPE_SECRET_KEY=sk_live_... \
  --app=portfolioai-backend
```

### 6. Deploy Backend

```bash
# From project root
git remote add heroku-backend https://git.heroku.com/portfolioai-backend.git

cd backend
git subtree push --prefix backend heroku-backend main

# Run migrations
heroku run "alembic upgrade head" --app=portfolioai-backend
```

### 7. Deploy Frontend

```bash
git remote add heroku-frontend https://git.heroku.com/portfolioai-frontend.git

cd frontend
# Create Procfile if not exists:
echo "web: npm start" > Procfile

git subtree push --prefix frontend heroku-frontend main
```

### 8. Configure Domain

```bash
heroku domains:add api.portfolioai.app --app=portfolioai-backend
heroku domains:add portfolioai.app --app=portfolioai-frontend
```

---

## Option 3: AWS (Scalable, More Configuration)

### 3.1 Backend Deployment (ECS)

#### Step 1: Create ECR Repository

```bash
aws ecr create-repository --repository-name portfolioai-backend --region us-east-1
```

#### Step 2: Build and Push Docker Image

Create `backend/Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api/ api/
COPY migrations/ migrations/
COPY alembic.ini .

ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and push:

```bash
# Get ECR login
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# Build image
docker build -t portfolioai-backend:latest ./backend

# Tag image
docker tag portfolioai-backend:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/portfolioai-backend:latest

# Push image
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/portfolioai-backend:latest
```

#### Step 3: Create RDS PostgreSQL Database

```bash
aws rds create-db-instance \
  --db-instance-identifier portfolioai-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --master-username postgres \
  --master-user-password <strong-password> \
  --allocated-storage 20 \
  --publicly-accessible false \
  --region us-east-1
```

#### Step 4: Create ElastiCache Redis Cluster

```bash
aws elasticache create-cache-cluster \
  --cache-cluster-id portfolioai-redis \
  --cache-node-type cache.t3.micro \
  --engine redis \
  --num-cache-nodes 1 \
  --region us-east-1
```

#### Step 5: Create ECS Cluster & Service

```bash
# Create cluster
aws ecs create-cluster --cluster-name portfolioai --region us-east-1

# Create task definition (portfolioai-task.json)
# Then register it
aws ecs register-task-definition --cli-input-json file://portfolioai-task.json --region us-east-1

# Create service
aws ecs create-service \
  --cluster portfolioai \
  --service-name portfolioai-backend \
  --task-definition portfolioai:1 \
  --desired-count 1 \
  --launch-type FARGATE \
  --region us-east-1
```

### 3.2 Frontend Deployment (S3 + CloudFront)

#### Step 1: Create S3 Bucket

```bash
aws s3 mb s3://portfolioai-frontend --region us-east-1
```

#### Step 2: Enable Static Website Hosting

```bash
aws s3 website s3://portfolioai-frontend \
  --index-document index.html \
  --error-document 404.html
```

#### Step 3: Build and Upload Frontend

```bash
cd frontend
npm run build

# Upload to S3
aws s3 sync out/ s3://portfolioai-frontend --delete
```

#### Step 4: Create CloudFront Distribution

```bash
# Use AWS Console for easier CloudFront setup
# Or use AWS CLI with distribution config JSON
```

---

## Option 4: DigitalOcean App Platform

Similar to Railway, but DigitalOcean offers more control.

### 1. Create DigitalOcean Account

1. Go to https://digitalocean.com
2. Sign up
3. Create project

### 2. Create App from GitHub

1. Click "Create" → "Apps"
2. Select GitHub repository
3. DigitalOcean auto-detects components

### 3. Configure Services

**Backend Service**:
- Build Command: `pip install -r requirements.txt`
- Run Command: `uvicorn api.main:app --host 0.0.0.0 --port 8000`
- HTTP Port: 8000

**Frontend Service**:
- Build Command: `npm install && npm run build`
- Run Command: `npm start`
- HTTP Port: 3000

### 4. Add Databases

1. Click "Add Resource" → "Database"
2. Select PostgreSQL (managed)
3. Select Redis (managed)

### 5. Deploy

1. Set environment variables in app spec
2. Deploy via GitHub push to `main` branch

---

## Post-Deployment Setup

### 1. Configure Stripe Webhook

1. Go to Stripe Dashboard → Developers → Webhooks
2. Add endpoint: `https://api.portfolioai.app/api/billing/webhook`
3. Select events: `customer.subscription.*`, `invoice.payment_*`, `charge.dispute.*`
4. Copy webhook signing secret → Update `STRIPE_WEBHOOK_SECRET`

### 2. Configure GitHub OAuth

1. Go to GitHub Settings → Developer settings → OAuth Apps
2. Update callback URL: `https://api.portfolioai.app/api/auth/github/callback`
3. Verify Client ID and Secret are in production env vars

### 3. Test End-to-End

```bash
# 1. Test API health
curl https://api.portfolioai.app/health

# 2. Test GitHub OAuth
# Visit https://portfolioai.app and try login

# 3. Test Stripe
# Go to pricing page, try checkout with test card

# 4. Check logs for errors
# Monitor application logs on deployment platform
```

### 4. Enable Monitoring

#### Set Up Sentry (Error Tracking)

1. Create account at https://sentry.io
2. Create project for Python
3. Add to `.env`:
   ```
   SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx
   ```

#### Set Up Uptime Monitoring

1. Create account at https://uptimerobot.com
2. Add monitor for `https://api.portfolioai.app/health`
3. Set alerts to email

#### Configure CloudWatch (AWS)

1. Go to CloudWatch → Logs
2. Create log group for application
3. Set up alarms for error rates

### 5. Set Up Database Backups

**Railway**: Automatic daily backups included

**Heroku**: Use `heroku pg:backups:schedule`

**AWS RDS**: Enable automated backups (default is 7 days)

**DigitalOcean**: Enable managed database backups

---

## Domain Configuration

### Configure Base Domain

1. **Frontend**: Point `portfolioai.app` to frontend hosting
2. **Backend API**: Point `api.portfolioai.app` to backend hosting
3. **CDN**: Point `cdn.portfolioai.app` to object storage (R2 or S3)

### Enable HTTPS

All platforms above provide free HTTPS via Let's Encrypt or auto-provisioning.

Verify with:
```bash
curl -I https://api.portfolioai.app
# Should return 200 and HTTPS header
```

---

## Scaling

### Horizontal Scaling

- **Railway**: Auto-scales horizontally on deployed services
- **Heroku**: Use `heroku ps:scale web=2`
- **AWS ECS**: Increase `desired_count` and use auto-scaling
- **DigitalOcean**: Scale via app spec

### Database Scaling

- **PostgreSQL**: Increase storage/compute as needed
- **Redis**: Monitor memory usage, increase node type if needed

### CDN Scaling

- **Cloudflare R2**: Unlimited bandwidth, no egress costs
- **AWS CloudFront**: Scales automatically

---

## Cost Estimation

### Monthly Costs (Approximate)

| Component | Railway | Heroku | AWS | DigitalOcean |
|-----------|---------|--------|-----|--------------|
| Backend App | $5-50 | $7-50 | $5-20 | $5-20 |
| PostgreSQL | $5-50 | $9-50 | $10-50 | $10-50 |
| Redis | $5-20 | $10-50 | $5-20 | $5-20 |
| Storage/CDN | $0-10 | $0-10 | $5-20 | $5-20 |
| **Total** | **$15-130** | **$26-150** | **$25-110** | **$25-110** |

**Recommendation**: Start with Railway or DigitalOcean for simplicity. Scale to AWS when traffic justifies the complexity.

---

## Troubleshooting Deployment

### Backend Not Starting

Check logs:
```bash
# Railway
railway logs

# Heroku
heroku logs -t --app=portfolioai-backend

# AWS
aws logs tail /aws/ecs/portfolioai-backend --follow
```

Common issues:
- Environment variables missing → Check `.env` vars are set
- Database migration failed → Run `alembic upgrade head` manually
- Port binding error → Check app is listening on correct port

### Database Connection Error

```
Error: could not connect to server: No such file or directory
```

Verify:
- `DATABASE_URL` is correct format
- Database server is running
- Network security groups allow inbound connections

### CORS Errors

Frontend cannot reach backend:

1. Check `NEXT_PUBLIC_API_URL` is correct
2. Verify backend has CORS enabled in `api/config.py`
3. Check frontend is on HTTPS if backend is HTTPS

---

## Security Checklist

- [ ] All secrets in environment variables (never in code)
- [ ] HTTPS enforced (redirect HTTP → HTTPS)
- [ ] Database credentials are strong
- [ ] Regular automated backups enabled
- [ ] Monitor for suspicious activity (Sentry, CloudWatch)
- [ ] Rate limiting enabled (Redis)
- [ ] CORS configured correctly (no `*`)
- [ ] SQL injection prevention (use ORM, parameterized queries)
- [ ] XSS prevention (Next.js built-in)

---

## Rollback Strategy

If deployment has critical bugs:

### Railway
```bash
# Revert to previous deployment
railway deployment rollback
```

### Heroku
```bash
# Revert to previous release
heroku releases:rollback --app=portfolioai-backend
```

### AWS
```bash
# Update ECS service to previous task definition
aws ecs update-service \
  --cluster portfolioai \
  --service portfolioai-backend \
  --task-definition portfolioai:N \
  --force-new-deployment
```

---

## Disaster Recovery

### Restore from Database Backup

**Railway/Heroku/DigitalOcean**: Use managed database restore feature

**AWS RDS**:
```bash
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier portfolioai-restored \
  --db-snapshot-identifier portfolio-backup-snapshot
```

### Restore from Code

```bash
# Redeploy from git history
git revert <commit-hash>
git push origin main
# Platform auto-redeploys
```

---

## Maintenance Window

Schedule weekly maintenance:

1. **Monday 2am UTC**: Database optimization
2. **Wednesday 2am UTC**: Dependency updates
3. **Friday 2am UTC**: Backup verification

During maintenance, users may experience:
- 5-10 minute downtime
- Slower API responses
- Cannot build portfolios

Announce maintenance 48 hours in advance.

---

## Support & Documentation

- **Railway Docs**: https://docs.railway.app
- **Heroku Docs**: https://devcenter.heroku.com
- **AWS Docs**: https://docs.aws.amazon.com
- **DigitalOcean Docs**: https://docs.digitalocean.com
- **PortfolioAI Issues**: https://github.com/yourusername/portfolioai/issues

---

**Ready to deploy?** Start with Railway (easiest), then migrate to AWS as you scale. 🚀
