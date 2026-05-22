from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.cache import cached
from app.core.config import get_settings
from app.db import get_db
from app.schemas import (
    AgriInputForecastPoint,
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


@router.get("/input-prices/forecast", response_model=list[AgriInputForecastPoint])
@cached(prefix="input-price-forecast", ttl_seconds=900)
def input_price_forecast(
    product_slug: str = Query(..., min_length=1, max_length=80),
    province: str | None = Query(default=None, max_length=100),
    brand: str | None = Query(default=None, max_length=120),
    days: int = Query(default=30, ge=1, le=60),
    db: Session = Depends(get_db),
) -> list[dict]:
    return InputPriceService(db).forecast(
        product_slug=product_slug,
        province=province,
        brand=brand,
        days=days,
    )
