# Phase 1 — Auth & Security Implementation

## Overview
Phase 1 adds production-grade authentication, security hardening, and input validation to PortfolioAI. This forms the foundation for monetization (Stripe), email/webhooks, and scaling.

## What's New (Phase 1)

### 1. Token Management
- **Access + Refresh Token Pair**: 15-min access tokens, 30-day refresh tokens
- **Secure Token Utilities**: `backend/api/auth/tokens.py`
- **Token Types**: Prevents token confusion (access vs refresh)
- **JWT ID (jti)**: For token revocation tracking

### 2. Password Hashing
- **bcrypt Integration**: `backend/api/auth/password.py`
- **8+ Character Requirement**: Enforced at hashing time
- **No Plain Text**: Passwords hashed before DB storage

### 3. Security Hardening
- **CORS**: Strict origin whitelisting (production-ready)
- **Security Headers**: HSTS, CSP, X-Frame-Options, X-Content-Type-Options
- **Trusted Hosts**: Host header validation
- **Rate Limiting**: Per-user, tier-based (free: 100 req/min, pro: 500)
- **HTTPS Enforcement**: In production, redirects HTTP → HTTPS

### 4. Input Validation
- **Pydantic Models**: All request/response schemas validated
- **Email Validation**: EmailStr type for email fields
- **Field Constraints**: Min/max lengths, regex patterns, custom validators
- **Structured Error Responses**: Trace ID + field details on validation failure

### 5. Enhanced Configuration
- **Environment Enums**: Development | Staging | Production
- **Subscription Tiers**: Free | Pro | Team (with limits)
- **Production Validation**: Required settings check at startup
- **Feature Flags**: Email, webhooks, analytics, white-label (off by default)

### 6. Global Error Handling
- **Structured Errors**: All responses follow `{error, code, trace_id, details}`
- **Validation Exception Handler**: Collects field-level errors
- **HTTP Exception Handler**: Logs & traces all exceptions
- **No Internal Details**: Hide stack traces in production

---

## Setup Instructions

### Step 1: Update Dependencies
```bash
cd backend
pip install -r requirements.txt
```

New dependencies added:
- `email-validator==2.1.0` (for EmailStr validation)

All auth libs already present (python-jose, passlib, etc.)

### Step 2: Generate JWT Secret
```bash
openssl rand -hex 32
```
Copy output and paste into `.env`:
```
JWT_SECRET=<your_secret_here>
```

### Step 3: Configure .env
Copy `..env.example` to `.env`:
```bash
cp .env.example .env
```

Update these required fields:
```env
ENVIRONMENT=development
JWT_SECRET=your_generated_secret
DATABASE_URL=postgresql+asyncpg://postgres:password@127.0.0.1/portfolioai
GOOGLE_API_KEY=your_gemini_key
GITHUB_CLIENT_ID=your_github_id
GITHUB_CLIENT_SECRET=your_github_secret
GITHUB_WEBHOOK_SECRET=your_webhook_secret
```

Optional (for next phases):
- STRIPE_* keys (Phase 2)
- SENDGRID_* keys (Phase 3)
- SENTRY_DSN (Phase 4)

### Step 4: Test the Setup
```bash
# Start backend
cd backend
uvicorn api.main:app --reload --port 8000

# Test health endpoint
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "ok",
  "version": "1.0.0",
  "environment": "development",
  "timestamp": "2024-05-19T14:10:00Z"
}
```

### Step 5: Test Auth Flow
```bash
# GitHub OAuth login (triggers redirect to GitHub)
curl -X GET http://localhost:8000/api/auth/github

# After GitHub callback, you'll get a token in the dashboard URL
# Use it to fetch user profile
curl -H "Authorization: Bearer <your_token>" \
  http://localhost:8000/api/auth/me
```

---

## Key Files Created/Modified

