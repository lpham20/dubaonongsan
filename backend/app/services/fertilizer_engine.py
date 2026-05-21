from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from math import ceil, prod
from typing import Any
from uuid import uuid4


ENGINE_VERSION = "1.1.0"
KNOWLEDGE_BASE_VERSION = "wasi-2016+ipi-2018+durian-dris-2025"

DEFAULT_SAFETY_CAPS = {"n": 500, "p2o5": 250, "k2o": 600}
DURIAN_SAFETY_CAPS = {"n": 300, "p2o5": 200, "k2o": 250}
PEPPER_P_EXCESS_THRESHOLD_MG_P_KG = 96.0
P2O5_MG_100G_TO_P_MG_KG = 4.36

CONFIDENCE_BADGES = {
    "high": {
        "badge_vi": "Đã hiệu chuẩn",
        "badge_icon": "green",
        "explain_vi": "Cà phê Robusta dùng ngưỡng và liều đã hiệu chỉnh theo tài liệu WASI/IPI cho Tây Nguyên.",
    },
    "medium": {
        "badge_vi": "Hiệu chuẩn một phần",
        "badge_icon": "yellow",
        "explain_vi": "Hồ tiêu có nền tham chiếu khu vực nhưng vẫn cần đối chiếu bệnh rễ, tuổi vườn và phân tích lá.",
    },
    "low": {
        "badge_vi": "Tham chiếu quốc tế",
        "badge_icon": "red",
        "explain_vi": "Sầu riêng đang dùng ngưỡng vay mượn từ DRIS/quốc tế; nên cập nhật bằng dữ liệu năng suất và phân tích lá tại vườn.",
    },
}

K_SOURCE_PRODUCTS = {
    "kcl": ("phu_my_kcl_60", "Kali clorua KCl 60%", 0.60),
    "k2so4": ("phu_my_k2so4_50", "Kali sunphat K2SO4", 0.50),
    "kno3": ("potassium_nitrate_13_0_46", "Kali nitrat KNO3", 0.46),
}


@dataclass(frozen=True)
class Factor:
    name: str
    code: str
    n: float = 1.0
    p: float = 1.0
    k: float = 1.0
    rationale_vi: str = ""
    rationale_en: str = ""
    missing: bool = False


def _dose(n: tuple[float, float], p: tuple[float, float], k: tuple[float, float]) -> dict[str, tuple[float, float]]:
    return {"n": n, "p2o5": p, "k2o": k}


