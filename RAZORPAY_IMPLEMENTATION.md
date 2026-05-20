# PortfolioAI Razorpay India Implementation Guide

Complete implementation for **₹200/month single-tier SaaS** using Razorpay.

---

## What's Included

### Backend
- ✅ `razorpay_client.py` — Razorpay SDK wrapper
- ✅ `subscription.py` (models) — Updated for Razorpay (no tier field)
- ✅ `002_razorpay_migration.py` — Database migration (Stripe → Razorpay)
- ✅ `.env.example.india` — Complete env vars with your GitHub OAuth + Gemini keys
- 📝 `billing.py` (routes) — See template below
- 📝 Pricing/Checkout frontend — See template below

### Your Credentials (Already Added)
```
GITHUB_CLIENT_ID=Ov23liykkjykXAzGjsmr
GITHUB_CLIENT_SECRET=2400ffad5623a321d98993046a0c4514514c4515
GOOGLE_API_KEY=AIzaSyDTIFGxPHajGfqgWomYUtm6Sk0h_WZ3pWw
RAZORPAY_KEY_ID=rzp_test_SrUrKdxyZyDClk (test)
RAZORPAY_KEY_SECRET=wpPh8hZTz9yZo0hVUfOy8sNe (test)
```

---

## Backend Implementation

### 1. Update `backend/api/main.py`

Add Razorpay client initialization:

```python
from api.integrations.razorpay_client import RazorpayClient

# Initialize Razorpay
razorpay_client = RazorpayClient(
    key_id=settings.razorpay_key_id,
    key_secret=settings.razorpay_key_secret
)

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "razorpay": razorpay_client.is_configured()
    }
```

### 2. Update `backend/api/routes/billing.py`

Replace all Stripe calls with Razorpay. Template:

