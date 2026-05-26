from datetime import date, datetime
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.db import Base


class DurianVariety(Base):
    __tablename__ = "durian_varieties"

    variety_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    crop_type: Mapped[str] = mapped_column(String(30), default="sau_rieng", index=True)
    description: Mapped[str | None] = mapped_column(Text)

    prices: Mapped[list["DailyMarketPrice"]] = relationship(back_populates="variety")


class ProductionRegion(Base):
    __tablename__ = "production_regions"

    region_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    region_name: Mapped[str] = mapped_column(String(100), nullable=False)
    province: Mapped[str | None] = mapped_column(String(100))
    export_code: Mapped[str | None] = mapped_column(String(50))
    risk_level_index: Mapped[float] = mapped_column(Numeric(3, 2), default=0.0)

    prices: Mapped[list["DailyMarketPrice"]] = relationship(back_populates="region")
    weather: Mapped[list["WeatherEnvironmentalMetric"]] = relationship(back_populates="region")
    telemetry: Mapped[list["IotSensorTelemetry"]] = relationship(back_populates="region")


class DailyMarketPrice(Base):
    __tablename__ = "daily_market_prices"
    __table_args__ = (
        CheckConstraint("crop_type IN ('sau_rieng', 'ca_phe', 'ho_tieu', 'lua')", name="ck_daily_market_prices_crop_type"),
        UniqueConstraint(
            "record_timestamp",
            "variety_id",
            "region_id",
            "quality_grade",
            "exchange_source",
            name="uq_daily_market_prices_grain",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    record_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    variety_id: Mapped[int] = mapped_column(ForeignKey("durian_varieties.variety_id"), index=True)
    crop_type: Mapped[str] = mapped_column(String(30), default="sau_rieng", index=True)
    quality_grade: Mapped[str | None] = mapped_column(String(50))
    region_id: Mapped[int] = mapped_column(ForeignKey("production_regions.region_id"), index=True)
    exchange_source: Mapped[str | None] = mapped_column(String(100))
    min_price_vnd: Mapped[float | None] = mapped_column(Numeric(12, 2))
    max_price_vnd: Mapped[float | None] = mapped_column(Numeric(12, 2))
    volume_traded_tons: Mapped[float | None] = mapped_column(Numeric(10, 2))

    variety: Mapped[DurianVariety] = relationship(back_populates="prices")
    region: Mapped[ProductionRegion] = relationship(back_populates="prices")


class AgriInputProduct(Base):
    __tablename__ = "agri_input_products"

    product_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    category: Mapped[str] = mapped_column(String(50), default="fertilizer", index=True)
    product_type: Mapped[str] = mapped_column(String(80), index=True)
    nutrient_profile: Mapped[str | None] = mapped_column(String(120))
    standard_unit: Mapped[str] = mapped_column(String(30), default="kg")
    package_label: Mapped[str | None] = mapped_column(String(80))
    package_size_kg: Mapped[float | None] = mapped_column(Numeric(8, 2))
    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1", index=True)

    observations: Mapped[list["AgriInputPriceObservation"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
    )


class AgriInputPriceObservation(Base):
    __tablename__ = "agri_input_price_observations"
    __table_args__ = (
        UniqueConstraint(
            "product_id",
            "observed_at",
            "province",
            "brand",
            "source_name",
            "package_size_kg",
            name="uq_agri_input_price_grain",
        ),
    )

    observation_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("agri_input_products.product_id"), index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    province: Mapped[str] = mapped_column(String(100), index=True)
    region_name: Mapped[str | None] = mapped_column(String(100), index=True)
    brand: Mapped[str | None] = mapped_column(String(120), index=True)
    seller_name: Mapped[str | None] = mapped_column(String(160))
    source_name: Mapped[str] = mapped_column(String(160), index=True)
    source_url: Mapped[str | None] = mapped_column(String(800))
    package_price_vnd: Mapped[float | None] = mapped_column(Numeric(14, 2))
    normalized_price_vnd: Mapped[float] = mapped_column(Numeric(14, 2))
    normalized_unit: Mapped[str] = mapped_column(String(30), default="kg")
    package_size_kg: Mapped[float | None] = mapped_column(Numeric(8, 2))
    confidence_score: Mapped[float] = mapped_column(Numeric(4, 3), default=0.55)
    data_kind: Mapped[str] = mapped_column(String(40), default="reference", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    product: Mapped[AgriInputProduct] = relationship(back_populates="observations")


class WorldCommodityPrice(Base):
    """World fertilizer commodity prices in nominal USD per metric tonne."""

    __tablename__ = "world_commodity_prices"
    __table_args__ = (
        UniqueConstraint("commodity_slug", "source", "quote_type", "observed_at", name="uq_world_price"),
        Index("ix_world_prices_commodity_observed_desc", "commodity_slug", "observed_at"),
    )

    price_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    commodity_slug: Mapped[str] = mapped_column(String(40), index=True)
    quote_type: Mapped[str] = mapped_column(String(80), index=True)
    source: Mapped[str] = mapped_column(String(60), index=True)
    source_url: Mapped[str | None] = mapped_column(String(800))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    price_usd_per_tonne: Mapped[float] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(10), default="USD", server_default="USD")
    confidence_score: Mapped[float] = mapped_column(Numeric(4, 3), default=0.75)
    raw_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class WorldCommodityForecast(Base):
    """Forecast snapshot for later accuracy tracking."""

    __tablename__ = "world_commodity_forecasts"

    forecast_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    commodity_slug: Mapped[str] = mapped_column(String(40), index=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    horizon_days: Mapped[int] = mapped_column(Integer)
    forecast_points_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    model_kind: Mapped[str] = mapped_column(String(80))
    base_price_usd_per_tonne: Mapped[float | None] = mapped_column(Numeric(12, 2))
    realized_outcome_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    @validates("forecast_points_json")
    def _validate_forecast_points(self, _key: str, value: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not isinstance(value, list) or not value:
            raise ValueError("forecast_points_json must be a non-empty list")
        required = {"date", "price_usd_per_tonne"}
        for index, point in enumerate(value):
            if not isinstance(point, dict):
                raise ValueError(f"forecast point {index} must be an object")
            missing = required - set(point)
            if missing:
                raise ValueError(f"forecast point {index} missing keys: {sorted(missing)}")
            try:
                price = float(point["price_usd_per_tonne"])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"forecast point {index} has invalid price") from exc
            if price <= 0:
                raise ValueError(f"forecast point {index} price must be positive")
        return value


class RoiScenario(Base):
    __tablename__ = "roi_scenarios"

    scenario_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("app_users.user_id", ondelete="CASCADE"), index=True)
    session_id: Mapped[str | None] = mapped_column(ForeignKey("recommendation_sessions.session_id", ondelete="SET NULL"), index=True)
    crop: Mapped[str] = mapped_column(String(40), index=True)
    crop_area_ha: Mapped[float] = mapped_column(Numeric(8, 2))
    expected_yield_t_ha: Mapped[float] = mapped_column(Numeric(8, 2))
    expected_sell_price_vnd_per_kg: Mapped[float] = mapped_column(Numeric(12, 2))
    fertilizer_cost_vnd_per_ha: Mapped[float] = mapped_column(Numeric(14, 2))
    fertilizer_breakdown_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    other_input_cost_vnd_per_ha: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    labor_cost_vnd_per_ha: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    total_revenue_vnd: Mapped[float | None] = mapped_column(Numeric(16, 2))
    total_cost_vnd: Mapped[float | None] = mapped_column(Numeric(16, 2))
    net_profit_vnd: Mapped[float | None] = mapped_column(Numeric(16, 2))
    roi_pct: Mapped[float | None] = mapped_column(Numeric(8, 2))
    scenarios_json: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON)
    forecast_model_kind: Mapped[str | None] = mapped_column(String(80))
    confidence_score: Mapped[float | None] = mapped_column(Numeric(4, 3))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class UserPriceReport(Base):
    __tablename__ = "user_price_reports"
    __table_args__ = (
        CheckConstraint("crop_type IN ('sau_rieng', 'ca_phe', 'ho_tieu', 'lua')", name="ck_user_price_reports_crop_type"),
    )

    report_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    crop_type: Mapped[str] = mapped_column(String(30), index=True)
    region_id: Mapped[int] = mapped_column(ForeignKey("production_regions.region_id"), index=True)
    variety_id: Mapped[int] = mapped_column(ForeignKey("durian_varieties.variety_id"), index=True)
    quality_grade: Mapped[str | None] = mapped_column(String(50))
    price_vnd: Mapped[float] = mapped_column(Numeric(12, 2))
    note: Mapped[str | None] = mapped_column(Text)
    reporter_name: Mapped[str | None] = mapped_column(String(120))
    approved_for_training: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    region: Mapped[ProductionRegion] = relationship()
    variety: Mapped[DurianVariety] = relationship()


class WeatherEnvironmentalMetric(Base):
    __tablename__ = "weather_environmental_metrics"
    __table_args__ = (UniqueConstraint("record_timestamp", "region_id", name="uq_weather_grain"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    record_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    region_id: Mapped[int] = mapped_column(ForeignKey("production_regions.region_id"), index=True)
    temp_max_celsius: Mapped[float | None] = mapped_column(Numeric(5, 2))
    temp_min_celsius: Mapped[float | None] = mapped_column(Numeric(5, 2))
    humidity_percent: Mapped[float | None] = mapped_column(Numeric(5, 2))
    precipitation_mm: Mapped[float | None] = mapped_column(Numeric(5, 2))
    wind_speed_kmh: Mapped[float | None] = mapped_column(Numeric(5, 2))
    cloud_cover_index: Mapped[float | None] = mapped_column(Numeric(5, 2))

    region: Mapped[ProductionRegion] = relationship(back_populates="weather")


class IotSensorTelemetry(Base):
    __tablename__ = "iot_sensor_telemetry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    record_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    device_id: Mapped[str] = mapped_column(String(50), index=True)
    region_id: Mapped[int] = mapped_column(ForeignKey("production_regions.region_id"), index=True)
    maturity_index: Mapped[float] = mapped_column(Numeric(4, 2))
    status: Mapped[str | None] = mapped_column(String(50))

    region: Mapped[ProductionRegion] = relationship(back_populates="telemetry")


class ScrapeRun(Base):
    __tablename__ = "scrape_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(100), index=True)
    source_url: Mapped[str] = mapped_column(String(500))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30), default="running")
    records_found: Mapped[int] = mapped_column(Integer, default=0)
    records_inserted: Mapped[int] = mapped_column(Integer, default=0)
    records_updated: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)


class AppUser(Base):
    __tablename__ = "app_users"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, server_default="0", index=True)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False, server_default="0")
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    watchlist: Mapped[list["WatchlistItem"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class RevokedToken(Base):
    __tablename__ = "revoked_tokens"

    jti: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("app_users.user_id"), index=True)
    revoked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"
    __table_args__ = (
        CheckConstraint("crop_type IN ('sau_rieng', 'ca_phe', 'ho_tieu', 'lua')", name="ck_watchlist_items_crop_type"),
        UniqueConstraint("user_id", "crop_type", "region_id", "variety_id", name="uq_watchlist_market"),
        Index("ix_watchlist_user_created", "user_id", "created_at"),
    )

    item_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("app_users.user_id"), index=True)
    crop_type: Mapped[str] = mapped_column(String(30), index=True)
    region_id: Mapped[int] = mapped_column(ForeignKey("production_regions.region_id"), index=True)
    variety_id: Mapped[int] = mapped_column(ForeignKey("durian_varieties.variety_id"), index=True)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    user: Mapped[AppUser] = relationship(back_populates="watchlist")
    region: Mapped[ProductionRegion] = relationship()
    variety: Mapped[DurianVariety] = relationship()


