"""
Billing Routes - Stripe Integration
Handles checkout, webhooks, subscription management
"""
from fastapi import APIRouter, HTTPException, Depends, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import json
import structlog
from datetime import datetime

from api.database import get_db, User
from api.config import settings
from api.integrations.stripe_client import StripeClient
from api.integrations.sendgrid_client import (
    send_subscription_welcome_email,
    send_payment_success_email,
    send_payment_failure_email,
    send_subscription_canceled_email,
)
from api.models.subscription import (
    Subscription, SubscriptionStatus, Invoice, WebhookLog, StripeProduct
)
from api.validation import TokenResponse

router = APIRouter()
log = structlog.get_logger()


async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and verify user from auth header."""
    from api.auth.tokens import verify_access_token
    from jose import JWTError
    
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Not authenticated")
    
    token = authorization.split(" ")[1]
    try:
        payload = verify_access_token(token)
        user_id = payload["sub"]
    except JWTError:
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
    """
    Create a Stripe checkout session for subscription upgrade.
    
    Args:
        tier: "pro" or "team"
    
    Returns:
        {session_id, checkout_url}
    """
    if tier not in ["pro", "team"]:
        raise HTTPException(400, "Invalid tier. Must be 'pro' or 'team'.")
    
    if tier == "pro" and not settings.STRIPE_PRODUCT_ID_PRO:
        raise HTTPException(500, "Pro plan not configured")
    if tier == "team" and not settings.STRIPE_PRODUCT_ID_TEAM:
        raise HTTPException(500, "Team plan not configured")
    
    # Get or create Stripe customer
    subscription = await db.execute(
        select(Subscription).where(Subscription.user_id == user.id)
    )
    sub = subscription.scalar_one_or_none()
    
    if sub and sub.stripe_customer_id:
        stripe_customer_id = sub.stripe_customer_id
    else:
        # Create new customer
        try:
            stripe_customer = StripeClient.create_customer(
                user_id=user.id,
                email=user.email,
                name=user.name,
            )
            stripe_customer_id = stripe_customer.id
            
            # Create/update subscription record
            if not sub:
                sub = Subscription(
                    user_id=user.id,
                    stripe_customer_id=stripe_customer_id,
                    tier="free",
                    status=SubscriptionStatus.INCOMPLETE,
                )
                db.add(sub)
            else:
                sub.stripe_customer_id = stripe_customer_id
            
            await db.commit()
        except Exception as e:
            log.error("Failed to create Stripe customer", user_id=user.id, error=str(e))
            raise HTTPException(500, "Failed to create checkout session")
    
    # Get the price ID for the tier
    if tier == "pro":
        # For MVP, we'll use a hardcoded price ID or fetch from Stripe
        # In production, fetch from stripe_products table
        price_id = settings.STRIPE_PRODUCT_ID_PRO
    else:
        price_id = settings.STRIPE_PRODUCT_ID_TEAM
    
    try:
        # Create checkout session
        session = StripeClient.create_checkout_session(
            stripe_customer_id=stripe_customer_id,
            stripe_price_id=price_id,
            success_url=f"{settings.APP_URL}/dashboard?session={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.APP_URL}/pricing",
        )
        
        return {
            "session_id": session.id,
            "checkout_url": session.url,
        }
    except Exception as e:
        log.error("Failed to create checkout session", user_id=user.id, error=str(e))
        raise HTTPException(500, "Failed to create checkout session")


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Handle Stripe webhook events.
    Signature verification, idempotency, and event processing.
    """
    # Get webhook signature
    sig_header = request.headers.get("stripe-signature")
    if not sig_header:
        raise HTTPException(400, "Missing stripe-signature header")
    
    # Get raw body
    body = await request.body()
    
    # Verify signature
    try:
        event = StripeClient.verify_webhook_signature(body, sig_header)
    except (ValueError, Exception) as e:
        log.warning("Webhook signature verification failed", error=str(e))
        raise HTTPException(400, "Invalid signature")
    
    event_id = event.get("id")
    event_type = event.get("type")
    
    log.info("Stripe webhook received", event_id=event_id, event_type=event_type)
    
    # Log webhook for idempotency
    existing_log = await db.execute(
        select(WebhookLog).where(WebhookLog.stripe_event_id == event_id)
    )
    if existing_log.scalar_one_or_none():
        log.info("Webhook already processed", event_id=event_id)
        return {"success": True}
    
    webhook_log = WebhookLog(
        stripe_event_id=event_id,
        event_type=event_type,
        event_data=event,
        received_at=datetime.utcnow(),
    )
    db.add(webhook_log)
    
    try:
        # Handle different event types
        if event_type == "customer.subscription.created":
            await handle_subscription_created(event, db)
        elif event_type == "customer.subscription.updated":
            await handle_subscription_updated(event, db)
        elif event_type == "customer.subscription.deleted":
            await handle_subscription_deleted(event, db)
        elif event_type == "invoice.payment_succeeded":
            await handle_invoice_payment_succeeded(event, db)
        elif event_type == "invoice.payment_failed":
            await handle_invoice_payment_failed(event, db)
        elif event_type == "charge.dispute.created":
            await handle_charge_dispute(event, db)
        else:
            log.info("Unhandled webhook event", event_type=event_type)
        
        webhook_log.processed = True
        webhook_log.processed_at = datetime.utcnow()
    except Exception as e:
        log.error("Failed to process webhook", event_id=event_id, error=str(e))
        webhook_log.error = str(e)
    
    await db.commit()
    return {"success": True}


