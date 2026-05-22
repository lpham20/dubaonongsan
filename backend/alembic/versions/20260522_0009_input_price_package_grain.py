"""Include package size in input price uniqueness grain."""

from __future__ import annotations

from alembic import op


revision = "20260522_0009"
down_revision = "20260522_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("agri_input_price_observations") as batch_op:
        batch_op.drop_constraint("uq_agri_input_price_grain", type_="unique")
        batch_op.create_unique_constraint(
            "uq_agri_input_price_grain",
            ["product_id", "observed_at", "province", "brand", "source_name", "package_size_kg"],
        )


def downgrade() -> None:
    with op.batch_alter_table("agri_input_price_observations") as batch_op:
        batch_op.drop_constraint("uq_agri_input_price_grain", type_="unique")
        batch_op.create_unique_constraint(
            "uq_agri_input_price_grain",
            ["product_id", "observed_at", "province", "brand", "source_name"],
        )