class RecommendationSession(Base):
    __tablename__ = "recommendation_sessions"

    session_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("app_users.user_id", ondelete="SET NULL"), index=True)
    crop: Mapped[str] = mapped_column(String(40), index=True)
    variety: Mapped[str | None] = mapped_column(String(80), index=True)
    growth_stage: Mapped[str | None] = mapped_column(String(50), index=True)
    province: Mapped[str | None] = mapped_column(String(100), index=True)
    soil_texture: Mapped[str | None] = mapped_column(String(50))
    yield_target_t_ha: Mapped[float | None] = mapped_column(Numeric(8, 2))
    tree_density_per_ha: Mapped[int | None] = mapped_column(Integer)
    annual_n_kg_ha: Mapped[float | None] = mapped_column(Numeric(8, 2))
    annual_p2o5_kg_ha: Mapped[float | None] = mapped_column(Numeric(8, 2))
    annual_k2o_kg_ha: Mapped[float | None] = mapped_column(Numeric(8, 2))
    confidence_tier: Mapped[str | None] = mapped_column(String(20), index=True)
    confidence_score: Mapped[float | None] = mapped_column(Numeric(4, 3))
    engine_version: Mapped[str | None] = mapped_column(String(40))
    knowledge_base_version: Mapped[str | None] = mapped_column(String(100))
    request_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    response_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    ip_address: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_date: Mapped[date | None] = mapped_column(Date, index=True)

    feedback: Mapped["YieldFeedback | None"] = relationship(back_populates="session", cascade="all, delete-orphan")
    leaf_analyses: Mapped[list["LeafAnalysis"]] = relationship(back_populates="session", passive_deletes=True)


