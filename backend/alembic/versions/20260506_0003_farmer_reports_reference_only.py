"""keep farmer reports separate from training prices

Revision ID: 20260506_0003
Revises: 20260505_0002
Create Date: 2026-05-06
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260506_0003"
down_revision = "20260505_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_price_reports",
        sa.Column("approved_for_training", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.execute(
        """
        INSERT INTO user_price_reports (
            crop_type,
            region_id,
            variety_id,
            quality_grade,
            price_vnd,
            note,
            reporter_name,
            approved_for_training,
            created_at
        )
        SELECT
            d.crop_type,
            d.region_id,
            d.variety_id,
            d.quality_grade,
            COALESCE(d.max_price_vnd, d.min_price_vnd),
            'Chuyển từ bảng giá huấn luyện cũ sang bảng báo giá nông dân',
            NULL,
            0,
            d.record_timestamp
        FROM daily_market_prices d
        WHERE d.exchange_source = 'Người dùng báo giá'
          AND COALESCE(d.max_price_vnd, d.min_price_vnd) IS NOT NULL
          AND NOT EXISTS (
              SELECT 1
              FROM user_price_reports r
              WHERE r.crop_type = d.crop_type
                AND r.region_id = d.region_id
                AND r.variety_id = d.variety_id
                AND COALESCE(r.quality_grade, '') = COALESCE(d.quality_grade, '')
                AND r.created_at = d.record_timestamp
          )
        """
    )
    op.execute("DELETE FROM daily_market_prices WHERE exchange_source = 'Người dùng báo giá'")


def downgrade() -> None:
    op.drop_column("user_price_reports", "approved_for_training")
