from datetime import timedelta
from sqlalchemy import Select, and_, func, select
from sqlalchemy.orm import Session

from app.models import (
    DailyMarketPrice,
    DurianVariety,
    IotSensorTelemetry,
    ProductionRegion,
    WeatherEnvironmentalMetric,
)


SYNTHETIC_SOURCE = "Nội suy từ giá vùng"
DERIVED_SOURCE_PREFIX = "Hiệu chỉnh từ "


class DataLoader:
    """Tạo tập dữ liệu đa biến cho biểu đồ, dự báo và tín hiệu giao dịch."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def historical_prices(
        self,
        crop_type: str = "sau_rieng",
        region_id: int | None = None,
        variety_id: int | None = None,
        quality_grade: str | None = "Loại A",
        limit: int = 240,
    ) -> list[dict]:
        stmt = self._base_price_query()
        filters = [DailyMarketPrice.crop_type == crop_type]
        if region_id:
            filters.append(DailyMarketPrice.region_id == region_id)
        if variety_id:
            filters.append(DailyMarketPrice.variety_id == variety_id)
        if quality_grade:
            filters.append(DailyMarketPrice.quality_grade == quality_grade)
        if filters:
            stmt = stmt.where(and_(*filters))
        rows = self.db.execute(
            stmt.order_by(DailyMarketPrice.record_timestamp.desc()).limit(limit)
        ).mappings()
        return list(reversed([self._row_to_point(row) for row in rows]))

    def daily_price_series(
        self,
        crop_type: str = "sau_rieng",
        region_id: int | None = None,
        variety_id: int | None = None,
        quality_grade: str | None = "Loại A",
        limit: int = 240,
    ) -> list[dict]:
        raw_limit = min(max(limit * 6, limit), 5000)
        points = self.historical_prices(
            region_id=region_id,
            variety_id=variety_id,
            crop_type=crop_type,
            quality_grade=quality_grade,
            limit=raw_limit,
        )
        return self._daily_series(points)[-limit:]

    def latest_feature_window(
        self,
        crop_type: str = "sau_rieng",
        region_id: int | None = None,
        variety_id: int | None = None,
        lookback_days: int = 60,
    ) -> list[dict]:
        points = self.daily_price_series(
            region_id=region_id,
            variety_id=variety_id,
            crop_type=crop_type,
            quality_grade="Loại A",
            limit=lookback_days,
        )
        if not points:
            points = self.daily_price_series(
                region_id=region_id,
                variety_id=variety_id,
                crop_type=crop_type,
                quality_grade=None,
                limit=lookback_days,
            )
        return self._interpolate(points)

    def _base_price_query(self) -> Select:
        latest_telemetry = (
            select(
                IotSensorTelemetry.region_id.label("region_id"),
                IotSensorTelemetry.maturity_index.label("maturity_index"),
                func.row_number()
                .over(
                    partition_by=IotSensorTelemetry.region_id,
                    order_by=(IotSensorTelemetry.record_timestamp.desc(), IotSensorTelemetry.id.desc()),
                )
                .label("rn"),
            )
            .subquery()
        )

        return (
            select(
                DailyMarketPrice.record_timestamp.label("timestamp"),
                DailyMarketPrice.region_id.label("region_id"),
                DailyMarketPrice.variety_id.label("variety_id"),
                DurianVariety.name.label("variety"),
                ProductionRegion.region_name.label("region"),
                ProductionRegion.province.label("province"),
                DailyMarketPrice.quality_grade,
                DailyMarketPrice.exchange_source,
                DailyMarketPrice.min_price_vnd,
                DailyMarketPrice.max_price_vnd,
                DailyMarketPrice.volume_traded_tons,
                WeatherEnvironmentalMetric.temp_max_celsius,
                WeatherEnvironmentalMetric.precipitation_mm,
                latest_telemetry.c.maturity_index,
            )
            .join(DurianVariety, DailyMarketPrice.variety_id == DurianVariety.variety_id)
            .join(ProductionRegion, DailyMarketPrice.region_id == ProductionRegion.region_id)
            .outerjoin(
                WeatherEnvironmentalMetric,
                and_(
                    WeatherEnvironmentalMetric.region_id == DailyMarketPrice.region_id,
                    WeatherEnvironmentalMetric.record_timestamp == DailyMarketPrice.record_timestamp,
                ),
            )
            .outerjoin(
                latest_telemetry,
                and_(
                    latest_telemetry.c.region_id == DailyMarketPrice.region_id,
                    latest_telemetry.c.rn == 1,
                ),
            )
        )

    @staticmethod
    def _row_to_point(row) -> dict:
        point = dict(row)
        for key in (
            "min_price_vnd",
            "max_price_vnd",
            "volume_traded_tons",
            "temp_max_celsius",
            "precipitation_mm",
            "maturity_index",
        ):
            if point.get(key) is not None:
                point[key] = float(point[key])
        source = point.get("exchange_source") or ""
        is_interpolated = source == SYNTHETIC_SOURCE
        is_calibrated = source.startswith(DERIVED_SOURCE_PREFIX)
        point["is_synthetic"] = is_interpolated or is_calibrated
        point["data_kind"] = "Nội suy" if is_interpolated else ("Hiệu chỉnh" if is_calibrated else "Quan sát")
        return point

    @staticmethod
    def _daily_series(points: list[dict]) -> list[dict]:
        grouped: dict[str, list[dict]] = {}
        order: list[str] = []
        for point in points:
            key = DataLoader._date_key(point.get("timestamp"))
            if key not in grouped:
                grouped[key] = []
                order.append(key)
            grouped[key].append(point)

        result: list[dict] = []
        for key in order:
            rows = grouped[key]
            usable = [row for row in rows if not row.get("is_synthetic")] or rows
            base = dict(usable[-1])
            for numeric_key in (
                "min_price_vnd",
                "max_price_vnd",
                "volume_traded_tons",
                "temp_max_celsius",
                "precipitation_mm",
                "maturity_index",
            ):
                values = [float(row[numeric_key]) for row in usable if row.get(numeric_key) is not None]
                if values:
                    digits = 1 if numeric_key in {"temp_max_celsius", "precipitation_mm", "maturity_index"} else 2
                    base[numeric_key] = round(sum(values) / len(values), digits)
            base["timestamp"] = rows[-1].get("timestamp")
            base["is_synthetic"] = all(bool(row.get("is_synthetic")) for row in usable)
            result.append(base)
        return result

    @staticmethod
    def _date_key(value) -> str:
        if hasattr(value, "date"):
            return value.date().isoformat()
        return str(value)[:10]

    @staticmethod
    def _interpolate(points: list[dict]) -> list[dict]:
        if not points:
            return []
        result = [dict(point) for point in points]
        numeric_keys = [
            "max_price_vnd",
            "temp_max_celsius",
            "precipitation_mm",
            "volume_traded_tons",
            "maturity_index",
        ]
        last_seen = {key: None for key in numeric_keys}
        for point in result:
            for key in numeric_keys:
                if point.get(key) is None:
                    point[key] = last_seen[key]
                else:
                    last_seen[key] = point[key]
        for key in numeric_keys:
            fallback = next((p[key] for p in result if p.get(key) is not None), 0.0)
            for point in result:
                if point.get(key) is None:
                    point[key] = fallback
        return result

    @staticmethod
    def extend_timestamps(last_timestamp, horizon_days: int):
        return [last_timestamp + timedelta(days=offset) for offset in range(1, horizon_days + 1)]
