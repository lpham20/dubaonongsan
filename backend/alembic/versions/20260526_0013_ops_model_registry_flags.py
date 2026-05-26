"""add ops checkpoints, model registry and feature flags

Revision ID: 20260526_0013
Revises: 20260526_0012
Create Date: 2026-05-26 21:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260526_0013"
down_revision = "20260526_0012"
branch_labels = None
depends_on = None


CROP_CHECK = "crop_type IN ('sau_rieng', 'ca_phe', 'ho_tieu', 'lua')"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("model_ready_backfill_checkpoints"):
        op.create_table(
            "model_ready_backfill_checkpoints",
            sa.Column("checkpoint_id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("crop_type", sa.String(length=30), nullable=False),
            sa.Column("region_id", sa.Integer(), nullable=False),
            sa.Column("variety_id", sa.Integer(), nullable=False),
            sa.Column("source", sa.String(length=100), nullable=False),
            sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
            sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("records_inserted", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("records_updated", sa.Integer(), nullable=False, server_default="0"),
            sa.UniqueConstraint("crop_type", "region_id", "variety_id", "source", name="uq_model_ready_checkpoint_pair"),
        )
        op.create_index(
            "ix_model_ready_checkpoint_crop_window",
            "model_ready_backfill_checkpoints",
            ["crop_type", "window_end"],
        )
        op.create_index("ix_model_ready_backfill_checkpoints_crop_type", "model_ready_backfill_checkpoints", ["crop_type"])
        op.create_index("ix_model_ready_backfill_checkpoints_region_id", "model_ready_backfill_checkpoints", ["region_id"])
        op.create_index("ix_model_ready_backfill_checkpoints_variety_id", "model_ready_backfill_checkpoints", ["variety_id"])
        op.create_index("ix_model_ready_backfill_checkpoints_completed_at", "model_ready_backfill_checkpoints", ["completed_at"])

    if not inspector.has_table("ml_model_versions"):
        op.create_table(
            "ml_model_versions",
            sa.Column("version_id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("model_key", sa.String(length=80), nullable=False),
            sa.Column("model_kind", sa.String(length=100), nullable=False),
            sa.Column("crop_type", sa.String(length=30), nullable=True),
            sa.Column("commodity_slug", sa.String(length=40), nullable=True),
            sa.Column("artifact_path", sa.String(length=500), nullable=False),
            sa.Column("artifact_sha256", sa.String(length=64), nullable=False),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
            sa.Column("metrics_json", sa.JSON(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("model_key", "artifact_sha256", name="uq_ml_model_version_artifact"),
        )
        op.create_index("ix_ml_model_versions_model_key", "ml_model_versions", ["model_key"])
        op.create_index("ix_ml_model_versions_crop_type", "ml_model_versions", ["crop_type"])
        op.create_index("ix_ml_model_versions_commodity_slug", "ml_model_versions", ["commodity_slug"])
        op.create_index("ix_ml_model_versions_is_active", "ml_model_versions", ["is_active"])
        op.create_index("ix_ml_model_versions_created_at", "ml_model_versions", ["created_at"])
        op.create_index("ix_ml_model_versions_activated_at", "ml_model_versions", ["activated_at"])
        op.create_index("ix_ml_model_versions_model_active", "ml_model_versions", ["model_key", "is_active"])

    if not inspector.has_table("feature_flags"):
        op.create_table(
            "feature_flags",
            sa.Column("flag_key", sa.String(length=120), primary_key=True),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_by", sa.Integer(), sa.ForeignKey("app_users.user_id", ondelete="SET NULL"), nullable=True),
        )
        op.create_index("ix_feature_flags_enabled", "feature_flags", ["enabled"])
        op.create_index("ix_feature_flags_updated_at", "feature_flags", ["updated_at"])
        op.create_index("ix_feature_flags_updated_by", "feature_flags", ["updated_by"])

    if bind.dialect.name == "postgresql":
        _add_check_constraint_if_missing(inspector, "daily_market_prices", "ck_daily_market_prices_crop_type", CROP_CHECK)
        _add_check_constraint_if_missing(inspector, "user_price_reports", "ck_user_price_reports_crop_type", CROP_CHECK)
        _add_check_constraint_if_missing(inspector, "watchlist_items", "ck_watchlist_items_crop_type", CROP_CHECK)
        _alter_confidence_precision()


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if bind.dialect.name == "postgresql":
        op.alter_column(
            "recommendation_sessions",
            "confidence_score",
            type_=sa.Numeric(4, 2),
            existing_type=sa.Numeric(4, 3),
            existing_nullable=True,
        )
        op.alter_column(
            "agri_input_price_observations",
            "confidence_score",
            type_=sa.Numeric(4, 2),
            existing_type=sa.Numeric(4, 3),
            existing_nullable=False,
        )
        for table, name in (
            ("watchlist_items", "ck_watchlist_items_crop_type"),
            ("user_price_reports", "ck_user_price_reports_crop_type"),
            ("daily_market_prices", "ck_daily_market_prices_crop_type"),
        ):
            if inspector.has_table(table):
                op.execute(sa.text(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {name}"))

    for index_name, table_name in (
        ("ix_feature_flags_updated_by", "feature_flags"),
        ("ix_feature_flags_updated_at", "feature_flags"),
        ("ix_feature_flags_enabled", "feature_flags"),
    ):
        if inspector.has_table(table_name):
            op.drop_index(index_name, table_name=table_name)
    if inspector.has_table("feature_flags"):
        op.drop_table("feature_flags")

    for index_name, table_name in (
        ("ix_ml_model_versions_model_active", "ml_model_versions"),
        ("ix_ml_model_versions_activated_at", "ml_model_versions"),
        ("ix_ml_model_versions_created_at", "ml_model_versions"),
        ("ix_ml_model_versions_is_active", "ml_model_versions"),
        ("ix_ml_model_versions_commodity_slug", "ml_model_versions"),
        ("ix_ml_model_versions_crop_type", "ml_model_versions"),
        ("ix_ml_model_versions_model_key", "ml_model_versions"),
    ):
        if inspector.has_table(table_name):
            op.drop_index(index_name, table_name=table_name)
    if inspector.has_table("ml_model_versions"):
        op.drop_table("ml_model_versions")

    for index_name, table_name in (
        ("ix_model_ready_backfill_checkpoints_completed_at", "model_ready_backfill_checkpoints"),
        ("ix_model_ready_backfill_checkpoints_variety_id", "model_ready_backfill_checkpoints"),
        ("ix_model_ready_backfill_checkpoints_region_id", "model_ready_backfill_checkpoints"),
        ("ix_model_ready_backfill_checkpoints_crop_type", "model_ready_backfill_checkpoints"),
        ("ix_model_ready_checkpoint_crop_window", "model_ready_backfill_checkpoints"),
    ):
        if inspector.has_table(table_name):
            op.drop_index(index_name, table_name=table_name)
    if inspector.has_table("model_ready_backfill_checkpoints"):
        op.drop_table("model_ready_backfill_checkpoints")


def _add_check_constraint_if_missing(inspector: sa.Inspector, table: str, name: str, condition: str) -> None:
    if not inspector.has_table(table):
        return
    existing = {constraint.get("name") for constraint in inspector.get_check_constraints(table)}
    if name in existing:
        return
    op.execute(sa.text(f"ALTER TABLE {table} ADD CONSTRAINT {name} CHECK ({condition}) NOT VALID"))


def _alter_confidence_precision() -> None:
    op.alter_column(
        "agri_input_price_observations",
        "confidence_score",
        type_=sa.Numeric(4, 3),
        existing_type=sa.Numeric(4, 2),
        existing_nullable=False,
    )
    op.alter_column(
        "recommendation_sessions",
        "confidence_score",
        type_=sa.Numeric(4, 3),
        existing_type=sa.Numeric(4, 2),
        existing_nullable=True,
    )
