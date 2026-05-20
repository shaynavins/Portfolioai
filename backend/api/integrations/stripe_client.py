"""
Stripe API Client
Wrapper around stripe-python SDK for creating customers, subscriptions, and managing billing
"""
import stripe
import structlog
from typing import Optional, Dict, Any
from datetime import datetime

from api.config import settings

log = structlog.get_logger()

# Configure Stripe API key
stripe.api_key = settings.STRIPE_SECRET_KEY


class StripeClient:
    """Wrapper for Stripe API operations."""

    @staticmethod
    def create_customer(user_id: str, email: str, name: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a Stripe customer.
        
        Args:
            user_id: Internal user ID (stored in metadata)
            email: User email
            name: User name
        
        Returns:
            Stripe customer object
        """
        try:
            customer = stripe.Customer.create(
                email=email,
                name=name or email.split("@")[0],
                metadata={"user_id": user_id},
            )
            log.info("Stripe customer created", user_id=user_id, stripe_customer_id=customer.id)
            return customer
        except stripe.error.StripeError as e:
            log.error("Failed to create Stripe customer", user_id=user_id, error=str(e))
            raise

    @staticmethod
    def create_checkout_session(
        stripe_customer_id: str,
        stripe_price_id: str,
        success_url: str,
        cancel_url: str,
        billing_email: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a Stripe Checkout session for subscription.
        
        Args:
            stripe_customer_id: Stripe customer ID
            stripe_price_id: Stripe price ID (product price)
            success_url: Redirect after successful payment
            cancel_url: Redirect if user cancels
            billing_email: Email for invoice
        
        Returns:
            Stripe session object
        """
        try:
            session = stripe.checkout.Session.create(
                customer=stripe_customer_id,
                mode="subscription",
                payment_method_types=["card"],
                line_items=[
                    {
                        "price": stripe_price_id,
                        "quantity": 1,
                    }
                ],
                success_url=success_url,
                cancel_url=cancel_url,
                billing_address_collection="auto",
            )
            log.info(
                "Stripe checkout session created",
                stripe_customer_id=stripe_customer_id,
                session_id=session.id,
            )
            return session
        except stripe.error.StripeError as e:
            log.error(
                "Failed to create checkout session",
                stripe_customer_id=stripe_customer_id,
                error=str(e),
            )
            raise

    @staticmethod
    def get_subscription(stripe_subscription_id: str) -> Dict[str, Any]:
        """Fetch subscription details from Stripe."""
        try:
            sub = stripe.Subscription.retrieve(stripe_subscription_id)
            return sub
        except stripe.error.StripeError as e:
            log.error("Failed to fetch subscription", stripe_subscription_id=stripe_subscription_id, error=str(e))
            raise

    @staticmethod
    def cancel_subscription(
        stripe_subscription_id: str,
        at_period_end: bool = True,
    ) -> Dict[str, Any]:
        """
        Cancel a subscription.
        
        Args:
            stripe_subscription_id: Subscription ID
            at_period_end: If True, cancel at end of billing period. If False, cancel immediately.
        
        Returns:
            Updated subscription object
        """
        try:
            sub = stripe.Subscription.delete(
                stripe_subscription_id,
                proration_behavior="none" if at_period_end else "create_prorations",
            )
            log.info(
                "Subscription canceled",
                stripe_subscription_id=stripe_subscription_id,
                at_period_end=at_period_end,
            )
            return sub
        except stripe.error.StripeError as e:
            log.error("Failed to cancel subscription", stripe_subscription_id=stripe_subscription_id, error=str(e))
            raise

    @staticmethod
    def update_subscription(
        stripe_subscription_id: str,
        stripe_price_id: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Update subscription (e.g., change price/tier)."""
        try:
            update_kwargs = {}
            
            if stripe_price_id:
                update_kwargs["items"] = [
                    {
                        "id": stripe.Subscription.retrieve(stripe_subscription_id).items.data[0].id,
                        "price": stripe_price_id,
                    }
                ]
            
            if metadata:
                update_kwargs["metadata"] = metadata
            
            sub = stripe.Subscription.modify(stripe_subscription_id, **update_kwargs)
            log.info("Subscription updated", stripe_subscription_id=stripe_subscription_id)
            return sub
        except stripe.error.StripeError as e:
            log.error("Failed to update subscription", stripe_subscription_id=stripe_subscription_id, error=str(e))
            raise

    @staticmethod
    def verify_webhook_signature(payload: bytes, sig_header: str) -> Dict[str, Any]:
        """
        Verify Stripe webhook signature and return event.
        
        Args:
            payload: Raw webhook payload
            sig_header: Signature header from Stripe
        
        Returns:
            Verified event object
        
        Raises:
            ValueError: If signature is invalid
        """
        try:
            event = stripe.Webhook.construct_event(
                payload,
                sig_header,
                settings.STRIPE_WEBHOOK_SECRET,
            )
            return event
        except ValueError as e:
            log.error("Invalid webhook signature", error=str(e))
            raise
        except stripe.error.SignatureVerificationError as e:
            log.error("Stripe webhook signature verification failed", error=str(e))
            raise

    @staticmethod
    def get_invoice(stripe_invoice_id: str) -> Dict[str, Any]:
        """Fetch invoice details from Stripe."""
        try:
            invoice = stripe.Invoice.retrieve(stripe_invoice_id)
            return invoice
        except stripe.error.StripeError as e:
            log.error("Failed to fetch invoice", stripe_invoice_id=stripe_invoice_id, error=str(e))
            raise

    @staticmethod
    def list_invoices(stripe_customer_id: str, limit: int = 10) -> list:
        """List invoices for a customer."""
        try:
            invoices = stripe.Invoice.list(
                customer=stripe_customer_id,
                limit=limit,
                expand=["data.subscription"],
            )
            return invoices.data
        except stripe.error.StripeError as e:
            log.error("Failed to list invoices", stripe_customer_id=stripe_customer_id, error=str(e))
            raise

    @staticmethod
    def list_prices(product_id: Optional[str] = None) -> list:
        """List Stripe prices (optionally filtered by product)."""
        try:
            kwargs = {"limit": 100}
            if product_id:
                kwargs["product"] = product_id
            
            prices = stripe.Price.list(**kwargs)
            return prices.data
        except stripe.error.StripeError as e:
            log.error("Failed to list prices", error=str(e))
            raise

    @staticmethod
    def list_products(active_only: bool = True) -> list:
        """List Stripe products."""
        try:
            kwargs = {"limit": 100}
            if active_only:
                kwargs["active"] = True
            
            products = stripe.Product.list(**kwargs)
            return products.data
        except stripe.error.StripeError as e:
            log.error("Failed to list products", error=str(e))
            raise
