"""Add world fertilizer commodity price tables."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260522_0010"
down_revision = "20260522_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("world_commodity_prices"):
        op.create_table(
            "world_commodity_prices",
            sa.Column("price_id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("commodity_slug", sa.String(length=40), nullable=False),
            sa.Column("quote_type", sa.String(length=80), nullable=False),
            sa.Column("source", sa.String(length=60), nullable=False),
            sa.Column("source_url", sa.String(length=800), nullable=True),
            sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("price_usd_per_tonne", sa.Numeric(12, 2), nullable=False),
            sa.Column("currency", sa.String(length=10), nullable=False),
            sa.Column("confidence_score", sa.Numeric(4, 3), nullable=False),
            sa.Column("raw_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("price_id"),
            sa.UniqueConstraint("commodity_slug", "source", "quote_type", "observed_at", name="uq_world_price"),
        )
        op.create_index(op.f("ix_world_commodity_prices_commodity_slug"), "world_commodity_prices", ["commodity_slug"])
        op.create_index(op.f("ix_world_commodity_prices_created_at"), "world_commodity_prices", ["created_at"])
        op.create_index(op.f("ix_world_commodity_prices_observed_at"), "world_commodity_prices", ["observed_at"])
        op.create_index(op.f("ix_world_commodity_prices_quote_type"), "world_commodity_prices", ["quote_type"])
        op.create_index(op.f("ix_world_commodity_prices_source"), "world_commodity_prices", ["source"])

    if not inspector.has_table("world_commodity_forecasts"):
        op.create_table(
            "world_commodity_forecasts",
            sa.Column("forecast_id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("commodity_slug", sa.String(length=40), nullable=False),
            sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("horizon_days", sa.Integer(), nullable=False),
            sa.Column("forecast_points_json", sa.JSON(), nullable=False),
            sa.Column("model_kind", sa.String(length=80), nullable=False),
            sa.Column("base_price_usd_per_tonne", sa.Numeric(12, 2), nullable=True),
            sa.Column("realized_outcome_json", sa.JSON(), nullable=True),
            sa.PrimaryKeyConstraint("forecast_id"),
        )
        op.create_index(op.f("ix_world_commodity_forecasts_commodity_slug"), "world_commodity_forecasts", ["commodity_slug"])
        op.create_index(op.f("ix_world_commodity_forecasts_generated_at"), "world_commodity_forecasts", ["generated_at"])


def downgrade() -> None:
    op.drop_index(op.f("ix_world_commodity_forecasts_generated_at"), table_name="world_commodity_forecasts")
    op.drop_index(op.f("ix_world_commodity_forecasts_commodity_slug"), table_name="world_commodity_forecasts")
    op.drop_table("world_commodity_forecasts")

    op.drop_index(op.f("ix_world_commodity_prices_source"), table_name="world_commodity_prices")
    op.drop_index(op.f("ix_world_commodity_prices_quote_type"), table_name="world_commodity_prices")
    op.drop_index(op.f("ix_world_commodity_prices_observed_at"), table_name="world_commodity_prices")
    op.drop_index(op.f("ix_world_commodity_prices_created_at"), table_name="world_commodity_prices")
    op.drop_index(op.f("ix_world_commodity_prices_commodity_slug"), table_name="world_commodity_prices")
    op.drop_table("world_commodity_prices")
