"""add audit follow-up defaults and indexes

Revision ID: 20260526_0012
Revises: 20260522_0011
Create Date: 2026-05-26 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260526_0012"
down_revision = "20260522_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("world_commodity_prices"):
        with op.batch_alter_table("world_commodity_prices") as batch_op:
            batch_op.alter_column(
                "currency",
                existing_type=sa.String(length=10),
                existing_nullable=False,
                server_default="USD",
            )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_world_prices_commodity_observed_desc "
            "ON world_commodity_prices (commodity_slug, observed_at DESC)"
        )
    if inspector.has_table("watchlist_items"):
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_watchlist_user_created "
            "ON watchlist_items (user_id, created_at DESC)"
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("watchlist_items"):
        op.execute("DROP INDEX IF EXISTS ix_watchlist_user_created")
    if inspector.has_table("world_commodity_prices"):
        op.execute("DROP INDEX IF EXISTS ix_world_prices_commodity_observed_desc")
        with op.batch_alter_table("world_commodity_prices") as batch_op:
            batch_op.alter_column(
                "currency",
                existing_type=sa.String(length=10),
                existing_nullable=False,
                server_default=None,
            )
