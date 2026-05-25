"""add google resume sync table

Revision ID: 004_add_google_resume_sync
Revises: 003_add_user_build_tracking
Create Date: 2026-05-25
"""
from alembic import op
import sqlalchemy as sa


revision = "004_add_google_resume_sync"
down_revision = "003_add_user_build_tracking"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "google_resume_syncs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("google_access_token", sa.Text(), nullable=True),
        sa.Column("google_refresh_token", sa.Text(), nullable=True),
        sa.Column("google_token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("doc_id", sa.String(), nullable=True),
        sa.Column("doc_name", sa.String(), nullable=True),
        sa.Column("doc_url", sa.Text(), nullable=True),
        sa.Column("doc_modified_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_resume_text", sa.Text(), nullable=True),
        sa.Column("parsed_resume", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index(op.f("ix_google_resume_syncs_doc_id"), "google_resume_syncs", ["doc_id"], unique=False)
    op.create_index(op.f("ix_google_resume_syncs_user_id"), "google_resume_syncs", ["user_id"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_google_resume_syncs_user_id"), table_name="google_resume_syncs")
    op.drop_index(op.f("ix_google_resume_syncs_doc_id"), table_name="google_resume_syncs")
    op.drop_table("google_resume_syncs")
