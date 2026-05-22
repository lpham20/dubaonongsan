from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.cache import cached
from app.core.config import get_settings
from app.db import get_db
from app.schemas import (
    WorldFertilizerCommodityOut,
    WorldFertilizerForecastOut,
    WorldFertilizerHistoryPoint,
)
from app.services.world_fertilizer import WorldFertilizerForecastService


settings = get_settings()
router = APIRouter(prefix=settings.api_prefix, tags=["world-fertilizer"])


@router.get("/advisory/world-fertilizer/commodities", response_model=list[WorldFertilizerCommodityOut])
@cached(prefix="world-fertilizer-commodities", ttl_seconds=1800)
def world_fertilizer_commodities(db: Session = Depends(get_db)) -> list[dict]:
    return WorldFertilizerForecastService(db).commodities()


@router.get("/advisory/world-fertilizer/history", response_model=list[WorldFertilizerHistoryPoint])
@cached(prefix="world-fertilizer-history", ttl_seconds=900)
def world_fertilizer_history(
    commodity: str = Query(default="urea", min_length=1, max_length=40),
    days: int = Query(default=365, ge=30, le=3650),
    db: Session = Depends(get_db),
) -> list[dict]:
    try:
        return WorldFertilizerForecastService(db).history(commodity_slug=commodity, days=days)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/advisory/world-fertilizer/forecast", response_model=WorldFertilizerForecastOut)
@cached(prefix="world-fertilizer-forecast", ttl_seconds=1800)
def world_fertilizer_forecast(
    commodity: str = Query(default="urea", min_length=1, max_length=40),
    horizon_days: int = Query(default=30, ge=7, le=60),
    db: Session = Depends(get_db),
) -> dict:
    try:
        return WorldFertilizerForecastService(db).forecast(commodity_slug=commodity, horizon_days=horizon_days)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/platform/world-fertilizer/health")
@cached(prefix="world-fertilizer-health", ttl_seconds=120)
def world_fertilizer_health(
    stale_after_days: int = Query(default=60, ge=14, le=180),
    db: Session = Depends(get_db),
) -> dict:
    return WorldFertilizerForecastService(db).health(stale_after_days=stale_after_days)