CROPS: dict[str, dict[str, Any]] = {
    "robusta_coffee": {
        "name_vi": "Cà phê vối Robusta",
        "calibration_status": "locally_calibrated",
        "confidence": "high",
        "valid_yield_range": (1.0, 5.5),
        "textures": ["basaltic_red", "grey_granite", "gneiss"],
        "thresholds": {
            "n": {"low_max": 0.10, "high_min": 0.25, "unit": "pct", "source": "WASI 2016"},
            "p": {"low_max": 3.0, "high_min": 6.0, "unit": "mg_p2o5_per_100g", "source": "WASI 2016"},
            "k": {"low_max": 10.0, "high_min": 25.0, "unit": "mg_k2o_per_100g", "source": "WASI 2016 / IPI 2015"},
        },
        "dose": {
            "basaltic_red": {
                "baseline": 3.0,
                "low": _dose((300, 330), (100, 120), (240, 300)),
                "medium": _dose((220, 300), (60, 100), (180, 240)),
                "high": _dose((150, 220), (40, 60), (150, 180)),
            },
            "grey_granite": {
                "baseline": 2.5,
                "low": _dose((250, 300), (130, 150), (230, 280)),
                "medium": _dose((200, 250), (100, 130), (170, 230)),
                "high": _dose((160, 200), (70, 100), (140, 170)),
            },
            "gneiss": {
                "baseline": 2.5,
                "low": _dose((250, 300), (130, 150), (230, 280)),
                "medium": _dose((200, 250), (100, 130), (170, 230)),
                "high": _dose((160, 200), (70, 100), (140, 170)),
            },
        },
        "yield_increment": {"n": 70, "p2o5": 15, "k2o": 70},
        "establishment": {
            "establishment_y1": {"n": 60, "p2o5": 100, "k2o": 30},
            "establishment_y2": {"n": 120, "p2o5": 100, "k2o": 100},
            "establishment_y3": {"n": 150, "p2o5": 100, "k2o": 130},
        },
        "splits": [
            ("Sau thu hoạch", "Sau thu hoạch", "Tháng 1-2", 15, 50, 15),
            ("Đầu mùa mưa", "Đầu mùa mưa", "Tháng 5-6", 30, 25, 25),
            ("Giữa mùa mưa", "Giữa mùa mưa", "Tháng 7-8", 30, 15, 30),
            ("Cuối mùa mưa", "Cuối mùa mưa", "Tháng 9-10", 25, 10, 30),
        ],
        "ph_optimum": (4.5, 5.5),
        "lime": {"base": 500, "per_half": 500, "cap": 1500},
        "organic_t_ha": (15, 20),
        "sources": ["WASI 2005, 2016", "Truong Hong 1997", "Tien et al. 2015"],
    },
    "black_pepper": {
        "name_vi": "Hồ tiêu",
        "calibration_status": "partially_calibrated",
        "confidence": "medium",
        "valid_yield_range": (1.0, 6.0),
        "textures": ["basaltic_red", "acrisol"],
        "thresholds": {
            "n": {"low_max": 0.10, "high_min": 0.20, "unit": "pct", "source": "IISR / WASI extension"},
            "p": {"low_max": 6.0, "high_min": 10.0, "unit": "mg_p2o5_per_100g", "source": "Sarawak / WASI extension"},
            "k": {"low_max": 15.0, "high_min": 25.0, "unit": "mg_k2o_per_100g", "source": "WASI pepper"},
        },
        "dose": {
            "basaltic_red": {
                "baseline": 3.0,
                "low": _dose((300, 345), (120, 150), (300, 400)),
                "medium": _dose((250, 300), (90, 120), (240, 300)),
                "high": _dose((200, 250), (60, 90), (180, 240)),
            },
            "acrisol": {
                "baseline": 2.5,
                "low": _dose((300, 345), (130, 160), (320, 420)),
                "medium": _dose((250, 300), (100, 130), (260, 320)),
                "high": _dose((200, 250), (70, 100), (200, 260)),
            },
        },
        "yield_increment": {"n": 60, "p2o5": 20, "k2o": 80},
        "establishment": {
            "establishment_y1": {"n": 120, "p2o5": 120, "k2o": 170},
            "establishment_y2": {"n": 240, "p2o5": 240, "k2o": 340},
            "establishment_y3": {"n": 300, "p2o5": 200, "k2o": 400},
        },
        "splits": [
            ("Sau thu hoạch / sau cắt tỉa", "Sau thu hoạch / sau cắt tỉa", "Tháng 4-5", 30, 40, 15),
            ("Trước ra hoa", "Trước ra hoa", "Tháng 6", 20, 30, 20),
            ("Đậu trái", "Đậu trái", "Tháng 7-8", 25, 20, 30),
            ("Nuôi trái", "Nuôi trái", "Tháng 10-11", 25, 10, 35),
        ],
        "ph_optimum": (5.0, 6.0),
        "lime": {"base": 500, "per_half": 500, "cap": 2000},
        "organic_t_ha": (10, 20),
        "sources": ["WASI Pepper Research and Development Center", "IPI/SFRI 2016-2018", "Sarawak pepper nutrient references"],
    },
    "durian": {
        "name_vi": "Sầu riêng",
        "calibration_status": "borrowed",
        "confidence": "low",
        "valid_yield_range": (5.0, 25.0),
        "textures": ["basaltic_red", "acrisol", "alluvial"],
        "default_tree_density": 150,
        "thresholds": {
            "n": {"low_max": 0.10, "high_min": 0.15, "unit": "pct", "source": "Thai DOA / DRIS borrowed"},
            "p": {"low_max": 20.0, "high_min": 50.0, "unit": "mg_p_per_kg", "source": "Thai / Mekong Delta DRIS"},
            "k": {"low_max": 80.0, "high_min": 250.0, "unit": "mg_k_per_kg", "source": "Thai / Mekong Delta DRIS"},
        },
        "per_tree": {
            "baseline_kg_tree": 100,
            "low": _dose((1.5, 1.8), (1.1, 1.4), (1.0, 1.3)),
            "medium": _dose((1.2, 1.5), (0.9, 1.1), (0.8, 1.0)),
            "high": _dose((1.0, 1.2), (0.7, 0.9), (0.7, 0.8)),
        },
        "yield_increment_per_100kg_tree": {"n": 0.6, "p2o5": 0.3, "k2o": 0.5},
        "establishment_per_tree": {
            "establishment_y1": {"n": 0.10, "p2o5": 0.10, "k2o": 0.05},
            "establishment_y2": {"n": 0.20, "p2o5": 0.20, "k2o": 0.15},
            "establishment_y3": {"n": 0.40, "p2o5": 0.30, "k2o": 0.30},
            "establishment_y4": {"n": 0.70, "p2o5": 0.50, "k2o": 0.50},
            "establishment_y5": {"n": 1.00, "p2o5": 0.70, "k2o": 0.80},
        },
        "splits": [
            ("Sau thu hoạch", "Sau thu hoạch", "Tháng 8-9", 35, 30, 15),
            ("Trước ra hoa", "Trước ra hoa", "Tháng 11-12", 10, 40, 15),
            ("Đậu trái 0-60 ngày", "Đậu trái 0-60 ngày", "Tháng 2-3", 30, 20, 25),
            ("Nuôi trái 60 ngày trước thu hoạch", "Nuôi trái 60 ngày trước thu hoạch", "Tháng 4-5", 25, 10, 45),
        ],
        "ph_optimum": (5.5, 6.5),
        "lime": {"base": 1000, "per_half": 500, "cap": 2500},
        "organic_kg_tree": (20, 30),
        "sources": ["Poovarodom & Tawinteung", "Horticulturae 2024 DRIS norms", "Thai DOA / Mekong Delta DRIS reference"],
    },
}


def supported_crops() -> list[dict[str, Any]]:
    return _clean_response_text([
        {
            "crop": key,
            "name_vi": data["name_vi"],
            "calibration_status": data["calibration_status"],
            "confidence": data["confidence"],
            "valid_yield_range_t_ha": data["valid_yield_range"],
            "valid_textures": data["textures"],
        }
        for key, data in CROPS.items()
    ])


