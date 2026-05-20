"""
Razorpay Subscription Models
Manages customer subscriptions, payment methods, and billing history for India.
"""
from sqlalchemy import Column, String, Integer, DateTime, Text, JSON, ForeignKey, Enum, Boolean, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
import uuid
from datetime import datetime

from api.database import Base


class SubscriptionStatus(str, enum.Enum):
    """Razorpay subscription status."""
    ACTIVE = "active"
    PAST_DUE = "past_due"
    UNPAID = "unpaid"
    CANCELED = "canceled"
    CANCELLED = "cancelled"
    INCOMPLETE = "incomplete"
    INCOMPLETE_EXPIRED = "incomplete_expired"
    TRIALING = "trialing"
    AUTHENTICATED = "authenticated"
    HALTED = "halted"
    PAUSED = "paused"
    COMPLETED = "completed"


class PaymentStatus(str, enum.Enum):
    """Payment status."""
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REQUIRES_ACTION = "requires_action"
    CANCELED = "canceled"


class Subscription(Base):
    """
    Razorpay subscription for a user.
    Single tier: ₹200/month with 14-day free trial.
    One subscription per user, updated via Razorpay webhooks.
    """
    __tablename__ = "subscriptions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    
    # Razorpay identifiers
    razorpay_customer_id = Column(String, nullable=False, unique=True, index=True)
    razorpay_subscription_id = Column(String, nullable=True, unique=True, index=True)
    
    # Subscription details
    status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.TRIALING)
    
    # Billing
    current_period_start = Column(DateTime(timezone=True), nullable=True)
    current_period_end = Column(DateTime(timezone=True), nullable=True)
    trial_start = Column(DateTime(timezone=True), nullable=True)
    trial_end = Column(DateTime(timezone=True), nullable=True)
    billing_email = Column(String, nullable=True)
    
    # Pricing
    monthly_price_paise = Column(Integer, default=20000)  # ₹200
    currency = Column(String, default="inr")
    
    # Billing cycle
    cancel_at = Column(DateTime(timezone=True), nullable=True)
    canceled_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    custom_metadata = Column(JSON, default=dict)  # Custom data from Razorpay
    
    # Tracking
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_webhook_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="subscription")
    invoices = relationship("Invoice", back_populates="subscription", cascade="all, delete-orphan")


class Invoice(Base):
    """
    Razorpay invoice/order records.
    Created when a payment is attempted or invoice is issued.
    """
    __tablename__ = "invoices"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    subscription_id = Column(String, ForeignKey("subscriptions.id"), nullable=True)
    
    # Razorpay identifiers
    razorpay_invoice_id = Column(String, nullable=False, unique=True, index=True)
    razorpay_customer_id = Column(String, nullable=False, index=True)
    razorpay_payment_id = Column(String, nullable=True, unique=True)
    razorpay_order_id = Column(String, nullable=True, unique=True)
    
    # Invoice details
    amount_due_paise = Column(Integer, nullable=False)
    amount_paid_paise = Column(Integer, default=0)
    amount_remaining_paise = Column(Integer, nullable=False)
    currency = Column(String, default="inr")
    
    # Status
    status = Column(String, default="draft")  # draft | open | paid | void | uncollectible
    paid = Column(Boolean, default=False)
    attempted = Column(Boolean, default=False)
    
    # Dates
    due_date = Column(DateTime(timezone=True), nullable=True)
    issued_at = Column(DateTime(timezone=True), nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    next_payment_attempt = Column(DateTime(timezone=True), nullable=True)
    
    # URLs
    hosted_invoice_url = Column(String, nullable=True)
    pdf_url = Column(String, nullable=True)
    
    # Metadata
    description = Column(String, nullable=True)
    custom_metadata = Column(JSON, default=dict)
    
    # Tracking
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    subscription = relationship("Subscription", back_populates="invoices")


class PaymentMethod(Base):
    """
    Stored payment methods for users.
    Allows users to manage multiple cards.
    """
    __tablename__ = "payment_methods"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    
    # Razorpay identifiers
    razorpay_payment_method_id = Column(String, nullable=False, unique=True, index=True)
    razorpay_customer_id = Column(String, nullable=False, index=True)
    
    # Card details (redacted from Stripe, we store only the last 4)
    card_type = Column(String)  # visa, mastercard, amex, etc.
    card_last_four = Column(String)  # Last 4 digits
    card_expiry_month = Column(Integer)
    card_expiry_year = Column(Integer)
    card_brand = Column(String)  # visa, mastercard, etc.
    
    # Status
    is_default = Column(Boolean, default=False)
    is_expired = Column(Boolean, default=False)
    
    # Metadata
    custom_metadata = Column(JSON, default=dict)
    
    # Tracking
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class WebhookLog(Base):
    """
    Log of all Razorpay webhook events.
    Used for debugging, audit trail, and replay logic.
    """
    __tablename__ = "webhook_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Event details
    razorpay_event_id = Column(String, nullable=False, unique=True, index=True)
    event_type = Column(String, nullable=False, index=True)  # customer.subscription.created, etc.
    
    # User/subscription context (if applicable)
    razorpay_customer_id = Column(String, nullable=True, index=True)
    razorpay_subscription_id = Column(String, nullable=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    
    # Raw event data
    event_data = Column(JSON, nullable=False)
    
    # Processing
    processed = Column(Boolean, default=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    error = Column(Text, nullable=True)
    
    # Tracking
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    received_at = Column(DateTime(timezone=True), nullable=True)


