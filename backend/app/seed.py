from datetime import UTC, datetime, timedelta
import math
import random
from sqlalchemy import and_, delete, select, update
from sqlalchemy.orm import Session

from app.core.admin_units import is_crop_province, normalize_location
from app.core.vietnamese import vi_grade, vi_province, vi_region, vi_source, vi_status, vi_variety
from app.models import (
    DailyMarketPrice,
    DurianVariety,
    IotSensorTelemetry,
    ProductionRegion,
    ScrapeRun,
    WatchlistItem,
    WeatherEnvironmentalMetric,
)


VARIETIES = [
    ("Ri6", "Giống sầu riêng phổ biến, thanh khoản nội địa cao."),
    ("Sầu Thái Dona", "Giống Thái/Dona phục vụ phân khúc xuất khẩu và hàng tuyển."),
    ("Sầu Musang King", "Giống cao cấp có biên giá lớn."),
    ("Sầu Black Thorn", "Giống cao cấp ngách, khối lượng giao dịch thấp hơn."),
]

REGIONS = [
    ("Tây Nam Bộ", "Tiền Giang", "VN-TGPH-748", 0.18),
    ("Tây Nguyên", "Đắk Lắk", "VN-DLPH-035", 0.23),
    ("Tây Nguyên", "Lâm Đồng", "VN-LDPH-112", 0.16),
]


def seed_database(db: Session) -> None:
    existing = db.scalar(select(DurianVariety).limit(1))
    if existing:
        return

    varieties = [
        DurianVariety(name=name, description=description) for name, description in VARIETIES
    ]
    regions = [
        ProductionRegion(
            region_name=region,
            province=province,
            export_code=code,
            risk_level_index=risk,
        )
        for region, province, code, risk in REGIONS
    ]
    db.add_all(varieties + regions)
    db.flush()

    rng = random.Random(20260428)
    today = datetime(2026, 4, 28, tzinfo=UTC)
    sources = ["MXV", "VMEX", "Chợ Thủ Đức", "giacaphe.com"]

    for region_idx, region in enumerate(regions):
        for day in range(120):
            ts = today - timedelta(days=119 - day)
            seasonal = math.sin(day / 9.0) * 5500 + math.sin(day / 23.0) * 3500
            heat_wave = 4200 if 70 <= day <= 84 and region_idx == 1 else 0
            rain = max(0.0, 16 + math.sin(day / 6.0 + region_idx) * 13 + rng.uniform(-5, 6))
            temp_max = 29.5 + region_idx * 0.8 + math.sin(day / 10.0) * 2.4 + heat_wave / 6000

            db.add(
                WeatherEnvironmentalMetric(
                    record_timestamp=ts,
                    region_id=region.region_id,
                    temp_max_celsius=round(temp_max, 2),
                    temp_min_celsius=round(temp_max - rng.uniform(5.5, 8.0), 2),
                    humidity_percent=round(65 + rain * 0.7 + rng.uniform(-4, 4), 2),
                    precipitation_mm=round(rain, 2),
                    wind_speed_kmh=round(7 + rng.random() * 12, 2),
                    cloud_cover_index=round(min(1.0, rain / 35), 2),
                )
            )
            db.add(
                IotSensorTelemetry(
                    record_timestamp=ts,
                    device_id=f"T-Abyss-{region.region_id:03d}",
                    region_id=region.region_id,
                    maturity_index=round(5.7 + math.sin(day / 13.0) * 1.6 + rng.random(), 2),
                    status="Sẵn sàng thu hoạch" if day % 19 in (0, 1, 2) else "Đang theo dõi",
                )
            )

            for variety_idx, variety in enumerate(varieties[:2]):
                variety_premium = variety_idx * 14500
                region_basis = region_idx * 5200
                shock = 11000 if 88 <= day <= 94 and variety_idx == 1 else 0
                base_price = 52000 + variety_premium + region_basis + seasonal + heat_wave + shock
                for grade_idx, grade in enumerate(["Loại A", "Hàng xô"]):
                    grade_discount = 0 if grade_idx == 0 else -9500
                    noise = rng.uniform(-1800, 1800)
                    max_price = max(30000, base_price + grade_discount + noise)
                    min_price = max_price - rng.uniform(3500, 6500)
                    db.add(
                        DailyMarketPrice(
                            record_timestamp=ts,
                            variety_id=variety.variety_id,
                            quality_grade=grade,
                            region_id=region.region_id,
                            exchange_source=sources[(day + region_idx + variety_idx) % len(sources)],
                            min_price_vnd=round(min_price, 2),
                            max_price_vnd=round(max_price, 2),
                            volume_traded_tons=round(18 + rng.random() * 52 + grade_idx * 11, 2),
                        )
                    )
    db.commit()