def recommend(payload: dict[str, Any]) -> dict[str, Any]:
    crop_key = payload["crop"]
    kb = CROPS[crop_key]
    warnings: list[dict[str, str]] = []
    trace: list[str] = []
    soil = payload["soil"]
    stage = payload.get("growth_stage", "mature_kinh_doanh")
    preferences = dict(payload.get("preferences") or {})
    tree_density = payload.get("tree_density_per_ha") or kb.get("default_tree_density", 1100)
    yield_target = payload.get("yield_target_t_ha")
    missing_critical: list[str] = []

    min_yield, max_yield = kb["valid_yield_range"]
    if yield_target is None:
        yield_target = kb.get("dose", {}).get(soil["texture"], {}).get("baseline", min_yield)
        if crop_key == "durian":
            yield_target = 15.0
    if yield_target < 0.5:
        raise ValueError("Mục tiêu năng suất quá thấp để lập khuyến nghị bón phân.")
    if yield_target > max_yield:
        warnings.append(_warning("warning", "YIELD_TARGET_UNREALISTIC", f"Năng suất mục tiêu {yield_target:g} tấn/ha vượt vùng hiệu lực. Hệ thống dùng ngưỡng {max_yield:g} tấn/ha để tính an toàn."))
        trace.append(f"yield_target={yield_target:g} > max={max_yield:g} -> dùng {max_yield:g}")
        yield_target = max_yield

    n_category = _classify(soil.get("total_n_pct"), kb["thresholds"]["n"], "N", missing_critical, warnings, trace)
    p_value = _available_p_for_crop(crop_key, soil, warnings, trace)
    p_category = _classify(p_value, kb["thresholds"]["p"], "P", missing_critical, warnings, trace)
    k_value = _exchangeable_k_for_crop(crop_key, soil)
    k_category = _classify(k_value, kb["thresholds"]["k"], "K", missing_critical, warnings, trace)

    if stage.startswith("establishment"):
        base = _establishment_dose(crop_key, kb, stage, tree_density)
        trace.append(f"Giai đoạn kiến thiết {stage}: dùng liều cố định, không cộng theo năng suất mục tiêu.")
        if payload.get("yield_target_t_ha") is not None:
            warnings.append(_warning("info", "ESTABLISHMENT_YIELD_IGNORED", "Giai đoạn kiến thiết cơ bản dùng liều cố định; năng suất mục tiêu chỉ dùng cho vườn kinh doanh."))
    else:
        base = _mature_base_dose(crop_key, kb, soil["texture"], n_category, p_category, k_category, yield_target, tree_density, trace)

    factors = _compute_factors(payload, kb, soil)
    n_factor, p_factor, k_factor, clamped = _compose_factors(factors)
    before = base.copy()
    adjusted = {
        "n": round(base["n"] * n_factor),
        "p2o5": round(base["p2o5"] * p_factor),
        "k2o": round(base["k2o"] * k_factor),
    }
    trace.append(f"Hệ số hiệu chỉnh tổng hợp: N={n_factor:.3f}, P={p_factor:.3f}, K={k_factor:.3f}")
    if clamped:
        warnings.append(_warning("warning", "ADJUSTMENT_FACTORS_CLAMPED", "Hệ số hiệu chỉnh đã được chặn trong khoảng an toàn 0,6-1,4 để tránh liều bón cực đoan."))

    _apply_safety(crop_key, adjusted, soil, p_value, warnings, trace, stage, preferences)
    k_source = _effective_k_source(crop_key, stage, preferences, warnings, trace)
    lime = _lime_kg_ha(kb, soil["ph_kcl"])
    if soil["ph_kcl"] < kb["ph_optimum"][0]:
        warnings.append(_warning("warning", f"PH_BELOW_{str(kb['ph_optimum'][0]).replace('.', '_')}", f"pH KCl {soil['ph_kcl']:g} thấp hơn vùng tối ưu {kb['ph_optimum'][0]}-{kb['ph_optimum'][1]}. Nên bón vôi khoảng {lime} kg/ha trước mùa mưa."))
    if crop_key == "durian":
        warnings.append(_warning("warning", "DURIAN_LOW_CONFIDENCE", "Khuyến nghị sầu riêng Tây Nguyên dùng ngưỡng vay mượn từ Thái Lan/ĐBSCL. Nên kiểm tra dinh dưỡng lá hằng năm để điều chỉnh."))
    if crop_key == "black_pepper":
        warnings.append(_warning("warning", "PEPPER_DISEASE_REGION", "Vườn tiêu Tây Nguyên có rủi ro chết nhanh/chết chậm. Không tăng liều mạnh nếu chưa kiểm tra Phytophthora/Fusarium."))

    confidence = _confidence(kb, missing_critical, factors, warnings)
    splits = _splits(kb, adjusted, crop_key, stage, k_source)
    organic = _organic_recommendation(crop_key, kb, tree_density)

    return _clean_response_text({
        "request_id": str(uuid4()),
        "timestamp": datetime.now(UTC).isoformat(),
        "engine_version": ENGINE_VERSION,
        "knowledge_base_version": KNOWLEDGE_BASE_VERSION,
        "crop": crop_key,
        "variety": payload.get("variety"),
        "crop_name_vi": kb["name_vi"],
        "calibration_status": kb["calibration_status"],
        "soil_categorization": {
            "n": _category_block(n_category, soil.get("total_n_pct"), kb["thresholds"]["n"], "kjeldahl"),
            "p": _category_block(p_category, p_value, kb["thresholds"]["p"], soil.get("available_p_method", "bray_ii")),
            "k": _category_block(k_category, k_value, kb["thresholds"]["k"], soil.get("exchangeable_k_method", "nh4oac")),
            "ph": {
                "status": "acidic" if soil["ph_kcl"] < kb["ph_optimum"][0] else "optimal" if soil["ph_kcl"] <= kb["ph_optimum"][1] else "high",
                "value_input": soil["ph_kcl"],
                "optimum_range": list(kb["ph_optimum"]),
                "lime_required_kg_ha": lime,
                "source": "WASI / tài liệu hiệu chỉnh vùng nhiệt đới",
            },
        },
        "recommendation": {
            "annual_total": {
                "n_kg_ha": adjusted["n"],
                "n_kg_ha_before_adjustment": round(before["n"]),
                "p2o5_kg_ha": adjusted["p2o5"],
                "p2o5_kg_ha_before_adjustment": round(before["p2o5"]),
                "k2o_kg_ha": adjusted["k2o"],
                "k2o_kg_ha_before_adjustment": round(before["k2o"]),
                "lime_kg_ha": lime,
                **organic,
                "adjustment_factors": {
                    "n_combined": n_factor,
                    "p_combined": p_factor,
                    "k_combined": k_factor,
                    "n_clamped": clamped,
                    "p_clamped": clamped,
                    "k_clamped": clamped,
                    "breakdown": [factor.__dict__ for factor in factors],
                },
                "rationale_vi": _rationale_vi(kb, n_category, p_category, k_category, yield_target),
                "rationale_en": "Deterministic recommendation from soil category, yield target and conservative adjustment factors.",
            },
            "splits": splits,
            "product_mix_options": [_product_mix(adjusted, crop_key, stage, warnings, k_source)],
        },
        "confidence": confidence,
        "warnings": warnings,
        "rationale": {"calculation_trace": trace, "sources_cited": [{"id": source.lower().replace(" ", "_")[:40], "title": source} for source in kb["sources"]]},
    })