class YieldFeedback(Base):
    __tablename__ = "yield_feedback"

    feedback_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("recommendation_sessions.session_id", ondelete="CASCADE"), unique=True, index=True)
    crop: Mapped[str] = mapped_column(String(40), index=True)
    variety: Mapped[str | None] = mapped_column(String(80), index=True)
    actual_yield_t_ha: Mapped[float] = mapped_column(Numeric(8, 2))
    harvest_date: Mapped[date | None] = mapped_column(Date)
    yield_unit: Mapped[str] = mapped_column(String(20), default="t_ha")
    fertilizer_followed_pct: Mapped[float | None] = mapped_column(Numeric(5, 2))
    rating: Mapped[int | None] = mapped_column(Integer)
    note: Mapped[str | None] = mapped_column(Text)
    contact_phone: Mapped[str | None] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    session: Mapped[RecommendationSession] = relationship(back_populates="feedback")


class LeafAnalysis(Base):
    __tablename__ = "leaf_analysis"

    analysis_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str | None] = mapped_column(ForeignKey("recommendation_sessions.session_id", ondelete="SET NULL"), index=True)
    crop: Mapped[str] = mapped_column(String(40), index=True)
    variety: Mapped[str | None] = mapped_column(String(80), index=True)
    sample_date: Mapped[date | None] = mapped_column(Date, index=True)
    n_pct: Mapped[float | None] = mapped_column(Numeric(6, 3))
    p_pct: Mapped[float | None] = mapped_column(Numeric(6, 3))
    k_pct: Mapped[float | None] = mapped_column(Numeric(6, 3))
    ca_pct: Mapped[float | None] = mapped_column(Numeric(6, 3))
    mg_pct: Mapped[float | None] = mapped_column(Numeric(6, 3))
    b_mg_kg: Mapped[float | None] = mapped_column(Numeric(8, 2))
    zn_mg_kg: Mapped[float | None] = mapped_column(Numeric(8, 2))
    lab_name: Mapped[str | None] = mapped_column(String(160))
    raw_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    session: Mapped[RecommendationSession | None] = relationship(back_populates="leaf_analyses")