### New Files
- `backend/api/auth/tokens.py` — Token generation & verification
- `backend/api/auth/password.py` — Password hashing utilities
- `backend/api/security.py` — CORS, security headers, rate limiting
- `backend/api/validation.py` — Pydantic models for all endpoints
- `PHASE_1_SETUP.md` — This file

### Modified Files
- `backend/api/config.py` — Expanded with 50+ settings
- `backend/api/main.py` — Integrated security middleware & error handlers
- `.env.example` — Complete production-grade template
- `backend/requirements.txt` — Added email-validator

---

## Architecture

```
┌─────────────────────────────────────────────┐
│         FastAPI App (main.py)               │
│  - Global exception handlers                │
│  - Security middleware (CORS, headers)      │
│  - Route registration                       │
└────────────────┬────────────────────────────┘
                 │
        ┌────────┴────────┐
        │                 │
   ┌────▼────┐        ┌───▼──────┐
   │  auth   │        │ portfolio │
   │ routes  │        │  routes   │
   └────┬────┘        └───┬──────┘
        │                 │
  ┌─────▼─────────┬──────▼──────────┐
  │               │                 │
  │           ┌───▼────┐        ┌───▼────────┐
  │           │ tokens │        │ validation │
  │           └────────┘        └────────────┘
  │
  │     (Uses for auth checks)
  ├────────────────────────────┐
  │                            │
  │  ┌──────────────────┐      │
  │  │ security.py      │◄─────┘
  │  │ - Rate limiting  │
  │  │ - CORS setup     │
  │  │ - Headers        │
  │  └──────────────────┘
  │
  └─ config.py (all settings)
```

---

## Testing Checklist

- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Generate JWT secret: `openssl rand -hex 32`
- [ ] Create `.env` file with all required variables
- [ ] Start FastAPI: `uvicorn api.main:app --reload`
- [ ] Test `/health` endpoint (should return 200)
- [ ] Test GitHub OAuth flow (should redirect to github.com)
- [ ] Test invalid token (should return 401)
- [ ] Test rate limiting (hit endpoint 100+ times, should get 429)
- [ ] Test input validation (POST with invalid email, should return 422)
- [ ] Test CORS (from different origin, should have security headers)

---

## Next Steps (Phase 2)

Once Phase 1 is solid, move to **Phase 2: Stripe Integration**

- Create Stripe account & API keys
- Add subscription models to database
- Implement `/api/billing/checkout` endpoint
- Build Stripe webhook listener
- Add subscription gates to portfolio/build endpoints
- Create pricing page on frontend

See plan document for full roadmap.

---

## Troubleshooting

**Issue**: `Missing required environment variables`
- **Fix**: Check `.env` has all required variables. Run `validate_production_settings()` to see which are missing.

**Issue**: `JWT token expired or invalid`
- **Fix**: Access tokens expire after 15 minutes. Use refresh token endpoint (coming in Phase 1.5).

**Issue**: `Rate limit exceeded`
- **Fix**: Free tier allows 100 requests/minute. Wait or upgrade to Pro tier.

**Issue**: `CORS error in browser`
- **Fix**: Make sure `ALLOWED_ORIGINS` in `.env` includes your frontend URL.

**Issue**: `Email validation failed`
- **Fix**: Use valid email format (user@domain.com). EmailStr is strict.

---

## Security Best Practices

✅ **Do:**
- Rotate JWT_SECRET regularly in production
- Use HTTPS in production (REQUIRE_HTTPS=true)
- Store secrets in environment variables, never in code
- Use strong, random webhook secrets
- Log all authentication failures (included by default)
- Review rate limits for your use case

❌ **Don't:**
- Commit `.env` to version control
- Use weak JWT secrets
- Expose error details in production
- Log passwords or tokens
- Run without CORS restrictions in production
- Allow unlimited requests per user

---

## Questions?

Refer to the full implementation plan at the repository root for architecture details, or check the inline documentation in each file.
