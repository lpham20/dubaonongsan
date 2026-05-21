"""add fertilizer recommendation sessions and feedback tables

Revision ID: 20260521_0005
Revises: 20260518_0004
Create Date: 2026-05-21
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260521_0005"
down_revision = "20260518_0004"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in set(inspector.get_table_names())


def _create_indexes() -> None:
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_recommendation_sessions_crop_created "
        "ON recommendation_sessions (crop, created_at DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_recommendation_sessions_user_created "
        "ON recommendation_sessions (user_id, created_at DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_recommendation_sessions_crop_variety "
        "ON recommendation_sessions (crop, variety)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_yield_feedback_crop_created "
        "ON yield_feedback (crop, created_at DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_leaf_analysis_crop_sample "
        "ON leaf_analysis (crop, sample_date DESC)"
    )


def _create_training_view() -> None:
    op.execute("DROP VIEW IF EXISTS v_tier2_training_data")
    op.execute(
        """
        CREATE VIEW v_tier2_training_data AS
        SELECT
            s.session_id,
            s.created_at AS recommendation_created_at,
            s.created_date,
            s.user_id,
            s.crop,
            s.variety,
            s.growth_stage,
            s.province,
            s.soil_texture,
            s.yield_target_t_ha,
            s.tree_density_per_ha,
            s.annual_n_kg_ha,
            s.annual_p2o5_kg_ha,
            s.annual_k2o_kg_ha,
            s.confidence_tier,
            s.confidence_score,
            f.actual_yield_t_ha,
            f.harvest_date,
            f.fertilizer_followed_pct,
            f.rating,
            f.note AS feedback_note,
            l.sample_date AS leaf_sample_date,
            l.n_pct AS leaf_n_pct,
            l.p_pct AS leaf_p_pct,
            l.k_pct AS leaf_k_pct,
            l.ca_pct AS leaf_ca_pct,
            l.mg_pct AS leaf_mg_pct,
            l.b_mg_kg AS leaf_b_mg_kg,
            l.zn_mg_kg AS leaf_zn_mg_kg
        FROM recommendation_sessions s
        LEFT JOIN yield_feedback f ON f.session_id = s.session_id
        LEFT JOIN leaf_analysis l ON l.session_id = s.session_id
        WHERE f.feedback_id IS NOT NULL OR l.analysis_id IS NOT NULL
        """
    )


def upgrade() -> None:
    if not _has_table("recommendation_sessions"):
        op.create_table(
            "recommendation_sessions",
            sa.Column("session_id", sa.String(length=36), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("app_users.user_id", ondelete="SET NULL"), nullable=True),
            sa.Column("crop", sa.String(length=40), nullable=False),
            sa.Column("variety", sa.String(length=80), nullable=True),
            sa.Column("growth_stage", sa.String(length=50), nullable=True),
            sa.Column("province", sa.String(length=100), nullable=True),
            sa.Column("soil_texture", sa.String(length=50), nullable=True),
            sa.Column("yield_target_t_ha", sa.Numeric(8, 2), nullable=True),
            sa.Column("tree_density_per_ha", sa.Integer(), nullable=True),
            sa.Column("annual_n_kg_ha", sa.Numeric(8, 2), nullable=True),
            sa.Column("annual_p2o5_kg_ha", sa.Numeric(8, 2), nullable=True),
            sa.Column("annual_k2o_kg_ha", sa.Numeric(8, 2), nullable=True),
            sa.Column("confidence_tier", sa.String(length=20), nullable=True),
            sa.Column("confidence_score", sa.Numeric(4, 2), nullable=True),
            sa.Column("engine_version", sa.String(length=40), nullable=True),
            sa.Column("knowledge_base_version", sa.String(length=100), nullable=True),
            sa.Column("request_json", sa.JSON(), nullable=True),
            sa.Column("response_json", sa.JSON(), nullable=True),
            sa.Column("ip_address", sa.String(length=64), nullable=True),
            sa.Column("user_agent", sa.String(length=500), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_date", sa.Date(), nullable=True),
        )
    if not _has_table("yield_feedback"):
        op.create_table(
            "yield_feedback",
            sa.Column("feedback_id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("session_id", sa.String(length=36), sa.ForeignKey("recommendation_sessions.session_id", ondelete="CASCADE"), nullable=False, unique=True),
            sa.Column("crop", sa.String(length=40), nullable=False),
            sa.Column("variety", sa.String(length=80), nullable=True),
            sa.Column("actual_yield_t_ha", sa.Numeric(8, 2), nullable=False),
            sa.Column("harvest_date", sa.Date(), nullable=True),
            sa.Column("yield_unit", sa.String(length=20), nullable=False, server_default="t_ha"),
            sa.Column("fertilizer_followed_pct", sa.Numeric(5, 2), nullable=True),
            sa.Column("rating", sa.Integer(), nullable=True),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("contact_phone", sa.String(length=40), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if not _has_table("leaf_analysis"):
        op.create_table(
            "leaf_analysis",
            sa.Column("analysis_id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("session_id", sa.String(length=36), sa.ForeignKey("recommendation_sessions.session_id", ondelete="SET NULL"), nullable=True),
            sa.Column("crop", sa.String(length=40), nullable=False),
            sa.Column("variety", sa.String(length=80), nullable=True),
            sa.Column("sample_date", sa.Date(), nullable=True),
            sa.Column("n_pct", sa.Numeric(6, 3), nullable=True),
            sa.Column("p_pct", sa.Numeric(6, 3), nullable=True),
            sa.Column("k_pct", sa.Numeric(6, 3), nullable=True),
            sa.Column("ca_pct", sa.Numeric(6, 3), nullable=True),
            sa.Column("mg_pct", sa.Numeric(6, 3), nullable=True),
            sa.Column("b_mg_kg", sa.Numeric(8, 2), nullable=True),
            sa.Column("zn_mg_kg", sa.Numeric(8, 2), nullable=True),
            sa.Column("lab_name", sa.String(length=160), nullable=True),
            sa.Column("raw_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    _create_indexes()
    _create_training_view()


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS v_tier2_training_data")
    for index_name in [
        "ix_leaf_analysis_crop_sample",
        "ix_yield_feedback_crop_created",
        "ix_recommendation_sessions_crop_variety",
        "ix_recommendation_sessions_user_created",
        "ix_recommendation_sessions_crop_created",
    ]:
        op.execute(f"DROP INDEX IF EXISTS {index_name}")
    if _has_table("leaf_analysis"):
        op.drop_table("leaf_analysis")
    if _has_table("yield_feedback"):
        op.drop_table("yield_feedback")
    if _has_table("recommendation_sessions"):
        op.drop_table("recommendation_sessions")
