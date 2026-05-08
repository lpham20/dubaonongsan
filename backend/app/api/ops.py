from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.db import get_db
from app.ingestion.service import PriceIngestionService
from app.models import AppUser, IotSensorTelemetry
from app.schemas import ModelTrainingRunOut, PlatformJobRunOut, ScrapeRunOut, SensorTelemetryIn, SensorTelemetryOut
from app.services.auth import require_admin
from app.services.model_ready_backfill import ModelReadyBackfillService
from app.services.platform_jobs import PlatformJobService


settings = get_settings()
router = APIRouter(prefix=settings.api_prefix, tags=["operations"])


def require_iot_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if x_api_key != settings.iot_api_key:
        raise HTTPException(status_code=401, detail="IoT API key không hợp lệ")


@router.get("/platform/jobs", response_model=list[PlatformJobRunOut])
def platform_jobs(
    _: AppUser = Depends(require_admin),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list:
    return PlatformJobService(db).latest_jobs(limit=limit)


@router.get("/platform/model-runs", response_model=list[ModelTrainingRunOut])
def platform_model_runs(
    _: AppUser = Depends(require_admin),
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list:
    return PlatformJobService(db).latest_training_runs(limit=limit)


@router.post("/platform/jobs/scrape")
def run_scrape_job(
    _: AppUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    return PlatformJobService(db).run_scrape()


@router.post("/platform/jobs/data-quality")
def run_data_quality_job(
    _: AppUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    return PlatformJobService(db).run_data_quality()


@router.post("/platform/jobs/news")
def run_news_scrape_job(
    _: AppUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    return PlatformJobService(db).run_news_scrape()


@router.post("/platform/jobs/weather")
def run_weather_job(
    _: AppUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    return PlatformJobService(db).run_weather()


@router.post("/platform/jobs/retrain")
def run_retrain_job(
    _: AppUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    return PlatformJobService(db).run_retrain()


@router.post(
    "/sensors/maturity-telemetry",
    response_model=SensorTelemetryOut,
    status_code=201,
)
@limiter.limit("60/minute")
def ingest_maturity_telemetry(
    request: Request,
    payload: SensorTelemetryIn,
    _: None = Depends(require_iot_api_key),
    db: Session = Depends(get_db),
) -> SensorTelemetryOut:
    record = IotSensorTelemetry(
        record_timestamp=payload.timestamp,
        device_id=payload.device_id,
        region_id=payload.region_id,
        maturity_index=payload.maturity_index,
        status=payload.status,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return SensorTelemetryOut(
        id=record.id,
        device_id=record.device_id,
        region_id=record.region_id,
        maturity_index=float(record.maturity_index),
        status=record.status,
        timestamp=record.record_timestamp,
    )


@router.post("/ingestion/scrape-prices")
def scrape_prices(
    _: AppUser = Depends(require_admin),
    source: str | None = Query(default=None, description="Optional scraper source key"),
    db: Session = Depends(get_db),
) -> list[dict]:
    return PriceIngestionService(db).scrape_and_store(source=source)


@router.post("/ingestion/backfill-model-ready")
def backfill_model_ready(
    _: AppUser = Depends(require_admin),
    crop: str = Query(default="sau_rieng"),
    db: Session = Depends(get_db),
) -> dict:
    return ModelReadyBackfillService(db, crop_type=crop).backfill()


@router.get("/ingestion/scrape-runs", response_model=list[ScrapeRunOut])
def scrape_runs(
    _: AppUser = Depends(require_admin),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[dict]:
    return PriceIngestionService(db).latest_runs(limit=limit)
