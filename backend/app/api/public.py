from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.analytics import forecast_30_days
from app.core.config import get_settings
from app.db import get_db
from app.schemas import ForecastPoint, HistoricalPricePoint
from app.services.data_loader import DataLoader


settings = get_settings()
router = APIRouter(prefix=settings.api_prefix, tags=["public"])


def require_public_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if x_api_key != settings.public_api_key:
        raise HTTPException(status_code=401, detail="API key không hợp lệ")


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