```python path=null start=null
"""
Razorpay Billing Routes for India (₹200/month)

Endpoints:
- POST /api/billing/start-trial → Create Razorpay customer + trial period
- POST /api/billing/checkout → Create subscription payment link
- POST /api/billing/webhook → Handle Razorpay events
- GET /api/billing/status → Get subscription status
- POST /api/billing/cancel → Cancel subscription
- GET /api/billing/invoices → Get invoice history
"""

from fastapi import APIRouter, HTTPException, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
import logging

from api.database import get_db
from api.auth.security import get_current_user
from api.models.user import User
from api.models.subscription import Subscription, Invoice, SubscriptionStatus
from api.integrations.razorpay_client import RazorpayClient
from api.integrations.sendgrid_client import SendGridClient
from api.config import settings

router = APIRouter(prefix="/api/billing", tags=["billing"])
logger = logging.getLogger(__name__)

razorpay = RazorpayClient(settings.razorpay_key_id, settings.razorpay_key_secret)
email_client = SendGridClient(settings.sendgrid_api_key)


@router.post("/start-trial")
async def start_trial(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """
    Start 14-day free trial for user.
    
    Creates Razorpay customer + subscription with trial period.
    """
    if not razorpay.is_configured():
        raise HTTPException(status_code=500, detail="Payment processing unavailable")
    
    # Check if already has subscription
    existing = await db.execute(
        select(Subscription).filter(Subscription.user_id == user.id)
    )
    if existing.scalar():
        raise HTTPException(status_code=400, detail="User already has subscription")
    
    try:
        # Create Razorpay customer
        customer = razorpay.create_customer(user.id, user.email)
        
        # Calculate trial end (14 days from now)
        trial_end = datetime.utcnow() + timedelta(days=14)
        
        # Create subscription with trial
        subscription = Subscription(
            user_id=user.id,
            razorpay_customer_id=customer.get("id"),
            status=SubscriptionStatus.TRIALING,
            trial_start=datetime.utcnow(),
            trial_end=trial_end,
            billing_email=user.email,
            monthly_price_paise=20000,  # ₹200
            currency="INR"
        )
        
        db.add(subscription)
        await db.commit()
        
        # Send welcome email
        email_client.send_welcome_email(
            email=user.email,
            name=user.github_username,
            trial_days=14
        )
        
        return {
            "status": "trial_started",
            "trial_days": 14,
            "trial_end": trial_end.isoformat(),
            "message": "14-day free trial started. Payment required after trial."
        }
    
    except Exception as e:
        logger.error(f"Failed to start trial: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to start trial")


@router.post("/checkout")
async def create_checkout(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Create Razorpay subscription payment link.
    
    User clicks link to pay ₹200/month subscription.
    """
    if not razorpay.is_configured():
        raise HTTPException(status_code=500, detail="Payment processing unavailable")
    
    try:
        # Get or create subscription
        sub = await db.execute(
            select(Subscription).filter(Subscription.user_id == user.id)
        )
        subscription = sub.scalar()
        
        if not subscription:
            raise HTTPException(status_code=404, detail="No subscription found. Start trial first.")
        
        # Create subscription payment link
        link = razorpay.create_subscription_link(
            customer_id=subscription.razorpay_customer_id,
            email=user.email,
            trial_days=14,
            notes={"user_id": user.id}
        )
        
        return {
            "checkout_url": link,
            "amount_inr": 200,
            "currency": "INR",
            "billing_period": "monthly"
        }
    
    except Exception as e:
        logger.error(f"Failed to create checkout: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create checkout")


@router.post("/webhook")
async def handle_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Handle Razorpay webhook events.
    
    Events:
    - subscription.created → User started trial
    - subscription.activated → Trial ended, first payment succeeded
    - subscription.paid → Monthly payment succeeded
    - subscription.failed → Payment failed
    - subscription.cancelled → User cancelled
    """
    
    # Get signature from headers
    signature = request.headers.get("X-Razorpay-Signature")
    if not signature:
        raise HTTPException(status_code=400, detail="Missing signature")
    
    # Read body
    body = await request.body()
    
    # Verify signature
    if not razorpay.verify_webhook_signature(
        body.decode(),
        signature,
        settings.razorpay_webhook_secret
    ):
        logger.warning("Invalid webhook signature")
        raise HTTPException(status_code=403, detail="Invalid signature")
    
    # Parse event
    import json
    event = json.loads(body)
    
    # Process event
    processed = razorpay.process_webhook_event(event)
    if not processed:
        raise HTTPException(status_code=400, detail="Invalid event")
    
    event_type = processed.get("event_type")
    subscription_id = processed.get("subscription_id")
    customer_id = processed.get("customer_id")
    
    try:
        if event_type == "subscription.activated":
            # Trial ended, payment succeeded
            sub = await db.execute(
                select(Subscription).filter(Subscription.razorpay_subscription_id == subscription_id)
            )
            subscription = sub.scalar()
            
            if subscription:
                subscription.status = SubscriptionStatus.ACTIVE
                subscription.razorpay_subscription_id = subscription_id
                subscription.current_period_start = datetime.utcnow()
                subscription.current_period_end = datetime.utcnow() + timedelta(days=30)
                subscription.last_webhook_at = datetime.utcnow()
                
                # Send payment success email
                user = await db.execute(
                    select(User).filter(User.id == subscription.user_id)
                )
                user_obj = user.scalar()
                if user_obj:
                    email_client.send_payment_success_email(
                        email=user_obj.email,
                        name=user_obj.github_username,
                        amount_inr=200
                    )
        
        elif event_type == "subscription.failed":
            # Payment failed
            sub = await db.execute(
                select(Subscription).filter(Subscription.razorpay_subscription_id == subscription_id)
            )
            subscription = sub.scalar()
            
            if subscription:
                subscription.status = SubscriptionStatus.PAST_DUE
                
                user = await db.execute(
                    select(User).filter(User.id == subscription.user_id)
                )
                user_obj = user.scalar()
                if user_obj:
                    email_client.send_payment_failure_email(
                        email=user_obj.email,
                        name=user_obj.github_username
                    )
        
        elif event_type == "subscription.cancelled":
            # User cancelled
            sub = await db.execute(
                select(Subscription).filter(Subscription.razorpay_subscription_id == subscription_id)
            )
            subscription = sub.scalar()
            
            if subscription:
                subscription.status = SubscriptionStatus.CANCELED
                subscription.canceled_at = datetime.utcnow()
                
                user = await db.execute(
                    select(User).filter(User.id == subscription.user_id)
                )
                user_obj = user.scalar()
                if user_obj:
                    email_client.send_cancellation_email(
                        email=user_obj.email,
                        name=user_obj.github_username
                    )
        
        await db.commit()
    
    except Exception as e:
        logger.error(f"Failed to process webhook: {str(e)}")
        await db.rollback()
    
    return {"received": True}


@router.get("/status")
async def get_subscription_status(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Get current subscription status."""
    
    result = await db.execute(
        select(Subscription).filter(Subscription.user_id == user.id)
    )
    subscription = result.scalar()
    
    if not subscription:
        return {
            "status": "free",
            "message": "No active subscription. Start 14-day trial to unlock unlimited builds."
        }
    
    return {
        "subscription_id": subscription.razorpay_subscription_id,
        "customer_id": subscription.razorpay_customer_id,
        "status": subscription.status.value,
        "trial_start": subscription.trial_start.isoformat() if subscription.trial_start else None,
        "trial_end": subscription.trial_end.isoformat() if subscription.trial_end else None,
        "current_period_start": subscription.current_period_start.isoformat() if subscription.current_period_start else None,
        "current_period_end": subscription.current_period_end.isoformat() if subscription.current_period_end else None,
        "amount_inr": 200,
        "currency": "INR"
    }


@router.post("/cancel")
async def cancel_subscription(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Cancel subscription at end of billing period."""
    
    result = await db.execute(
        select(Subscription).filter(Subscription.user_id == user.id)
    )
    subscription = result.scalar()
    
    if not subscription or not subscription.razorpay_subscription_id:
        raise HTTPException(status_code=404, detail="No active subscription")
    
    try:
        razorpay.cancel_subscription(subscription.razorpay_subscription_id, at_period_end=True)
        subscription.cancel_at = subscription.current_period_end
        await db.commit()
        
        return {
            "status": "cancelled",
            "cancel_at": subscription.current_period_end.isoformat() if subscription.current_period_end else None,
            "message": "Subscription will be cancelled at end of billing period"
        }
    
    except Exception as e:
        logger.error(f"Failed to cancel subscription: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to cancel subscription")


@router.get("/invoices")
async def get_invoices(
    skip: int = 0,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Get invoice history."""
    
    result = await db.execute(
        select(Invoice)
        .filter(Invoice.user_id == user.id)
        .order_by(Invoice.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    invoices = result.scalars().all()
    
    return [
        {
            "id": inv.razorpay_invoice_id,
            "amount_inr": inv.amount_due_paise / 100,
            "currency": "INR",
            "status": inv.status,
            "created_at": inv.created_at.isoformat(),
            "paid_at": inv.paid_at.isoformat() if inv.paid_at else None,
            "hosted_url": inv.hosted_invoice_url
        }
        for inv in invoices
    ]
```

