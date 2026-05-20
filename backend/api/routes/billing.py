"""
Billing Routes - Razorpay Integration
Handles checkout, webhooks, subscription management for India
"""
from fastapi import APIRouter, HTTPException, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from datetime import datetime
from jose import jwt

from api.database import get_db, User
from api.config import settings
from api.models.subscription import Subscription, SubscriptionStatus

router = APIRouter()


async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and verify user from auth header."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Not authenticated")
    
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        user_id = payload["sub"]
    except Exception:
        raise HTTPException(401, "Invalid token")
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")
    
    return user


@router.post("/checkout")
async def create_checkout_session(
    tier: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a Razorpay checkout session."""
    if tier not in ["pro"]:
        raise HTTPException(400, "Invalid tier. Must be 'pro'.")
    
    # Get or create subscription
    result = await db.execute(
        select(Subscription).where(Subscription.user_id == user.id)
    )
    subscription = result.scalar_one_or_none()
    
    if not subscription:
        subscription = Subscription(
            user_id=user.id,
            razorpay_customer_id=f"cust_{user.id}",
            status=SubscriptionStatus.TRIALING,
        )
        db.add(subscription)
        await db.commit()
    
    return {"checkout_url": "https://rzp.io/l/portfolioai"}


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
        return {"tier": "free", "status": "active", "renewal_date": None}
    
    return {
        "tier": "pro",
        "status": subscription.status.value if subscription.status else "active",
        "renewal_date": subscription.current_period_end.isoformat() if subscription.current_period_end else None,
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