def _classify(value: float | None, thresholds: dict[str, Any], nutrient: str, missing: list[str], warnings: list[dict[str, str]], trace: list[str]) -> str:
    if value is None:
        missing.append(nutrient)
        warnings.append(_warning("warning", f"MISSING_INPUT_{nutrient}", f"Thiếu chỉ tiêu {nutrient}; hệ thống tạm xếp mức trung bình và hạ độ tin cậy."))
        trace.append(f"{nutrient}: thiếu dữ liệu -> category=medium")
        return "medium"
    if value < thresholds["low_max"]:
        category = "low"
    elif value < thresholds["high_min"]:
        category = "medium"
    else:
        category = "high"
    trace.append(f"{nutrient}: {value:g} {thresholds['unit']} -> category={category}")
    return category


def _available_p_for_crop(crop: str, soil: dict[str, Any], warnings: list[dict[str, str]], trace: list[str]) -> float | None:
    value = soil.get("available_p_mg_per_100g")
    if soil.get("available_p_mg_per_kg") is not None:
        value = soil["available_p_mg_per_kg"]
        if crop in {"robusta_coffee", "black_pepper"}:
            value = value / P2O5_MG_100G_TO_P_MG_KG
            trace.append("P mg/kg được quy đổi xấp xỉ sang mg P2O5/100g để phân loại cà phê/tiêu.")
    if value is None:
        return None
    if soil.get("available_p_method") == "mehlich_3":
        value *= 0.8
        warnings.append(_warning("info", "METHOD_CONVERSION_USED", "P Mehlich-3 được quy đổi bảo thủ sang Bray II tương đương trước khi phân loại."))
        trace.append("Quy đổi P Mehlich-3 x 0,8 -> Bray II tương đương")
    if crop == "durian" and soil.get("available_p_mg_per_kg") is None:
        value = value * P2O5_MG_100G_TO_P_MG_KG
        trace.append("Sầu riêng dùng ngưỡng mg P/kg; P2O5 mg/100g được quy đổi xấp xỉ sang mg P/kg.")
    return value


def _available_p_mg_p_per_kg(soil: dict[str, Any]) -> float | None:
    if soil.get("available_p_mg_per_kg") is not None:
        value = float(soil["available_p_mg_per_kg"])
    elif soil.get("available_p_mg_per_100g") is not None:
        value = float(soil["available_p_mg_per_100g"]) * P2O5_MG_100G_TO_P_MG_KG
    else:
        return None
    if soil.get("available_p_method") == "mehlich_3":
        value *= 0.8
    return value


def _exchangeable_k_for_crop(crop: str, soil: dict[str, Any]) -> float | None:
    value = soil.get("exchangeable_k2o_mg_per_100g")
    if crop == "durian" and value is not None:
        return value * 8.3
    return value


def _midpoint(bounds: tuple[float, float]) -> float:
    return (bounds[0] + bounds[1]) / 2


