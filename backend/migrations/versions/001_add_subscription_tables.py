"""Add subscription tables for Stripe integration

Revision ID: 001
Revises: 
Create Date: 2026-05-19 14:20:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create subscription table
    op.create_table(
        'subscriptions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('stripe_customer_id', sa.String(), nullable=False),
        sa.Column('stripe_subscription_id', sa.String(), nullable=True),
        sa.Column('stripe_payment_method_id', sa.String(), nullable=True),
        sa.Column('status', postgresql.ENUM('active', 'past_due', 'unpaid', 'canceled', 'incomplete', 'incomplete_expired', 'trialing', name='subscriptionstatus'), nullable=False),
        sa.Column('tier', sa.String(), nullable=False),
        sa.Column('stripe_product_id', sa.String(), nullable=True),
        sa.Column('stripe_price_id', sa.String(), nullable=True),
        sa.Column('current_period_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('current_period_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('trial_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('trial_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('billing_email', sa.String(), nullable=True),
        sa.Column('monthly_price_cents', sa.Integer(), nullable=True),
        sa.Column('currency', sa.String(), nullable=False),
        sa.Column('billing_cycle_anchor', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancel_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('canceled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_webhook_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
        sa.UniqueConstraint('stripe_customer_id'),
        sa.UniqueConstraint('stripe_subscription_id'),
    )
    op.create_index(op.f('ix_subscriptions_user_id'), 'subscriptions', ['user_id'], unique=False)
    op.create_index(op.f('ix_subscriptions_stripe_customer_id'), 'subscriptions', ['stripe_customer_id'], unique=False)
    op.create_index(op.f('ix_subscriptions_stripe_subscription_id'), 'subscriptions', ['stripe_subscription_id'], unique=False)

    # Create invoices table
    op.create_table(
        'invoices',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('subscription_id', sa.String(), nullable=True),
        sa.Column('stripe_invoice_id', sa.String(), nullable=False),
        sa.Column('stripe_customer_id', sa.String(), nullable=False),
        sa.Column('stripe_payment_intent_id', sa.String(), nullable=True),
        sa.Column('amount_due_cents', sa.Integer(), nullable=False),
        sa.Column('amount_paid_cents', sa.Integer(), nullable=False),
        sa.Column('amount_remaining_cents', sa.Integer(), nullable=False),
        sa.Column('currency', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('paid', sa.Boolean(), nullable=False),
        sa.Column('attempted', sa.Boolean(), nullable=False),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('issued_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_payment_attempt', sa.DateTime(timezone=True), nullable=True),
        sa.Column('hosted_invoice_url', sa.String(), nullable=True),
        sa.Column('pdf_url', sa.String(), nullable=True),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['subscription_id'], ['subscriptions.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('stripe_invoice_id'),
        sa.UniqueConstraint('stripe_payment_intent_id'),
    )
    op.create_index(op.f('ix_invoices_user_id'), 'invoices', ['user_id'], unique=False)
    op.create_index(op.f('ix_invoices_stripe_invoice_id'), 'invoices', ['stripe_invoice_id'], unique=False)

    # Create payment_methods table
    op.create_table(
        'payment_methods',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('stripe_payment_method_id', sa.String(), nullable=False),
        sa.Column('stripe_customer_id', sa.String(), nullable=False),
        sa.Column('card_type', sa.String(), nullable=True),
        sa.Column('card_last_four', sa.String(), nullable=True),
        sa.Column('card_expiry_month', sa.Integer(), nullable=True),
        sa.Column('card_expiry_year', sa.Integer(), nullable=True),
        sa.Column('card_brand', sa.String(), nullable=True),
        sa.Column('is_default', sa.Boolean(), nullable=False),
        sa.Column('is_expired', sa.Boolean(), nullable=False),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('stripe_payment_method_id'),
    )
    op.create_index(op.f('ix_payment_methods_user_id'), 'payment_methods', ['user_id'], unique=False)
    op.create_index(op.f('ix_payment_methods_stripe_payment_method_id'), 'payment_methods', ['stripe_payment_method_id'], unique=False)

    # Create webhook_logs table
    op.create_table(
        'webhook_logs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('stripe_event_id', sa.String(), nullable=False),
        sa.Column('event_type', sa.String(), nullable=False),
        sa.Column('stripe_customer_id', sa.String(), nullable=True),
        sa.Column('stripe_subscription_id', sa.String(), nullable=True),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('event_data', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('processed', sa.Boolean(), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('received_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('stripe_event_id'),
    )
    op.create_index(op.f('ix_webhook_logs_stripe_event_id'), 'webhook_logs', ['stripe_event_id'], unique=False)
    op.create_index(op.f('ix_webhook_logs_event_type'), 'webhook_logs', ['event_type'], unique=False)
    op.create_index(op.f('ix_webhook_logs_stripe_customer_id'), 'webhook_logs', ['stripe_customer_id'], unique=False)
    op.create_index(op.f('ix_webhook_logs_stripe_subscription_id'), 'webhook_logs', ['stripe_subscription_id'], unique=False)
    op.create_index(op.f('ix_webhook_logs_user_id'), 'webhook_logs', ['user_id'], unique=False)

    # Create stripe_products table
    op.create_table(
        'stripe_products',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('stripe_product_id', sa.String(), nullable=False),
        sa.Column('stripe_price_id', sa.String(), nullable=False),
        sa.Column('tier', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('amount_cents', sa.Integer(), nullable=False),
        sa.Column('currency', sa.String(), nullable=False),
        sa.Column('interval', sa.String(), nullable=False),
        sa.Column('interval_count', sa.Integer(), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('synced_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('stripe_product_id'),
        sa.UniqueConstraint('stripe_price_id'),
        sa.UniqueConstraint('tier'),
    )
    op.create_index(op.f('ix_stripe_products_stripe_product_id'), 'stripe_products', ['stripe_product_id'], unique=False)
    op.create_index(op.f('ix_stripe_products_stripe_price_id'), 'stripe_products', ['stripe_price_id'], unique=False)
    op.create_index(op.f('ix_stripe_products_tier'), 'stripe_products', ['tier'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_stripe_products_tier'), table_name='stripe_products')
    op.drop_index(op.f('ix_stripe_products_stripe_price_id'), table_name='stripe_products')
    op.drop_index(op.f('ix_stripe_products_stripe_product_id'), table_name='stripe_products')
    op.drop_table('stripe_products')
    
    op.drop_index(op.f('ix_webhook_logs_user_id'), table_name='webhook_logs')
    op.drop_index(op.f('ix_webhook_logs_stripe_subscription_id'), table_name='webhook_logs')
    op.drop_index(op.f('ix_webhook_logs_stripe_customer_id'), table_name='webhook_logs')
    op.drop_index(op.f('ix_webhook_logs_event_type'), table_name='webhook_logs')
    op.drop_index(op.f('ix_webhook_logs_stripe_event_id'), table_name='webhook_logs')
    op.drop_table('webhook_logs')
    
    op.drop_index(op.f('ix_payment_methods_stripe_payment_method_id'), table_name='payment_methods')
    op.drop_index(op.f('ix_payment_methods_user_id'), table_name='payment_methods')
    op.drop_table('payment_methods')
    
    op.drop_index(op.f('ix_invoices_stripe_invoice_id'), table_name='invoices')
    op.drop_index(op.f('ix_invoices_user_id'), table_name='invoices')
    op.drop_table('invoices')
    
    op.drop_index(op.f('ix_subscriptions_stripe_subscription_id'), table_name='subscriptions')
    op.drop_index(op.f('ix_subscriptions_stripe_customer_id'), table_name='subscriptions')
    op.drop_index(op.f('ix_subscriptions_user_id'), table_name='subscriptions')
    op.drop_table('subscriptions')
