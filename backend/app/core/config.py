from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Dự báo nông sản"
    api_prefix: str = "/api/v1"
    environment: str = Field(default="development", description="development | production")
    database_url: str = Field(
        default=f"sqlite:///{Path(__file__).resolve().parents[3] / 'marketai.db'}",
        description="Use postgresql+psycopg://... in production.",
    )
    seed_on_startup: bool = False
    create_demo_user: bool = False
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"])
    auth_token_secret: str = Field(default="", description="Required in production")
    auth_previous_token_secrets: str = Field(
        default="",
        description="Comma-separated old JWT secrets accepted during controlled key rotation.",
    )
    auth_token_minutes: int = 60 * 24 * 7
    public_api_key: str = Field(default="", description="Required in production")
    iot_api_key: str = Field(default="", description="API key for IoT telemetry devices")
    start_scheduler_in_api: bool = True
    scrape_interval_minutes: int = 60 * 2
    news_scrape_interval_minutes: int = 60 * 3
    news_scrape_daily_hour: int = 7
    news_scrape_daily_minute: int = 0
    data_quality_interval_minutes: int = 60 * 24
    retrain_interval_minutes: int = 60 * 24
    rate_limit_storage_uri: str = "memory://"
    sentry_dsn: str = ""
    world_fertilizer_current_retry_attempts: int = 3
    world_fertilizer_current_retry_delay_seconds: int = 60
    ml_artifacts: str = "/app/ml_artifacts"
    ml_enable_tflite: bool = True
    ml_max_models: int = 1

    model_config = SettingsConfigDict(env_file=".env", env_prefix="MARKETAI_")

    @field_validator("auth_token_secret")
    @classmethod
    def validate_auth_token_secret(cls, value: str, info) -> str:
        environment = info.data.get("environment", "development")
        weak_values = {"marketai-local-dev-secret", "changeme", "secret"}
        if environment == "production":
            if not value or len(value) < 32:
                raise ValueError("MARKETAI_AUTH_TOKEN_SECRET phải có ít nhất 32 ký tự trong production")
            if value in weak_values:
                raise ValueError("MARKETAI_AUTH_TOKEN_SECRET đang dùng giá trị mặc định, cần đổi trước khi publish")
        return value or "dev-only-secret-not-for-production-" + ("x" * 32)

    @field_validator("public_api_key")
    @classmethod
    def validate_public_api_key(cls, value: str, info) -> str:
        environment = info.data.get("environment", "development")
        if environment == "production" and (not value or len(value) < 24):
            raise ValueError("MARKETAI_PUBLIC_API_KEY phải có ít nhất 24 ký tự trong production")
        return value or "marketai-public-demo-key"

    @field_validator("iot_api_key")
    @classmethod
    def validate_iot_api_key(cls, value: str, info) -> str:
        environment = info.data.get("environment", "development")
        if environment == "production" and (not value or len(value) < 24):
            raise ValueError("MARKETAI_IOT_API_KEY phải có ít nhất 24 ký tự trong production")
        return value or "marketai-iot-dev-key"

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, value: list[str], info) -> list[str]:
        environment = info.data.get("environment", "development")
        origins = [origin.strip().rstrip("/") for origin in value if origin and origin.strip()]
        if environment == "production":
            if not origins:
                raise ValueError("MARKETAI_CORS_ORIGINS is required in production")
            if "*" in origins:
                raise ValueError("MARKETAI_CORS_ORIGINS cannot use wildcard in production")
            for origin in origins:
                if "localhost" in origin or "127.0.0.1" in origin:
                    raise ValueError(f"MARKETAI_CORS_ORIGINS cannot contain localhost in production: {origin}")
                if not origin.startswith("https://"):
                    raise ValueError(f"Production CORS origin must use HTTPS: {origin}")
        return origins

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str, info) -> str:
        environment = info.data.get("environment", "development")
        if environment == "production" and value.startswith("sqlite"):
            raise ValueError("MARKETAI_DATABASE_URL cannot use SQLite in production")
        return value

    @field_validator("rate_limit_storage_uri")
    @classmethod
    def validate_rate_limit_storage_uri(cls, value: str, info) -> str:
        environment = info.data.get("environment", "development")
        if environment == "production" and value == "memory://":
            raise ValueError("MARKETAI_RATE_LIMIT_STORAGE_URI must use shared storage in production")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
