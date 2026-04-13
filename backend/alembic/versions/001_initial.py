"""PortfolioAI — Initial migration
Create all tables: users, portfolios, build_jobs
"""
from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("github_id", sa.Integer(), nullable=False),
        sa.Column("github_username", sa.String(), nullable=False),
        sa.Column("github_token", sa.Text(), nullable=False),
        sa.Column("email", sa.String()),
        sa.Column("name", sa.String()),
        sa.Column("avatar_url", sa.String()),
        sa.Column("plan", sa.String(), default="free"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("github_id"),
    )
    op.create_index("ix_users_github_id", "users", ["github_id"])

    op.create_table(
        "portfolios",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("title", sa.String()),
        sa.Column("bio", sa.Text()),
        sa.Column("theme", sa.String(), default="minimal"),
        sa.Column("custom_domain", sa.String()),
        sa.Column("is_published", sa.Boolean(), default=False),
        sa.Column("site_url", sa.String()),
        sa.Column("vercel_project_id", sa.String()),
        sa.Column("r2_path", sa.String()),
        sa.Column("portfolio_data", sa.JSON()),
        sa.Column("last_built_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )

    op.create_table(
        "build_jobs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("portfolio_id", sa.String(), sa.ForeignKey("portfolios.id")),
        sa.Column("status", sa.String(), default="pending"),
        sa.Column("trigger", sa.String(), default="manual"),
        sa.Column("celery_task_id", sa.String()),
        sa.Column("progress_steps", sa.JSON(), default=list),
        sa.Column("error", sa.Text()),
        sa.Column("result", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("build_jobs")
    op.drop_table("portfolios")
    op.drop_table("users")
