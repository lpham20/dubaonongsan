from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.core.cache import cached
from app.core.config import get_settings
from app.db import get_db
from app.models import AgriInputPriceObservation, AgriInputProduct, ScrapeRun
from app.schemas import (
    AgriInputForecast,
    AgriInputPricePoint,
    AgriInputPriceSummary,
    AgriInputProductOut,
)
from app.services.input_prices import InputPriceService


settings = get_settings()
router = APIRouter(prefix=settings.api_prefix, tags=["input-prices"])


@router.get("/input-prices/products", response_model=list[AgriInputProductOut])
@cached(prefix="input-price-products", ttl_seconds=900)
def input_price_products(
    category: str = Query(default="fertilizer", pattern="^(fertilizer)$"),
    db: Session = Depends(get_db),
) -> list:
    return InputPriceService(db).products(category=category)


@router.get("/input-prices/summary", response_model=AgriInputPriceSummary)
@cached(prefix="input-price-summary", ttl_seconds=600)
def input_price_summary(
    category: str = Query(default="fertilizer", pattern="^(fertilizer)$"),
    db: Session = Depends(get_db),
) -> dict:
    return InputPriceService(db).summary(category=category)


@router.get("/input-prices/latest", response_model=list[AgriInputPricePoint])
@cached(prefix="input-price-latest", ttl_seconds=300)
def input_price_latest(
    category: str = Query(default="fertilizer", pattern="^(fertilizer)$"),
    product_slug: str | None = Query(default=None, max_length=80),
    province: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=200, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[dict]:
    return InputPriceService(db).latest_prices(
        category=category,
        product_slug=product_slug,
        province=province,
        limit=limit,
    )


@router.get("/input-prices/history", response_model=list[AgriInputPricePoint])
@cached(prefix="input-price-history", ttl_seconds=300)
def input_price_history(
    product_slug: str = Query(..., min_length=1, max_length=80),
    province: str | None = Query(default=None, max_length=100),
    brand: str | None = Query(default=None, max_length=120),
    months: int = Query(default=12, ge=1, le=36),
    db: Session = Depends(get_db),
) -> list[dict]:
    return InputPriceService(db).history(
        product_slug=product_slug,
        province=province,
        brand=brand,
        months=months,
    )


@router.get("/input-prices/forecast", response_model=AgriInputForecast)
@cached(prefix="input-price-forecast", ttl_seconds=900)
def input_price_forecast(
    product_slug: str = Query(..., min_length=1, max_length=80),
    province: str | None = Query(default=None, max_length=100),
    brand: str | None = Query(default=None, max_length=120),
    days: int = Query(default=30, ge=1, le=60),
    db: Session = Depends(get_db),
) -> dict:
    return InputPriceService(db).forecast(
        product_slug=product_slug,
        province=province,
        brand=brand,
        days=days,
    )


@router.get("/platform/input-prices/health")
@cached(prefix="input-price-health", ttl_seconds=120)
def input_price_health(
    stale_after_hours: int = Query(default=36, ge=1, le=168),
    db: Session = Depends(get_db),
) -> dict:
    latest_scraped_at = db.scalar(
        select(func.max(AgriInputPriceObservation.observed_at))
        .join(AgriInputProduct)
        .where(AgriInputProduct.category == "fertilizer", AgriInputPriceObservation.data_kind == "scraped")
    )
    latest_any_at = db.scalar(
        select(func.max(AgriInputPriceObservation.observed_at))
        .join(AgriInputProduct)
        .where(AgriInputProduct.category == "fertilizer")
    )
    scraped_count = db.scalar(
        select(func.count(AgriInputPriceObservation.observation_id))
        .join(AgriInputProduct)
        .where(AgriInputProduct.category == "fertilizer", AgriInputPriceObservation.data_kind == "scraped")
    )
    source_count = db.scalar(
        select(func.count(AgriInputPriceObservation.source_name.distinct()))
        .join(AgriInputProduct)
        .where(AgriInputProduct.category == "fertilizer", AgriInputPriceObservation.data_kind == "scraped")
    )
    latest_run = db.scalar(
        select(ScrapeRun)
        .where(ScrapeRun.source.like("input:%"))
        .order_by(desc(ScrapeRun.started_at))
        .limit(1)
    )
    now = datetime.now(UTC)
    freshness_hours = None
    if latest_scraped_at is not None:
        if latest_scraped_at.tzinfo is None:
            latest_scraped_at = latest_scraped_at.replace(tzinfo=UTC)
        freshness_hours = round((now - latest_scraped_at.astimezone(UTC)).total_seconds() / 3600, 2)
    stale = latest_scraped_at is None or freshness_hours is None or freshness_hours > stale_after_hours
    latest_run_status = latest_run.status if latest_run else None
    if latest_run_status == "thất bại":
        stale = True
    return {
        "status": "stale" if stale else "ok",
        "category": "fertilizer",
        "latest_scraped_observed_at": latest_scraped_at,
        "latest_any_observed_at": latest_any_at,
        "freshness_hours": freshness_hours,
        "stale_after_hours": stale_after_hours,
        "scraped_count": int(scraped_count or 0),
        "source_count": int(source_count or 0),
        "latest_run": {
            "id": latest_run.id if latest_run else None,
            "source": latest_run.source if latest_run else None,
            "status": latest_run_status,
            "started_at": latest_run.started_at if latest_run else None,
            "finished_at": latest_run.finished_at if latest_run else None,
            "records_found": latest_run.records_found if latest_run else 0,
            "records_inserted": latest_run.records_inserted if latest_run else 0,
            "records_updated": latest_run.records_updated if latest_run else 0,
            "error_message": latest_run.error_message if latest_run else None,
        },
    }
