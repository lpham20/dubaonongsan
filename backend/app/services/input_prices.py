from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
import hashlib
import math
import random
from statistics import pstdev

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models import AgriInputPriceObservation, AgriInputProduct


INPUT_FORECAST_MODEL_KIND = "input-price-seasonal-v3"
MAX_INPUT_FORECAST_DAYS = 60
MIN_INPUT_FORECAST_POINTS = 3
TREND_SMOOTHING = 0.35
SEASONAL_AMPLITUDE = 0.055


FERTILIZER_PRODUCTS = [
    {
        "slug": "ure",
        "name": "Urê",
        "product_type": "Phân đơn",
        "nutrient_profile": "46% N",
        "package_label": "Bao 50 kg",
        "package_size_kg": 50,
        "base_package_price": 590_000,
        "brands": ["Phú Mỹ", "Cà Mau"],
    },
    {
        "slug": "dap",
        "name": "DAP",
        "product_type": "Phân đơn",
        "nutrient_profile": "18-46-0",
        "package_label": "Bao 50 kg",
        "package_size_kg": 50,
        "base_package_price": 1_030_000,
        "brands": ["Đình Vũ", "Nhập khẩu"],
    },
    {
        "slug": "kali-mop",
        "name": "Kali MOP",
        "product_type": "Phân đơn",
        "nutrient_profile": "60% K2O",
        "package_label": "Bao 50 kg",
        "package_size_kg": 50,
        "base_package_price": 760_000,
        "brands": ["Phú Mỹ", "Nhập khẩu"],
    },
    {
        "slug": "kali-sop",
        "name": "Kali SOP",
        "product_type": "Phân đơn",
        "nutrient_profile": "50% K2O + 18% S",
        "package_label": "Bao 50 kg",
        "package_size_kg": 50,
        "base_package_price": 1_050_000,
        "brands": ["Nhập khẩu", "SOP tiêu chuẩn"],
    },
    {
        "slug": "sa",
        "name": "SA",
        "product_type": "Phân đơn",
        "nutrient_profile": "21% N + 24% S",
        "package_label": "Bao 50 kg",
        "package_size_kg": 50,
        "base_package_price": 350_000,
        "brands": ["Nhập khẩu", "Phú Mỹ"],
    },
    {
        "slug": "lan-nung-chay",
        "name": "Lân nung chảy",
        "product_type": "Phân lân",
        "nutrient_profile": "P2O5 + CaO + MgO",
        "package_label": "Bao 50 kg",
        "package_size_kg": 50,
        "base_package_price": 245_000,
        "brands": ["Lâm Thao", "Văn Điển"],
    },
    {
        "slug": "npk-16-16-8",
        "name": "NPK 16-16-8",
        "product_type": "Phân hỗn hợp",
        "nutrient_profile": "16-16-8",
        "package_label": "Bao 50 kg",
        "package_size_kg": 50,
        "base_package_price": 690_000,
        "brands": ["Bình Điền", "Phú Mỹ"],
    },
    {
        "slug": "npk-20-20-15",
        "name": "NPK 20-20-15",
        "product_type": "Phân hỗn hợp",
        "nutrient_profile": "20-20-15",
        "package_label": "Bao 50 kg",
        "package_size_kg": 50,
        "base_package_price": 870_000,
        "brands": ["Bình Điền", "Cà Mau"],
    },
    {
        "slug": "npk-15-15-15",
        "name": "NPK 15-15-15",
        "product_type": "Phân hỗn hợp",
        "nutrient_profile": "15-15-15",
        "package_label": "Bao 50 kg",
        "package_size_kg": 50,
        "base_package_price": 650_000,
        "brands": ["Bình Điền", "Lâm Thao"],
    },
    {
        "slug": "phan-huu-co-vi-sinh",
        "name": "Phân hữu cơ vi sinh",
        "product_type": "Phân hữu cơ",
        "nutrient_profile": "Hữu cơ + vi sinh",
        "package_label": "Bao 25 kg",
        "package_size_kg": 25,
        "base_package_price": 145_000,
        "brands": ["Hữu cơ miền Tây", "Hữu cơ Tây Nguyên"],
    },
]

REFERENCE_PROVINCES = [
    ("Đắk Lắk", "Tây Nguyên", 1.02),
    ("Lâm Đồng", "Tây Nguyên", 1.03),
    ("Đồng Tháp", "Đồng bằng sông Cửu Long", 0.99),
    ("Tiền Giang", "Đồng bằng sông Cửu Long", 1.0),
]


