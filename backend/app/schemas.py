from datetime import UTC, datetime, timedelta
import html
import re

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class HistoricalPricePoint(BaseModel):
    timestamp: datetime
    region_id: int | None = None
    variety_id: int | None = None
    variety: str
    region: str
    province: str | None
    quality_grade: str | None
    exchange_source: str | None
    min_price_vnd: float | None
    max_price_vnd: float | None
    volume_traded_tons: float | None
    temp_max_celsius: float | None
    precipitation_mm: float | None
    maturity_index: float | None
    data_kind: str = "observed"
    is_synthetic: bool = False
    farmer_report_price_vnd: float | None = None
    farmer_reported_at: datetime | None = None
    farmer_report_quality_grade: str | None = None


class ForecastPoint(BaseModel):
    timestamp: datetime
    forecast_price_vnd: float
    confidence_low_vnd: float
    confidence_high_vnd: float
    model_kind: str = "baseline-statistical"


class AgriInputProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: int
    slug: str
    name: str
    category: str
    product_type: str
    nutrient_profile: str | None = None
    standard_unit: str
    package_label: str | None = None
    package_size_kg: float | None = None
    notes: str | None = None
    is_active: bool = True


class AgriInputPricePoint(BaseModel):
    observation_id: int
    product_id: int
    product_slug: str
    product_name: str
    product_type: str
    observed_at: datetime
    province: str
    region_name: str | None = None
    brand: str | None = None
    seller_name: str | None = None
    source_name: str
    source_url: str | None = None
    package_price_vnd: float | None = None
    normalized_price_vnd: float
    normalized_unit: str = "kg"
    package_size_kg: float | None = None
    package_label: str | None = None
    confidence_score: float
    data_kind: str


class AgriInputForecastPoint(BaseModel):
    timestamp: datetime
    forecast_price_vnd: float
    confidence_low_vnd: float
    confidence_high_vnd: float
    normalized_price_vnd: float
    normalized_low_vnd: float
    normalized_high_vnd: float
    model_kind: str = "input-price-seasonal-v3"


class AgriInputForecast(BaseModel):
    points: list[AgriInputForecastPoint]
    model_kind: str
    history_points: int = 0
    volatility: float = 0.0
    latest_observed_at: datetime | None = None


class AgriInputPriceSummary(BaseModel):
    category: str
    latest_count: int
    provinces: list[str]
    products: list[str]
    latest_observed_at: datetime | None = None


class WorldFertilizerCommodityOut(BaseModel):
    commodity_slug: str
    name_vi: str
    name_en: str
    quote_type: str
    driver_note_vi: str


class WorldFertilizerHistoryPoint(BaseModel):
    observed_at: datetime
    price_usd_per_tonne: float
    quote_type: str
    source: str
    source_url: str | None = None
    confidence_score: float


class WorldFertilizerForecastPoint(BaseModel):
    date: str
    price_usd_per_tonne: float
    price_low_usd_per_tonne: float
    price_high_usd_per_tonne: float
    daily_pct_change: float
    cumulative_pct_from_today: float


class WorldFertilizerWeeklyPoint(BaseModel):
    week_index: int
    week_label_vi: str
    date_from: str
    date_to: str
    median_price_usd_per_tonne: float
    low_price_usd_per_tonne: float | None = None
    high_price_usd_per_tonne: float | None = None
    pct_change_vs_prev_week: float
    pct_change_vs_today: float
    daily_breakdown: list[WorldFertilizerForecastPoint]


class WorldFertilizerForecastOut(BaseModel):
    commodity_slug: str
    commodity_name_vi: str
    quote_type: str | None = None
    base_price_usd_per_tonne: float | None = None
    base_observed_at: datetime | None = None
    model_kind: str
    history_points: int
    volatility: float
    volatility_daily: float | None = None
    source_mode: str | None = None
    data_quality: dict | None = None
    forecast_daily: list[WorldFertilizerForecastPoint]
    forecast_weekly: list[WorldFertilizerWeeklyPoint]
    note_vi: str


class TradingSignal(BaseModel):
    timestamp: datetime
    price_vnd: float
    signal: str = "CẢNH BÁO BÁN"
    reason: str
    prominence: float


class SensorTelemetryIn(BaseModel):
    device_id: str = Field(examples=["T-Abyss-001"])
    region_id: int
    maturity_index: float = Field(ge=0, le=10)
    status: str | None = Field(default=None, examples=["Sẵn sàng thu hoạch"])
    timestamp: datetime

    @field_validator("timestamp")
    @classmethod
    def timestamp_in_reasonable_range(cls, value: datetime) -> datetime:
        observed_at = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
        now = datetime.now(UTC)
        if observed_at < now - timedelta(days=30) or observed_at > now + timedelta(hours=6):
            raise ValueError("Timestamp cảm biến nằm ngoài khoảng hợp lệ.")
        return value


class SensorTelemetryOut(SensorTelemetryIn):
    id: int


