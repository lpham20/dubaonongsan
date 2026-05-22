from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db import get_db
from app.models import AppUser, RoiScenario
from app.services.auth import current_user
from app.services.input_prices import InputPriceService


settings = get_settings()
router = APIRouter(prefix=settings.api_prefix, tags=["roi"])


class FertilizerLine(BaseModel):
    product_slug: str = Field(..., min_length=1, max_length=80)
    kg_per_ha: float = Field(..., ge=0, le=5000)


class RoiCalculateRequest(BaseModel):
    crop: Literal["sau_rieng", "ca_phe", "ho_tieu", "lua"]
    crop_area_ha: float = Field(..., ge=0.01, le=1000)
    expected_yield_t_ha: float = Field(..., ge=0.1, le=80)
    expected_sell_price_vnd_per_kg: float = Field(..., ge=100, le=500_000)
    fertilizer_lines: list[FertilizerLine] = Field(default_factory=list, max_length=20)
    other_input_cost_vnd_per_ha: float = Field(default=0, ge=0)
    labor_cost_vnd_per_ha: float = Field(default=0, ge=0)
    save: bool = False


class RoiCalculateResponse(BaseModel):
    scenario_id: int | None
    fertilizer_cost_vnd_per_ha: float
    total_revenue_vnd: float
    total_cost_vnd: float
    net_profit_vnd: float
    roi_pct: float
    breakdown: list[dict]
    sensitivity: dict
    notes_vi: list[str]


@router.post("/roi/calculate", response_model=RoiCalculateResponse)
def calculate_roi(
    payload: RoiCalculateRequest,
    user: AppUser = Depends(current_user),
    db: Session = Depends(get_db),
) -> RoiCalculateResponse:
    service = InputPriceService(db)
    fertilizer_cost_per_ha = 0.0
    breakdown: list[dict] = []

    for line in payload.fertilizer_lines:
        if line.kg_per_ha <= 0:
            continue
        latest = service.latest_prices(product_slug=line.product_slug, limit=9)
        if not latest:
            raise HTTPException(status_code=404, detail=f"Không có giá cho {line.product_slug}")
        prices = sorted(float(row["normalized_price_vnd"]) for row in latest if row.get("normalized_price_vnd"))
        if not prices:
            raise HTTPException(status_code=404, detail=f"Không có giá quy đổi cho {line.product_slug}")
        median_price = prices[len(prices) // 2]
        cost = median_price * line.kg_per_ha
        fertilizer_cost_per_ha += cost
        first = latest[0]
        observed_at = first["observed_at"]
        if hasattr(observed_at, "isoformat"):
            observed_at = observed_at.isoformat()
        breakdown.append(
            {
                "product_slug": line.product_slug,
                "product_name": first["product_name"],
                "kg_per_ha": line.kg_per_ha,
                "price_vnd_per_kg": round(median_price, 2),
                "cost_vnd_per_ha": round(cost, 2),
                "source_name": first["source_name"],
                "observed_at": observed_at,
            }
        )

    total_cost_per_ha = fertilizer_cost_per_ha + payload.other_input_cost_vnd_per_ha + payload.labor_cost_vnd_per_ha
    revenue_per_ha = payload.expected_yield_t_ha * 1000 * payload.expected_sell_price_vnd_per_kg
    profit_per_ha = revenue_per_ha - total_cost_per_ha
    roi_pct = (profit_per_ha / total_cost_per_ha * 100) if total_cost_per_ha > 0 else 0.0

    total_revenue = revenue_per_ha * payload.crop_area_ha
    total_cost = total_cost_per_ha * payload.crop_area_ha
    net_profit = profit_per_ha * payload.crop_area_ha
    sensitivity = _sensitivity_table(revenue_per_ha, total_cost_per_ha, fertilizer_cost_per_ha, payload.crop_area_ha)
    notes = _roi_notes(roi_pct, fertilizer_cost_per_ha, total_cost_per_ha)

    scenario_id = None
    if payload.save:
        scenario = RoiScenario(
            user_id=user.user_id,
            crop=payload.crop,
            crop_area_ha=payload.crop_area_ha,
            expected_yield_t_ha=payload.expected_yield_t_ha,
            expected_sell_price_vnd_per_kg=payload.expected_sell_price_vnd_per_kg,
            fertilizer_cost_vnd_per_ha=fertilizer_cost_per_ha,
            fertilizer_breakdown_json={"lines": breakdown},
            other_input_cost_vnd_per_ha=payload.other_input_cost_vnd_per_ha,
            labor_cost_vnd_per_ha=payload.labor_cost_vnd_per_ha,
            total_revenue_vnd=total_revenue,
            total_cost_vnd=total_cost,
            net_profit_vnd=net_profit,
            roi_pct=roi_pct,
            notes="\n".join(notes),
            created_at=datetime.now(UTC),
        )
        db.add(scenario)
        db.commit()
        db.refresh(scenario)
        scenario_id = scenario.scenario_id

    return RoiCalculateResponse(
        scenario_id=scenario_id,
        fertilizer_cost_vnd_per_ha=round(fertilizer_cost_per_ha, 2),
        total_revenue_vnd=round(total_revenue, 2),
        total_cost_vnd=round(total_cost, 2),
        net_profit_vnd=round(net_profit, 2),
        roi_pct=round(roi_pct, 2),
        breakdown=breakdown,
        sensitivity=sensitivity,
        notes_vi=notes,
    )


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


def _roi_notes(roi_pct: float, fertilizer_cost_per_ha: float, total_cost_per_ha: float) -> list[str]:
    notes: list[str] = []
    if roi_pct < 15:
        notes.append("ROI dưới 15% - nên rà lại chi phí phân bón, nhân công hoặc chờ giá bán tốt hơn.")
    if total_cost_per_ha > 0 and fertilizer_cost_per_ha / total_cost_per_ha > 0.5:
        notes.append("Phân bón chiếm trên 50% tổng chi phí - nên so lại liều lượng và thời điểm mua.")
    if not notes:
        notes.append("Kịch bản hiện tại có ROI dương; vẫn nên kiểm tra thêm rủi ro giá bán và thời tiết.")
    return notes