def _mature_base_dose(crop: str, kb: dict[str, Any], texture: str, n_cat: str, p_cat: str, k_cat: str, yield_target: float, density: int, trace: list[str]) -> dict[str, float]:
    if crop == "durian":
        per_tree = kb["per_tree"]
        baseline_t_ha = per_tree["baseline_kg_tree"] * density / 1000
        delta_100kg_tree = ((yield_target * 1000 / density) - per_tree["baseline_kg_tree"]) / 100
        base = {
            "n": _midpoint(per_tree[n_cat]["n"]) * density,
            "p2o5": _midpoint(per_tree[p_cat]["p2o5"]) * density,
            "k2o": _midpoint(per_tree[k_cat]["k2o"]) * density,
        }
        inc = kb["yield_increment_per_100kg_tree"]
        base["n"] += delta_100kg_tree * inc["n"] * density
        base["p2o5"] += delta_100kg_tree * inc["p2o5"] * density
        base["k2o"] += delta_100kg_tree * inc["k2o"] * density
        trace.append(f"Sầu riêng: baseline {baseline_t_ha:.1f} tấn/ha tại {density} cây/ha, cộng theo chênh lệch kg/cây.")
        return {key: max(0, value) for key, value in base.items()}
    matrix = kb["dose"][texture]
    base = {
        "n": _midpoint(matrix[n_cat]["n"]),
        "p2o5": _midpoint(matrix[p_cat]["p2o5"]),
        "k2o": _midpoint(matrix[k_cat]["k2o"]),
    }
    delta = yield_target - matrix["baseline"]
    inc = kb["yield_increment"]
    base["n"] += delta * inc["n"]
    base["p2o5"] += delta * inc["p2o5"]
    base["k2o"] += delta * inc["k2o"]
    trace.append(f"Liều nền {texture}: N={base['n']:.1f}, P2O5={base['p2o5']:.1f}, K2O={base['k2o']:.1f} sau hiệu chỉnh năng suất.")
    return {key: max(0, value) for key, value in base.items()}


def _establishment_dose(crop: str, kb: dict[str, Any], stage: str, density: int) -> dict[str, float]:
    if crop == "durian":
        per_tree = kb["establishment_per_tree"].get(stage, kb["establishment_per_tree"]["establishment_y3"])
        return {key: value * density for key, value in per_tree.items()}
    return kb["establishment"].get(stage, kb["establishment"]["establishment_y3"]).copy()


def _compute_factors(payload: dict[str, Any], kb: dict[str, Any], soil: dict[str, Any]) -> list[Factor]:
    climate = payload.get("climate") or {}
    field = payload.get("field") or {}
    return [
        _ph_factor(soil["ph_kcl"], kb),
        _moisture_factor(climate),
        _texture_factor(soil),
        _slope_factor(field),
        _age_factor(payload["crop"], field.get("years_under_current_crop")),
        _organic_carbon_factor(soil),
    ]


def _ph_factor(ph: float, kb: dict[str, Any]) -> Factor:
    low, high = kb["ph_optimum"]
    if ph < low - 1.0:
        return Factor("pH", "PH_VERY_ACIDIC", 1.20, 1.30, 1.10, "pH rất chua: tăng N, P, K để bù hiệu lực thấp.")
    if ph < low:
        return Factor("pH", "PH_ACIDIC", 1.10, 1.15, 1.05, "pH chua: tăng nhẹ N, P, K và ưu tiên bón vôi.")
    if ph <= high:
        return Factor("pH", "PH_OPTIMAL", 1.0, 1.0, 1.0, "pH nằm trong vùng phù hợp.")
    if ph > high + 1.0:
        return Factor("pH", "PH_ALKALINE", 0.95, 1.10, 1.0, "pH cao: tăng nhẹ P do nguy cơ cố định bởi Ca.")
    return Factor("pH", "PH_SLIGHTLY_HIGH", 1.0, 1.05, 1.0, "pH hơi cao: tăng nhẹ P.")


def _moisture_factor(climate: dict[str, Any]) -> Factor:
    rain = climate.get("annual_rainfall_mm")
    if rain is None:
        return Factor("Moisture", "MOISTURE_UNKNOWN", missing=True, rationale_vi="Thiếu lượng mưa/nước tưới.")
    if rain > 2500:
        return Factor("Moisture", "RAINFALL_EXCESSIVE", 1.15, 1.0, 1.10, "Mưa lớn: tăng N và K do rửa trôi.")
    if rain >= 1700:
        return Factor("Moisture", "RAINFALL_ADEQUATE", 1.0, 1.0, 1.0, "Lượng mưa phù hợp.")
    if rain >= 1200:
        if climate.get("irrigation_available"):
            return Factor("Moisture", "RAINFALL_LOW_IRRIGATED", 1.0, 1.0, 1.0, "Mưa thấp nhưng có tưới.")
        return Factor("Moisture", "RAINFALL_MARGINAL", 0.90, 0.95, 0.85, "Thiếu nước: giảm liều để tránh lãng phí.")
    if climate.get("irrigation_available"):
        return Factor("Moisture", "RAINFALL_DRY_IRRIGATED", 0.95, 1.0, 0.95, "Khô hạn nhưng có tưới bổ sung.")
    return Factor("Moisture", "RAINFALL_INSUFFICIENT", 0.75, 0.90, 0.70, "Thiếu nước nặng: cây hấp thu kém, cần giảm liều và ưu tiên nước.")


