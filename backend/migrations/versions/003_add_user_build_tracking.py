"""Add build tracking columns to users table.

Revision ID: 003
Revises: 002_razorpay_migration
Create Date: 2026-05-22 04:51:00.000000

Changes:
- Add builds_this_month (Integer) to track monthly builds for free users
- Add last_build_date (DateTime) to track when the last build was done
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade: Add build tracking columns to users table."""
    
    # Add columns to users table
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('builds_this_month', sa.Integer(), nullable=True, server_default='0'))
        batch_op.add_column(sa.Column('last_build_date', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Downgrade: Remove build tracking columns from users table."""
    
    # Remove columns from users table
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('builds_this_month')
        batch_op.drop_column('last_build_date')