class PlatformJobRun(Base):
    __tablename__ = "platform_job_runs"

    job_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_name: Mapped[str] = mapped_column(String(80), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30), default="running")
    summary: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)


class ModelReadyBackfillCheckpoint(Base):
    __tablename__ = "model_ready_backfill_checkpoints"
    __table_args__ = (
        UniqueConstraint(
            "crop_type",
            "region_id",
            "variety_id",
            "source",
            name="uq_model_ready_checkpoint_pair",
        ),
        Index("ix_model_ready_checkpoint_crop_window", "crop_type", "window_end"),
    )

    checkpoint_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    crop_type: Mapped[str] = mapped_column(String(30), index=True, nullable=False)
    region_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    variety_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    records_inserted: Mapped[int] = mapped_column(Integer, default=0, nullable=False, server_default="0")
    records_updated: Mapped[int] = mapped_column(Integer, default=0, nullable=False, server_default="0")


class ModelTrainingRun(Base):
    __tablename__ = "model_training_runs"

    run_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    crop_type: Mapped[str] = mapped_column(String(30), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30), default="running")
    rmse_vnd_per_kg: Mapped[float | None] = mapped_column(Numeric(12, 2))
    mae_vnd_per_kg: Mapped[float | None] = mapped_column(Numeric(12, 2))
    backtest_samples: Mapped[int] = mapped_column(Integer, default=0)
    evaluated_series: Mapped[int] = mapped_column(Integer, default=0)
    note: Mapped[str | None] = mapped_column(Text)


class MlModelVersion(Base):
    __tablename__ = "ml_model_versions"
    __table_args__ = (
        UniqueConstraint("model_key", "artifact_sha256", name="uq_ml_model_version_artifact"),
        Index("ix_ml_model_versions_model_active", "model_key", "is_active"),
    )

    version_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model_key: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    model_kind: Mapped[str] = mapped_column(String(100), nullable=False)
    crop_type: Mapped[str | None] = mapped_column(String(30), index=True)
    commodity_slug: Mapped[str | None] = mapped_column(String(40), index=True)
    artifact_path: Mapped[str] = mapped_column(String(500), nullable=False)
    artifact_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    metrics_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, server_default="1", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)


class FeatureFlag(Base):
    __tablename__ = "feature_flags"

    flag_key: Mapped[str] = mapped_column(String(120), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0", index=True)
    description: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("app_users.user_id", ondelete="SET NULL"), index=True)


class NewsArticle(Base):
    __tablename__ = "news_articles"

    article_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_name: Mapped[str] = mapped_column(String(120), index=True)
    source_url: Mapped[str] = mapped_column(String(800), index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    excerpt: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(80), default="Tin nông nghiệp", index=True)
    image_url: Mapped[str | None] = mapped_column(String(800))
    public_slug: Mapped[str | None] = mapped_column(String(180), index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class GuidePost(Base):
    __tablename__ = "guide_posts"

    post_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    public_slug: Mapped[str | None] = mapped_column(String(180), index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    crop_type: Mapped[str | None] = mapped_column(String(30), index=True)
    category: Mapped[str] = mapped_column(String(100), index=True)
    tags: Mapped[str | None] = mapped_column(String(500))
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str] = mapped_column(String(120), default="Ban kỹ thuật Dự báo nông sản")
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class Subscriber(Base):
    __tablename__ = "subscribers"

    subscriber_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    source: Mapped[str | None] = mapped_column(String(120), default="footer")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