def _texture_factor(soil: dict[str, Any]) -> Factor:
    texture = soil["texture"]
    cec = soil.get("cec_cmolc_per_kg")
    if texture == "basaltic_red":
        cec_value = cec if cec is not None else 8.0
        if cec_value < 6:
            return Factor("Texture", "CEC_VERY_LOW", 1.05, 1.10, 1.15, "CEC thấp: tăng K và chia nhỏ đợt bón.")
        if cec_value < 10:
            return Factor("Texture", "CEC_NORMAL_BASALT", 1.0, 1.05, 1.0, "Đất bazan đỏ có cố định P cao: tăng P nhẹ.")
        return Factor("Texture", "CEC_HIGH", 1.0, 1.0, 0.95, "CEC cao: giữ K tốt, giảm K nhẹ.")
    if texture in {"grey_granite", "gneiss"}:
        return Factor("Texture", "TEXTURE_LIGHT", 1.10, 1.0, 1.10, "Đất nhẹ dễ rửa trôi: tăng N và K.")
    return Factor("Texture", "TEXTURE_NEUTRAL", 1.0, 1.0, 1.0, "Kết cấu đất không cần hiệu chỉnh thêm.")


def _slope_factor(field: dict[str, Any]) -> Factor:
    slope = field.get("slope_pct")
    if slope is None:
        return Factor("Slope", "SLOPE_UNKNOWN", missing=True, rationale_vi="Thiếu độ dốc lô đất.")
    if slope < 8:
        return Factor("Slope", "SLOPE_FLAT")
    if slope < 15:
        return Factor("Slope", "SLOPE_GENTLE", 1.05, 1.05, 1.05, "Đất dốc nhẹ: bù hao hụt do dòng chảy mặt.")
    if slope < 25:
        return Factor("Slope", "SLOPE_MODERATE", 1.10, 1.10, 1.10, "Đất dốc vừa: cần chia nhỏ đợt bón và giữ cỏ phủ.")
    return Factor("Slope", "SLOPE_STEEP", 1.15, 1.15, 1.15, "Đất dốc lớn: nguy cơ xói mòn cao, cần bậc thang/đường đồng mức.")


def _age_factor(crop: str, age: int | None) -> Factor:
    if age is None:
        return Factor("Age", "AGE_UNKNOWN", missing=True, rationale_vi="Thiếu tuổi vườn.")
    if crop in {"robusta_coffee", "black_pepper"}:
        if age < 7:
            return Factor("Age", "AGE_YOUNG_PRODUCTIVE", 1.10, 1.05, 1.0, "Vườn trẻ đang mở tán: tăng N nhẹ.")
        if age <= 15:
            return Factor("Age", "AGE_PEAK", 1.0, 1.0, 1.0, "Vườn ở tuổi sung sức.")
        if age <= 25:
            return Factor("Age", "AGE_LATE", 0.95, 1.0, 1.05, "Vườn lớn tuổi: giảm N, tăng K nhẹ.")
        return Factor("Age", "AGE_SENESCENT", 0.85, 1.05, 1.10, "Vườn già: bón duy trì và cân nhắc tái canh.")
    if age < 10:
        return Factor("Age", "AGE_YOUNG_DURIAN", 1.0, 1.05, 1.0, "Sầu riêng trẻ: ưu tiên rễ và khung cành.")
    if age <= 25:
        return Factor("Age", "AGE_PEAK_DURIAN")
    return Factor("Age", "AGE_OLD_DURIAN", 0.90, 1.0, 1.05, "Sầu riêng già: giảm N, tăng K nhẹ.")


def _organic_carbon_factor(soil: dict[str, Any]) -> Factor:
    oc = soil.get("organic_carbon_pct")
    if oc is None:
        return Factor("Organic Carbon", "OC_UNKNOWN", missing=True, rationale_vi="Thiếu chất hữu cơ/OC.")
    if oc < 1.5:
        return Factor("Organic Carbon", "OC_LOW", 1.10, 1.0, 1.0, "OC thấp: tăng N và bắt buộc tăng hữu cơ.")
    if oc <= 3.0:
        return Factor("Organic Carbon", "OC_NORMAL")
    return Factor("Organic Carbon", "OC_HIGH", 0.90, 1.0, 1.0, "OC cao: giảm N nhờ khoáng hóa hữu cơ.")


def _compose_factors(factors: list[Factor]) -> tuple[float, float, float, bool]:
    raw = (prod(f.n for f in factors), prod(f.p for f in factors), prod(f.k for f in factors))
    final = tuple(max(0.6, min(1.4, value)) for value in raw)
    return round(final[0], 3), round(final[1], 3), round(final[2], 3), raw != final


