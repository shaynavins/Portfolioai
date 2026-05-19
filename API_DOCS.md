# PortfolioAI — API Documentation

Complete API reference for PortfolioAI backend. Base URL: `https://api.portfolioai.app` (or your backend domain).

## Authentication

All endpoints (except `/auth/*` and `/health`) require a **Bearer token** in the `Authorization` header:

```bash
Authorization: Bearer <access_token>
```

Tokens are obtained via GitHub OAuth login and are valid for 15 minutes. Use the refresh token to obtain a new access token when expired.

### Token Structure
- **Access Token**: Expires in 15 minutes (`JWT`)
- **Refresh Token**: Expires in 30 days (`HTTP-only cookie`)
- Both stored in browser on login, automatically refreshed before expiry

---

## Auth Endpoints

### POST /api/auth/github/login

Initiates GitHub OAuth login flow.

**Request**:
```json
{
  "code": "github_authorization_code"
}
```

**Response** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 900
}
```

Refresh token is set as `HttpOnly` cookie: `Set-Cookie: refresh_token=...; HttpOnly; Secure; SameSite=Strict`

**Errors**:
- `400 Bad Request`: Missing code
- `400 Bad Request`: Invalid GitHub code
- `500 Internal Server Error`: GitHub API error

---

### POST /api/auth/refresh

Refresh access token using refresh token cookie.

**Request**:
```
POST /api/auth/refresh
Cookie: refresh_token=<refresh_token>
```

**Response** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 900
}
```

**Errors**:
- `401 Unauthorized`: Missing or invalid refresh token
- `401 Unauthorized`: Token expired

---

### POST /api/auth/logout

Logout user and invalidate refresh token.

**Request**:
```
POST /api/auth/logout
Authorization: Bearer <access_token>
```

**Response** (204 No Content):
```
Set-Cookie: refresh_token=; Max-Age=0; Path=/; HttpOnly; Secure; SameSite=Strict
```

---

### GET /api/auth/me

Get current authenticated user.

**Request**:
```
GET /api/auth/me
Authorization: Bearer <access_token>
```

**Response** (200 OK):
```json
{
  "id": "user_123",
  "github_username": "octocat",
  "email": "octocat@github.com",
  "avatar_url": "https://avatars.githubusercontent.com/u/1?v=4",
  "created_at": "2025-01-15T10:30:00Z",
  "plan": "pro"
}
```

**Errors**:
- `401 Unauthorized`: Invalid or missing token

---

## Portfolio Endpoints

### GET /api/portfolios

List all portfolios for the authenticated user.

**Request**:
```
GET /api/portfolios
Authorization: Bearer <access_token>
```

**Query Parameters**:
- `skip` (int, optional): Number of results to skip (default: 0)
- `limit` (int, optional): Number of results to return (default: 10, max: 100)

**Response** (200 OK):
```json
[
  {
    "id": "portfolio_123",
    "title": "My Portfolio",
    "description": "Portfolio website",
    "github_repo": "octocat/portfolio",
    "framework": "next.js",
    "domain": "portfolio.myapp.io",
    "status": "deployed",
    "created_at": "2025-01-15T10:30:00Z",
    "updated_at": "2025-01-15T10:30:00Z"
  }
]
```

**Errors**:
- `401 Unauthorized`: Invalid token

---

### POST /api/portfolios

Create a new portfolio.

**Request**:
```json
{
  "title": "My Portfolio",
  "description": "My awesome portfolio",
  "github_repo": "username/repo-name",
  "framework": "next.js"
}
```

**Response** (201 Created):
```json
{
  "id": "portfolio_123",
  "title": "My Portfolio",
  "description": "My awesome portfolio",
  "github_repo": "username/repo-name",
  "framework": "next.js",
  "domain": "portfolio_123.myapp.io",
  "status": "pending",
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:00Z"
}
```

**Validation**:
- `title`: Required, 1-255 characters
- `description`: Optional, max 1000 characters
- `github_repo`: Required, format: `username/repo`
- `framework`: Required, one of: `next.js`, `react`, `vue`, `svelte`, `static`

**Errors**:
- `400 Bad Request`: Validation failed
- `401 Unauthorized`: Invalid token
- `429 Too Many Requests`: Build limit exceeded

---

### GET /api/portfolios/{portfolio_id}

Get a specific portfolio.

**Request**:
```
GET /api/portfolios/portfolio_123
Authorization: Bearer <access_token>
```

**Response** (200 OK):
```json
{
  "id": "portfolio_123",
  "title": "My Portfolio",
  "description": "My awesome portfolio",
  "github_repo": "username/repo-name",
  "framework": "next.js",
  "domain": "portfolio_123.myapp.io",
  "status": "deployed",
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:00Z"
}
```

**Errors**:
- `404 Not Found`: Portfolio not found
- `401 Unauthorized`: Not authorized to view this portfolio

---

### PUT /api/portfolios/{portfolio_id}

Update a portfolio.

**Request**:
```json
{
  "title": "Updated Portfolio",
  "description": "Updated description",
  "framework": "react"
}
```

