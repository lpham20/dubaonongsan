from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import math
import random
from statistics import mean

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.core.admin_units import is_crop_province
from app.models import DailyMarketPrice, DurianVariety, ProductionRegion


BACKFILL_SOURCE = "Nội suy từ giá vùng"
MODEL_READY_DAYS = 240
MODEL_READY_GRADE = "Loại A"
ANCHOR_LOOKBACK_DAYS = 365

NON_PRODUCTION_REGIONS = {"Thị trường Việt Nam", "Chợ đầu mối TP.HCM"}

VARIETY_BASE_PRICE = {
    "Ri6": 60000.0,
    "Sầu Thái Dona": 85000.0,
    "Sầu Thái Monthong": 88000.0,
    "Sầu Musang King": 125000.0,
    "Sầu Black Thorn": 150000.0,
    "Sầu Chuồng Bò": 70000.0,
    "Sầu Sáp Hữu": 76000.0,
    "Sầu riêng tổng hợp": 72000.0,
    "Robusta nhân xô": 136000.0,
    "Robusta loại 1": 141000.0,
    "Arabica Catimor": 160000.0,
    "Culi Robusta": 150000.0,
    "Moka Cầu Đất": 238000.0,
    "Cà phê tổng hợp": 138000.0,
    "Tiêu đen": 145000.0,
    "Tiêu trắng": 208000.0,
    "Tiêu đỏ": 172000.0,
    "Tiêu hữu cơ": 178000.0,
    "Lúa OM 5451": 7800.0,
    "Lúa Đài thơm 8": 9000.0,
    "Lúa ST25": 10800.0,
    "Lúa Nàng Hoa 9": 8800.0,
    "Lúa IR 50404": 7200.0,
    "Lúa Jasmine 85": 9200.0,
}

REGION_BASIS = {
    "Tây Nam Bộ": 0.98,
    "Đông Nam Bộ": 1.0,
    "Tây Nguyên": 1.04,
    "Tây Bắc": 0.98,
}

PROVINCE_BASIS = {
    "Tiền Giang": 1.02,
    "Cần Thơ": 0.98,
    "Đồng Tháp": 0.97,
    "Bến Tre": 0.99,
    "Vĩnh Long": 0.98,
    "An Giang": 1.0,
    "Cà Mau": 0.99,
    "Đắk Lắk": 1.04,
    "Lâm Đồng": 1.02,
    "Gia Lai": 1.01,
    "Đắk Nông": 1.03,
    "Đồng Nai": 1.0,
    "Bình Phước": 0.99,
    "Tây Ninh": 0.98,
    "Kon Tum": 0.99,
    "Bà Rịa - Vũng Tàu": 1.01,
    "Sơn La": 0.98,
    "Điện Biên": 0.97,
}


@dataclass(frozen=True)
class BackfillSummary:
    source: str
    status: str
    records_found: int
    records_inserted: int
    records_updated: int
    model_ready_pairs: int


