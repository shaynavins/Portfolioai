# Phase 2 — Stripe Integration

## Overview
Phase 2 adds Stripe payments, subscription management, and billing to PortfolioAI. Users can now upgrade from Free → Pro ($9/mo) or Team ($29/mo) tiers with automatic billing and webhook-driven subscription management.

## What's New (Phase 2)

### 1. Stripe Database Models
- **Subscription** — Tracks Stripe subscription per user (1:1 relationship)
- **Invoice** — Payment history and invoice records
- **PaymentMethod** — Stored card details (masked, safe)
- **WebhookLog** — Audit trail of all Stripe webhook events
- **StripeProduct** — Mirror of Stripe products/prices for local reference

### 2. Stripe API Client
- Wrapper around `stripe-python` SDK
- Methods: create_customer, create_checkout_session, cancel_subscription, verify_webhook_signature, etc.
- Proper error handling & logging
- No secrets hardcoded

### 3. Billing Routes
- **`POST /api/billing/checkout`** — Create Stripe checkout session for upgrade
- **`POST /api/billing/webhook`** — Receives & processes Stripe webhook events
- Event handlers for: subscription created/updated/deleted, invoice succeeded/failed, chargeback disputes

### 4. Webhook Event Handlers
- Automatic subscription status sync from Stripe
- Invoice tracking & payment record keeping
- Subscription cancellation handling
- Chargeback dispute detection

---

## Setup Instructions

### Step 1: Create Stripe Account
1. Sign up at https://stripe.com
2. Complete identity verification
3. Get API keys from https://dashboard.stripe.com/apikeys
   - Copy **Secret Key** (starts with `sk_test_` or `sk_live_`)
   - Copy **Publishable Key** (starts with `pk_test_` or `pk_live_`)

### Step 2: Create Products & Prices
In Stripe Dashboard:

1. Go to **Products** → **Create Product**
   - Name: "Pro Plan"
   - Price: $9.00 USD / month (recurring)
   - Copy the **Price ID** (starts with `price_`)
   
2. Create another product:
   - Name: "Team Plan"
   - Price: $29.00 USD / month (recurring)
   - Copy the **Price ID**

### Step 3: Set Webhook Endpoint
1. Go to **Developers** → **Webhooks**
2. Click **Add endpoint**
3. Enter URL: `https://api.portfolioai.app/api/billing/webhook`
   - For local testing: `http://localhost:8000/api/billing/webhook`
4. Select events: 
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
   - `charge.dispute.created`
5. Copy the **Signing Secret** (starts with `whsec_`)

### Step 4: Update .env
```env
# Stripe Keys
STRIPE_SECRET_KEY=sk_test_xxxxx
STRIPE_PUBLISHABLE_KEY=pk_test_xxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxx
STRIPE_PRODUCT_ID_PRO=price_xxxxx
STRIPE_PRODUCT_ID_TEAM=price_xxxxx
```

### Step 5: Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

New dependencies:
- `stripe==9.8.1`

### Step 6: Test Locally

#### 6a. Start the backend
```bash
uvicorn api.main:app --reload --port 8000
```

#### 6b. Test checkout endpoint
```bash
curl -X POST http://localhost:8000/api/billing/checkout \
  -H "Authorization: Bearer <your_token>" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "tier=pro"
```

Expected response:
```json
{
  "session_id": "cs_test_xxxxx",
  "checkout_url": "https://checkout.stripe.com/c/..."
}
```

#### 6c. Test webhook locally
Use Stripe CLI to forward webhooks to local server:

```bash
# Install Stripe CLI: https://stripe.com/docs/stripe-cli
stripe login
stripe listen --forward-to localhost:8000/api/billing/webhook
```

Then trigger a test event:
```bash
stripe trigger customer.subscription.created
```

### Step 7: Verify Database
Check that subscription records are being created:

```bash
# Connect to database
psql postgresql://user:password@localhost/portfolioai

# Check subscriptions table
SELECT * FROM subscriptions;
SELECT * FROM webhook_logs;
```

---

## Architecture

