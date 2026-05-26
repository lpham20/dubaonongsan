from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.db import get_db
from app.models import AppUser
from app.services.auth import current_user
from app.services.fertilizer_engine import ENGINE_VERSION, KNOWLEDGE_BASE_VERSION, recommend, sample_request, supported_crops
from app.services.recommendation_sessions import log_recommendation_session, save_yield_feedback


settings = get_settings()
router = APIRouter(prefix=settings.api_prefix, tags=["fertilizer"])


Crop = Literal["robusta_coffee", "black_pepper", "durian"]
GrowthStage = Literal["mature_kinh_doanh", "establishment_y1", "establishment_y2", "establishment_y3", "establishment_y4", "establishment_y5", "fruit_set", "fruit_fill"]
SoilTexture = Literal["basaltic_red", "grey_granite", "gneiss", "acrisol", "alluvial"]
PMethod = Literal["bray_ii", "mehlich_3"]
KMethod = Literal["nh4oac"]
KSource = Literal["kcl", "k2so4", "kno3"]


DURIAN_VARIETIES = {"Ri6", "Monthong", "TR4", "TR9", "Musang King", "Khác"}


class SoilSample(BaseModel):
    texture: SoilTexture
    ph_kcl: float = Field(..., ge=3.0, le=9.0)
    ph_h2o: float | None = Field(default=None, ge=3.0, le=10.0)
    organic_carbon_pct: float | None = Field(default=None, ge=0.0, le=15.0)
    total_n_pct: float | None = Field(default=None, ge=0.0, le=1.0)
    available_p_method: PMethod = "bray_ii"
    available_p_mg_per_100g: float | None = Field(default=None, ge=0.0, le=500.0)
    available_p_mg_per_kg: float | None = Field(default=None, ge=0.0, le=1000.0)
    exchangeable_k_method: KMethod = "nh4oac"
    exchangeable_k2o_mg_per_100g: float | None = Field(default=None, ge=0.0, le=200.0)
    exchangeable_ca_cmolc_per_kg: float | None = Field(default=None, ge=0.0, le=50.0)
    exchangeable_mg_cmolc_per_kg: float | None = Field(default=None, ge=0.0, le=20.0)
    cec_cmolc_per_kg: float | None = Field(default=None, ge=0.0, le=80.0)
    sample_depth_cm: int | None = Field(default=None, ge=0, le=100)
    sample_date: date | None = None

    @model_validator(mode="after")
    def validate_ph_pair(self) -> "SoilSample":
        if self.ph_h2o is not None and self.ph_h2o < self.ph_kcl:
            raise ValueError("pH H2O không được thấp hơn pH KCl. Vui lòng kiểm tra lại phiếu phân tích đất.")
        return self


class LocationContext(BaseModel):
    province: str | None = None
    district: str | None = None
    commune: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    elevation_m: float | None = None


class ClimateContext(BaseModel):
    annual_rainfall_mm: float | None = Field(default=None, ge=0, le=5000)
    irrigation_available: bool | None = None


class FieldContext(BaseModel):
    slope_pct: float | None = Field(default=None, ge=0, le=80)
    years_under_current_crop: int | None = Field(default=None, ge=0, le=80)


class Preferences(BaseModel):
    language: Literal["vi", "en"] = "vi"
    include_product_mix: bool = True
    preferred_brand: str | None = None
    preferred_k_source: KSource | None = None
    organic_available_t_ha: float | None = Field(default=None, ge=0, le=100)


class RecommendRequest(BaseModel):
    crop: Crop
    variety: str | None = Field(default=None, max_length=80)
    growth_stage: GrowthStage = "mature_kinh_doanh"
    yield_target_t_ha: float | None = Field(default=None, ge=0.5, le=25.0)
    tree_density_per_ha: int | None = Field(default=None, ge=50, le=3000)
    soil: SoilSample
    location: LocationContext = Field(default_factory=LocationContext)
    climate: ClimateContext | None = None
    field: FieldContext | None = None
    preferences: Preferences = Field(default_factory=Preferences)

    @model_validator(mode="after")
    def validate_variety(self) -> "RecommendRequest":
        if self.variety is not None:
            self.variety = self.variety.strip() or None
        if self.crop == "durian" and self.variety is not None and self.variety not in DURIAN_VARIETIES:
            raise ValueError("Giống sầu riêng chỉ nhận Ri6, Monthong, TR4, TR9, Musang King hoặc Khác.")
        return self


