"""add roi v2 scenario columns

Revision ID: 20260522_0011
Revises: 20260522_0010
Create Date: 2026-05-22 21:15:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260522_0011"
down_revision = "20260522_0010"
branch_labels = None
depends_on = None


def _has_column(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    if table_name not in set(inspector.get_table_names()):
        return False
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    with op.batch_alter_table("roi_scenarios") as batch_op:
        if not _has_column("roi_scenarios", "scenarios_json"):
            batch_op.add_column(sa.Column("scenarios_json", sa.JSON(), nullable=True))
        if not _has_column("roi_scenarios", "forecast_model_kind"):
            batch_op.add_column(sa.Column("forecast_model_kind", sa.String(length=80), nullable=True))
        if not _has_column("roi_scenarios", "confidence_score"):
            batch_op.add_column(sa.Column("confidence_score", sa.Numeric(4, 3), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("roi_scenarios") as batch_op:
        if _has_column("roi_scenarios", "confidence_score"):
            batch_op.drop_column("confidence_score")
        if _has_column("roi_scenarios", "forecast_model_kind"):
            batch_op.drop_column("forecast_model_kind")
        if _has_column("roi_scenarios", "scenarios_json"):
            batch_op.drop_column("scenarios_json")