---

## Frontend Implementation

### 1. Update Pricing Page

```tsx path=null start=null
// frontend/src/app/pricing/page.tsx

export default function PricingPage() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-slate-100 py-16">
      <div className="max-w-4xl mx-auto px-6">
        <h1 className="text-4xl font-bold text-center mb-2">Simple, Transparent Pricing</h1>
        <p className="text-center text-slate-600 mb-12">
          One plan. Unlimited portfolios. 14-day free trial.
        </p>

        {/* Single Tier Card */}
        <div className="bg-white rounded-lg shadow-lg p-8 border-2 border-blue-500">
          <div className="text-center">
            <h2 className="text-2xl font-bold mb-2">PortfolioAI Pro</h2>
            <p className="text-slate-600 mb-6">Everything you need to create stunning portfolios</p>
            
            <div className="mb-8">
              <span className="text-5xl font-bold">₹200</span>
              <span className="text-slate-600">/month</span>
            </div>

            <div className="mb-8 p-4 bg-green-50 border border-green-200 rounded-lg">
              <p className="text-green-800 font-semibold">🎉 14-day free trial — no credit card required</p>
            </div>

            <button
              onClick={() => router.push('/trial')}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-6 rounded-lg mb-4"
            >
              Start Free Trial
            </button>

            <p className="text-sm text-slate-500 mb-8">
              After trial, ₹200/month. Cancel anytime.
            </p>

            {/* Features List */}
            <ul className="text-left space-y-3 border-t pt-8">
              <li className="flex items-center">
                <span className="text-green-600 mr-3">✓</span>
                Unlimited AI-generated portfolios
              </li>
              <li className="flex items-center">
                <span className="text-green-600 mr-3">✓</span>
                Instant deployment to custom domains
              </li>
              <li className="flex items-center">
                <span className="text-green-600 mr-3">✓</span>
                Real-time GitHub sync
              </li>
              <li className="flex items-center">
                <span className="text-green-600 mr-3">✓</span>
                Advanced analytics
              </li>
              <li className="flex items-center">
                <span className="text-green-600 mr-3">✓</span>
                Email support
              </li>
              <li className="flex items-center">
                <span className="text-green-600 mr-3">✓</span>
                SEO optimization
              </li>
            </ul>
          </div>
        </div>

        {/* FAQ */}
        <div className="mt-16">
          <h3 className="text-2xl font-bold text-center mb-8">Frequently Asked Questions</h3>
          
          <div className="space-y-4">
            <details className="bg-white p-6 rounded-lg shadow">
              <summary className="font-bold cursor-pointer">Do I need a credit card for the trial?</summary>
              <p className="text-slate-600 mt-2">No! Your 14-day trial is completely free. You'll only be charged after the trial ends.</p>
            </details>
            
            <details className="bg-white p-6 rounded-lg shadow">
              <summary className="font-bold cursor-pointer">Can I cancel anytime?</summary>
              <p className="text-slate-600 mt-2">Yes. Cancel your subscription anytime and your access continues until the end of your billing period.</p>
            </details>
            
            <details className="bg-white p-6 rounded-lg shadow">
              <summary className="font-bold cursor-pointer">What payment methods do you accept?</summary>
              <p className="text-slate-600 mt-2">We accept all major credit/debit cards via Razorpay. UPI coming soon!</p>
            </details>
          </div>
        </div>
      </div>
    </div>
  )
}
```

