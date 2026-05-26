"""Include package size in input price uniqueness grain."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260522_0009"
down_revision = "20260522_0008"
branch_labels = None
depends_on = None


def _unique_columns(name: str) -> list[str]:
    inspector = sa.inspect(op.get_bind())
    if "agri_input_price_observations" not in set(inspector.get_table_names()):
        return []
    for constraint in inspector.get_unique_constraints("agri_input_price_observations"):
        if constraint.get("name") == name:
            return list(constraint.get("column_names") or [])
    return []


def upgrade() -> None:
    desired = ["product_id", "observed_at", "province", "brand", "source_name", "package_size_kg"]
    if _unique_columns("uq_agri_input_price_grain") == desired:
        return
    with op.batch_alter_table("agri_input_price_observations") as batch_op:
        batch_op.drop_constraint("uq_agri_input_price_grain", type_="unique")
        batch_op.create_unique_constraint(
            "uq_agri_input_price_grain",
            ["product_id", "observed_at", "province", "brand", "source_name", "package_size_kg"],
        )


def downgrade() -> None:
    desired = ["product_id", "observed_at", "province", "brand", "source_name"]
    if _unique_columns("uq_agri_input_price_grain") == desired:
        return
    with op.batch_alter_table("agri_input_price_observations") as batch_op:
        batch_op.drop_constraint("uq_agri_input_price_grain", type_="unique")
        batch_op.create_unique_constraint(
            "uq_agri_input_price_grain",
            ["product_id", "observed_at", "province", "brand", "source_name"],
        )
