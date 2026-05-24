from __future__ import annotations

from datetime import UTC, date, datetime
from statistics import median
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.admin_units import is_crop_province, is_production_region, normalize_province_name
from app.core.config import get_settings
from app.db import get_db
from app.ml_engine.lstm_forecaster import ForecastConfig, LSTMForecaster
from app.models import AppUser, DailyMarketPrice, ProductionRegion
from app.services.auth import current_user
from app.services.data_loader import DataLoader


settings = get_settings()
router = APIRouter(prefix=f"{settings.api_prefix}/advisory", tags=["advisory"])

Crop = Literal["sau_rieng", "ca_phe", "ho_tieu", "lua"]

CROP_LABELS = {
    "sau_rieng": "Sầu riêng",
    "ca_phe": "Cà phê",
    "ho_tieu": "Hồ tiêu",
    "lua": "Lúa",
}

DEFAULT_YIELDS_T_HA = {
    "sau_rieng": 16.0,
    "ca_phe": 3.0,
    "ho_tieu": 2.4,
    "lua": 6.2,
}

DEFAULT_COSTS_VND_HA = {
    "sau_rieng": 95_000_000,
    "ca_phe": 58_000_000,
    "ho_tieu": 70_000_000,
    "lua": 28_000_000,
}

REGION_SUITABILITY = {
    "Đắk Lắk": {"sau_rieng": 0.86, "ca_phe": 1.0, "ho_tieu": 0.78, "lua": 0.45},
    "Lâm Đồng": {"sau_rieng": 0.72, "ca_phe": 0.92, "ho_tieu": 0.55, "lua": 0.35},
    "Gia Lai": {"sau_rieng": 0.76, "ca_phe": 0.9, "ho_tieu": 0.82, "lua": 0.42},
    "An Giang": {"sau_rieng": 0.42, "ca_phe": 0.05, "ho_tieu": 0.1, "lua": 1.0},
    "Đồng Tháp": {"sau_rieng": 0.5, "ca_phe": 0.05, "ho_tieu": 0.1, "lua": 0.98},
}


class SellingTimeRequest(BaseModel):
    crop: Crop
    region_id: int | None = Field(default=None, ge=1)
    variety_id: int | None = Field(default=None, ge=1)
    quantity_kg: float = Field(default=1000, gt=0, le=5_000_000)
    storage_cost_vnd_per_kg_per_day: float = Field(default=0, ge=0, le=100_000)
    earliest_sale_date: date | None = None


class CrossCommodityRequest(BaseModel):
    region_id: int
    current_crop: Crop | None = None
    area_hectares: float = Field(default=1, gt=0, le=10_000)