class ModelReadyBackfillService:
    def __init__(self, db: Session, days: int = MODEL_READY_DAYS, crop_type: str = "sau_rieng") -> None:
        self.db = db
        self.days = days
        self.crop_type = crop_type

    def backfill(self) -> dict:
        regions = self._production_regions()
        varieties = self.db.scalars(
            select(DurianVariety)
            .where(DurianVariety.crop_type == self.crop_type)
            .order_by(DurianVariety.variety_id)
        ).all()
        dates = self._date_window()
        inserted = 0
        updated = 0

        for region in regions:
            for variety in varieties:
                anchors = self._anchor_prices(region, variety)
                existing_dates = set(
                    self.db.scalars(
                        select(DailyMarketPrice.record_timestamp).where(
                            and_(
                                DailyMarketPrice.region_id == region.region_id,
                                DailyMarketPrice.variety_id == variety.variety_id,
                                DailyMarketPrice.crop_type == self.crop_type,
                                DailyMarketPrice.quality_grade == MODEL_READY_GRADE,
                            )
                        )
                    ).all()
                )
                for idx, day in enumerate(dates):
                    if day in existing_dates:
                        continue
                    min_price, max_price, volume = self._synthetic_price(
                        region=region,
                        variety=variety,
                        day_index=idx,
                        anchor_prices=anchors,
                    )
                    existing = self.db.scalar(
                        select(DailyMarketPrice).where(
                            and_(
                                DailyMarketPrice.record_timestamp == day,
                                DailyMarketPrice.crop_type == self.crop_type,
                                DailyMarketPrice.region_id == region.region_id,
                                DailyMarketPrice.variety_id == variety.variety_id,
                                DailyMarketPrice.quality_grade == MODEL_READY_GRADE,
                                DailyMarketPrice.exchange_source == BACKFILL_SOURCE,
                            )
                        )
                    )
                    if existing:
                        existing.min_price_vnd = min_price
                        existing.max_price_vnd = max_price
                        existing.volume_traded_tons = volume
                        updated += 1
                    else:
                        self.db.add(
                            DailyMarketPrice(
                                record_timestamp=day,
                                crop_type=self.crop_type,
                                region_id=region.region_id,
                                variety_id=variety.variety_id,
                                quality_grade=MODEL_READY_GRADE,
                                exchange_source=BACKFILL_SOURCE,
                                min_price_vnd=min_price,
                                max_price_vnd=max_price,
                                volume_traded_tons=volume,
                            )
                        )
                        inserted += 1
        self.db.commit()
        total_pairs = len(regions) * len(varieties)
        return BackfillSummary(
            source=BACKFILL_SOURCE,
            status="thành công",
            records_found=total_pairs * len(dates),
            records_inserted=inserted,
            records_updated=updated,
            model_ready_pairs=total_pairs,
        ).__dict__

    def _production_regions(self) -> list[ProductionRegion]:
        rows = self.db.scalars(select(ProductionRegion).order_by(ProductionRegion.region_id)).all()
        return [
            row
            for row in rows
            if row.province is not None
            and row.region_name not in NON_PRODUCTION_REGIONS
            and is_crop_province(self.crop_type, row.province)
            and self.db.scalar(
                select(DailyMarketPrice.id)
                .where(DailyMarketPrice.region_id == row.region_id)
                .where(DailyMarketPrice.crop_type == self.crop_type)
                .limit(1)
            )
        ]

    def _date_window(self) -> list[datetime]:
        latest = self.db.scalar(select(func.max(DailyMarketPrice.record_timestamp)))
        if latest is None:
            latest = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        latest = latest.replace(tzinfo=None, hour=0, minute=0, second=0, microsecond=0)
        start = latest - timedelta(days=self.days - 1)
        return [start + timedelta(days=offset) for offset in range(self.days)]

    def _anchor_prices(self, region: ProductionRegion, variety: DurianVariety) -> list[float]:
        exact = self._prices_for(region_id=region.region_id, variety_id=variety.variety_id)
        if len(exact) >= 3:
            return exact

        regional_same_variety = self._prices_for(
            region_name=region.region_name,
            variety_id=variety.variety_id,
        )
        if len(regional_same_variety) >= 3:
            return regional_same_variety

        same_region = self._prices_for(region_id=region.region_id)
        if len(same_region) >= 3:
            target_base = self._variety_base(variety.name)
            source_base = mean(same_region)
            scale = target_base / source_base if source_base else 1.0
            return [price * scale for price in same_region]

        global_same_variety = self._prices_for(variety_id=variety.variety_id)
        if len(global_same_variety) >= 3:
            return global_same_variety

        return [self._regional_base(region, variety)]

    def _prices_for(
        self,
        region_id: int | None = None,
        region_name: str | None = None,
        variety_id: int | None = None,
    ) -> list[float]:
        stmt = (
            select(DailyMarketPrice.max_price_vnd)
            .join(ProductionRegion, DailyMarketPrice.region_id == ProductionRegion.region_id)
            .where(DailyMarketPrice.max_price_vnd.is_not(None))
            .where(DailyMarketPrice.crop_type == self.crop_type)
        )
        filters = []
        if region_id:
            filters.append(DailyMarketPrice.region_id == region_id)
        if region_name:
            filters.append(ProductionRegion.region_name == region_name)
        if variety_id:
            filters.append(DailyMarketPrice.variety_id == variety_id)
        if filters:
            stmt = stmt.where(and_(*filters))
        latest = self.db.scalar(
            select(func.max(DailyMarketPrice.record_timestamp)).where(DailyMarketPrice.crop_type == self.crop_type)
        )
        if latest is not None:
            stmt = stmt.where(DailyMarketPrice.record_timestamp >= latest - timedelta(days=ANCHOR_LOOKBACK_DAYS))
        rows = self.db.scalars(stmt.order_by(DailyMarketPrice.record_timestamp.desc()).limit(240)).all()
        return [float(row) for row in rows]

    def _synthetic_price(
        self,
        region: ProductionRegion,
        variety: DurianVariety,
        day_index: int,
        anchor_prices: list[float],
    ) -> tuple[float, float, float]:
        anchor = mean(anchor_prices[-30:]) if len(anchor_prices) >= 30 else mean(anchor_prices)
        base = 0.74 * anchor + 0.26 * self._regional_base(region, variety)
        rng = random.Random(f"{region.region_id}-{variety.variety_id}-{day_index}")
        seasonal = math.sin(day_index / 8.5) * base * 0.055 + math.sin(day_index / 27.0) * base * 0.035
        trend = (day_index - self.days / 2) * base * 0.00045
        noise = rng.uniform(-0.018, 0.018) * base
        floor = 4200.0 if self.crop_type == "lua" else 52000.0 if self.crop_type in {"ca_phe", "ho_tieu"} else 22000.0
        max_price = max(floor, base + seasonal + trend + noise)
        min_price = max(floor * 0.88, max_price - max(floor * 0.08, max_price * rng.uniform(0.035, 0.07)))
        volume = max(3.0, 18.0 + rng.random() * 42.0)
        return round(min_price, 2), round(max_price, 2), round(volume, 2)

    def _regional_base(self, region: ProductionRegion, variety: DurianVariety) -> float:
        return (
            self._variety_base(variety.name)
            * REGION_BASIS.get(region.region_name, 1.0)
            * PROVINCE_BASIS.get(region.province or "", 1.0)
        )

    @staticmethod
    def _variety_base(variety_name: str) -> float:
        return VARIETY_BASE_PRICE.get(variety_name, 74000.0)
