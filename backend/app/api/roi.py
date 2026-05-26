from __future__ import annotations

from datetime import UTC, datetime
from statistics import median
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.db import get_db
from app.ml_engine.lstm_forecaster import ForecastConfig, LSTMForecaster
from app.models import AppUser, DailyMarketPrice, RoiScenario
from app.services.auth import current_user
from app.services.data_loader import DataLoader
from app.services.input_prices import InputPriceService


settings = get_settings()
router = APIRouter(prefix=settings.api_prefix, tags=["roi"])


class FertilizerLine(BaseModel):
    product_slug: str | None = Field(default=None, max_length=80)
    name: str | None = Field(default=None, max_length=100)
    kg_per_ha: float = Field(..., gt=0, le=5000)
    price_vnd_per_kg: float | None = Field(default=None, gt=0, le=10_000_000)

    @model_validator(mode="after")
    def has_name_or_product(self) -> "FertilizerLine":
        if not self.product_slug and not self.name:
            raise ValueError("Mỗi dòng phân bón cần có tên phân hoặc product_slug.")
        return self


class RoiCalculateRequest(BaseModel):
    crop: Literal["sau_rieng", "ca_phe", "ho_tieu", "lua"]
    crop_area_ha: float = Field(..., ge=0.01, le=1000)
    expected_yield_t_ha: float = Field(..., ge=0.1, le=80)
    expected_sell_price_vnd_per_kg: float = Field(..., ge=100, le=500_000)
    region_id: int | None = Field(default=None, ge=1)
    variety_id: int | None = Field(default=None, ge=1)
    fertilizer_total_cost_vnd_per_ha: float | None = Field(default=None, ge=0, le=5_000_000_000)
    fertilizer_lines: list[FertilizerLine] = Field(default_factory=list, max_length=20)
    other_input_cost_vnd_per_ha: float = Field(default=0, ge=0)
    labor_cost_vnd_per_ha: float = Field(default=0, ge=0)
    save: bool = False


class RoiScenarioOut(BaseModel):
    scenario: Literal["pessimistic", "expected", "optimistic"]
    label_vi: str
    sell_price_vnd_per_kg: float
    yield_t_ha: float
    revenue_vnd: float
    total_cost_vnd: float
    net_profit_vnd: float
    roi_pct: float
    rationale_vi: str


class RoiCalculateResponse(BaseModel):
    scenario_id: int | None
    fertilizer_input_mode: Literal["simple", "detail", "db_reference"]
    fertilizer_cost_vnd_per_ha: float
    total_revenue_vnd: float
    total_cost_vnd: float
    net_profit_vnd: float
    roi_pct: float
    scenarios: list[RoiScenarioOut]
    confidence_score: float
    forecast_model_kind: str
    breakdown: list[dict]
    sensitivity: dict
    notes_vi: list[str]
    recommendations_vi: list[str]


@router.post("/roi/calculate", response_model=RoiCalculateResponse)
@limiter.limit("20/minute")
def calculate_roi(
    request: Request,
    payload: RoiCalculateRequest,
    user: AppUser = Depends(current_user),
    db: Session = Depends(get_db),
) -> RoiCalculateResponse:
    return _calculate_roi_v2(payload=payload, user=user, db=db)


@router.post("/advisory/roi/calculate", response_model=RoiCalculateResponse)
@limiter.limit("20/minute")
def calculate_advisory_roi(
    request: Request,
    payload: RoiCalculateRequest,
    user: AppUser = Depends(current_user),
    db: Session = Depends(get_db),
) -> RoiCalculateResponse:
    return _calculate_roi_v2(payload=payload, user=user, db=db)