async def handle_subscription_created(event: dict, db: AsyncSession):
    """Handle customer.subscription.created event."""
    subscription_data = event["data"]["object"]
    stripe_customer_id = subscription_data["customer"]
    stripe_subscription_id = subscription_data["id"]
    
    # Get or create subscription record
    sub = await db.execute(
        select(Subscription).where(Subscription.stripe_customer_id == stripe_customer_id)
    )
    subscription = sub.scalar_one_or_none()
    
    # Determine tier from product
    tier = "pro"  # Default; in production, map from product metadata
    price = subscription_data["items"]["data"][0]["price"]
    
    if not subscription:
        # Get user by stripe customer ID (from metadata)
        from api.integrations.stripe_client import stripe
        customer = stripe.Customer.retrieve(stripe_customer_id)
        user_id = customer.metadata.get("user_id")
        
        if not user_id:
            log.warning("No user_id in customer metadata", stripe_customer_id=stripe_customer_id)
            return
        
        subscription = Subscription(
            user_id=user_id,
            stripe_customer_id=stripe_customer_id,
            stripe_subscription_id=stripe_subscription_id,
            stripe_price_id=price.id,
            tier=tier,
            status=SubscriptionStatus.ACTIVE if subscription_data["status"] == "active" else SubscriptionStatus.INCOMPLETE,
            current_period_start=datetime.fromtimestamp(subscription_data["current_period_start"]),
            current_period_end=datetime.fromtimestamp(subscription_data["current_period_end"]),
        )
        db.add(subscription)
    else:
        subscription.stripe_subscription_id = stripe_subscription_id
        subscription.tier = tier
        subscription.status = SubscriptionStatus.ACTIVE if subscription_data["status"] == "active" else SubscriptionStatus.INCOMPLETE
    
    await db.commit()
    log.info("Subscription created", stripe_subscription_id=stripe_subscription_id, tier=tier)
    
    # Send welcome email
    if subscription and subscription.user_id:
        user_result = await db.execute(select(User).where(User.id == subscription.user_id))
        user = user_result.scalar_one_or_none()
        if user:
            # Get price from Stripe subscription
            try:
                price_amount = subscription_data["items"]["data"][0]["price"]["unit_amount"] / 100
                send_subscription_welcome_email(
                    user_email=user.email,
                    user_name=user.name or user.github_username,
                    plan=tier,
                    amount=price_amount,
                )
            except Exception as e:
                log.error("Failed to send welcome email", user_id=user.id, error=str(e))


async def handle_subscription_updated(event: dict, db: AsyncSession):
    """Handle customer.subscription.updated event."""
    subscription_data = event["data"]["object"]
    stripe_subscription_id = subscription_data["id"]
    
    sub = await db.execute(
        select(Subscription).where(Subscription.stripe_subscription_id == stripe_subscription_id)
    )
    subscription = sub.scalar_one_or_none()
    
    if subscription:
        subscription.status = SubscriptionStatus(subscription_data["status"])
        subscription.current_period_start = datetime.fromtimestamp(subscription_data["current_period_start"])
        subscription.current_period_end = datetime.fromtimestamp(subscription_data["current_period_end"])
        subscription.last_webhook_at = datetime.utcnow()
        
        await db.commit()
        log.info("Subscription updated", stripe_subscription_id=stripe_subscription_id)


