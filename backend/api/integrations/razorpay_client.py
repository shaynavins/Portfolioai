"""
Razorpay Payment Integration Client

Handles all Razorpay API interactions for PortfolioAI India:
- Customer creation and management
- Subscription creation and management
- Webhook event processing
- Invoice/order retrieval
"""

import logging
import hmac
import hashlib
from typing import Optional, Dict, Any
from datetime import datetime

import razorpay
from razorpay.client import Client as RazorpayClient

logger = logging.getLogger(__name__)


class RazorpayClient:
    """
    Razorpay payment processor client.
    
    Single tier model: ₹200/month with 14-day free trial.
    Subscriptions are recurring, auto-renewing monthly.
    """
    
    # ₹200/month subscription amount (in paise: 200 * 100)
    MONTHLY_AMOUNT_PAISE = 20000
    MONTHLY_AMOUNT_INR = 200
    
    # Free trial period: 14 days
    TRIAL_DAYS = 14
    
    def __init__(self, key_id: str, key_secret: str):
        """Initialize Razorpay client."""
        if not key_id or not key_secret:
            logger.warning("Razorpay credentials not provided - payment processing disabled")
            self.client = None
            self.key_id = None
            self.key_secret = None
        else:
            self.client = razorpay.Client(auth=(key_id, key_secret))
            self.key_id = key_id
            self.key_secret = key_secret
    
    def is_configured(self) -> bool:
        """Check if Razorpay is properly configured."""
        return self.client is not None
    
    def create_customer(self, user_id: str, email: str, phone: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Create a Razorpay customer.
        
        Args:
            user_id: PortfolioAI user ID (for idempotency)
            email: Customer email
            phone: Customer phone number (optional)
        
        Returns:
            Customer object or None if not configured
        
        Raises:
            razorpay.BadRequestError: Invalid request
            razorpay.ServerError: Razorpay server error
        """
        if not self.is_configured():
            logger.info(f"[DEV MODE] Would create customer: {email}")
            return {"id": f"cust_dev_{user_id}", "email": email}
        
        try:
            customer_data = {
                "email": email,
                "contact": phone or "",
                "description": f"PortfolioAI user {user_id}"
            }
            
            customer = self.client.customer.create(customer_data)
            logger.info(f"Created Razorpay customer: {customer.get('id')} for {email}")
            return customer
        
        except Exception as e:
            logger.error(f"Failed to create Razorpay customer: {str(e)}")
            raise
    
    def create_subscription(
        self,
        customer_id: str,
        trial_end_timestamp: Optional[int] = None,
        notes: Optional[Dict[str, str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a recurring subscription (₹200/month with 14-day trial).
        
        Args:
            customer_id: Razorpay customer ID
            trial_end_timestamp: Unix timestamp when trial ends (payment starts after)
            notes: Additional notes (e.g., user_id)
        
        Returns:
            Subscription object or None if not configured
        
        Raises:
            razorpay.BadRequestError: Invalid request
            razorpay.ServerError: Razorpay server error
        """
        if not self.is_configured():
            logger.info(f"[DEV MODE] Would create subscription for customer {customer_id}")
            return {
                "id": f"sub_dev_{customer_id}",
                "customer_id": customer_id,
                "plan_id": "plan_dev_monthly",
                "status": "active",
                "current_start": int(datetime.now().timestamp()),
                "current_end": trial_end_timestamp or int(datetime.now().timestamp()) + (14 * 86400)
            }
        
        try:
            subscription_data = {
                "plan_id": "plan_dev_monthly",  # Will be replaced with actual plan ID from Razorpay
                "customer_notify": 1,  # Send notification to customer
                "quantity": 1,
                "total_count": 0,  # Recurring forever (0 = no end date)
                "notes": notes or {}
            }
            
            # Add trial end date if provided
            if trial_end_timestamp:
                subscription_data["start_at"] = trial_end_timestamp
            
            subscription = self.client.subscription.create(subscription_data)
            logger.info(f"Created Razorpay subscription: {subscription.get('id')} for customer {customer_id}")
            return subscription
        
        except Exception as e:
            logger.error(f"Failed to create Razorpay subscription: {str(e)}")
            raise
    
    def create_subscription_link(
        self,
        customer_id: str,
        email: str,
        trial_days: int = TRIAL_DAYS,
        notes: Optional[Dict[str, str]] = None
    ) -> Optional[str]:
        """
        Create a subscription link for payment.
        
        Customer can click the link to pay for subscription with trial period.
        
        Args:
            customer_id: Razorpay customer ID
            email: Customer email
            trial_days: Free trial period in days (default: 14)
            notes: Additional notes
        
        Returns:
            Subscription link URL or None if not configured
        
        Raises:
            razorpay.BadRequestError: Invalid request
        """
        if not self.is_configured():
            logger.info(f"[DEV MODE] Would create subscription link for {email}")
            return f"https://rzp.io/l/dev_subscription_{customer_id}"
        
        try:
            # Calculate trial end timestamp (14 days from now)
            trial_end_timestamp = int(datetime.now().timestamp()) + (trial_days * 86400)
            
            # Create subscription
            subscription = self.create_subscription(
                customer_id=customer_id,
                trial_end_timestamp=trial_end_timestamp,
                notes=notes or {}
            )
            
            if not subscription:
                return None
            
            # Get subscription short URL (Razorpay generates this)
            subscription_link = subscription.get("short_url")
            logger.info(f"Created subscription link: {subscription_link}")
            return subscription_link
        
        except Exception as e:
            logger.error(f"Failed to create subscription link: {str(e)}")
            raise
    
    def get_subscription(self, subscription_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch subscription details from Razorpay.
        
        Args:
            subscription_id: Razorpay subscription ID
        
        Returns:
            Subscription object or None if not configured
        
        Raises:
            razorpay.BadRequestError: Subscription not found
        """
        if not self.is_configured():
            logger.info(f"[DEV MODE] Would fetch subscription {subscription_id}")
            return {"id": subscription_id, "status": "active"}
        
        try:
            subscription = self.client.subscription.fetch(subscription_id)
            return subscription
        except Exception as e:
            logger.error(f"Failed to fetch subscription {subscription_id}: {str(e)}")
            raise
    
    def cancel_subscription(
        self,
        subscription_id: str,
        at_period_end: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Cancel a subscription.
        
        Args:
            subscription_id: Razorpay subscription ID
            at_period_end: If True, cancel at end of billing period
                          If False, cancel immediately and refund
        
        Returns:
            Cancelled subscription object or None if not configured
        
        Raises:
            razorpay.BadRequestError: Subscription not found
        """
        if not self.is_configured():
            logger.info(f"[DEV MODE] Would cancel subscription {subscription_id}")
            return {"id": subscription_id, "status": "cancelled"}
        
        try:
            cancel_params = {}
            if not at_period_end:
                cancel_params["at_period_end"] = 0
            
            subscription = self.client.subscription.cancel(subscription_id, cancel_params)
            logger.info(f"Cancelled subscription: {subscription_id}")
            return subscription
        except Exception as e:
            logger.error(f"Failed to cancel subscription {subscription_id}: {str(e)}")
            raise
    
    def get_orders(self, customer_id: str, limit: int = 10) -> Optional[list]:
        """
        Fetch all orders (invoices) for a customer.
        
        Args:
            customer_id: Razorpay customer ID
            limit: Number of orders to fetch
        
        Returns:
            List of order objects or None if not configured
        
        Raises:
            razorpay.BadRequestError: Invalid request
        """
        if not self.is_configured():
            logger.info(f"[DEV MODE] Would fetch orders for customer {customer_id}")
            return []
        
        try:
            orders = self.client.order.all({"customer_id": customer_id, "count": limit})
            return orders.get("items", [])
        except Exception as e:
            logger.error(f"Failed to fetch orders for customer {customer_id}: {str(e)}")
            raise
    
    def verify_webhook_signature(self, payload: str, signature: str, secret: str) -> bool:
        """
        Verify Razorpay webhook signature.
        
        Args:
            payload: Raw webhook payload (JSON string)
            signature: X-Razorpay-Signature header value
            secret: Webhook secret from Razorpay dashboard
        
        Returns:
            True if signature is valid, False otherwise
        
        Security: Use timing-safe comparison to prevent timing attacks.
        """
        try:
            # Generate HMAC-SHA256 hash
            generated_signature = hmac.new(
                secret.encode(),
                payload.encode(),
                hashlib.sha256
            ).hexdigest()
            
            # Timing-safe comparison
            return hmac.compare_digest(generated_signature, signature)
        except Exception as e:
            logger.error(f"Failed to verify webhook signature: {str(e)}")
            return False
    
    def process_webhook_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process a Razorpay webhook event.
        
        Supported events:
        - subscription.created: User created subscription (trial starts)
        - subscription.activated: Trial ended, first payment succeeded
        - subscription.paid: Monthly payment succeeded
        - subscription.failed: Monthly payment failed
        - subscription.halted: Payment failed multiple times
        - subscription.cancelled: Subscription cancelled
        - subscription.completed: All payments completed (non-recurring)
        - subscription.paused: Subscription paused
        
        Args:
            event: Webhook event data from Razorpay
        
        Returns:
            Processed event data or None if error
        """
        try:
            event_type = event.get("event")
            event_data = event.get("payload", {}).get("subscription", {})
            
            if not event_type or not event_data:
                logger.warning(f"Invalid webhook event: {event}")
                return None
            
            subscription_id = event_data.get("id")
            customer_id = event_data.get("customer_id")
            status = event_data.get("status")
            
            logger.info(f"Processing webhook event: {event_type} for subscription {subscription_id}")
            
            # Return processed event data for application to handle
            return {
                "event_type": event_type,
                "subscription_id": subscription_id,
                "customer_id": customer_id,
                "status": status,
                "created_at": event.get("created_at"),
                "raw_event": event
            }
        
        except Exception as e:
            logger.error(f"Failed to process webhook event: {str(e)}")
            return None
    
    def refund_payment(self, payment_id: str, amount: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Process a refund for a payment.
        
        Args:
            payment_id: Razorpay payment ID
            amount: Refund amount in paise (None = full refund)
        
        Returns:
            Refund object or None if not configured
        
        Raises:
            razorpay.BadRequestError: Payment not found or refund failed
        """
        if not self.is_configured():
            logger.info(f"[DEV MODE] Would refund payment {payment_id}")
            return {"id": f"rfnd_dev_{payment_id}", "amount": amount}
        
        try:
            refund_data = {}
            if amount:
                refund_data["amount"] = amount
            
            refund = self.client.payment.refund(payment_id, refund_data)
            logger.info(f"Processed refund for payment {payment_id}: {refund.get('id')}")
            return refund
        except Exception as e:
            logger.error(f"Failed to refund payment {payment_id}: {str(e)}")
            raise