def _apply_safety(crop: str, dose: dict[str, int], soil: dict[str, Any], p_value: float | None, warnings: list[dict[str, str]], trace: list[str], stage: str, preferences: dict[str, Any]) -> None:
    caps = DURIAN_SAFETY_CAPS if crop == "durian" else DEFAULT_SAFETY_CAPS
    for key, cap in caps.items():
        if dose[key] > cap:
            warnings.append(_warning("warning", f"{key.upper()}_CAP_EXCEEDED", f"Liều {key.upper()} vượt ngưỡng an toàn {cap} kg/ha/năm; hệ thống đã chặn về {cap}."))
            trace.append(f"{key} cap: {dose[key]} -> {cap}")
            dose[key] = cap
    if soil["ph_kcl"] < 4.0:
        warnings.append(_warning("critical", "PH_BELOW_4_0", "pH dưới 4,0: hiệu quả phân bón sẽ bị giới hạn mạnh nếu chưa xử lý vôi/hữu cơ."))
    pepper_p_mg_kg = _available_p_mg_p_per_kg(soil) if crop == "black_pepper" else None
    if crop == "black_pepper" and pepper_p_mg_kg is not None and pepper_p_mg_kg > PEPPER_P_EXCESS_THRESHOLD_MG_P_KG:
        dose["p2o5"] = 0
        warnings.append(_warning("warning", "PEPPER_P_EXCESS", "P trong đất tiêu vượt 96 mg P/kg; khuyến nghị tạm ngưng lân để tránh tích lũy và tăng rủi ro bệnh rễ."))
        trace.append(f"Hồ tiêu P={pepper_p_mg_kg:.1f} mg P/kg > 96 -> p2o5=0")
    if soil["ph_kcl"] < 4 and (soil.get("total_n_pct") or 0) < 0.05 and (soil.get("organic_carbon_pct") or 99) < 1.0:
        warnings.append(_warning("warning", "ANOMALOUS_SOIL_PROFILE", "Tổ hợp pH rất thấp, N rất thấp và OC thấp bất thường; nên kiểm tra lại mẫu đất trước khi bón liều cao."))


def _requested_k_source(preferences: dict[str, Any]) -> str | None:
    value = (preferences.get("preferred_k_source") or "").strip().lower()
    if value in K_SOURCE_PRODUCTS:
        return value
    brand = (preferences.get("preferred_brand") or "").strip().lower()
    if "k2so4" in brand or "sop" in brand or "sunphat" in brand:
        return "k2so4"
    if "kno3" in brand or "nitrat" in brand:
        return "kno3"
    if "kcl" in brand or "mop" in brand or "clorua" in brand:
        return "kcl"
    return None


def _effective_k_source(crop: str, stage: str, preferences: dict[str, Any], warnings: list[dict[str, str]], trace: list[str]) -> str:
    requested = _requested_k_source(preferences)
    if crop == "durian" and stage == "fruit_fill":
        if requested == "kcl":
            warnings.append(_warning("critical", "DURIAN_NO_KCL_FRUIT_FILL", "Sầu riêng giai đoạn nuôi trái không dùng KCl; hệ thống đã đổi nguồn kali sang K2SO4."))
            trace.append("Sầu riêng fruit_fill: nguồn KCl không được phép -> dùng K2SO4.")
            return "k2so4"
        if requested in {"k2so4", "kno3"}:
            return requested
        trace.append("Sầu riêng fruit_fill: không chọn nguồn kali -> mặc định dùng K2SO4.")
        return "k2so4"
    return requested or "kcl"


def _lime_kg_ha(kb: dict[str, Any], ph: float) -> int:
    low = kb["ph_optimum"][0]
    rule = kb["lime"]
    if ph >= low:
        return 0
    diff = low - ph
    raw = rule["base"] + diff / 0.5 * rule["per_half"]
    return min(rule["cap"], int(ceil(raw / 200) * 200))


def _organic_recommendation(crop: str, kb: dict[str, Any], density: int) -> dict[str, Any]:
    if crop == "durian":
        low, high = kb["organic_kg_tree"]
        return {"organic_kg_tree": round((low + high) / 2), "organic_t_ha": round(((low + high) / 2) * density / 1000, 1)}
    low, high = kb["organic_t_ha"]
    return {"organic_t_ha": round((low + high) / 2)}

def _product_lines(dose: dict[str, int], crop: str, stage: str, k_source: str = "kcl") -> list[dict[str, Any]]:
    dap = dose["p2o5"] / 0.46 if dose["p2o5"] else 0
    n_from_dap = dap * 0.18
    urea = max(0, (dose["n"] - n_from_dap) / 0.463)
    k_sku, k_name, k_grade = K_SOURCE_PRODUCTS.get(k_source, K_SOURCE_PRODUCTS["kcl"])
    k_rate = dose["k2o"] / k_grade if dose["k2o"] else 0
    return [
        {"sku": "phu_my_urea_46n", "name_vi": "Urê 46% N", "kg_ha_yr": round(urea), "bags_50kg_ha": round(urea / 50, 1)},
        {"sku": "phu_my_dap_18_46", "name_vi": "DAP 18-46", "kg_ha_yr": round(dap), "bags_50kg_ha": round(dap / 50, 1)},
        {"sku": k_sku, "name_vi": k_name, "kg_ha_yr": round(k_rate), "bags_50kg_ha": round(k_rate / 50, 1)},
    ]