def seed_input_prices(db: Session) -> None:
    if db.scalar(select(AgriInputProduct.product_id).limit(1)):
        return

    now = datetime.now(UTC)
    products: list[AgriInputProduct] = []
    for item in FERTILIZER_PRODUCTS:
        product = AgriInputProduct(
            slug=item["slug"],
            name=item["name"],
            category="fertilizer",
            product_type=item["product_type"],
            nutrient_profile=item["nutrient_profile"],
            standard_unit="kg",
            package_label=item["package_label"],
            package_size_kg=item["package_size_kg"],
            notes="Dữ liệu nền tham chiếu; cần đối chiếu với báo giá đại lý trước khi ra quyết định mua bán.",
            is_active=True,
        )
        products.append(product)
    db.add_all(products)
    db.flush()

    rng = random.Random(20260522)
    months = _month_starts(datetime(2025, 6, 1, tzinfo=UTC), 12)
    for product, item in zip(products, FERTILIZER_PRODUCTS, strict=False):
        for month_idx, observed_at in enumerate(months):
            seasonal = 1 + math.sin(month_idx / 2.3) * 0.025
            slow_trend = 1 + (month_idx - 6) * 0.004
            for province, region_name, province_factor in REFERENCE_PROVINCES:
                for brand_idx, brand in enumerate(item["brands"]):
                    brand_factor = 1 + (brand_idx * 0.025)
                    noise = rng.uniform(-0.018, 0.018)
                    package_price = round(
                        item["base_package_price"] * seasonal * slow_trend * province_factor * brand_factor * (1 + noise),
                        -3,
                    )
                    package_size = float(item["package_size_kg"])
                    db.add(
                        AgriInputPriceObservation(
                            product_id=product.product_id,
                            observed_at=observed_at,
                            province=province,
                            region_name=region_name,
                            brand=brand,
                            seller_name=None,
                            source_name="Dữ liệu tham chiếu nền",
                            source_url=None,
                            package_price_vnd=package_price,
                            normalized_price_vnd=round(package_price / package_size, 2),
                            normalized_unit="kg",
                            package_size_kg=package_size,
                            confidence_score=0.55,
                            data_kind="reference",
                            created_at=now,
                        )
                    )
    db.commit()


def _month_starts(start: datetime, count: int) -> list[datetime]:
    rows = []
    year = start.year
    month = start.month
    for _ in range(count):
        rows.append(datetime(year, month, 1, tzinfo=UTC))
        month += 1
        if month > 12:
            month = 1
            year += 1
    return rows


