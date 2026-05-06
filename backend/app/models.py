from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

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


class UserPriceReport(Base):
    __tablename__ = "user_price_reports"

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
    status: Mapped[str] = mapped_column(String(30), default="đang chạy")
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

    watchlist: Mapped[list["WatchlistItem"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"
    __table_args__ = (
        UniqueConstraint("user_id", "crop_type", "region_id", "variety_id", name="uq_watchlist_market"),
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


class PlatformJobRun(Base):
    __tablename__ = "platform_job_runs"

    job_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_name: Mapped[str] = mapped_column(String(80), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30), default="đang chạy")
    summary: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)


class ModelTrainingRun(Base):
    __tablename__ = "model_training_runs"

    run_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    crop_type: Mapped[str] = mapped_column(String(30), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30), default="đang chạy")
    rmse_vnd_per_kg: Mapped[float | None] = mapped_column(Numeric(12, 2))
    mae_vnd_per_kg: Mapped[float | None] = mapped_column(Numeric(12, 2))
    backtest_samples: Mapped[int] = mapped_column(Integer, default=0)
    evaluated_series: Mapped[int] = mapped_column(Integer, default=0)
    note: Mapped[str | None] = mapped_column(Text)


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
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class GuidePost(Base):
    __tablename__ = "guide_posts"

    post_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    crop_type: Mapped[str | None] = mapped_column(String(30), index=True)
    category: Mapped[str] = mapped_column(String(100), index=True)
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
