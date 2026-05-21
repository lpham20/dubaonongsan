from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator

from app.core.config import get_settings
from app.models import AppUser
from app.services.auth import current_user
from app.services.fertilizer_engine import ENGINE_VERSION, KNOWLEDGE_BASE_VERSION, recommend, sample_request, supported_crops


settings = get_settings()
router = APIRouter(prefix=settings.api_prefix, tags=["fertilizer"])


Crop = Literal["robusta_coffee", "black_pepper", "durian"]
GrowthStage = Literal["mature_kinh_doanh", "establishment_y1", "establishment_y2", "establishment_y3", "establishment_y4", "establishment_y5", "fruit_fill"]
SoilTexture = Literal["basaltic_red", "grey_granite", "gneiss", "acrisol", "alluvial"]
PMethod = Literal["bray_ii", "mehlich_3"]
KMethod = Literal["nh4oac"]


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
    organic_available_t_ha: float | None = Field(default=None, ge=0, le=100)


class RecommendRequest(BaseModel):
    crop: Crop
    growth_stage: GrowthStage = "mature_kinh_doanh"
    yield_target_t_ha: float | None = Field(default=None, ge=0.5, le=25.0)
    tree_density_per_ha: int | None = Field(default=None, ge=50, le=3000)
    soil: SoilSample
    location: LocationContext = Field(default_factory=LocationContext)
    climate: ClimateContext | None = None
    field: FieldContext | None = None
    preferences: Preferences = Field(default_factory=Preferences)


@router.post("/fertilizer/recommend")
@router.post("/recommend", include_in_schema=False)
def fertilizer_recommendation(payload: RecommendRequest, _: AppUser = Depends(current_user)) -> dict:
    try:
        return recommend(payload.model_dump(mode="json"))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=422, detail=f"Dữ liệu đầu vào chưa phù hợp: {exc}") from exc


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
@router.get("/healthz", include_in_schema=False)
def fertilizer_healthz() -> dict:
    return {"status": "ok"}