def _calculate_roi_v2(
    *,
    payload: RoiCalculateRequest,
    user: AppUser,
    db: Session,
) -> RoiCalculateResponse:
    fertilizer_cost_per_ha, breakdown, input_mode = _fertilizer_cost(payload, db)
    total_cost_per_ha = fertilizer_cost_per_ha + payload.other_input_cost_vnd_per_ha + payload.labor_cost_vnd_per_ha
    if total_cost_per_ha <= 0:
        raise HTTPException(status_code=400, detail="Tổng chi phí/ha phải lớn hơn 0 để tính lợi nhuận.")

    forecast = _forecast_context(payload, db)
    scenarios = _build_scenarios(payload, total_cost_per_ha, forecast)
    expected = next(item for item in scenarios if item["scenario"] == "expected")
    total_revenue = expected["revenue_vnd"]
    total_cost = expected["total_cost_vnd"]
    net_profit = expected["net_profit_vnd"]
    roi_pct = expected["roi_pct"]
    sensitivity = _sensitivity_table(
        payload.expected_yield_t_ha * 1000 * forecast["expected_price"],
        total_cost_per_ha,
        fertilizer_cost_per_ha,
        payload.crop_area_ha,
    )
    confidence = _confidence_score(forecast, input_mode, payload, total_cost_per_ha)
    notes = _roi_notes(roi_pct, fertilizer_cost_per_ha, total_cost_per_ha)
    recommendations = _roi_recommendations(
        roi_pct=roi_pct,
        fertilizer_cost_per_ha=fertilizer_cost_per_ha,
        total_cost_per_ha=total_cost_per_ha,
        forecast=forecast,
        input_mode=input_mode,
    )

    scenario_id = None
    if payload.save:
        scenario = RoiScenario(
            user_id=user.user_id,
            crop=payload.crop,
            crop_area_ha=payload.crop_area_ha,
            expected_yield_t_ha=payload.expected_yield_t_ha,
            expected_sell_price_vnd_per_kg=payload.expected_sell_price_vnd_per_kg,
            fertilizer_cost_vnd_per_ha=fertilizer_cost_per_ha,
            fertilizer_breakdown_json={"mode": input_mode, "lines": breakdown},
            other_input_cost_vnd_per_ha=payload.other_input_cost_vnd_per_ha,
            labor_cost_vnd_per_ha=payload.labor_cost_vnd_per_ha,
            total_revenue_vnd=total_revenue,
            total_cost_vnd=total_cost,
            net_profit_vnd=net_profit,
            roi_pct=roi_pct,
            scenarios_json=scenarios,
            forecast_model_kind=forecast["model_kind"],
            confidence_score=confidence,
            notes="\n".join(recommendations),
            created_at=datetime.now(UTC),
        )
        db.add(scenario)
        db.commit()
        db.refresh(scenario)
        scenario_id = scenario.scenario_id

    return RoiCalculateResponse(
        scenario_id=scenario_id,
        fertilizer_input_mode=input_mode,
        fertilizer_cost_vnd_per_ha=round(fertilizer_cost_per_ha, 2),
        total_revenue_vnd=round(total_revenue, 2),
        total_cost_vnd=round(total_cost, 2),
        net_profit_vnd=round(net_profit, 2),
        roi_pct=round(roi_pct, 2),
        scenarios=[RoiScenarioOut(**item) for item in scenarios],
        confidence_score=confidence,
        forecast_model_kind=forecast["model_kind"],
        breakdown=breakdown,
        sensitivity=sensitivity,
        notes_vi=notes,
        recommendations_vi=recommendations,
    )