class InputPriceService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def products(self, category: str = "fertilizer") -> list[AgriInputProduct]:
        return self.db.scalars(
            select(AgriInputProduct)
            .where(AgriInputProduct.category == category, AgriInputProduct.is_active.is_(True))
            .order_by(AgriInputProduct.product_type, AgriInputProduct.name)
        ).all()

    def summary(self, category: str = "fertilizer") -> dict:
        product_rows = self.products(category)
        latest_observed_at = self.db.scalar(
            select(func.max(AgriInputPriceObservation.observed_at))
            .join(AgriInputProduct)
            .where(AgriInputProduct.category == category)
        )
        provinces = self.db.scalars(
            select(AgriInputPriceObservation.province)
            .join(AgriInputProduct)
            .where(AgriInputProduct.category == category)
            .distinct()
            .order_by(AgriInputPriceObservation.province)
        ).all()
        return {
            "category": category,
            "latest_count": len(self.latest_prices(category=category, limit=500)),
            "provinces": list(provinces),
            "products": [row.name for row in product_rows],
            "latest_observed_at": latest_observed_at,
        }

    def latest_prices(
        self,
        *,
        category: str = "fertilizer",
        product_slug: str | None = None,
        province: str | None = None,
        limit: int = 200,
    ) -> list[dict]:
        query = (
            select(AgriInputPriceObservation)
            .join(AgriInputProduct)
            .where(AgriInputProduct.category == category, AgriInputProduct.is_active.is_(True))
            .order_by(desc(AgriInputPriceObservation.observed_at), AgriInputProduct.name)
        )
        if product_slug:
            query = query.where(AgriInputProduct.slug == product_slug)
        if province:
            query = query.where(AgriInputPriceObservation.province == province)

        latest_by_key: dict[tuple[int, str, str | None], AgriInputPriceObservation] = {}
        for row in self.db.scalars(query.limit(5000)).all():
            key = (row.product_id, row.province, row.brand)
            if key not in latest_by_key:
                latest_by_key[key] = row
            if len(latest_by_key) >= limit:
                break
        return [self._price_row(row) for row in latest_by_key.values()]

    def history(
        self,
        *,
        product_slug: str,
        province: str | None = None,
        brand: str | None = None,
        months: int = 12,
    ) -> list[dict]:
        since = datetime.now(UTC) - timedelta(days=max(1, months) * 31)
        query = (
            select(AgriInputPriceObservation)
            .join(AgriInputProduct)
            .where(
                AgriInputProduct.slug == product_slug,
                AgriInputProduct.category == "fertilizer",
                AgriInputPriceObservation.observed_at >= since,
            )
            .order_by(AgriInputPriceObservation.observed_at, AgriInputPriceObservation.brand)
        )
        if province:
            query = query.where(AgriInputPriceObservation.province == province)
        if brand:
            query = query.where(AgriInputPriceObservation.brand == brand)
        return [self._price_row(row) for row in self.db.scalars(query.limit(1200)).all()]

    def forecast(
        self,
        *,
        product_slug: str,
        province: str | None = None,
        brand: str | None = None,
        days: int = 30,
    ) -> dict:
        history = self.history(product_slug=product_slug, province=province, brand=brand, months=18)
        points = _aggregate_daily_input_prices(history)
        if len(points) < MIN_INPUT_FORECAST_POINTS and (province or brand):
            fallback_history = self.history(product_slug=product_slug, province=None, brand=None, months=18)
            fallback_points = _aggregate_daily_input_prices(fallback_history)
            if len(fallback_points) >= MIN_INPUT_FORECAST_POINTS:
                points = fallback_points

        if len(points) < MIN_INPUT_FORECAST_POINTS:
            return _empty_forecast("no-data", len(points))

        last_ts, last_package, _last_normalized, package_size = points[-1]
        ewma_trend = _ewma_daily_trend(points)
        daily_volatility = _daily_log_return_volatility(points)
        horizon = min(max(days, 1), MAX_INPUT_FORECAST_DAYS)
        last_seasonal = _seasonal_multiplier(last_ts)
        clean_curve: list[tuple[datetime, float]] = []
        for day in range(1, horizon + 1):
            ts = last_ts + timedelta(days=day)
            trend_component = ewma_trend * day * math.exp(-day / 45)
            seasonal_ratio = _seasonal_multiplier(ts) / last_seasonal
            clean_value = max(last_package * 0.35, (last_package + trend_component) * seasonal_ratio)
            clean_curve.append((ts, clean_value))

        seed = _forecast_seed(product_slug, province, brand, last_ts)
        base_curve = _add_deterministic_shock(clean_curve, daily_volatility, seed)
        base_curve = _ensure_minimum_spread(base_curve)

        points_output: list[dict] = []
        for index, (ts, base_value) in enumerate(base_curve, start=1):
            confidence_band = max(
                base_value * 0.004 * math.sqrt(index),
                base_value * max(0.012, daily_volatility * 0.9) * math.sqrt(index / 7),
            )
            low = max(0, base_value - confidence_band)
            high = base_value + confidence_band
            points_output.append(_forecast_point(ts, base_value, low, high, package_size))

        return {
            "points": points_output,
            "model_kind": INPUT_FORECAST_MODEL_KIND,
            "history_points": len(points),
            "volatility": round(daily_volatility, 6),
            "latest_observed_at": last_ts,
        }

    @staticmethod
    def _price_row(row: AgriInputPriceObservation) -> dict:
        return {
            "observation_id": row.observation_id,
            "product_id": row.product_id,
            "product_slug": row.product.slug,
            "product_name": row.product.name,
            "product_type": row.product.product_type,
            "observed_at": row.observed_at,
            "province": row.province,
            "region_name": row.region_name,
            "brand": row.brand,
            "seller_name": row.seller_name,
            "source_name": row.source_name,
            "source_url": row.source_url,
            "package_price_vnd": float(row.package_price_vnd) if row.package_price_vnd is not None else None,
            "normalized_price_vnd": float(row.normalized_price_vnd),
            "normalized_unit": row.normalized_unit,
            "package_size_kg": float(row.package_size_kg) if row.package_size_kg is not None else None,
            "package_label": f"Bao {float(row.package_size_kg):g} kg" if row.package_size_kg is not None else row.product.package_label,
            "confidence_score": float(row.confidence_score),
            "data_kind": row.data_kind,
        }


def _empty_forecast(model_kind: str, history_points: int = 0) -> dict:
    return {
        "points": [],
        "model_kind": model_kind,
        "history_points": history_points,
        "volatility": 0.0,
        "latest_observed_at": None,
    }


def _aggregate_daily_input_prices(history: list[dict]) -> list[tuple[datetime, float, float, float]]:
    grouped: dict[datetime, list[dict]] = defaultdict(list)
    for row in history:
        observed_at = row.get("observed_at")
        if not isinstance(observed_at, datetime):
            continue
        observed_day = observed_at.replace(hour=0, minute=0, second=0, microsecond=0)
        grouped[observed_day].append(row)

    points: list[tuple[datetime, float, float, float]] = []
    for ts in sorted(grouped):
        rows = grouped[ts]
        confidence_total = 0.0
        weighted_package = 0.0
        weighted_normalized = 0.0
        for row in rows:
            package_price = float(row.get("package_price_vnd") or 0)
            normalized_price = float(row.get("normalized_price_vnd") or 0)
            if package_price <= 0 or normalized_price <= 0:
                continue
            weight = max(0.2, min(1.0, float(row.get("confidence_score") or 0.55)))
            confidence_total += weight
            weighted_package += package_price * weight
            weighted_normalized += normalized_price * weight
        if confidence_total <= 0:
            continue
        package_size = float(rows[0].get("package_size_kg") or 1)
        points.append((ts, weighted_package / confidence_total, weighted_normalized / confidence_total, package_size))
    return points


