"""add rotating refresh tokens

Revision ID: 20260526_0014
Revises: 20260526_0013
Create Date: 2026-05-26 22:30:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260526_0014"
down_revision = "20260526_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("auth_refresh_tokens"):
        return
    op.create_table(
        "auth_refresh_tokens",
        sa.Column("token_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("app_users.user_id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("family_id", sa.String(length=64), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by_token_id", sa.Integer(), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.UniqueConstraint("token_hash", name="uq_auth_refresh_tokens_hash"),
    )
    op.create_index("ix_auth_refresh_tokens_user_id", "auth_refresh_tokens", ["user_id"])
    op.create_index("ix_auth_refresh_tokens_token_hash", "auth_refresh_tokens", ["token_hash"])
    op.create_index("ix_auth_refresh_tokens_family_id", "auth_refresh_tokens", ["family_id"])
    op.create_index("ix_auth_refresh_tokens_issued_at", "auth_refresh_tokens", ["issued_at"])
    op.create_index("ix_auth_refresh_tokens_expires_at", "auth_refresh_tokens", ["expires_at"])
    op.create_index("ix_auth_refresh_tokens_revoked_at", "auth_refresh_tokens", ["revoked_at"])
    op.create_index("ix_auth_refresh_tokens_replaced_by_token_id", "auth_refresh_tokens", ["replaced_by_token_id"])
    op.create_index(
        "ix_auth_refresh_tokens_user_active",
        "auth_refresh_tokens",
        ["user_id", "revoked_at", "expires_at"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("auth_refresh_tokens"):
        return
    for index_name in (
        "ix_auth_refresh_tokens_user_active",
        "ix_auth_refresh_tokens_replaced_by_token_id",
        "ix_auth_refresh_tokens_revoked_at",
        "ix_auth_refresh_tokens_expires_at",
        "ix_auth_refresh_tokens_issued_at",
        "ix_auth_refresh_tokens_family_id",
        "ix_auth_refresh_tokens_token_hash",
        "ix_auth_refresh_tokens_user_id",
    ):
        op.drop_index(index_name, table_name="auth_refresh_tokens")
    op.drop_table("auth_refresh_tokens")