**Response** (200 OK):
```json
{
  "id": "portfolio_123",
  "title": "Updated Portfolio",
  "description": "Updated description",
  "framework": "react",
  "domain": "portfolio_123.myapp.io",
  "status": "deployed",
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T11:45:00Z"
}
```

**Errors**:
- `404 Not Found`: Portfolio not found
- `401 Unauthorized`: Not authorized
- `400 Bad Request`: Validation failed

---

### DELETE /api/portfolios/{portfolio_id}

Delete a portfolio.

**Request**:
```
DELETE /api/portfolios/portfolio_123
Authorization: Bearer <access_token>
```

**Response** (204 No Content):
```
(empty body)
```

**Errors**:
- `404 Not Found`: Portfolio not found
- `401 Unauthorized`: Not authorized

---

### POST /api/portfolios/{portfolio_id}/build

Trigger a build for a portfolio.

**Request**:
```
POST /api/portfolios/portfolio_123/build
Authorization: Bearer <access_token>
```

**Response** (202 Accepted):
```json
{
  "build_id": "build_456",
  "status": "queued",
  "portfolio_id": "portfolio_123",
  "created_at": "2025-01-15T10:30:00Z"
}
```

**Errors**:
- `404 Not Found`: Portfolio not found
- `401 Unauthorized`: Not authorized
- `429 Too Many Requests`: Build limit exceeded for your plan
  ```json
  {
    "error": "Build limit exceeded",
    "limit": 3,
    "current": 3,
    "plan": "free",
    "reset_date": "2025-02-15"
  }
  ```

---

### GET /api/portfolios/{portfolio_id}/builds

Get build history for a portfolio.

**Request**:
```
GET /api/portfolios/portfolio_123/builds?limit=10
Authorization: Bearer <access_token>
```

**Query Parameters**:
- `skip` (int, optional): Skip results (default: 0)
- `limit` (int, optional): Results per page (default: 10, max: 100)
- `status` (string, optional): Filter by status: `queued`, `running`, `completed`, `failed`

**Response** (200 OK):
```json
[
  {
    "id": "build_456",
    "portfolio_id": "portfolio_123",
    "status": "completed",
    "output_url": "https://s3.myapp.io/builds/build_456/index.html",
    "duration_seconds": 45,
    "error_message": null,
    "created_at": "2025-01-15T10:30:00Z",
    "completed_at": "2025-01-15T10:31:00Z"
  }
]
```

---

## Billing Endpoints

### POST /api/billing/checkout

Create a Stripe checkout session.

**Request**:
```json
{
  "price_id": "price_1234567890",
  "success_url": "https://app.portfolioai.app/dashboard?session_id={CHECKOUT_SESSION_ID}",
  "cancel_url": "https://app.portfolioai.app/pricing"
}
```

**Response** (200 OK):
```json
{
  "checkout_url": "https://checkout.stripe.com/pay/cs_test_123456789...",
  "session_id": "cs_test_123456789"
}
```

**Errors**:
- `400 Bad Request`: Invalid price_id
- `401 Unauthorized`: Not authenticated

---

### POST /api/billing/webhook

Stripe webhook endpoint. **Do not call directly** — Stripe calls this.

**Events Processed**:
- `customer.subscription.created`: Create subscription record
- `customer.subscription.updated`: Update subscription status/tier
- `customer.subscription.deleted`: Mark subscription as cancelled
- `invoice.payment_succeeded`: Create invoice record, send email
- `invoice.payment_failed`: Send payment failure email
- `charge.dispute.created`: Log dispute

**Request** (from Stripe):
```bash
POST /api/billing/webhook
Content-Type: application/json
Stripe-Signature: t=1614556731,v1=abcd1234...

{
  "id": "evt_123...",
  "object": "event",
  "type": "customer.subscription.created",
  "data": {
    "object": {
      "id": "sub_123...",
      "customer": "cus_123...",
      "items": {
        "data": [
          {
            "price": {
              "id": "price_pro"
            }
          }
        ]
      }
    }
  }
}
```

**Response** (200 OK):
```json
{
  "received": true
}
```

**Errors**:
- `400 Bad Request`: Invalid payload
- `403 Forbidden`: Invalid signature (webhook secret mismatch)

---

### GET /api/billing/status

Get current subscription status.

**Request**:
```
GET /api/billing/status
Authorization: Bearer <access_token>
```

**Response** (200 OK):
```json
{
  "subscription_id": "sub_123...",
  "customer_id": "cus_123...",
  "status": "active",
  "tier": "pro",
  "current_period_start": "2025-01-15T10:30:00Z",
  "current_period_end": "2025-02-15T10:30:00Z",
  "cancel_at_period_end": false,
  "amount_cents": 900,
  "currency": "usd"
}
```

Or, if no subscription (Free tier):
```json
{
  "subscription_id": null,
  "status": "free",
  "tier": "free",
  "build_limit": 3,
  "builds_this_month": 1,
  "remaining": 2
}
```

**Errors**:
- `401 Unauthorized`: Not authenticated

---

### POST /api/billing/cancel

Cancel active subscription at end of period.

**Request**:
```json
{
  "at_period_end": true
}
```