async def handle_subscription_deleted(event: dict, db: AsyncSession):
    """Handle customer.subscription.deleted event."""
    subscription_data = event["data"]["object"]
    stripe_subscription_id = subscription_data["id"]
    
    sub = await db.execute(
        select(Subscription).where(Subscription.stripe_subscription_id == stripe_subscription_id)
    )
    subscription = sub.scalar_one_or_none()
    
    if subscription:
        subscription.status = SubscriptionStatus.CANCELED
        subscription.canceled_at = datetime.utcnow()
        subscription.tier = "free"
        
    await db.commit()
    log.info("Subscription deleted", stripe_subscription_id=stripe_subscription_id)
    
    # Send cancellation email
    if subscription:
        user_result = await db.execute(select(User).where(User.id == subscription.user_id))
        user = user_result.scalar_one_or_none()
        if user:
            send_subscription_canceled_email(
                user_email=user.email,
                user_name=user.name or user.github_username,
            )


async def handle_invoice_payment_succeeded(event: dict, db: AsyncSession):
    """Handle invoice.payment_succeeded event."""
    invoice_data = event["data"]["object"]
    stripe_invoice_id = invoice_data["id"]
    
    # Create/update invoice record
    inv = await db.execute(
        select(Invoice).where(Invoice.stripe_invoice_id == stripe_invoice_id)
    )
    invoice = inv.scalar_one_or_none()
    
    if not invoice:
        stripe_customer_id = invoice_data["customer"]
        
        # Get user from subscription
        sub = await db.execute(
            select(Subscription).where(Subscription.stripe_customer_id == stripe_customer_id)
        )
        subscription = sub.scalar_one_or_none()
        
        if subscription:
            invoice = Invoice(
                user_id=subscription.user_id,
                subscription_id=subscription.id,
                stripe_invoice_id=stripe_invoice_id,
                stripe_customer_id=stripe_customer_id,
                amount_due_cents=invoice_data["amount_due"],
                amount_paid_cents=invoice_data["amount_paid"],
                amount_remaining_cents=invoice_data["amount_remaining"],
                status=invoice_data["status"],
                paid=invoice_data["paid"],
                paid_at=datetime.utcnow(),
            )
            db.add(invoice)
    else:
        invoice.status = invoice_data["status"]
        invoice.paid = True
        invoice.paid_at = datetime.utcnow()
    
    await db.commit()
    log.info("Invoice payment succeeded", stripe_invoice_id=stripe_invoice_id)
    
    # Send payment success email
    if invoice and invoice.user_id:
        user_result = await db.execute(select(User).where(User.id == invoice.user_id))
        user = user_result.scalar_one_or_none()
        if user and subscription:
            amount = invoice_data["amount_paid"] / 100
            next_billing = subscription.current_period_end.strftime("%B %d, %Y") if subscription.current_period_end else "TBA"
            send_payment_success_email(
                user_email=user.email,
                user_name=user.name or user.github_username,
                amount=amount,
                next_billing_date=next_billing,
            )


async def handle_invoice_payment_failed(event: dict, db: AsyncSession):
    """Handle invoice.payment_failed event."""
    invoice_data = event["data"]["object"]
    stripe_invoice_id = invoice_data["id"]
    
    inv = await db.execute(
        select(Invoice).where(Invoice.stripe_invoice_id == stripe_invoice_id)
    )
    invoice = inv.scalar_one_or_none()
    
    if invoice:
        invoice.status = "open"
        invoice.attempted = True
        
        await db.commit()
        log.warning("Invoice payment failed", stripe_invoice_id=stripe_invoice_id)
        
        # Send payment failure email
        if invoice.user_id:
            user_result = await db.execute(select(User).where(User.id == invoice.user_id))
            user = user_result.scalar_one_or_none()
            if user:
                send_payment_failure_email(
                    user_email=user.email,
                    user_name=user.name or user.github_username,
                )


async def handle_charge_dispute(event: dict, db: AsyncSession):
    """Handle charge.dispute.created event (chargeback)."""
    dispute_data = event["data"]["object"]
    log.warning("Chargeback disputed", charge_id=dispute_data.get("charge"), amount=dispute_data.get("amount"))
    # TODO: Suspend subscription, notify user