```
User                Stripe            PortfolioAI Backend
 │                   │                        │
 ├─ Clicks upgrade ──┤                        │
 │                   │                        │
 ├─────────────────────────────────────────>  POST /api/billing/checkout
 │                   │                        │
 │                   │<─────────────────────  create_checkout_session()
 │                   │                        │
 │<────────────────────────────────────────── {session_url}
 │                   │
 │─────────────────>  │ (opens checkout)
 │                   │
 │                   ├─ Enters card ─────────┤
 │                   │ ─────────────>         │
 │                   │                        │
 │<───────────────────────────────────────────┤ Success page
 │                   │                        │
 │                   ├─ Creates subscription ┤
 │                   │                        │
 │                   ├─ Webhook event ──────> POST /api/billing/webhook
 │                   │                        │
 │                   │                        ├─ Verify signature
 │                   │                        ├─ Create Subscription record
 │                   │                        ├─ Update user.plan = "pro"
 │                   │                        │
 │                   │<─ 200 OK ─────────────┤
 │                   │
 │                   ├─ Monthly invoice ────> webhook
 │                   │ (auto-charges card)   │
```

---

## File Structure

```
backend/api/
├── models/
│   └── subscription.py          (NEW) Subscription models
├── integrations/
│   └── stripe_client.py         (NEW) Stripe API wrapper
├── routes/
│   └── billing.py               (NEW) Checkout & webhook routes
├── database.py                  (MODIFIED) Added subscription relationship
├── main.py                      (MODIFIED) Added billing router
└── requirements.txt             (MODIFIED) Added stripe library
```

---

## Testing Checklist

- [ ] Stripe account created & verified
- [ ] Products created (Pro & Team)
- [ ] API keys copied to .env
- [ ] Webhook endpoint configured
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Backend starts (`uvicorn api.main:app --reload`)
- [ ] Database initialized (new subscription tables created)
- [ ] Checkout endpoint returns valid Stripe session URL
- [ ] Can visit checkout URL in browser
- [ ] Webhook events are logged in database
- [ ] Subscription status is created/updated via webhook

---

## Key Endpoints

### POST /api/billing/checkout
Create a checkout session for upgrade.

Request:
```bash
curl -X POST http://localhost:8000/api/billing/checkout?tier=pro \
  -H "Authorization: Bearer <token>"
```

Response:
```json
{
  "session_id": "cs_test_xxxxx",
  "checkout_url": "https://checkout.stripe.com/c/..."
}
```

### POST /api/billing/webhook (Internal)
Stripe sends events here. Signature verified automatically.

---

## Common Issues

**Issue**: `StripeError: Invalid API Key`
- **Fix**: Check STRIPE_SECRET_KEY in .env is correct (starts with `sk_test_` or `sk_live_`)

**Issue**: Webhook signature verification fails
- **Fix**: Ensure STRIPE_WEBHOOK_SECRET matches the endpoint's signing secret exactly

**Issue**: Subscription not created after checkout
- **Fix**: Check webhook logs in database. Ensure webhook endpoint is registered and receiving events. Use Stripe CLI to test locally.

**Issue**: `ModuleNotFoundError: stripe`
- **Fix**: Install dependencies: `pip install -r requirements.txt`

---

## Security Best Practices

✅ **Do:**
- Never commit Stripe keys to git (use .env)
- Always verify webhook signatures
- Use test mode (sk_test_) for development
- Rotate keys regularly in production
- Log webhook events for audit trail
- Handle webhook idempotency (check event ID exists)

❌ **Don't:**
- Store full credit card numbers (Stripe handles this)
- Log payment details or card numbers
- Hardcode API keys in code
- Skip webhook signature verification
- Assume all Stripe events are valid without verification

---

## Next Steps (Phase 3)

After Phase 2 is working:

1. **Email Integration** (SendGrid)
   - Welcome email after signup
   - Invoice confirmation emails
   - Subscription renewal reminders
   - Failed payment alerts

2. **User Webhooks**
   - Allow users to configure their own webhooks
   - Trigger on: portfolio built, subscription changed, payment failed

3. **Billing Dashboard**
   - Invoice history
   - Payment method management
   - Subscription upgrade/downgrade
   - Billing address management

See full plan document for complete roadmap.

---

## Questions?

- Stripe API docs: https://stripe.com/docs/api
- Stripe Python SDK: https://github.com/stripe/stripe-python
- Webhook testing: https://stripe.com/docs/webhooks/test
