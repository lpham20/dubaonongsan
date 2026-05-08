from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta

import requests
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models import DailyMarketPrice, ProductionRegion, WeatherEnvironmentalMetric


logger = logging.getLogger(__name__)

OPEN_METEO_URLS = (
    "https://archive-api.open-meteo.com/v1/archive",
    "https://api.open-meteo.com/v1/archive",
)

PROVINCE_COORDS: dict[str, tuple[float, float]] = {
    "An Giang": (10.52, 105.13),
    "Bà Rịa-Vũng Tàu": (10.54, 107.24),
    "Bình Phước": (11.75, 106.72),
    "Bến Tre": (10.24, 106.38),
    "Cần Thơ": (10.04, 105.78),
    "Gia Lai": (13.81, 108.11),
    "Kon Tum": (14.35, 108.00),
    "Long An": (10.54, 106.40),
    "Lâm Đồng": (11.94, 108.45),
    "Tây Ninh": (11.31, 106.10),
    "Tiền Giang": (10.36, 106.36),
    "Vĩnh Long": (10.25, 105.97),
    "Đắk Lắk": (12.66, 108.05),
    "Đắk Nông": (12.00, 107.69),
    "Đồng Nai": (10.95, 106.83),
    "Đồng Tháp": (10.54, 105.69),
}


def fetch_rainfall_for_province(province: str, start: date, end: date) -> dict[date, float]:
    coords = PROVINCE_COORDS.get(province)
    if coords is None:
        logger.warning("No Open-Meteo coordinates configured for province: %s", province)
        return {}

    params = {
        "latitude": coords[0],
        "longitude": coords[1],
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "daily": "precipitation_sum",
        "timezone": "Asia/Bangkok",
    }
    for url in OPEN_METEO_URLS:
        try:
            response = requests.get(url, params=params, timeout=20)
            response.raise_for_status()
            payload = response.json()
            days = payload.get("daily", {}).get("time", [])
            rainfall = payload.get("daily", {}).get("precipitation_sum", [])
            return {
                date.fromisoformat(day): float(mm)
                for day, mm in zip(days, rainfall, strict=False)
                if mm is not None
            }
        except Exception as exc:
            logger.warning("Open-Meteo fetch failed for %s via %s: %s", province, url, exc)
    return {}


def populate_precipitation(db: Session, days_back: int = 90) -> dict:
    end = datetime.now(UTC).date()
    start = end - timedelta(days=days_back)
    start_dt = datetime.combine(start, datetime.min.time(), tzinfo=UTC)

    regions = db.scalars(
        select(ProductionRegion)
        .join(DailyMarketPrice, DailyMarketPrice.region_id == ProductionRegion.region_id)
        .where(ProductionRegion.province.is_not(None))
        .where(DailyMarketPrice.record_timestamp >= start_dt)
        .order_by(ProductionRegion.region_id)
        .distinct()
    ).all()

    rainfall_by_province: dict[str, dict[date, float]] = {}
    failed_provinces: list[str] = []
    rows_inserted = 0
    rows_updated = 0

    for region in regions:
        province = region.province
        if not province:
            continue
        if province not in rainfall_by_province:
            rainfall_by_province[province] = fetch_rainfall_for_province(province, start, end)
            if not rainfall_by_province[province]:
                failed_provinces.append(province)
                continue

        timestamps = db.scalars(
            select(DailyMarketPrice.record_timestamp)
            .where(DailyMarketPrice.region_id == region.region_id)
            .where(DailyMarketPrice.record_timestamp >= start_dt)
            .distinct()
        ).all()

        for timestamp in timestamps:
            mm = rainfall_by_province[province].get(timestamp.date())
            if mm is None:
                continue
            existing = db.scalar(
                select(WeatherEnvironmentalMetric).where(
                    and_(
                        WeatherEnvironmentalMetric.region_id == region.region_id,
                        WeatherEnvironmentalMetric.record_timestamp == timestamp,
                    )
                )
            )
            if existing:
                if existing.precipitation_mm is None:
                    rows_updated += 1
                existing.precipitation_mm = mm
                db.add(existing)
            else:
                rows_inserted += 1
                db.add(
                    WeatherEnvironmentalMetric(
                        record_timestamp=timestamp,
                        region_id=region.region_id,
                        precipitation_mm=mm,
                    )
                )

    db.commit()
    return {
        "days_back": days_back,
        "regions_processed": len(regions),
        "provinces_processed": len(rainfall_by_province) - len(set(failed_provinces)),
        "provinces_failed": sorted(set(failed_provinces)),
        "rows_inserted": rows_inserted,
        "rows_updated": rows_updated,
    }