class YieldFeedbackRequest(BaseModel):
    actual_yield_t_ha: float = Field(..., ge=0.1, le=80)
    harvest_date: date | None = None
    fertilizer_followed_pct: float | None = Field(default=None, ge=0, le=100)
    rating: int | None = Field(default=None, ge=1, le=5)
    note: str | None = Field(default=None, max_length=2000)
    contact_phone: str | None = Field(default=None, max_length=20, pattern=r"^(?:\+?84|0)[0-9]{8,11}$")


class YieldFeedbackResponse(BaseModel):
    session_id: str
    session_code: str
    feedback_id: int
    message: str


@router.post("/fertilizer/recommend")
@router.post("/recommend", include_in_schema=False)
@limiter.limit("12/minute")
def fertilizer_recommendation(
    payload: RecommendRequest,
    request: Request,
    user: AppUser = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    try:
        payload_data = payload.model_dump(mode="json")
        result = recommend(payload_data)
        session = log_recommendation_session(db, user=user, request=request, payload=payload_data, result=result)
        result["session_id"] = session.session_id
        result["session_code"] = session.session_id[:8].upper()
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=422, detail="Dữ liệu đầu vào chưa phù hợp. Vui lòng kiểm tra lại biểu mẫu.") from exc


@router.post("/sessions/{session_id}/feedback", response_model=YieldFeedbackResponse, status_code=201)
@router.post("/fertilizer/sessions/{session_id}/feedback", response_model=YieldFeedbackResponse, status_code=201, include_in_schema=False)
def submit_yield_feedback(
    session_id: str,
    payload: YieldFeedbackRequest,
    user: AppUser = Depends(current_user),
    db: Session = Depends(get_db),
) -> YieldFeedbackResponse:
    feedback = save_yield_feedback(
        db,
        session_code=session_id,
        user=user,
        actual_yield_t_ha=payload.actual_yield_t_ha,
        harvest_date=payload.harvest_date,
        fertilizer_followed_pct=payload.fertilizer_followed_pct,
        rating=payload.rating,
        note=payload.note.strip() if payload.note else None,
        contact_phone=payload.contact_phone.strip() if payload.contact_phone else None,
    )
    return YieldFeedbackResponse(
        session_id=feedback.session_id,
        session_code=feedback.session_id[:8].upper(),
        feedback_id=feedback.feedback_id,
        message="Đã nhận báo cáo năng suất. Dữ liệu này sẽ được dùng để hiệu chỉnh Tier 2.",
    )


@router.get("/fertilizer/crops")
@router.get("/crops", include_in_schema=False)
def fertilizer_crops() -> list[dict]:
    return supported_crops()


@router.get("/fertilizer/soil-test-methods")
@router.get("/soil_test_methods", include_in_schema=False)
def fertilizer_soil_test_methods() -> dict:
    return {
        "p_methods": [
            {"value": "bray_ii", "label_vi": "Bray II", "note_vi": "Phù hợp đất chua Tây Nguyên."},
            {"value": "mehlich_3", "label_vi": "Mehlich-3", "note_vi": "Được quy đổi bảo thủ sang Bray II tương đương."},
        ],
        "k_methods": [{"value": "nh4oac", "label_vi": "NH4OAc", "note_vi": "Phương pháp trao đổi K phổ biến."}],
    }


@router.get("/fertilizer/sample-request")
def fertilizer_sample_request() -> dict:
    return sample_request()


@router.get("/fertilizer/version")
@router.get("/version", include_in_schema=False)
def fertilizer_version() -> dict:
    return {"engine": ENGINE_VERSION, "knowledge_base": KNOWLEDGE_BASE_VERSION}


@router.get("/fertilizer/healthz")
def fertilizer_healthz() -> dict:
    return {"status": "ok"}