def _splits(kb: dict[str, Any], dose: dict[str, int], crop: str, stage: str, k_source: str = "kcl") -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, (name_vi, _name_en, window, n_pct, p_pct, k_pct) in enumerate(kb["splits"], start=1):
        split_dose = {
            "n": round(dose["n"] * n_pct / 100),
            "p2o5": round(dose["p2o5"] * p_pct / 100),
            "k2o": round(dose["k2o"] * k_pct / 100),
        }
        rows.append(
            {
                "split_index": index,
                "name_vi": name_vi,
                "name_en": name_vi,
                "calendar_window": window,
                "n_pct": n_pct,
                "p2o5_pct": p_pct,
                "k2o_pct": k_pct,
                "n_kg_ha": split_dose["n"],
                "p2o5_kg_ha": split_dose["p2o5"],
                "k2o_kg_ha": split_dose["k2o"],
                "notes_vi": "Bón theo rãnh mép tán, lấp đất sau bón; không bón tập trung khi đất khô.",
                "notes_en": "Bón theo rãnh mép tán, lấp đất sau bón; không bón tập trung khi đất khô.",
                "commercial_products": _product_lines(split_dose, crop, stage, k_source),
            }
        )
    return rows


def _product_mix(dose: dict[str, int], crop: str, stage: str, warnings: list[dict[str, str]], k_source: str = "kcl") -> dict[str, Any]:
    products = _product_lines(dose, crop, stage, k_source)
    if crop == "durian" and stage == "fruit_fill" and any(product["sku"] == "phu_my_k2so4_50" for product in products):
        if not any(warning["code"] == "K_SOURCE_CHANGED" for warning in warnings):
            warnings.append(_warning("info", "K_SOURCE_CHANGED", "Nguồn kali đang dùng K2SO4 cho sầu riêng giai đoạn nuôi trái."))
    return {
        "option_id": 1,
        "label_vi": "Phương án quy đổi phân đơn",
        "label_en": "Phương án quy đổi phân đơn",
        "products": products,
        "estimated_cost_vnd_ha": None,
    }


def _confidence(kb: dict[str, Any], missing_critical: list[str], factors: list[Factor], warnings: list[dict[str, str]]) -> dict[str, Any]:
    base = {"locally_calibrated": 0.90, "partially_calibrated": 0.70, "borrowed": 0.40}[kb["calibration_status"]]
    missing_context = [f.code for f in factors if f.missing]
    anomalies = [w for w in warnings if w["code"] in {"ANOMALOUS_SOIL_PROFILE", "PH_BELOW_4_0"}]
    score = max(0.1, min(1.0, base - 0.10 * len(missing_critical) - 0.05 * len(missing_context) - 0.10 * len(anomalies)))
    tier = "high" if score >= 0.75 else "medium" if score >= 0.50 else "low"
    calibration_tier = kb["confidence"]
    badge = CONFIDENCE_BADGES[calibration_tier]
    return {
        "overall": tier,
        "calibration_tier": calibration_tier,
        "score": round(score, 2),
        **badge,
        "data_quality_score": round(score, 2),
        "calibration_basis": kb["sources"],
        "limitations": ["Khuyến nghị được tính bằng bộ quy tắc cố định, cần đối chiếu phân tích lá và điều kiện vườn thực tế."],
        "missing_inputs": missing_critical + missing_context,
    }


def _category_block(category: str, value: float | None, thresholds: dict[str, Any], method: str) -> dict[str, Any]:
    return {
        "category": category,
        "value_input": value,
        "unit": thresholds["unit"],
        "thresholds": {"low_max": thresholds["low_max"], "high_min": thresholds["high_min"]},
        "method": method,
        "source": thresholds["source"],
    }


def _rationale_vi(kb: dict[str, Any], n: str, p: str, k: str, yield_target: float) -> str:
    return f"Đất được xếp N={n}, P={p}, K={k}; liều nền lấy theo ma trận {kb['name_vi']} và mục tiêu năng suất {yield_target:g} tấn/ha, sau đó hiệu chỉnh bằng pH, nước, kết cấu đất, độ dốc, tuổi vườn và OC."


def _warning(level: str, code: str, message_vi: str, message_en: str | None = None) -> dict[str, str]:
    return {
        "level": level,
        "code": code,
        "message_vi": message_vi,
        "message_en": message_en or message_vi,
    }


def _clean_response_text(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return value.encode("latin1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return value
    if isinstance(value, list):
        return [_clean_response_text(item) for item in value]
    if isinstance(value, dict):
        return {key: _clean_response_text(item) for key, item in value.items()}
    return value


def sample_request() -> dict[str, Any]:
    return _clean_response_text({
        "crop": "robusta_coffee",
        "growth_stage": "mature_kinh_doanh",
        "yield_target_t_ha": 3.5,
        "tree_density_per_ha": 1100,
        "soil": {
            "texture": "basaltic_red",
            "ph_kcl": 4.3,
            "organic_carbon_pct": 2.8,
            "total_n_pct": 0.18,
            "available_p_method": "bray_ii",
            "available_p_mg_per_100g": 4.5,
            "exchangeable_k_method": "nh4oac",
            "exchangeable_k2o_mg_per_100g": 12,
            "cec_cmolc_per_kg": 8,
            "sample_depth_cm": 30,
            "sample_date": date.today().isoformat(),
        },
        "location": {"province": "Đắk Lắk", "district": "Cư M'gar", "elevation_m": 600},
        "climate": {"annual_rainfall_mm": 1900, "irrigation_available": True},
        "field": {"slope_pct": 5, "years_under_current_crop": 10},
        "preferences": {"language": "vi", "include_product_mix": True, "organic_available_t_ha": 10},
    })
