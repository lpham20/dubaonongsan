from datetime import datetime, time, timedelta, timezone
import hmac
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.api.analytics import forecast_30_days
from app.core.config import get_settings
from app.core.job_status import STATUS_EMPTY, SUCCESS_STATUSES
from app.db import get_db
from app.models import ScrapeRun
from app.schemas import ForecastPoint, HistoricalPricePoint
from app.services.data_loader import DataLoader


settings = get_settings()
router = APIRouter(prefix=settings.api_prefix, tags=["public"])
PRICE_SCRAPE_TIMEZONE = ZoneInfo("Asia/Ho_Chi_Minh")
PRICE_SCRAPE_START_HOUR = 6
PRICE_SCRAPE_END_HOUR = 22
PRICE_SCRAPE_EXPECTED_INTERVAL_MINUTES = 60
PRICE_SCRAPE_STALE_AFTER_ACTIVE_MINUTES = 180
PRICE_SCRAPE_DEAD_AFTER_ACTIVE_MINUTES = 240


def _price_scrape_active_minutes_between(start: datetime, end: datetime) -> float:
    """Count elapsed minutes only while the scheduled price scraper is active."""
    if end <= start:
        return 0.0

    start_local = start.astimezone(PRICE_SCRAPE_TIMEZONE)
    end_local = end.astimezone(PRICE_SCRAPE_TIMEZONE)
    current_day = start_local.date()
    final_day = end_local.date()
    active_minutes = 0.0

    while current_day <= final_day:
        window_start = datetime.combine(
            current_day,
            time(hour=PRICE_SCRAPE_START_HOUR),
            tzinfo=PRICE_SCRAPE_TIMEZONE,
        )
        window_end = datetime.combine(
            current_day,
            time(hour=PRICE_SCRAPE_END_HOUR),
            tzinfo=PRICE_SCRAPE_TIMEZONE,
        )
        overlap_start = max(start_local, window_start)
        overlap_end = min(end_local, window_end)
        if overlap_end > overlap_start:
            active_minutes += (overlap_end - overlap_start).total_seconds() / 60
        current_day += timedelta(days=1)

    return active_minutes


def _price_scrape_health_status(active_age_minutes: float) -> str:
    if active_age_minutes > PRICE_SCRAPE_DEAD_AFTER_ACTIVE_MINUTES:
        return "worker_dead"
    if active_age_minutes > PRICE_SCRAPE_STALE_AFTER_ACTIVE_MINUTES:
        return "stale"
    return "ok"


def require_public_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if not x_api_key or not hmac.compare_digest(x_api_key, settings.public_api_key):
        raise HTTPException(status_code=401, detail="API key không hợp lệ")


@router.get("/health/scrape")
def scrape_health(db: Session = Depends(get_db)) -> dict:
    """
    Report whether the scrape worker has completed a scrape run recently.

    External uptime monitors should alert when this returns anything other than
    HTTP 200. Per-source freshness remains available at /analytics/source-health.
    """
    healthy_statuses = [
        *SUCCESS_STATUSES,
        STATUS_EMPTY,
        "thành công",
        "trùng lặp",
        "trống",
        # Backward compatibility for records written before the encoding fix.
        "thÃ nh cÃ´ng",
        "trÃ¹ng láº·p",
        "trá»‘ng",
    ]
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
    active_age_minutes = _price_scrape_active_minutes_between(last_success_utc, now)
    status = _price_scrape_health_status(active_age_minutes)
    body = {
        "status": status,
        "last_success_at": last_success_utc.isoformat(),
        "age_minutes": round(age_minutes, 1),
        "active_age_minutes": round(active_age_minutes, 1),
        "expected_interval_minutes": PRICE_SCRAPE_EXPECTED_INTERVAL_MINUTES,
        "schedule_timezone": str(PRICE_SCRAPE_TIMEZONE),
        "schedule_window_local": f"{PRICE_SCRAPE_START_HOUR:02d}:00-{PRICE_SCRAPE_END_HOUR:02d}:00",
    }

    if status == "worker_dead":
        raise HTTPException(status_code=503, detail=body)
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
