"""add user price reports

Revision ID: 20260505_0002
Revises: 20260501_0001
Create Date: 2026-05-05
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260505_0002"
down_revision = "20260501_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_price_reports",
        sa.Column("report_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("crop_type", sa.String(length=30), nullable=False),
        sa.Column("region_id", sa.Integer(), sa.ForeignKey("production_regions.region_id"), nullable=False),
        sa.Column("variety_id", sa.Integer(), sa.ForeignKey("durian_varieties.variety_id"), nullable=False),
        sa.Column("quality_grade", sa.String(length=50), nullable=True),
        sa.Column("price_vnd", sa.Numeric(12, 2), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("reporter_name", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_user_price_reports_crop_created ON user_price_reports (crop_type, created_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_user_price_reports_region_created ON user_price_reports (region_id, created_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_user_price_reports_variety_created ON user_price_reports (variety_id, created_at DESC)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_user_price_reports_variety_created")
    op.execute("DROP INDEX IF EXISTS ix_user_price_reports_region_created")
    op.execute("DROP INDEX IF EXISTS ix_user_price_reports_crop_created")
    op.drop_table("user_price_reports")
