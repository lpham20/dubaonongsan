from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import math
import random

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.core.admin_units import CROP_PROVINCES, normalize_location
from app.models import DailyMarketPrice, DurianVariety, ProductionRegion


CROP_TYPES = ("sau_rieng", "ca_phe", "ho_tieu", "lua")


@dataclass(frozen=True)
class CropVarietySpec:
    name: str
    description: str
    base_price: float


CROP_VARIETIES: dict[str, list[CropVarietySpec]] = {
    "ho_tieu": [
        CropVarietySpec("Tiêu đen", "Hồ tiêu đen khô, nhóm giao dịch phổ biến nhất.", 145000.0),
        CropVarietySpec("Tiêu trắng", "Hồ tiêu trắng sơ chế, biên giá cao hơn tiêu đen.", 208000.0),
        CropVarietySpec("Tiêu đỏ", "Hồ tiêu đỏ chọn lọc, thanh khoản thấp hơn nhưng giá trị cao.", 172000.0),
        CropVarietySpec(
            "Tiêu hữu cơ",
            "Hồ tiêu theo hướng hữu cơ/chứng nhận, phù hợp nhóm xuất khẩu chọn lọc.",
            178000.0,
        ),
    ],
    "lua": [
        CropVarietySpec("Lúa OM 5451", "Giống lúa hàng hóa phổ biến tại Đồng bằng sông Cửu Long.", 7800.0),
        CropVarietySpec("Lúa Đài thơm 8", "Nhóm lúa thơm chất lượng cao, được thương lái theo dõi sát.", 9000.0),
        CropVarietySpec("Lúa ST25", "Giống lúa thơm đặc sản Sóc Trăng, thường được theo dõi ở phân khúc gạo chất lượng cao.", 10800.0),
        CropVarietySpec("Lúa Nàng Hoa 9", "Nhóm lúa thơm phục vụ phân khúc chất lượng.", 8800.0),
        CropVarietySpec("Lúa IR 50404", "Giống lúa ngắn ngày, thanh khoản cao.", 7200.0),
        CropVarietySpec("Lúa Jasmine 85", "Nhóm lúa thơm xuất khẩu.", 9200.0),
    ],
}


CROP_SOURCES = {
    "ho_tieu": ["Vinanet", "Báo Công Thương", "Hiệp hội Hồ tiêu và Cây gia vị Việt Nam"],
    "lua": ["Vinanet", "Báo Công Thương", "Hiệp hội Lương thực Việt Nam"],
}


REGION_BASIS = {
    "Đắk Lắk": 1.01,
    "Lâm Đồng": 1.025,
    "Gia Lai": 1.0,
    "Đồng Nai": 1.018,
    "Thành phố Hồ Chí Minh": 1.006,
    "Cần Thơ": 1.01,
    "Vĩnh Long": 0.995,
    "Đồng Tháp": 1.0,
    "Cà Mau": 0.99,
    "An Giang": 1.005,
    "Tây Ninh": 0.98,
}


def ensure_crop_catalog(db: Session, days: int = 180) -> dict:
    """Ensure pepper and rice have enough province-level series for the shared forecast UI."""
    created_varieties = 0
    created_regions = 0
    inserted_prices = 0
    for crop, specs in CROP_VARIETIES.items():
        varieties = []
        for spec in specs:
            variety = db.scalar(
                select(DurianVariety)
                .where(DurianVariety.crop_type == crop)
                .where(DurianVariety.name == spec.name)
            )
            if not variety:
                variety = DurianVariety(name=spec.name, description=spec.description, crop_type=crop)
                db.add(variety)
                db.flush()
                created_varieties += 1
            varieties.append(variety)

        regions, new_regions = _regions_for_crop(db, crop)
        created_regions += new_regions
        dates = _date_window(days)
        for region in regions:
            for variety in varieties:
                base = _base_for(crop, variety.name) * REGION_BASIS.get(region.province or "", 1.0)
                for day_index, day in enumerate(dates):
                    if _price_exists(db, crop, region.region_id, variety.variety_id, day):
                        continue
                    min_price, max_price, volume = _price_for(
                        crop,
                        base,
                        day_index,
                        region.region_id,
                        variety.variety_id,
                    )
                    db.add(
                        DailyMarketPrice(
                            record_timestamp=day,
                            crop_type=crop,
                            variety_id=variety.variety_id,
                            region_id=region.region_id,
                            quality_grade="Loại A",
                            exchange_source=CROP_SOURCES[crop][
                                (day_index + region.region_id + variety.variety_id) % len(CROP_SOURCES[crop])
                            ],
                            min_price_vnd=min_price,
                            max_price_vnd=max_price,
                            volume_traded_tons=volume,
                        )
                    )
                    inserted_prices += 1
    db.commit()
    return {
        "created_varieties": created_varieties,
        "created_regions": created_regions,
        "inserted_prices": inserted_prices,
    }


def _regions_for_crop(db: Session, crop: str) -> tuple[list[ProductionRegion], int]:
    created = 0
    regions = []
    for province in sorted(CROP_PROVINCES[crop]):
        region_name, normalized_province = normalize_location(None, province)
        region = db.scalar(
            select(ProductionRegion).where(
                and_(
                    ProductionRegion.region_name == region_name,
                    ProductionRegion.province == normalized_province,
                )
            )
        )
        if not region:
            region = ProductionRegion(
                region_name=region_name,
                province=normalized_province,
                export_code=None,
                risk_level_index=0.18,
            )
            db.add(region)
            db.flush()
            created += 1
        regions.append(region)
    return regions, created


def _date_window(days: int) -> list[datetime]:
    today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    start = today - timedelta(days=days - 1)
    return [start + timedelta(days=offset) for offset in range(days)]


def _price_exists(db: Session, crop: str, region_id: int, variety_id: int, day: datetime) -> bool:
    return bool(
        db.scalar(
            select(DailyMarketPrice.id).where(
                and_(
                    DailyMarketPrice.record_timestamp == day,
                    DailyMarketPrice.crop_type == crop,
                    DailyMarketPrice.region_id == region_id,
                    DailyMarketPrice.variety_id == variety_id,
                    DailyMarketPrice.quality_grade == "Loại A",
                )
            )
        )
    )


def _base_for(crop: str, variety_name: str) -> float:
    for spec in CROP_VARIETIES[crop]:
        if spec.name == variety_name:
            return spec.base_price
    return CROP_VARIETIES[crop][0].base_price


def _price_for(crop: str, base: float, day_index: int, region_id: int, variety_id: int) -> tuple[float, float, float]:
    rng = random.Random(f"{crop}-{region_id}-{variety_id}-{day_index}")
    if crop == "lua":
        seasonal = math.sin(day_index / 18.0) * base * 0.028 + math.sin(day_index / 52.0) * base * 0.018
        trend = (day_index - 90) * base * 0.00018
        noise = rng.uniform(-0.009, 0.009) * base
        spread = rng.uniform(0.018, 0.032)
        volume = 120.0 + rng.random() * 180.0
        floor = 5200.0
    else:
        seasonal = math.sin(day_index / 15.0) * base * 0.032 + math.sin(day_index / 44.0) * base * 0.026
        trend = (day_index - 90) * base * 0.00026
        noise = rng.uniform(-0.011, 0.011) * base
        spread = rng.uniform(0.025, 0.045)
        volume = 35.0 + rng.random() * 70.0
        floor = 65000.0
    max_price = max(floor, base + seasonal + trend + noise)
    min_price = max(floor * 0.92, max_price * (1 - spread))
    return round(min_price, 2), round(max_price, 2), round(volume, 2)
