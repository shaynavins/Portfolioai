# PortfolioAI Deployment Guide

## Pre-Deployment Checklist

- [ ] All tests pass locally
- [ ] Environment variables are configured
- [ ] Database migrations run successfully
- [ ] R2 bucket is created and public
- [ ] Razorpay production keys obtained
- [ ] GitHub OAuth app configured for production domain
- [ ] CORS settings updated for production domain
- [ ] SSL certificate ready (for HTTPS)
- [ ] Domain DNS configured
- [ ] Backups configured

---

## Backend Deployment

### Option 1: Deploy to Heroku

**1. Create Heroku app**
```bash
heroku create portfolioai-backend
```

**2. Add PostgreSQL addon**
```bash
heroku addons:create heroku-postgresql:hobby-dev
```

**3. Add Redis addon**
```bash
heroku addons:create heroku-redis:premium-0
```

**4. Set environment variables**
```bash
heroku config:set \
  GOOGLE_API_KEY="your_key" \
  GITHUB_CLIENT_ID="your_id" \
  GITHUB_CLIENT_SECRET="your_secret" \
  JWT_SECRET="$(openssl rand -hex 32)" \
  RAZORPAY_KEY_ID="your_key" \
  RAZORPAY_KEY_SECRET="your_secret" \
  R2_ACCOUNT_ID="your_id" \
  R2_ACCESS_KEY_ID="your_key" \
  R2_SECRET_ACCESS_KEY="your_secret" \
  APP_URL="https://yourdomain.com" \
  API_URL="https://api.yourdomain.com" \
  ENVIRONMENT="production"
```

**5. Create Procfile** in backend directory:
```
web: gunicorn -w 4 -b 0.0.0.0:$PORT api.main:app
```

**6. Deploy**
```bash
git push heroku main
```

### Option 2: Deploy to DigitalOcean App Platform

**1. Connect repository** to DigitalOcean
**2. Configure app spec:**
```yaml
name: portfolioai-backend
services:
  - name: api
    github:
      repo: your-repo/portfolioai
      branch: main
    build_command: pip install -r requirements.txt
    run_command: python -m uvicorn api.main:app --host 0.0.0.0
    envs:
      - key: GOOGLE_API_KEY
        value: ${GOOGLE_API_KEY}
      - key: DATABASE_URL
        value: ${DB_CONNECTION}
      # Add all other env vars
databases:
  - name: postgres
    engine: PG
  - name: redis
    engine: REDIS
```

**3. Deploy via dashboard** or CLI

### Option 3: Deploy to AWS (ECS + RDS + ElastiCache)

**1. Create RDS PostgreSQL instance**
```bash
aws rds create-db-instance \
  --db-instance-identifier portfolioai-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --master-username postgres \
  --master-user-password "strong_password" \
  --allocated-storage 20
```

**2. Create ElastiCache Redis cluster**
```bash
aws elasticache create-cache-cluster \
  --cache-cluster-id portfolioai-redis \
  --cache-node-type cache.t3.micro \
  --engine redis
```

**3. Create ECR repository**
```bash
aws ecr create-repository --repository-name portfolioai-backend
```

**4. Build and push Docker image**
```bash
# In backend directory
docker build -t portfolioai-backend .
docker tag portfolioai-backend:latest <account_id>.dkr.ecr.us-east-1.amazonaws.com/portfolioai-backend:latest
docker push <account_id>.dkr.ecr.us-east-1.amazonaws.com/portfolioai-backend:latest
```

**5. Create ECS task definition and service** via AWS console or CLI

---

## Frontend Deployment

### Option 1: Deploy to Vercel

**1. Connect repository to Vercel**
```bash
vercel
```

**2. Set environment variables** in Vercel dashboard:
```
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
NEXT_PUBLIC_GITHUB_CLIENT_ID=your_client_id
NEXT_PUBLIC_APP_URL=https://yourdomain.com
NEXT_PUBLIC_RAZORPAY_KEY_ID=your_key
```

**3. Deploy**
```bash
git push main
```

Vercel auto-deploys on push to main branch.

### Option 2: Deploy to Netlify

**1. Connect repository**
```bash
netlify init
```

**2. Configure `netlify.toml`:**
```toml
[build]
  command = "npm run build"
  publish = ".next"

[[redirects]]
  from = "/api/*"
  to = "https://api.yourdomain.com/api/:splat"
  status = 200
  force = true

[env]
  NEXT_PUBLIC_API_URL = "https://api.yourdomain.com"
  NEXT_PUBLIC_GITHUB_CLIENT_ID = "your_client_id"
  NEXT_PUBLIC_APP_URL = "https://yourdomain.com"
  NEXT_PUBLIC_RAZORPAY_KEY_ID = "your_key"
```

**3. Deploy**
```bash
netlify deploy --prod
```

### Option 3: Deploy to AWS S3 + CloudFront

**1. Create S3 bucket**
```bash
aws s3 mb s3://portfolioai-frontend
```

**2. Build static files**
```bash
npm run build
npm run export  # If using next export
```

**3. Upload to S3**
```bash
aws s3 sync .next/static s3://portfolioai-frontend
```

**4. Create CloudFront distribution** pointing to S3 bucket

**5. Update Route 53 DNS** to point to CloudFront

---

## Domain & SSL Configuration

### Update DNS Records
```
A Record: yourdomain.com → API IP/endpoint
CNAME: api.yourdomain.com → API domain
CNAME: www.yourdomain.com → Frontend domain
```