### 2. Update Checkout Page

```tsx path=null start=null
// frontend/src/app/checkout/page.tsx

'use client'

import { useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import axios from 'axios'

export default function CheckoutPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    initiateCheckout()
  }, [])

  const initiateCheckout = async () => {
    try {
      setLoading(true)
      
      // Call backend to create Razorpay checkout
      const response = await axios.post('/api/billing/checkout', {})
      
      // Redirect to Razorpay payment link
      if (response.data.checkout_url) {
        window.location.href = response.data.checkout_url
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create checkout')
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-slate-50 to-slate-100">
      <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-8">
        {loading && (
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-slate-600">Redirecting to payment...</p>
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 p-4 rounded-lg mb-4">
            {error}
          </div>
        )}

        {!loading && !error && (
          <div>
            <h2 className="text-2xl font-bold mb-4">Subscription Details</h2>
            
            <div className="bg-slate-50 p-4 rounded-lg mb-6">
              <div className="flex justify-between mb-2">
                <span>PortfolioAI Pro</span>
                <span className="font-bold">₹200/month</span>
              </div>
              <div className="text-sm text-slate-600">
                Unlimited AI portfolios, custom domains, GitHub sync
              </div>
            </div>

            <div className="border-t pt-4 mb-6">
              <div className="flex justify-between font-bold text-lg">
                <span>Total</span>
                <span>₹200</span>
              </div>
            </div>

            <button
              onClick={initiateCheckout}
              disabled={loading}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-6 rounded-lg disabled:opacity-50"
            >
              Pay Now with Razorpay
            </button>

            <p className="text-sm text-slate-500 text-center mt-4">
              Secure payment powered by Razorpay
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
```

---

## Database Setup

Run migration to convert from Stripe to Razorpay:

```bash
cd backend
alembic upgrade head
```

This will:
- Rename stripe_* columns to razorpay_*
- Remove tier field (single tier only)
- Update currency to INR
- Remove StripeProduct table

---

## Environment Variables

Copy to `.env`:

```bash
cp .env.example.india .env
```

Update with your actual values:
- `DATABASE_URL` — Your PostgreSQL connection
- `REDIS_URL` — Your Redis connection
- `RAZORPAY_PLAN_ID` — Your Razorpay plan ID for ₹200/month
- `RAZORPAY_WEBHOOK_SECRET` — Your Razorpay webhook secret
- `SENDGRID_API_KEY` — Your SendGrid API key

---

## Testing Locally

```bash
# Start backend
cd backend
uvicorn api.main:app --reload

# Start frontend
cd frontend
npm run dev

# Visit http://localhost:3000/pricing
```

Test flow:
1. Click "Start Free Trial"
2. Authorize GitHub OAuth
3. After 14 days, click "Upgrade to Pro"
4. Redirect to Razorpay payment link (in test mode, no actual charge)
5. Webhook processes subscription.activated

---

## Live Deployment

When ready for production:

1. **Get live Razorpay keys**:
   - Replace `rzp_test_*` with `rzp_live_*` keys

2. **Update environment**:
   ```
   RAZORPAY_KEY_ID=rzp_live_xxxxx
   RAZORPAY_KEY_SECRET=xxxxx
   ENVIRONMENT=production
   REQUIRE_HTTPS=true
   ```

3. **Deploy to Railway/Heroku/AWS** following `DEPLOYMENT.md`

4. **Create Razorpay plan** for ₹200/month:
   - Dashboard → Plans → Create recurring plan

5. **Add webhook** in Razorpay dashboard:
   - `https://api.yourdomain.com/api/billing/webhook`
   - Select subscription events

6. **Test payment** with real card (small amount)

---

## Summary

- ✅ Single tier: **₹200/month**
- ✅ 14-day free trial (no credit card)
- ✅ Unlimited AI portfolios after payment
- ✅ Razorpay payment processor (India)
- ✅ GitHub OAuth for signup
- ✅ Gemini API for portfolio generation
- ✅ Email notifications via SendGrid

Ready to launch! 🚀
