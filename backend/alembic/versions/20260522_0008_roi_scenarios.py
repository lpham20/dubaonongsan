"""add roi scenarios

Revision ID: 20260522_0008
Revises: 20260522_0007
Create Date: 2026-05-22
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260522_0008"
down_revision = "20260522_0007"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return table_name in set(inspector.get_table_names())


def upgrade() -> None:
    if _has_table("roi_scenarios"):
        return
    op.create_table(
        "roi_scenarios",
        sa.Column("scenario_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("app_users.user_id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "session_id",
            sa.String(length=36),
            sa.ForeignKey("recommendation_sessions.session_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("crop", sa.String(length=40), nullable=False),
        sa.Column("crop_area_ha", sa.Numeric(8, 2), nullable=False),
        sa.Column("expected_yield_t_ha", sa.Numeric(8, 2), nullable=False),
        sa.Column("expected_sell_price_vnd_per_kg", sa.Numeric(12, 2), nullable=False),
        sa.Column("fertilizer_cost_vnd_per_ha", sa.Numeric(14, 2), nullable=False),
        sa.Column("fertilizer_breakdown_json", sa.JSON(), nullable=True),
        sa.Column("other_input_cost_vnd_per_ha", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("labor_cost_vnd_per_ha", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("total_revenue_vnd", sa.Numeric(16, 2), nullable=True),
        sa.Column("total_cost_vnd", sa.Numeric(16, 2), nullable=True),
        sa.Column("net_profit_vnd", sa.Numeric(16, 2), nullable=True),
        sa.Column("roi_pct", sa.Numeric(8, 2), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_roi_scenarios_user_id", "roi_scenarios", ["user_id"])
    op.create_index("ix_roi_scenarios_session_id", "roi_scenarios", ["session_id"])
    op.create_index("ix_roi_scenarios_crop", "roi_scenarios", ["crop"])
    op.create_index("ix_roi_scenarios_created_at", "roi_scenarios", ["created_at"])


def downgrade() -> None:
    for index_name in [
        "ix_roi_scenarios_created_at",
        "ix_roi_scenarios_crop",
        "ix_roi_scenarios_session_id",
        "ix_roi_scenarios_user_id",
    ]:
        op.execute(f"DROP INDEX IF EXISTS {index_name}")
    if _has_table("roi_scenarios"):
        op.drop_table("roi_scenarios")