### SSL Certificate
- **Vercel/Netlify**: Auto-configured with Let's Encrypt
- **Heroku**: Auto-configured with Acme
- **AWS/DigitalOcean**: Use ACM (AWS Certificate Manager) or Let's Encrypt

---

## Production Environment Variables

### Backend (.env)
```
# Set to production
ENVIRONMENT=production

# Disable debug mode
DEBUG=false

# Use production URLs
APP_URL=https://yourdomain.com
API_URL=https://api.yourdomain.com

# Use production databases
DATABASE_URL=postgresql://user:pass@prod-db:5432/portfolioai
REDIS_URL=redis://prod-redis:6379

# Update CORS
ALLOWED_ORIGINS=["https://yourdomain.com", "https://www.yourdomain.com"]

# Use production Razorpay keys (not test keys!)
RAZORPAY_KEY_ID=rzp_live_xxx
RAZORPAY_KEY_SECRET=xxx

# Use production GitHub OAuth
GITHUB_CLIENT_ID=prod_client_id
GITHUB_CLIENT_SECRET=prod_client_secret
```

### Frontend (.env.production)
```
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
NEXT_PUBLIC_APP_URL=https://yourdomain.com
NEXT_PUBLIC_GITHUB_CLIENT_ID=prod_client_id
NEXT_PUBLIC_RAZORPAY_KEY_ID=rzp_live_xxx
```

---

## Post-Deployment Steps

### 1. Verify Deployment
```bash
# Test backend health
curl https://api.yourdomain.com/api/health

# Test frontend loads
curl https://yourdomain.com

# Check database connection
# Access backend logs to verify DB is working
```

### 2. Update GitHub OAuth
- Go to GitHub Settings → Developer Settings → OAuth Apps
- Update redirect URI: `https://yourdomain.com/auth/github/callback`

### 3. Update Razorpay Webhook
- Go to Razorpay Dashboard → Webhooks
- Add webhook URL: `https://api.yourdomain.com/api/webhooks/razorpay`
- Subscribe to: `payment.authorized`, `payment.failed`, `subscription.activated`

### 4. Set Up Monitoring
```bash
# Sentry for error tracking
SENTRY_DSN=https://xxx@sentry.io/123456

# CloudWatch/DataDog for logs
```

### 5. Configure Backups
- **Database**: Daily automated backups (Heroku/AWS RDS default)
- **R2 Bucket**: Enable versioning in Cloudflare
- **Code**: GitHub repo is your backup

### 6. Set Up Auto-scaling (Optional)
- **Heroku**: Use Dyno autoscaling
- **AWS ECS**: Configure auto-scaling policies
- **DigitalOcean**: Configure app autoscaling

---

## Monitoring & Maintenance

### Key Metrics to Monitor
- API response times (target: < 200ms)
- Database connection pool usage
- R2 upload success rate
- Razorpay payment success rate
- Frontend page load time (target: < 3s)
- Error rate (target: < 0.5%)

### Daily Checks
- Check error logs
- Verify R2 uploads are working
- Check payment processing

### Weekly Checks
- Review analytics
- Check database size
- Review security logs
- Monitor costs

### Monthly Tasks
- Review and optimize slow queries
- Update dependencies
- Security audit
- Backup verification

---

## Troubleshooting Production Issues

### 503 Service Unavailable
- Check backend logs
- Verify database is running
- Check Redis connection
- Restart app instance

### CORS Errors
- Verify ALLOWED_ORIGINS in backend .env
- Check frontend domain is included
- Restart backend after changing CORS

### Payment Not Processing
- Verify Razorpay credentials
- Check payment logs
- Verify webhook is configured
- Test with Razorpay dashboard

### R2 Upload Failing
- Verify R2 credentials
- Check bucket permissions
- Verify bucket is public
- Check R2 bucket exists

---

## Rollback Procedure

### If deployment fails:

**Heroku**
```bash
heroku releases
heroku rollback v123  # Roll back to previous release
```

**Vercel**
- Go to Vercel Dashboard → Deployments
- Click "Rollback" on previous successful deployment

**Git**
```bash
git revert HEAD
git push main
```

---

## Cost Estimation

**Monthly costs (production):**
- Backend (Heroku Standard): $50/month
- PostgreSQL (Heroku Premium): $50/month
- Redis (Heroku Premium): $50/month
- Frontend (Vercel): Free tier
- R2 Storage: $0.15/GB + $0.30/million requests
- Razorpay: 2% + ₹3 per transaction
- **Total: ~$150-200/month** + payment processing fees

---

## Security Checklist

- [ ] HTTPS enforced on all URLs
- [ ] CORS properly configured
- [ ] JWT tokens expire after reasonable time
- [ ] Passwords hashed with bcrypt
- [ ] Rate limiting enabled
- [ ] SQL injection prevention (using ORMs)
- [ ] XSS prevention (React escapes by default)
- [ ] CSRF tokens for state-changing requests
- [ ] Environment variables not committed
- [ ] Database backups automated
- [ ] API keys rotated regularly
- [ ] Monitoring and alerting configured
- [ ] User data encrypted in transit (HTTPS)

---

## Performance Optimization

### Backend
- Enable response caching
- Use database connection pooling
- Implement rate limiting
- Optimize Gemini API calls
- Use CDN for static assets

### Frontend
- Code splitting by route
- Image optimization
- CSS minification
- JavaScript bundling
- Service workers for offline support

---

## Documentation for Users

Create a `PRODUCTION_RUNBOOK.md` with:
- How to access admin dashboard
- How to check payment status
- How to troubleshoot common issues
- Emergency contact procedures
- Escalation procedures
