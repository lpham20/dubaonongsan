from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
import math
import random
from statistics import pstdev

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models import AgriInputPriceObservation, AgriInputProduct


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
    ) -> list[dict]:
        history = self.history(product_slug=product_slug, province=province, brand=brand, months=18)
        if not history:
            return []

        grouped: dict[datetime, list[dict]] = defaultdict(list)
        for row in history:
            observed_day = row["observed_at"].replace(hour=0, minute=0, second=0, microsecond=0)
            grouped[observed_day].append(row)

        points = []
        for ts in sorted(grouped):
            rows = grouped[ts]
            avg_package = sum(float(row["package_price_vnd"] or 0) for row in rows) / len(rows)
            avg_normalized = sum(float(row["normalized_price_vnd"]) for row in rows) / len(rows)
            package_size = float(rows[0].get("package_size_kg") or 1)
            points.append((ts, avg_package, avg_normalized, package_size))
        if not points:
            return []

        last_ts, last_package, last_normalized, package_size = points[-1]
        lookback = points[max(0, len(points) - 4)]
        elapsed_days = max(1, (last_ts - lookback[0]).days)
        raw_daily_slope = (last_package - lookback[1]) / elapsed_days
        slope_cap = max(last_package * 0.0012, 300)
        daily_slope = max(-slope_cap, min(slope_cap, raw_daily_slope * 0.45))

        returns: list[float] = []
        for prev, current in zip(points, points[1:], strict=False):
            if prev[1] > 0:
                returns.append((current[1] - prev[1]) / prev[1])
        volatility = pstdev(returns) if len(returns) > 1 else 0.025
        volatility = max(0.018, min(0.08, volatility))

        output = []
        for day in range(1, min(max(days, 1), 60) + 1):
            ts = last_ts + timedelta(days=day)
            drifted = last_package + daily_slope * day
            forecast_package = max(last_package * 0.85, min(last_package * 1.15, drifted))
            band = max(last_package * 0.025, last_package * volatility * math.sqrt(day / 30))
            low = max(0, forecast_package - band)
            high = forecast_package + band
            output.append(
                {
                    "timestamp": ts,
                    "forecast_price_vnd": round(forecast_package, 2),
                    "confidence_low_vnd": round(low, 2),
                    "confidence_high_vnd": round(high, 2),
                    "normalized_price_vnd": round(forecast_package / package_size, 2),
                    "normalized_low_vnd": round(low / package_size, 2),
                    "normalized_high_vnd": round(high / package_size, 2),
                    "model_kind": "input-price-baseline-v1",
                }
            )
        return output

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
            "package_label": row.product.package_label,
            "confidence_score": float(row.confidence_score),
            "data_kind": row.data_kind,
        }
