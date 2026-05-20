"""Migration to replace Stripe with Razorpay for India.

Revision ID: 002
Revises: 001_add_subscription_tables
Create Date: 2025-05-20 05:05:00.000000

Changes:
- Rename stripe_customer_id → razorpay_customer_id
- Rename stripe_subscription_id → razorpay_subscription_id
- Remove tier field (single tier only: ₹200/month)
- Remove stripe_product_id, stripe_price_id fields
- Add trial fields (trial_start, trial_end)
- Update currency from USD to INR
- Update amount fields from cents to paise
- Update webhook_logs to use razorpay event IDs
- Remove StripeProduct table (no tier mapping needed)
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade: Stripe → Razorpay migration."""
    
    # Step 1: Rename Stripe identifier columns in subscriptions
    op.alter_column('subscriptions', 'stripe_customer_id', new_column_name='razorpay_customer_id')
    op.alter_column('subscriptions', 'stripe_subscription_id', new_column_name='razorpay_subscription_id')
    
    # Step 2: Drop Stripe-specific columns from subscriptions
    op.drop_column('subscriptions', 'tier')
    op.drop_column('subscriptions', 'stripe_product_id')
    op.drop_column('subscriptions', 'stripe_price_id')
    op.drop_column('subscriptions', 'stripe_payment_method_id')
    
    # Step 3: Update currency from USD to INR
    op.execute("UPDATE subscriptions SET currency = 'inr'")
    
    # Step 4: Update monthly_price_cents → monthly_price_paise (multiply by 100 to convert INR cents to paise)
    # ₹200/month = 20000 paise
    op.alter_column('subscriptions', 'monthly_price_cents',
                   new_column_name='monthly_price_paise',
                   type_=sa.Integer(),
                   existing_type=sa.Integer())
    op.execute("UPDATE subscriptions SET monthly_price_paise = 20000 WHERE monthly_price_paise IS NOT NULL")
    
    # Step 5: Add trial fields if not exist
    with op.batch_alter_table('subscriptions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('trial_start', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('trial_end', sa.DateTime(timezone=True), nullable=True))
    
    # Step 6: Rename columns in invoices (Stripe → Razorpay)
    op.alter_column('invoices', 'stripe_invoice_id', new_column_name='razorpay_invoice_id')
    op.alter_column('invoices', 'stripe_customer_id', new_column_name='razorpay_customer_id')
    op.alter_column('invoices', 'stripe_payment_intent_id', new_column_name='razorpay_payment_id')
    
    # Step 7: Add razorpay_order_id to invoices
    with op.batch_alter_table('invoices', schema=None) as batch_op:
        batch_op.add_column(sa.Column('razorpay_order_id', sa.String(), nullable=True))
        batch_op.create_unique_constraint('uq_invoices_razorpay_order_id', ['razorpay_order_id'])
    
    # Step 8: Convert invoice amounts from cents to paise
    op.alter_column('invoices', 'amount_due_cents',
                   new_column_name='amount_due_paise',
                   type_=sa.Integer(),
                   existing_type=sa.Integer())
    op.alter_column('invoices', 'amount_paid_cents',
                   new_column_name='amount_paid_paise',
                   type_=sa.Integer(),
                   existing_type=sa.Integer())
    op.alter_column('invoices', 'amount_remaining_cents',
                   new_column_name='amount_remaining_paise',
                   type_=sa.Integer(),
                   existing_type=sa.Integer())
    
    # Step 9: Update currency in invoices
    op.execute("UPDATE invoices SET currency = 'inr'")
    
    # Step 10: Rename columns in payment_methods
    op.alter_column('payment_methods', 'stripe_payment_method_id', new_column_name='razorpay_payment_method_id')
    op.alter_column('payment_methods', 'stripe_customer_id', new_column_name='razorpay_customer_id')
    
    # Step 11: Rename columns in webhook_logs
    op.alter_column('webhook_logs', 'stripe_event_id', new_column_name='razorpay_event_id')
    op.alter_column('webhook_logs', 'stripe_customer_id', new_column_name='razorpay_customer_id')
    op.alter_column('webhook_logs', 'stripe_subscription_id', new_column_name='razorpay_subscription_id')
    
    # Step 12: Drop StripeProduct table (no longer needed with single tier)
    op.drop_table('stripe_products')
    
    # Step 13: Update subscription status enum (add Razorpay statuses)
    # Note: This depends on your SQLAlchemy Enum handling
    # If using PostgreSQL, we need to add new enum values
    # For other databases, the enum is just a string


def downgrade() -> None:
    """Downgrade: Razorpay → Stripe rollback."""
    
    # Step 1: Recreate StripeProduct table
    op.create_table(
        'stripe_products',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('stripe_product_id', sa.String(), nullable=False, unique=True),
        sa.Column('stripe_price_id', sa.String(), nullable=False, unique=True),
        sa.Column('tier', sa.String(), nullable=False, unique=True),  # free | pro | team
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('amount_cents', sa.Integer(), nullable=False),
        sa.Column('currency', sa.String(), default='usd'),
        sa.Column('interval', sa.String(), default='month'),
        sa.Column('interval_count', sa.Integer(), default=1),
        sa.Column('active', sa.Boolean(), default=True),
        sa.Column('metadata', sa.JSON(), default=dict),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
        sa.Column('synced_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('stripe_product_id'),
        sa.UniqueConstraint('stripe_price_id'),
        sa.UniqueConstraint('tier')
    )
    
    # Step 2: Remove trial fields from subscriptions
    with op.batch_alter_table('subscriptions', schema=None) as batch_op:
        batch_op.drop_column('trial_start')
        batch_op.drop_column('trial_end')
    
    # Step 3: Convert amounts back from paise to cents
    op.alter_column('subscriptions', 'monthly_price_paise',
                   new_column_name='monthly_price_cents',
                   type_=sa.Integer(),
                   existing_type=sa.Integer())
    op.execute("UPDATE subscriptions SET monthly_price_cents = monthly_price_cents / 100 WHERE monthly_price_cents IS NOT NULL")
    
    # Step 4: Rename Razorpay columns back to Stripe
    op.alter_column('subscriptions', 'razorpay_customer_id', new_column_name='stripe_customer_id')
    op.alter_column('subscriptions', 'razorpay_subscription_id', new_column_name='stripe_subscription_id')
    
    # Step 5: Add back Stripe-specific columns
    with op.batch_alter_table('subscriptions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('tier', sa.String(), default='free'))
        batch_op.add_column(sa.Column('stripe_product_id', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('stripe_price_id', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('stripe_payment_method_id', sa.String(), nullable=True))
    
    # Step 6: Update currency back to USD
    op.execute("UPDATE subscriptions SET currency = 'usd'")
    
    # Step 7: Convert amounts in invoices back
    op.alter_column('invoices', 'amount_due_paise',
                   new_column_name='amount_due_cents',
                   type_=sa.Integer(),
                   existing_type=sa.Integer())
    op.alter_column('invoices', 'amount_paid_paise',
                   new_column_name='amount_paid_cents',
                   type_=sa.Integer(),
                   existing_type=sa.Integer())
    op.alter_column('invoices', 'amount_remaining_paise',
                   new_column_name='amount_remaining_cents',
                   type_=sa.Integer(),
                   existing_type=sa.Integer())
    
    # Step 8: Rename invoice columns back
    op.alter_column('invoices', 'razorpay_invoice_id', new_column_name='stripe_invoice_id')
    op.alter_column('invoices', 'razorpay_customer_id', new_column_name='stripe_customer_id')
    op.alter_column('invoices', 'razorpay_payment_id', new_column_name='stripe_payment_intent_id')
    
    # Step 9: Remove razorpay_order_id from invoices
    with op.batch_alter_table('invoices', schema=None) as batch_op:
        batch_op.drop_constraint('uq_invoices_razorpay_order_id', type_='unique')
        batch_op.drop_column('razorpay_order_id')
    
    # Step 10: Update currency in invoices back to USD
    op.execute("UPDATE invoices SET currency = 'usd'")
    
    # Step 11: Rename payment_methods columns back
    op.alter_column('payment_methods', 'razorpay_payment_method_id', new_column_name='stripe_payment_method_id')
    op.alter_column('payment_methods', 'razorpay_customer_id', new_column_name='stripe_customer_id')
    
    # Step 12: Rename webhook_logs columns back
    op.alter_column('webhook_logs', 'razorpay_event_id', new_column_name='stripe_event_id')
    op.alter_column('webhook_logs', 'razorpay_customer_id', new_column_name='stripe_customer_id')
    op.alter_column('webhook_logs', 'razorpay_subscription_id', new_column_name='stripe_subscription_id')
