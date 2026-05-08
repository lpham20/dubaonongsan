from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.api.analytics import forecast_30_days
from app.core.config import get_settings
from app.db import get_db
from app.models import ScrapeRun
from app.schemas import ForecastPoint, HistoricalPricePoint
from app.services.data_loader import DataLoader


settings = get_settings()
router = APIRouter(prefix=settings.api_prefix, tags=["public"])


def require_public_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if x_api_key != settings.public_api_key:
        raise HTTPException(status_code=401, detail="API key không hợp lệ")


@router.get("/health/scrape")
def scrape_health(db: Session = Depends(get_db)) -> dict:
    """
    Report whether the scrape worker has completed a scrape run recently.

    External uptime monitors should alert when this returns anything other than
    HTTP 200. Per-source freshness remains available at /analytics/source-health.
    """
    healthy_statuses = ["thành công", "trùng lặp", "trống"]
    now = datetime.now(timezone.utc)
    last_success = db.scalar(
        select(ScrapeRun.finished_at)
        .where(ScrapeRun.status.in_(healthy_statuses))
        .where(ScrapeRun.finished_at.is_not(None))
        .order_by(desc(ScrapeRun.finished_at))
        .limit(1)
    )

    if last_success is None:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "no_scrape_ever",
                "message": "No completed scrape recorded yet",
            },
        )

    last_success_utc = last_success if last_success.tzinfo else last_success.replace(tzinfo=timezone.utc)
    age_minutes = (now - last_success_utc).total_seconds() / 60
    body = {
        "status": "ok",
        "last_success_at": last_success_utc.isoformat(),
        "age_minutes": round(age_minutes, 1),
        "expected_interval_minutes": 120,
    }

    if age_minutes > 240:
        raise HTTPException(status_code=503, detail={**body, "status": "worker_dead"})
    if age_minutes > 180:
        return {**body, "status": "stale"}
    return body


@router.get("/public/prices", response_model=list[HistoricalPricePoint])
def public_prices(
    _: None = Depends(require_public_api_key),
    crop: str = Query(default="sau_rieng"),
    region_id: int | None = Query(default=None),
    variety_id: int | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> list[dict]:
    return DataLoader(db).historical_prices(
        crop_type=crop,
        region_id=region_id,
        variety_id=variety_id,
        quality_grade="Loại A",
        limit=limit,
    )


@router.get("/public/forecast", response_model=list[ForecastPoint])
def public_forecast(
    _: None = Depends(require_public_api_key),
    crop: str = Query(default="sau_rieng"),
    region_id: int = Query(default=1),
    variety_id: int = Query(default=1),
    db: Session = Depends(get_db),
) -> list[dict]:
    return forecast_30_days(crop=crop, region_id=region_id, variety_id=variety_id, variety=None, db=db)
