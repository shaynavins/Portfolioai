"""
Billing Routes - Razorpay Integration
Handles checkout, webhooks, subscription management for India
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
import structlog
from pydantic import BaseModel

from api.database import get_db, User
from api.models.subscription import Subscription, SubscriptionStatus
from api.routes.auth import get_current_user
from api.config import settings
from api.integrations.razorpay_client import RazorpayClient

router = APIRouter()
log = structlog.get_logger()

# Initialize Razorpay client
razorpay_client = RazorpayClient(
    settings.RAZORPAY_KEY_ID,
    settings.RAZORPAY_KEY_SECRET
)

# Pricing for plans (in INR)
PLAN_PRICING = {
    "pro": 199,  # ₹199 one-time payment
}


class CheckoutRequest(BaseModel):
    plan: str


class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    plan: str


@router.post("/checkout")
async def create_checkout_session(
    req: CheckoutRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a Razorpay checkout order."""
    try:
        plan = req.plan
        if plan not in PLAN_PRICING:
            raise HTTPException(400, f"Invalid plan: {plan}. Must be 'pro'.")
        
        if not razorpay_client.is_configured():
            raise HTTPException(500, "Payment processing not available")
        
        # Create Razorpay order
        amount_paise = PLAN_PRICING[plan] * 100  # Convert INR to paise
        
        try:
            order = razorpay_client.client.order.create({
                "amount": amount_paise,
                "currency": "INR",
                "receipt": f"user_{user.id}_{int(datetime.utcnow().timestamp())}",
                "notes": {
                    "user_id": user.id,
                    "plan": plan,
                    "email": user.email,
                }
            })
        except Exception as e:
            log.error("razorpay_order_creation_failed", error=str(e))
            raise HTTPException(500, "Failed to create payment order")
        
        log.info(
            "checkout_order_created",
            user_id=user.id,
            plan=plan,
            order_id=order['id'],
            amount=amount_paise
        )
        
        return {
            "order_id": order['id'],
            "amount": order['amount'],
            "currency": order['currency'],
            "key_id": settings.RAZORPAY_KEY_ID,
            "user_email": user.email,
            "user_name": user.name or user.github_username,
            "plan": plan,
            "price_inr": PLAN_PRICING[plan],
        }
    
    except HTTPException:
        raise
    except Exception as e:
        log.error("checkout_error", error=str(e), exc_info=True)
        raise HTTPException(500, f"Failed to create checkout: {str(e)}")


@router.post("/verify-payment")
async def verify_payment(
    req: VerifyPaymentRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Verify payment and create subscription."""
    try:
        if not razorpay_client.is_configured():
            raise HTTPException(500, "Payment processing not available")

        plan = req.plan
        if plan not in PLAN_PRICING:
            raise HTTPException(400, f"Invalid plan: {plan}")
        
        # Verify signature
        try:
            razorpay_client.client.utility.verify_payment_signature({
                'razorpay_order_id': req.razorpay_order_id,
                'razorpay_payment_id': req.razorpay_payment_id,
                'razorpay_signature': req.razorpay_signature
            })
        except Exception as e:
            log.error("payment_signature_verification_failed", error=str(e))
            raise HTTPException(400, "Payment verification failed")
        
        # Fetch payment details
        try:
            payment = razorpay_client.client.payment.fetch(req.razorpay_payment_id)
        except Exception as e:
            log.error("payment_fetch_failed", error=str(e))
            raise HTTPException(400, "Could not verify payment details")
        
        # Check payment status
        if payment['status'] != 'captured':
            raise HTTPException(400, "Payment was not successful")
        
        # Get or create subscription record
        result = await db.execute(
            select(Subscription).where(Subscription.user_id == user.id)
        )
        subscription = result.scalar_one_or_none()
        
        if subscription:
            # Update existing subscription (one-time payment, no expiry)
            subscription.status = SubscriptionStatus.ACTIVE
            subscription.updated_at = datetime.utcnow()
        else:
            # Create new subscription (one-time payment, no expiry)
            subscription = Subscription(
                user_id=user.id,
                status=SubscriptionStatus.ACTIVE,
                razorpay_customer_id=req.razorpay_payment_id,  # Use payment ID as customer ID for one-time payments
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(subscription)
        
        await db.commit()
        await db.refresh(subscription)
        
        log.info(
            "payment_verified_subscription_created",
            user_id=user.id,
            plan=plan,
            payment_id=req.razorpay_payment_id,
            order_id=req.razorpay_order_id
        )
        
        return {
            "status": "success",
            "message": f"Subscription to {plan} plan activated",
            "subscription_id": str(subscription.id),
            "tier": plan,
            "expires_at": None,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        log.error("payment_verification_error", error=str(e), exc_info=True)
        raise HTTPException(500, f"Failed to verify payment: {str(e)}")


@router.get("/subscription")
async def get_subscription(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user's subscription status."""
    result = await db.execute(
        select(Subscription).where(Subscription.user_id == user.id)
    )
    subscription = result.scalar_one_or_none()
    
    if not subscription:
        return {"tier": "free", "status": "active", "expires_at": None}
    
    return {
        "tier": "pro",  # One-time payment plan
        "status": subscription.status.value if subscription.status else "active",
        "expires_at": None,  # No expiry for one-time payment
    }


@router.post("/cancel")
async def cancel_subscription(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel user's subscription."""
    result = await db.execute(
        select(Subscription).where(Subscription.user_id == user.id)
    )
    subscription = result.scalar_one_or_none()
    
    if not subscription:
        raise HTTPException(404, "No active subscription")
    
    subscription.status = SubscriptionStatus.CANCELED
    subscription.cancel_at = datetime.utcnow()
    await db.commit()
    
    return {"success": True}