@router.get("/subscription")
async def get_subscription_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get user's current subscription status.
    Returns tier, status, renewal date, and next invoice.
    """
    result = await db.execute(
        select(Subscription).where(Subscription.user_id == user.id)
    )
    subscription = result.scalar_one_or_none()
    
    if not subscription:
        # User has no subscription (free tier)
        return {
            "tier": "free",
            "status": None,
            "renewal_date": None,
            "next_invoice_date": None,
        }
    
    return {
        "tier": subscription.tier,
        "status": subscription.status.value if subscription.status else None,
        "renewal_date": subscription.current_period_end.isoformat() if subscription.current_period_end else None,
        "next_invoice_date": subscription.current_period_end.isoformat() if subscription.current_period_end else None,
        "cancel_at_period_end": subscription.cancel_at is not None,
    }


@router.post("/cancel")
async def cancel_subscription(
    at_period_end: bool = True,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Cancel user's subscription.
    
    Args:
        at_period_end: If True, cancel at end of billing period. If False, cancel immediately.
    
    Returns:
        {success, message, tier_after_cancel}
    """
    result = await db.execute(
        select(Subscription).where(Subscription.user_id == user.id)
    )
    subscription = result.scalar_one_or_none()
    
    if not subscription or not subscription.stripe_subscription_id:
        raise HTTPException(400, "User has no active subscription")
    
    if subscription.status == SubscriptionStatus.CANCELED:
        raise HTTPException(400, "Subscription is already canceled")
    
    try:
        # Cancel via Stripe
        StripeClient.cancel_subscription(
            stripe_subscription_id=subscription.stripe_subscription_id,
            at_period_end=at_period_end,
        )
        
        # Update local record
        subscription.cancel_at = datetime.utcnow()
        if not at_period_end:
            subscription.status = SubscriptionStatus.CANCELED
            subscription.tier = "free"
            subscription.canceled_at = datetime.utcnow()
        
        await db.commit()
        
        return {
            "success": True,
            "message": f"Subscription canceled {'at end of period' if at_period_end else 'immediately'}",
            "tier_after_cancel": subscription.tier,
        }
    except Exception as e:
        log.error("Failed to cancel subscription", user_id=user.id, error=str(e))
        raise HTTPException(500, "Failed to cancel subscription")


@router.get("/invoices")
async def get_invoices(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get user's invoice history.
    Returns list of invoices with amounts, dates, and status.
    """
    result = await db.execute(
        select(Invoice).where(Invoice.user_id == user.id).order_by(Invoice.created_at.desc())
    )
    invoices = result.scalars().all()
    
    return {
        "invoices": [
            {
                "id": inv.stripe_invoice_id,
                "amount_cents": inv.amount_paid_cents,
                "amount": inv.amount_paid_cents / 100,
                "status": inv.status,
                "paid": inv.paid,
                "paid_at": inv.paid_at.isoformat() if inv.paid_at else None,
                "created_at": inv.created_at.isoformat() if inv.created_at else None,
                "url": inv.hosted_invoice_url,
            }
            for inv in invoices
        ]
    }


@router.get("/usage")
async def get_usage(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get user's monthly build usage.
    Returns builds used this month and limit based on plan.
    """
    from datetime import datetime as dt
    from sqlalchemy import func
    from api.database import BuildJob, JobStatus
    
    # Get current plan
    sub_result = await db.execute(
        select(Subscription).where(Subscription.user_id == user.id)
    )
    subscription = sub_result.scalar_one_or_none()
    tier = subscription.tier if subscription else "free"
    
    # Define limits
    limits = {
        "free": 3,
        "pro": 50,
        "team": None,  # Unlimited
    }
    limit = limits.get(tier, limits["free"])
    
    # Count this month's builds
    now = dt.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    count_result = await db.execute(
        select(func.count(BuildJob.id)).where(
            BuildJob.user_id == user.id,
            BuildJob.created_at >= month_start,
            BuildJob.status != JobStatus.FAILED,
        )
    )
    builds_used = count_result.scalar() or 0
    
    # Calculate remaining
    remaining = None if limit is None else max(0, limit - builds_used)
    
    return {
        "tier": tier,
        "builds_used": builds_used,
        "builds_limit": limit,
        "builds_remaining": remaining,
        "period_start": month_start.isoformat(),
        "period_end": (month_start.replace(month=month_start.month + 1) if month_start.month < 12 else month_start.replace(year=month_start.year + 1, month=1)).isoformat(),
        "is_unlimited": limit is None,
    }
