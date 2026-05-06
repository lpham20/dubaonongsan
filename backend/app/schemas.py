from datetime import datetime
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
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str | None = Field(default=None, max_length=120)

    @field_validator("email")
    @classmethod
    def normalize_auth_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if not re.search(r"\d", value):
            raise ValueError("Mật khẩu cần ít nhất 1 chữ số")
        return value


class AuthUserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    email: str
    display_name: str
    is_admin: bool = False


class AuthTokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthUserOut


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