**Response** (200 OK):
```json
{
  "subscription_id": "sub_123...",
  "status": "active",
  "cancel_at_period_end": true,
  "current_period_end": "2025-02-15T10:30:00Z",
  "message": "Subscription will be cancelled at the end of your billing period"
}
```

**Errors**:
- `404 Not Found`: No active subscription
- `401 Unauthorized`: Not authenticated

---

### GET /api/billing/invoices

Get invoice history.

**Request**:
```
GET /api/billing/invoices?limit=10
Authorization: Bearer <access_token>
```

**Query Parameters**:
- `skip` (int, optional): Skip results (default: 0)
- `limit` (int, optional): Results per page (default: 10, max: 100)

**Response** (200 OK):
```json
[
  {
    "id": "in_123...",
    "invoice_number": "INV-2025-001",
    "amount_cents": 900,
    "currency": "usd",
    "status": "paid",
    "created_at": "2025-01-15T10:30:00Z",
    "paid_at": "2025-01-15T10:31:00Z",
    "hosted_invoice_url": "https://invoice.stripe.com/i/acct_123.../inv_456..."
  }
]
```

**Errors**:
- `401 Unauthorized`: Not authenticated

---

### GET /api/billing/usage

Get build usage and quota information.

**Request**:
```
GET /api/billing/usage
Authorization: Bearer <access_token>
```

**Response** (200 OK):
```json
{
  "period_start": "2025-01-01T00:00:00Z",
  "period_end": "2025-01-31T23:59:59Z",
  "tier": "pro",
  "limit": 50,
  "used": 12,
  "remaining": 38,
  "percentage_used": 24
}
```

**Errors**:
- `401 Unauthorized`: Not authenticated

---

## Health Check

### GET /health

Check API health (no authentication required).

**Request**:
```
GET /health
```

**Response** (200 OK):
```json
{
  "status": "healthy",
  "timestamp": "2025-01-15T10:30:00Z",
  "version": "1.0.0"
}
```

---

## Error Responses

All error responses follow this format:

```json
{
  "error": "Error message",
  "status_code": 400,
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### Common Status Codes

| Code | Meaning |
|------|---------|
| 200 | OK — Request successful |
| 201 | Created — Resource created |
| 204 | No Content — Successful deletion |
| 400 | Bad Request — Invalid input |
| 401 | Unauthorized — Missing or invalid token |
| 403 | Forbidden — Insufficient permissions |
| 404 | Not Found — Resource doesn't exist |
| 429 | Too Many Requests — Rate limited or build limit exceeded |
| 500 | Internal Server Error — Server error |

---

## Rate Limiting

Rate limits are enforced per user:
- **Auth endpoints**: 5 requests per minute
- **Other endpoints**: 100 requests per minute
- **Build endpoint**: 10 requests per hour

Exceeding limits returns `429 Too Many Requests`:
```json
{
  "error": "Rate limit exceeded",
  "retry_after": 60
}
```

---

## Examples

### Example 1: Complete Signup → Build → Upgrade Flow

1. **Login with GitHub**:
   ```bash
   curl -X POST https://api.portfolioai.app/api/auth/github/login \
     -H "Content-Type: application/json" \
     -d '{"code":"github_code_from_oauth"}'
   ```
   Response: `access_token` + `refresh_token` (cookie)

2. **Create Portfolio**:
   ```bash
   curl -X POST https://api.portfolioai.app/api/portfolios \
     -H "Authorization: Bearer <access_token>" \
     -H "Content-Type: application/json" \
     -d '{
       "title": "My Portfolio",
       "github_repo": "username/repo",
       "framework": "next.js"
     }'
   ```
   Response: `portfolio_123` with status `pending`

3. **Trigger Build**:
   ```bash
   curl -X POST https://api.portfolioai.app/api/portfolios/portfolio_123/build \
     -H "Authorization: Bearer <access_token>"
   ```
   Response: `build_456` with status `queued`

4. **Check Build Status**:
   ```bash
   curl https://api.portfolioai.app/api/portfolios/portfolio_123/builds \
     -H "Authorization: Bearer <access_token>"
   ```

5. **Upgrade to Pro**:
   ```bash
   curl -X POST https://api.portfolioai.app/api/billing/checkout \
     -H "Authorization: Bearer <access_token>" \
     -H "Content-Type: application/json" \
     -d '{
       "price_id": "price_pro",
       "success_url": "https://app.portfolioai.app/dashboard",
       "cancel_url": "https://app.portfolioai.app/pricing"
     }'
   ```
   Response: `checkout_url` (user clicks to pay on Stripe)

6. **Check Subscription**:
   ```bash
   curl https://api.portfolioai.app/api/billing/status \
     -H "Authorization: Bearer <access_token>"
   ```
   Response: Subscription now active with tier `pro`

---

## SDK / Client Libraries

Coming soon: JavaScript/TypeScript client SDK for easier integration.

For now, use standard HTTP clients (fetch, axios, etc.) with the endpoints above.

---

## Support

For issues or questions about the API:
- Email: support@portfolioai.app
- GitHub Issues: https://github.com/yourusername/portfolioai/issues
- Docs: https://docs.portfolioai.app