@router.post("/selling-time")
def selling_time(
    payload: SellingTimeRequest,
    _: AppUser = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    region_id, variety_id = _resolve_series(db, payload.crop, payload.region_id, payload.variety_id)
    forecast = _crop_forecast(db, payload.crop, region_id, variety_id)
    if not forecast["points"]:
        raise HTTPException(status_code=404, detail="Chưa đủ dữ liệu dự báo cho cây/vùng này.")

    today = datetime.now(UTC).date()
    earliest = payload.earliest_sale_date or today
    candidates = []
    for index, point in enumerate(forecast["points"], start=1):
        sale_date = point["date"]
        if sale_date < earliest:
            continue
        storage_cost = max(0, (sale_date - today).days) * payload.storage_cost_vnd_per_kg_per_day * payload.quantity_kg
        gross = point["price_vnd_per_kg"] * payload.quantity_kg
        net = gross - storage_cost
        candidates.append(
            {
                "date": sale_date.isoformat(),
                "forecast_price_vnd_per_kg": round(point["price_vnd_per_kg"], 2),
                "net_revenue_vnd": round(net, 2),
                "uplift_pct_vs_today": round(((point["price_vnd_per_kg"] / forecast["base_price"]) - 1) * 100, 2),
                "storage_cost_vnd": round(storage_cost, 2),
            }
        )
    if not candidates:
        raise HTTPException(status_code=400, detail="Không có ngày bán phù hợp sau ngày sớm nhất đã chọn.")
    ranked = sorted(candidates, key=lambda item: item["net_revenue_vnd"], reverse=True)[:5]
    best = ranked[0]
    return {
        "crop": payload.crop,
        "crop_label_vi": CROP_LABELS[payload.crop],
        "region_id": region_id,
        "variety_id": variety_id,
        "model_kind": forecast["model_kind"],
        "best_window": best,
        "top_5_windows": ranked,
        "confidence_score": _forecast_confidence(forecast["history_points"], forecast["model_kind"]),
        "rationale_vi": f"Bán vào {best['date']} đang cho doanh thu ròng tốt nhất trong 30 ngày theo dự báo hiện có.",
    }


@router.get("/arbitrage")
def arbitrage(
    crop_type: Crop | None = Query(default=None),
    min_net_spread_pct: float = Query(default=3, ge=0, le=100),
    max_distance_km: float = Query(default=700, ge=10, le=3000),
    _: AppUser = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    crops = [crop_type] if crop_type else list(CROP_LABELS)
    opportunities = []
    for crop in crops:
        latest = _latest_prices_by_region(db, crop)
        for source in latest:
            for target in latest:
                if source["region_id"] == target["region_id"]:
                    continue
                if source["price"] <= 0 or target["price"] <= source["price"]:
                    continue
                distance = _estimated_distance_km(source["province"], target["province"])
                if distance > max_distance_km:
                    continue
                transport_cost_per_kg = 550 + distance * 7.5
                gross_spread = target["price"] - source["price"]
                net_spread = gross_spread - transport_cost_per_kg
                net_pct = net_spread / source["price"] * 100
                if net_pct < min_net_spread_pct:
                    continue
                opportunities.append(
                    {
                        "crop": crop,
                        "crop_label_vi": CROP_LABELS[crop],
                        "from_region": source["display_name"],
                        "to_region": target["display_name"],
                        "from_region_name": source["region"],
                        "to_region_name": target["region"],
                        "from_province": source["province"],
                        "to_province": target["province"],
                        "source_price_vnd_per_kg": round(source["price"], 2),
                        "target_price_vnd_per_kg": round(target["price"], 2),
                        "estimated_distance_km": round(distance, 1),
                        "transport_cost_vnd_per_kg": round(transport_cost_per_kg, 2),
                        "net_spread_vnd_per_kg": round(net_spread, 2),
                        "net_spread_pct": round(net_pct, 2),
                    }
                )
    return {
        "items": sorted(opportunities, key=lambda item: item["net_spread_pct"], reverse=True)[:50],
        "assumption_vi": "Khoảng cách và vận chuyển là ước tính thận trọng khi hệ thống chưa có tuyến logistics thực tế.",
    }


@router.post("/cross-commodity")
def cross_commodity(
    payload: CrossCommodityRequest,
    _: AppUser = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    region = db.get(ProductionRegion, payload.region_id)
    if not region:
        raise HTTPException(status_code=404, detail="Không tìm thấy vùng sản xuất.")
    suitability = REGION_SUITABILITY.get(region.province or "", {})
    rows = []
    for crop in CROP_LABELS:
        latest = _latest_crop_price(db, crop, payload.region_id)
        if latest is None:
            latest = _latest_crop_price(db, crop, None)
        price = latest or _fallback_price(crop)
        yield_t_ha = DEFAULT_YIELDS_T_HA[crop]
        revenue_per_ha = yield_t_ha * 1000 * price
        cost_per_ha = DEFAULT_COSTS_VND_HA[crop]
        suitability_score = suitability.get(crop, 0.55)
        profit_per_ha = (revenue_per_ha - cost_per_ha) * suitability_score
        rows.append(
            {
                "crop": crop,
                "crop_label_vi": CROP_LABELS[crop],
                "suitability_score": round(suitability_score, 2),
                "reference_price_vnd_per_kg": round(price, 2),
                "yield_t_ha": yield_t_ha,
                "estimated_profit_vnd": round(profit_per_ha * payload.area_hectares, 2),
                "roi_score": round((profit_per_ha / cost_per_ha) * 100, 2) if cost_per_ha > 0 else 0.0,
            }
        )
    return {
        "region_id": payload.region_id,
        "region_name": region.region_name,
        "province": region.province,
        "items": sorted(rows, key=lambda item: item["estimated_profit_vnd"], reverse=True),
        "intercropping_vi": _intercropping_notes(region.province or ""),
        "disclaimer_vi": "Đây là so sánh tham khảo theo giá, năng suất và độ phù hợp ước tính; không thay thế khảo sát đất, nước và hợp đồng đầu ra.",
    }


def _resolve_series(db: Session, crop: str, region_id: int | None, variety_id: int | None) -> tuple[int, int]:
    if region_id and variety_id:
        return region_id, variety_id
    row = db.scalar(
        select(DailyMarketPrice)
        .where(DailyMarketPrice.crop_type == crop)
        .order_by(desc(DailyMarketPrice.record_timestamp))
        .limit(1)
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Chưa có dữ liệu giá cho cây trồng này.")
    return region_id or row.region_id, variety_id or row.variety_id


def _crop_forecast(db: Session, crop: str, region_id: int, variety_id: int) -> dict:
    loader = DataLoader(db)
    window = loader.latest_feature_window(crop_type=crop, region_id=region_id, variety_id=variety_id)
    if not window:
        return {"points": [], "history_points": 0, "base_price": 0.0, "model_kind": "insufficient-data"}
    config = ForecastConfig()
    forecaster = LSTMForecaster(config, crop_type=crop, region_id=region_id, variety_id=variety_id)
    prices = forecaster.predict_30_days(window)
    timestamps = loader.extend_timestamps(window[-1]["timestamp"], config.horizon_days)
    return {
        "points": [{"date": ts.date(), "price_vnd_per_kg": float(price)} for ts, price in zip(timestamps, prices, strict=False)],
        "history_points": len(window),
        "base_price": float(window[-1].get("max_price_vnd") or prices[0] or 1),
        "model_kind": forecaster.last_model_kind,
    }


def _forecast_confidence(history_points: int, model_kind: str) -> float:
    score = 0.45 + min(history_points, 60) / 60 * 0.3
    if "lstm" in model_kind.lower() or "tflite" in model_kind.lower():
        score += 0.15
    return round(min(score, 0.9), 2)


def _latest_prices_by_region(db: Session, crop: str) -> list[dict]:
    rows = db.scalars(
        select(DailyMarketPrice)
        .where(DailyMarketPrice.crop_type == crop)
        .order_by(desc(DailyMarketPrice.record_timestamp))
        .limit(1000)
    ).all()
    latest: dict[int, DailyMarketPrice] = {}
    for row in rows:
        if row.region_id not in latest and row.max_price_vnd:
            latest[row.region_id] = row
        if len(latest) >= 30:
            break
    production_prices = []
    for row in latest.values():
        if row.region is None or not is_production_region(row.region.region_name, row.region.province):
            continue
        province = normalize_province_name(row.region.province)
        if not province or not is_crop_province(crop, province):
            continue
        production_prices.append(
            {
                "region_id": row.region_id,
                "region": row.region.region_name,
                "province": province,
                "display_name": province,
                "price": float(row.max_price_vnd),
            }
        )
    return production_prices


def _estimated_distance_km(source: str | None, target: str | None) -> float:
    if not source or not target:
        return 450.0
    if source == target:
        return 0.0
    pair = tuple(sorted((source, target)))
    known = {
        tuple(sorted(("Đắk Lắk", "Lâm Đồng"))): 210,
        tuple(sorted(("Đắk Lắk", "Gia Lai"))): 190,
        tuple(sorted(("Đắk Lắk", "Tây Ninh"))): 380,
        tuple(sorted(("An Giang", "Đồng Tháp"))): 95,
        tuple(sorted(("Cần Thơ", "An Giang"))): 120,
        tuple(sorted(("Lâm Đồng", "Đồng Nai"))): 230,
    }
    return float(known.get(pair, 420.0))


def _latest_crop_price(db: Session, crop: str, region_id: int | None) -> float | None:
    query = select(DailyMarketPrice).where(DailyMarketPrice.crop_type == crop)
    if region_id:
        query = query.where(DailyMarketPrice.region_id == region_id)
    rows = db.scalars(query.order_by(desc(DailyMarketPrice.record_timestamp)).limit(30)).all()
    prices = [float(row.max_price_vnd) for row in rows if row.max_price_vnd]
    return median(prices) if prices else None


def _fallback_price(crop: str) -> float:
    return {"sau_rieng": 72_000, "ca_phe": 95_000, "ho_tieu": 135_000, "lua": 8_500}[crop]


def _intercropping_notes(province: str) -> list[str]:
    if province in {"Đắk Lắk", "Gia Lai", "Lâm Đồng"}:
        return ["Cà phê xen sầu riêng có thể hợp với vùng Tây Nguyên nếu nước tưới ổn định.", "Hồ tiêu chỉ nên giữ tỷ trọng vừa phải vì rủi ro bệnh rễ cao."]
    if province in {"An Giang", "Đồng Tháp", "Cần Thơ"}:
        return ["Lúa vẫn là crop nền phù hợp nhất; chỉ thử cây ăn trái khi có mô hình thủy lợi và đầu ra rõ."]
    return ["Nên dùng kết quả này như bước sàng lọc ban đầu trước khi khảo sát đất và thị trường địa phương."]