def _fertilizer_cost(payload: RoiCalculateRequest, db: Session) -> tuple[float, list[dict], str]:
    if payload.fertilizer_lines:
        seen_slugs: set[str] = set()
        for line in payload.fertilizer_lines:
            if not line.product_slug:
                continue
            if line.product_slug in seen_slugs:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "code": "DUPLICATE_FERTILIZER",
                        "message": f"Mỗi loại phân chỉ nên nhập một dòng. {line.product_slug} đang bị trùng.",
                    },
                )
            seen_slugs.add(line.product_slug)
        total = 0.0
        breakdown = []
        service = InputPriceService(db)
        for line in payload.fertilizer_lines:
            line_name = line.name or line.product_slug or "Phân bón"
            price = line.price_vnd_per_kg
            source = "user_input"
            observed_at = None
            product_name = line_name
            if price is None:
                if not line.product_slug:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Vui lòng nhập giá VND/kg cho {line_name}, hoặc chọn product_slug để dùng giá tham chiếu.",
                    )
                latest = service.latest_prices(product_slug=line.product_slug, limit=20)
                prices = sorted(float(row["normalized_price_vnd"]) for row in latest if row.get("normalized_price_vnd"))
                if not prices:
                    raise HTTPException(
                        status_code=503,
                        detail=f"Chưa có giá tham chiếu cho {line.product_slug}. Vui lòng nhập giá thực tế từ đại lý.",
                    )
                price = prices[len(prices) // 2]
                first = latest[0]
                product_name = str(first["product_name"])
                source = "db_median"
                observed = first["observed_at"]
                observed_at = observed.isoformat() if hasattr(observed, "isoformat") else observed
            cost = price * line.kg_per_ha
            total += cost
            breakdown.append(
                {
                    "product_slug": line.product_slug,
                    "product_name": product_name,
                    "name": line_name,
                    "kg_per_ha": line.kg_per_ha,
                    "price_vnd_per_kg": round(price, 2),
                    "cost_vnd_per_ha": round(cost, 2),
                    "price_source": source,
                    "source_name": "Giá bạn nhập" if source == "user_input" else "Median DB",
                    "observed_at": observed_at,
                }
            )
        return total, breakdown, "detail" if any(row["price_source"] == "user_input" for row in breakdown) else "db_reference"

    if payload.fertilizer_total_cost_vnd_per_ha is not None:
        return (
            payload.fertilizer_total_cost_vnd_per_ha,
            [
                {
                    "product_slug": None,
                    "product_name": "Tổng tiền phân bón/ha",
                    "name": "Tổng tiền phân bón/ha",
                    "kg_per_ha": None,
                    "price_vnd_per_kg": None,
                    "cost_vnd_per_ha": round(payload.fertilizer_total_cost_vnd_per_ha, 2),
                    "price_source": "user_input",
                    "source_name": "Giá bạn nhập",
                    "observed_at": None,
                }
            ],
            "simple",
        )

    raise HTTPException(status_code=400, detail="Vui lòng nhập tổng tiền phân bón/ha hoặc ít nhất một dòng phân bón chi tiết.")


def _forecast_context(payload: RoiCalculateRequest, db: Session) -> dict:
    region_id = payload.region_id
    variety_id = payload.variety_id
    if region_id is None or variety_id is None:
        latest = db.scalar(
            select(DailyMarketPrice)
            .where(DailyMarketPrice.crop_type == payload.crop)
            .order_by(desc(DailyMarketPrice.record_timestamp))
            .limit(1)
        )
        region_id = region_id or (latest.region_id if latest else 1)
        variety_id = variety_id or (latest.variety_id if latest else 1)

    model_kind = "user-expected-price"
    prices: list[float] = []
    try:
        config = ForecastConfig()
        loader = DataLoader(db)
        window = loader.latest_feature_window(crop_type=payload.crop, region_id=region_id, variety_id=variety_id)
        if window:
            forecaster = LSTMForecaster(config, crop_type=payload.crop, region_id=region_id, variety_id=variety_id)
            prices = [float(value) for value in forecaster.predict_30_days(window) if value and value > 0]
            model_kind = forecaster.last_model_kind
    except Exception:
        prices = []

    if prices:
        ordered = sorted(prices)
        low_forecast = ordered[max(0, int(len(ordered) * 0.2) - 1)]
        expected_forecast = median(prices)
        high_forecast = ordered[min(len(ordered) - 1, int(len(ordered) * 0.8))]
        expected_price = 0.55 * payload.expected_sell_price_vnd_per_kg + 0.45 * expected_forecast
        return {
            "model_kind": model_kind,
            "points": len(prices),
            "low_price": min(payload.expected_sell_price_vnd_per_kg * 0.9, low_forecast),
            "expected_price": expected_price,
            "high_price": max(payload.expected_sell_price_vnd_per_kg * 1.08, high_forecast),
            "forecast_median": expected_forecast,
        }

    return {
        "model_kind": model_kind,
        "points": 0,
        "low_price": payload.expected_sell_price_vnd_per_kg * 0.9,
        "expected_price": payload.expected_sell_price_vnd_per_kg,
        "high_price": payload.expected_sell_price_vnd_per_kg * 1.1,
        "forecast_median": payload.expected_sell_price_vnd_per_kg,
    }


def _build_scenarios(payload: RoiCalculateRequest, cost_per_ha: float, forecast: dict) -> list[dict]:
    specs = [
        ("expected", "Cơ sở", forecast["expected_price"], 1.0, "Kết hợp giá bạn nhập với trung vị dự báo nông sản."),
    ]
    scenarios = []
    for key, label, price, yield_multiplier, rationale in specs:
        yield_t_ha = payload.expected_yield_t_ha * yield_multiplier
        revenue = yield_t_ha * 1000 * price * payload.crop_area_ha
        total_cost = cost_per_ha * payload.crop_area_ha
        profit = revenue - total_cost
        roi = profit / total_cost * 100 if total_cost > 0 else 0.0
        scenarios.append(
            {
                "scenario": key,
                "label_vi": label,
                "sell_price_vnd_per_kg": round(price, 2),
                "yield_t_ha": round(yield_t_ha, 3),
                "revenue_vnd": round(revenue, 2),
                "total_cost_vnd": round(total_cost, 2),
                "net_profit_vnd": round(profit, 2),
                "roi_pct": round(roi, 2),
                "rationale_vi": rationale,
            }
        )
    return scenarios


def _sensitivity_table(revenue_per_ha: float, cost_per_ha: float, fertilizer_cost_per_ha: float, area_ha: float) -> dict:
    scenarios = []
    fixed_cost_per_ha = max(0.0, cost_per_ha - fertilizer_cost_per_ha)
    for sell_price_delta_pct in (-10, 0, 10):
        for fertilizer_price_delta_pct in (-15, 0, 15):
            adjusted_revenue = revenue_per_ha * (1 + sell_price_delta_pct / 100)
            adjusted_cost = fixed_cost_per_ha + fertilizer_cost_per_ha * (1 + fertilizer_price_delta_pct / 100)
            adjusted_profit = adjusted_revenue - adjusted_cost
            roi = adjusted_profit / adjusted_cost * 100 if adjusted_cost > 0 else 0
            scenarios.append(
                {
                    "sell_price_delta_pct": sell_price_delta_pct,
                    "fertilizer_price_delta_pct": fertilizer_price_delta_pct,
                    "roi_pct": round(roi, 1),
                    "net_profit_vnd": round(adjusted_profit * area_ha, 2),
                }
            )
    return {"matrix": scenarios}


def _confidence_score(forecast: dict, input_mode: str, payload: RoiCalculateRequest, total_cost_per_ha: float) -> float:
    score = 0.45
    if forecast["points"] >= 20:
        score += 0.2
    elif forecast["points"] >= 7:
        score += 0.1
    if input_mode in {"simple", "detail"}:
        score += 0.15
    if payload.region_id:
        score += 0.05
    if total_cost_per_ha > 0 and payload.expected_yield_t_ha > 0:
        score += 0.05
    return round(max(0.0, min(score, 0.9)), 3)


def _roi_notes(roi_pct: float, fertilizer_cost_per_ha: float, total_cost_per_ha: float) -> list[str]:
    notes: list[str] = []
    if roi_pct < 0:
        notes.append("Lợi nhuận dự kiến âm - cần giảm chi phí, tăng chất lượng bán ra hoặc hoãn quyết định đầu tư lớn.")
    elif roi_pct < 15:
        notes.append("Tỷ suất lợi nhuận dưới 15% - nên rà lại chi phí phân bón, nhân công hoặc chờ giá bán tốt hơn.")
    if total_cost_per_ha > 0 and fertilizer_cost_per_ha / total_cost_per_ha > 0.5:
        notes.append("Phân bón chiếm trên 50% tổng chi phí - nên so lại liều lượng và thời điểm mua.")
    if not notes:
        notes.append("Kịch bản kỳ vọng có lợi nhuận dương; vẫn nên kiểm tra thêm rủi ro giá bán, thời tiết và dòng tiền.")
    return notes


def _roi_recommendations(
    *,
    roi_pct: float,
    fertilizer_cost_per_ha: float,
    total_cost_per_ha: float,
    forecast: dict,
    input_mode: str,
) -> list[str]:
    recommendations: list[str] = []
    fertilizer_share = fertilizer_cost_per_ha / total_cost_per_ha if total_cost_per_ha > 0 else 0
    if roi_pct < 0:
        recommendations.append("Không nên chốt phương án này ngay: lợi nhuận âm trong kịch bản kỳ vọng.")
    elif roi_pct < 15:
        recommendations.append("Chỉ nên triển khai nếu có hợp đồng/đầu ra chắc hơn, vì biên an toàn lợi nhuận còn mỏng.")
    else:
        recommendations.append("Có thể xem đây là phương án khả thi, nhưng nên theo dõi lại giá bán trước khi xuống tiền lớn.")
    if fertilizer_share > 0.5:
        recommendations.append("Chi phí phân bón đang chiếm hơn 50% tổng chi phí: mở trang giá phân bón thế giới để xem xu hướng Urê/DAP/Kali trước khi mua.")
    if input_mode == "db_reference":
        recommendations.append("Kết quả đang dùng giá tham chiếu DB; nếu anh có báo giá đại lý mới nhất, nhập tay sẽ sát thực tế hơn.")
    if forecast["points"] == 0:
        recommendations.append("Chưa lấy được forecast LSTM cho tổ hợp vùng/giống này; hệ thống đang dùng giá bán kỳ vọng anh nhập làm neo.")
    elif forecast["forecast_median"] > forecast["expected_price"] * 1.05:
        recommendations.append("Forecast nông sản đang nghiêng lên; có thể cân nhắc giữ hàng nếu chi phí lưu kho thấp.")
    return recommendations[:5]
