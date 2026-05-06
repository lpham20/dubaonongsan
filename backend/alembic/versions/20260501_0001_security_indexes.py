"""baseline security and performance indexes

Revision ID: 20260501_0001
Revises:
Create Date: 2026-05-01
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.db import Base
from app import models  # noqa: F401

revision = "20260501_0001"
down_revision = None
branch_labels = None
depends_on = None


def _ensure_column(inspector: sa.Inspector, table_name: str, column: sa.Column) -> None:
    columns = {item["name"] for item in inspector.get_columns(table_name)}
    if column.name not in columns:
        op.add_column(table_name, column)


def _prepare_hypertable_primary_key(inspector: sa.Inspector, table_name: str, time_column: str) -> None:
    pk = inspector.get_pk_constraint(table_name)
    pk_columns = list(pk.get("constrained_columns") or [])
    pk_name = pk.get("name")
    if not pk_columns or time_column in pk_columns or not pk_name:
        return
    op.drop_constraint(pk_name, table_name, type_="primary")
    op.create_primary_key(f"pk_{table_name}_time", table_name, [*pk_columns, time_column])


def _enable_timescale_if_available(bind: sa.engine.Connection, inspector: sa.Inspector) -> None:
    if bind.dialect.name != "postgresql":
        return
    has_timescale = bind.execute(
        sa.text("SELECT 1 FROM pg_available_extensions WHERE name = 'timescaledb'")
    ).scalar()
    if not has_timescale:
        return

    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")
    for table_name, time_column in [
        ("daily_market_prices", "record_timestamp"),
        ("weather_environmental_metrics", "record_timestamp"),
        ("iot_sensor_telemetry", "record_timestamp"),
    ]:
        _prepare_hypertable_primary_key(inspector, table_name, time_column)
        op.execute(
            sa.text(
                f"SELECT create_hypertable('{table_name}', '{time_column}', "
                "if_not_exists => TRUE, migrate_data => TRUE)"
            )
        )

    op.execute(
        """
        ALTER TABLE daily_market_prices SET (
            timescaledb.compress,
            timescaledb.compress_segmentby = 'variety_id, region_id, crop_type'
        )
        """
    )
    op.execute(
        sa.text(
            "SELECT add_compression_policy('daily_market_prices', "
            "INTERVAL '90 days', if_not_exists => TRUE)"
        )
    )


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)
    inspector = sa.inspect(bind)

    _ensure_column(
        inspector,
        "durian_varieties",
        sa.Column("crop_type", sa.String(length=30), server_default="sau_rieng", nullable=False),
    )
    _ensure_column(
        inspector,
        "daily_market_prices",
        sa.Column("crop_type", sa.String(length=30), server_default="sau_rieng", nullable=False),
    )
    _ensure_column(
        inspector,
        "app_users",
        sa.Column("is_admin", sa.Boolean(), server_default=sa.false(), nullable=False),
    )

    _enable_timescale_if_available(bind, inspector)

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_daily_market_prices_crop_region_variety_time "
        "ON daily_market_prices (crop_type, region_id, variety_id, record_timestamp DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_daily_market_prices_crop_time "
        "ON daily_market_prices (crop_type, record_timestamp DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_daily_market_prices_crop_source "
        "ON daily_market_prices (crop_type, exchange_source)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_daily_market_prices_crop_region "
        "ON daily_market_prices (crop_type, region_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_weather_region_time_desc "
        "ON weather_environmental_metrics (region_id, record_timestamp DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_iot_region_time_desc "
        "ON iot_sensor_telemetry (region_id, record_timestamp DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_news_articles_category_published "
        "ON news_articles (category, published_at DESC, scraped_at DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_news_articles_published "
        "ON news_articles (published_at DESC, scraped_at DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_guide_posts_crop_category_published "
        "ON guide_posts (crop_type, category, published_at DESC)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_news_articles_scraped ON news_articles (scraped_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_watchlist_user_created ON watchlist_items (user_id, created_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_subscribers_source ON subscribers (source, created_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_subscribers_created_at ON subscribers (created_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_platform_job_runs_name_started ON platform_job_runs (job_name, started_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_model_training_runs_crop_started ON model_training_runs (crop_type, started_at DESC)")

    if bind.dialect.name == "postgresql":
        op.execute("DROP INDEX IF EXISTS news_articles_source_url_key")
        op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_news_url_hash ON news_articles (md5(source_url))")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP INDEX IF EXISTS uq_news_url_hash")
    for index_name, table_name in [
        ("ix_model_training_runs_crop_started", "model_training_runs"),
        ("ix_platform_job_runs_name_started", "platform_job_runs"),
        ("ix_subscribers_created_at", "subscribers"),
        ("ix_subscribers_source", "subscribers"),
        ("ix_watchlist_user_created", "watchlist_items"),
        ("ix_news_articles_scraped", "news_articles"),
        ("ix_guide_posts_crop_category_published", "guide_posts"),
        ("ix_news_articles_published", "news_articles"),
        ("ix_news_articles_category_published", "news_articles"),
        ("ix_iot_region_time_desc", "iot_sensor_telemetry"),
        ("ix_weather_region_time_desc", "weather_environmental_metrics"),
        ("ix_daily_market_prices_crop_region", "daily_market_prices"),
        ("ix_daily_market_prices_crop_source", "daily_market_prices"),
        ("ix_daily_market_prices_crop_time", "daily_market_prices"),
        ("ix_daily_market_prices_crop_region_variety_time", "daily_market_prices"),
    ]:
        op.execute(f"DROP INDEX IF EXISTS {index_name}")