def normalize_vietnamese_labels(db: Session) -> None:
    for variety in db.scalars(select(DurianVariety)).all():
        variety.name = vi_variety(variety.name) or variety.name
        if variety.description == "Discovered by scraper from public market data.":
            variety.description = "Được phát hiện từ dữ liệu giá công khai."

    for region in db.scalars(select(ProductionRegion)).all():
        region.region_name = vi_region(region.region_name) or region.region_name
        region.province = vi_province(region.province)
        region.region_name, region.province = normalize_location(region.region_name, region.province)

    for price in db.scalars(select(DailyMarketPrice)).all():
        price.quality_grade = vi_grade(price.quality_grade)
        price.exchange_source = vi_source(price.exchange_source)

    for telemetry in db.scalars(select(IotSensorTelemetry)).all():
        telemetry.status = vi_status(telemetry.status)

    for run in db.scalars(select(ScrapeRun)).all():
        run.status = vi_status(run.status) or run.status

    db.commit()
    _merge_duplicate_varieties(db)
    _merge_duplicate_regions(db)
    _remove_wrong_crop_regions(db)


def _merge_duplicate_varieties(db: Session) -> None:
    seen: dict[str, DurianVariety] = {}
    for variety in db.scalars(select(DurianVariety).order_by(DurianVariety.variety_id)).all():
        canonical = seen.get(variety.name)
        if not canonical:
            seen[variety.name] = variety
            continue
        for price in db.scalars(
            select(DailyMarketPrice).where(DailyMarketPrice.variety_id == variety.variety_id)
        ).all():
            conflict = db.scalar(
                select(DailyMarketPrice).where(
                    and_(
                        DailyMarketPrice.record_timestamp == price.record_timestamp,
                        DailyMarketPrice.variety_id == canonical.variety_id,
                        DailyMarketPrice.region_id == price.region_id,
                        DailyMarketPrice.quality_grade == price.quality_grade,
                        DailyMarketPrice.exchange_source == price.exchange_source,
                    )
                )
            )
            if conflict:
                db.execute(delete(DailyMarketPrice).where(DailyMarketPrice.id == price.id))
            else:
                price.variety_id = canonical.variety_id
        db.execute(delete(DurianVariety).where(DurianVariety.variety_id == variety.variety_id))
    db.commit()


def _merge_duplicate_regions(db: Session) -> None:
    seen: dict[tuple[str, str | None], ProductionRegion] = {}
    for region in db.scalars(select(ProductionRegion).order_by(ProductionRegion.region_id)).all():
        key = (region.region_name, region.province)
        canonical = seen.get(key)
        if not canonical:
            seen[key] = region
            continue
        for price in db.scalars(
            select(DailyMarketPrice).where(DailyMarketPrice.region_id == region.region_id)
        ).all():
            conflict = db.scalar(
                select(DailyMarketPrice).where(
                    and_(
                        DailyMarketPrice.record_timestamp == price.record_timestamp,
                        DailyMarketPrice.variety_id == price.variety_id,
                        DailyMarketPrice.region_id == canonical.region_id,
                        DailyMarketPrice.quality_grade == price.quality_grade,
                        DailyMarketPrice.exchange_source == price.exchange_source,
                    )
                )
            )
            if conflict:
                db.execute(delete(DailyMarketPrice).where(DailyMarketPrice.id == price.id))
            else:
                price.region_id = canonical.region_id
        db.execute(
            update(WeatherEnvironmentalMetric)
            .where(WeatherEnvironmentalMetric.region_id == region.region_id)
            .values(region_id=canonical.region_id)
        )
        db.execute(
            update(IotSensorTelemetry)
            .where(IotSensorTelemetry.region_id == region.region_id)
            .values(region_id=canonical.region_id)
        )
        db.execute(
            update(WatchlistItem)
            .where(WatchlistItem.region_id == region.region_id)
            .values(region_id=canonical.region_id)
        )
        db.execute(delete(ProductionRegion).where(ProductionRegion.region_id == region.region_id))
    db.commit()


def _remove_wrong_crop_regions(db: Session) -> None:
    rows = db.scalars(select(DailyMarketPrice).join(ProductionRegion)).all()
    deleted = 0
    for price in rows:
        if price.region and price.region.province and not is_crop_province(price.crop_type, price.region.province):
            db.delete(price)
            deleted += 1
    if deleted:
        db.commit()