def _ewma_daily_trend(points: list[tuple[datetime, float, float, float]]) -> float:
    recent = points[-min(12, len(points)) :]
    daily_diffs: list[float] = []
    for previous, current in zip(recent, recent[1:], strict=False):
        gap_days = max(1, (current[0] - previous[0]).days)
        daily_diffs.append((current[1] - previous[1]) / gap_days)
    if not daily_diffs:
        return 0.0
    ewma = daily_diffs[0]
    for diff in daily_diffs[1:]:
        ewma = TREND_SMOOTHING * diff + (1 - TREND_SMOOTHING) * ewma
    return ewma


def _daily_log_return_volatility(points: list[tuple[datetime, float, float, float]]) -> float:
    returns: list[float] = []
    for previous, current in zip(points, points[1:], strict=False):
        if previous[1] <= 0 or current[1] <= 0:
            continue
        gap_days = max(1, (current[0] - previous[0]).days)
        returns.append(math.log(current[1] / previous[1]) / math.sqrt(gap_days))
    volatility = pstdev(returns) if len(returns) > 1 else 0.008
    return max(0.006, min(0.035, volatility))


def _seasonal_multiplier(value: datetime) -> float:
    month = value.month + (value.day - 1) / 31
    spring_summer_peak = _cyclic_peak(month, 5, width=1.55)
    winter_spring_peak = _cyclic_peak(month, 11, width=1.65)
    august_trough = _cyclic_peak(month, 8, width=1.9)
    february_trough = _cyclic_peak(month, 2, width=1.9)
    seasonal_signal = max(spring_summer_peak, winter_spring_peak) - 0.65 * max(august_trough, february_trough)
    seasonal_signal = max(-1.0, min(1.0, seasonal_signal))
    return 1 + SEASONAL_AMPLITUDE * seasonal_signal


def _cyclic_peak(month: float, center: float, *, width: float) -> float:
    distance = abs((month - center + 6) % 12 - 6)
    return math.exp(-((distance / width) ** 2))


def _forecast_seed(product_slug: str, province: str | None, brand: str | None, last_ts: datetime) -> int:
    raw = f"{product_slug}|{province or ''}|{brand or ''}|{last_ts.date().isoformat()}".encode("utf-8")
    return int(hashlib.sha256(raw).hexdigest()[:12], 16)


def _add_deterministic_shock(
    clean_curve: list[tuple[datetime, float]],
    daily_volatility: float,
    seed: int,
) -> list[tuple[datetime, float]]:
    rng = random.Random(seed)
    shocked: list[tuple[datetime, float]] = []
    cumulative = 0.0
    for ts, value in clean_curve:
        epsilon = rng.gauss(0, daily_volatility * 0.45)
        cumulative = 0.84 * cumulative + epsilon
        shocked.append((ts, max(0, value * (1 + cumulative))))
    return shocked


def _ensure_minimum_spread(curve: list[tuple[datetime, float]]) -> list[tuple[datetime, float]]:
    if len(curve) < 2:
        return curve
    values = [value for _, value in curve]
    avg = sum(values) / len(values)
    if avg <= 0:
        return curve
    spread = max(values) - min(values)
    required = avg * 0.011
    if spread >= required:
        return curve
    n = max(1, len(curve) - 1)
    amplitude = (required - spread) * 0.7
    adjusted: list[tuple[datetime, float]] = []
    for index, (ts, value) in enumerate(curve):
        wave = math.sin((index / n) * math.pi * 1.4 - math.pi / 5)
        adjusted.append((ts, max(0, value + amplitude * wave)))
    return adjusted


def _forecast_point(
    ts: datetime,
    value: float,
    low: float,
    high: float,
    package_size: float,
) -> dict:
    safe_package_size = max(package_size, 1)
    return {
        "timestamp": ts,
        "forecast_price_vnd": round(value, 2),
        "confidence_low_vnd": round(low, 2),
        "confidence_high_vnd": round(high, 2),
        "normalized_price_vnd": round(value / safe_package_size, 2),
        "normalized_low_vnd": round(low / safe_package_size, 2),
        "normalized_high_vnd": round(high / safe_package_size, 2),
        "model_kind": INPUT_FORECAST_MODEL_KIND,
    }