class ModelMetrics(BaseModel):
    rmse_usd_per_kg: float = 0.45
    mae_usd_per_kg: float = 0.32
    rmse_vnd_per_kg: float | None = None
    mae_vnd_per_kg: float | None = None
    lookback_days: int = 60
    forecast_horizon_days: int = 30
    backtest_samples: int = 0
    evaluated_series: int = 0
    note: str | None = None


class ScrapeRunOut(BaseModel):
    id: int | None = None
    source: str
    source_url: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    status: str
    records_found: int = 0
    records_inserted: int = 0
    records_updated: int = 0
    error_message: str | None = None


class AuthCredentials(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "email": "farmer@example.com",
                    "password": "StrongPass123",
                }
            ]
        }
    )

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    display_name: str | None = Field(default=None, max_length=120)
    turnstile_token: str | None = Field(default=None, max_length=4096)

    @field_validator("email")
    @classmethod
    def normalize_auth_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()


class AuthRegisterCredentials(AuthCredentials):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "email": "farmer@example.com",
                    "password": "StrongPass123",
                    "display_name": "Nguyen Van A",
                    "turnstile_token": "optional-turnstile-token",
                }
            ]
        }
    )

    password: str = Field(min_length=10, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if len(value) < 10:
            raise ValueError("Mật khẩu cần ít nhất 10 ký tự")
        if not re.search(r"[a-z]", value):
            raise ValueError("Mật khẩu cần ít nhất 1 chữ thường")
        if not re.search(r"[A-Z]", value) and not re.search(r"\d", value):
            raise ValueError("Mật khẩu cần ít nhất 1 chữ hoa hoặc 1 chữ số")
        return value


class AuthUserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    email: str
    display_name: str
    is_admin: bool = False


class AuthTokenOut(BaseModel):
    access_token: str
    refresh_token: str
    refresh_expires_at: datetime
    token_type: str = "bearer"
    user: AuthUserOut


class AuthRefreshRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "refresh_token": "refresh-token-from-login-or-register",
                }
            ]
        }
    )

    refresh_token: str = Field(min_length=32, max_length=512)


class AuthLogoutRequest(BaseModel):
    refresh_token: str | None = Field(default=None, min_length=32, max_length=512)


class WatchlistItemIn(BaseModel):
    crop_type: str
    region_id: int
    variety_id: int
    label: str


class WatchlistItemOut(WatchlistItemIn):
    model_config = ConfigDict(from_attributes=True)

    item_id: int
    created_at: datetime


class PlatformJobRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_id: int
    job_name: str
    started_at: datetime
    finished_at: datetime | None
    status: str
    summary: str | None = None
    error_message: str | None = None


class ModelTrainingRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    run_id: int
    crop_type: str
    started_at: datetime
    finished_at: datetime | None
    status: str
    rmse_vnd_per_kg: float | None = None
    mae_vnd_per_kg: float | None = None
    backtest_samples: int = 0
    evaluated_series: int = 0
    note: str | None = None


class MlModelVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    version_id: int
    model_key: str
    model_kind: str
    crop_type: str | None = None
    commodity_slug: str | None = None
    artifact_path: str
    artifact_sha256: str
    metadata_json: dict | None = None
    metrics_json: dict | None = None
    is_active: bool
    created_at: datetime
    activated_at: datetime | None = None


class FeatureFlagIn(BaseModel):
    enabled: bool
    description: str | None = Field(default=None, max_length=1000)


class FeatureFlagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    flag_key: str
    enabled: bool
    description: str | None = None
    updated_at: datetime
    updated_by: int | None = None


class NewsArticleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    article_id: int
    source_name: str
    source_url: str
    title: str
    summary: str
    excerpt: str | None = None
    category: str
    image_url: str | None = None
    published_at: datetime | None = None
    scraped_at: datetime


class GuidePostOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    post_id: int
    slug: str
    title: str
    crop_type: str | None
    category: str
    tags: str | None = None
    summary: str
    content: str
    author: str
    published_at: datetime


class SubscriberIn(BaseModel):
    email: EmailStr
    source: str | None = Field(default="footer", max_length=120)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()


class SubscriberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    subscriber_id: int
    email: str
    source: str | None = None
    created_at: datetime
    updated_at: datetime


class UserPriceReportIn(BaseModel):
    crop_type: str = Field(pattern="^(sau_rieng|ca_phe|ho_tieu|lua)$")
    region_id: int = Field(gt=0)
    variety_id: int = Field(gt=0)
    price_vnd: float = Field(gt=0, le=10_000_000)
    quality_grade: str | None = Field(default=None, max_length=50)
    reporter_name: str | None = Field(default=None, max_length=120)
    note: str | None = Field(default=None, max_length=300)

    @field_validator("quality_grade", "reporter_name", "note")
    @classmethod
    def strip_html(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = re.sub(r"<[^>]*>", "", value).strip()
        return html.escape(cleaned, quote=False) or None


class UserPriceReportOut(BaseModel):
    report_id: int
    crop_type: str
    region_id: int
    variety_id: int
    price_vnd: float
    quality_grade: str | None = None
    approved_for_training: bool = False
    created_at: datetime
    message: str = "Đã ghi nhận giá địa phương."
