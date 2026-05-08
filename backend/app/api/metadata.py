from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.admin_units import is_crop_province, is_production_region
from app.core.config import get_settings
from app.db import get_db
from app.models import DailyMarketPrice, DurianVariety, ProductionRegion


settings = get_settings()
router = APIRouter(prefix=settings.api_prefix, tags=["metadata"])


@router.get("/metadata/regions")
def regions(
    crop: str = Query(default="sau_rieng"),
    db: Session = Depends(get_db),
) -> list[dict]:
    rows = db.scalars(
        select(ProductionRegion)
        .join(DailyMarketPrice, DailyMarketPrice.region_id == ProductionRegion.region_id)
        .where(DailyMarketPrice.crop_type == crop)
        .order_by(ProductionRegion.region_id)
        .distinct()
    ).all()
    production_rows = [
        row
        for row in rows
        if is_production_region(row.region_name, row.province)
        and is_crop_province(crop, row.province)
    ]
    return [
        {
            "region_id": row.region_id,
            "region_name": row.region_name,
            "province": row.province,
            "export_code": row.export_code,
            "risk_level_index": float(row.risk_level_index),
        }
        for row in production_rows
    ]


@router.get("/metadata/varieties")
def varieties(
    crop: str = Query(default="sau_rieng"),
    db: Session = Depends(get_db),
) -> list[dict]:
    rows = db.scalars(
        select(DurianVariety)
        .where(DurianVariety.crop_type == crop)
        .order_by(DurianVariety.variety_id)
    ).all()
    return [
        {
            "variety_id": row.variety_id,
            "name": row.name,
            "description": row.description,
        }
        for row in rows
    ]


@router.get("/metadata/available-varieties")
def available_varieties(
    crop: str = Query(default="sau_rieng"),
    region_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[dict]:
    stmt = (
        select(DurianVariety)
        .join(DailyMarketPrice, DailyMarketPrice.variety_id == DurianVariety.variety_id)
        .where(DailyMarketPrice.crop_type == crop)
        .where(DurianVariety.crop_type == crop)
        .order_by(DurianVariety.variety_id)
        .distinct()
    )
    if region_id:
        stmt = stmt.where(DailyMarketPrice.region_id == region_id)
    rows = db.scalars(stmt).all()
    return [
        {
            "variety_id": row.variety_id,
            "name": row.name,
            "description": row.description,
        }
        for row in rows
    ]
