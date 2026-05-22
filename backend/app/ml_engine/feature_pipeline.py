from __future__ import annotations

from datetime import datetime
import math
from typing import Any

import numpy as np

from app.ml_engine.normalization import FEATURE_COLUMNS, Scaler


def build_inference_tensor(
    feature_window: list[dict[str, Any]],
    scaler: Scaler,
    region_id: int | None = None,
    variety_id: int | None = None,
) -> np.ndarray:
    rows = _prepare_window(feature_window, scaler.lookback_window, region_id, variety_id)
    matrix = np.asarray([_feature_values(row, scaler.feature_columns) for row in rows], dtype=np.float32)
    return scaler.transform_features(matrix)[None, :, :]


def build_training_windows(
    series_rows: list[dict[str, Any]],
    scaler: Scaler,
    stride: int = 7,
) -> tuple[np.ndarray, np.ndarray]:
    if len(series_rows) < scaler.lookback_window + scaler.horizon_days:
        return np.empty((0, scaler.lookback_window, len(scaler.feature_columns)), dtype=np.float32), np.empty(
            (0, scaler.horizon_days),
            dtype=np.float32,
        )

    x_values: list[np.ndarray] = []
    y_values: list[np.ndarray] = []
    max_start = len(series_rows) - scaler.lookback_window - scaler.horizon_days + 1
    step = max(1, stride)
    for start in range(0, max_start, step):
        window = series_rows[start : start + scaler.lookback_window]
        target = series_rows[
            start + scaler.lookback_window : start + scaler.lookback_window + scaler.horizon_days
        ]
        matrix = np.asarray([_feature_values(row, scaler.feature_columns) for row in window], dtype=np.float32)
        prices = np.asarray([float(row.get("max_price_vnd") or 0.0) for row in target], dtype=np.float32)
        if np.any(prices <= 0):
            continue
        if scaler.target_mode == "delta":
            prices = prices - float(window[-1].get("max_price_vnd") or 0.0)
        x_values.append(scaler.transform_features(matrix))
        y_values.append(scaler.transform_price(prices))

    if not x_values:
        return np.empty((0, scaler.lookback_window, len(scaler.feature_columns)), dtype=np.float32), np.empty(
            (0, scaler.horizon_days),
            dtype=np.float32,
        )
    return np.asarray(x_values, dtype=np.float32), np.asarray(y_values, dtype=np.float32)


def raw_feature_matrix(rows: list[dict[str, Any]], feature_columns: tuple[str, ...] = FEATURE_COLUMNS) -> np.ndarray:
    return np.asarray([_feature_values(row, feature_columns) for row in rows], dtype=np.float32)


def raw_target_values(rows: list[dict[str, Any]]) -> np.ndarray:
    return np.asarray([float(row.get("max_price_vnd") or 0.0) for row in rows], dtype=np.float32)


def _prepare_window(
    feature_window: list[dict[str, Any]],
    lookback_window: int,
    region_id: int | None,
    variety_id: int | None,
) -> list[dict[str, Any]]:
    if not feature_window:
        return []
    rows = [dict(row) for row in feature_window[-lookback_window:]]
    last_seen: dict[str, float | int | None] = {"region_id": region_id, "variety_id": variety_id}
    for row in rows:
        if region_id is not None:
            row["region_id"] = region_id
        if variety_id is not None:
            row["variety_id"] = variety_id
        for key in ("max_price_vnd", "min_price_vnd", "volume_traded_tons", "temp_max_celsius", "precipitation_mm", "maturity_index", "region_id", "variety_id"):
            if row.get(key) is None:
                row[key] = last_seen.get(key)
            else:
                last_seen[key] = row[key]
    fallback = rows[0]
    for row in rows:
        for key, value in fallback.items():
            if row.get(key) is None:
                row[key] = value
    if len(rows) < lookback_window:
        rows = [dict(rows[0]) for _ in range(lookback_window - len(rows))] + rows
    return rows


def _feature_values(row: dict[str, Any], feature_columns: tuple[str, ...]) -> list[float]:
    day_sin, day_cos = _day_features(row.get("timestamp") or row.get("record_timestamp"))
    values: dict[str, float] = {
        "max_price_vnd": _float(row.get("max_price_vnd")),
        "min_price_vnd": _float(row.get("min_price_vnd"), row.get("max_price_vnd")),
        "volume_traded_tons": _float(row.get("volume_traded_tons")),
        "temp_max_celsius": _float(row.get("temp_max_celsius"), 30.0),
        "precipitation_mm": _float(row.get("precipitation_mm")),
        "maturity_index": _float(row.get("maturity_index"), 6.0),
        "region_id": _float(row.get("region_id")),
        "variety_id": _float(row.get("variety_id")),
        "day_sin": day_sin,
        "day_cos": day_cos,
    }
    return [values[column] for column in feature_columns]


def _float(value: Any, fallback: Any = 0.0) -> float:
    try:
        if value is None or value == "":
            value = fallback
        return float(value or 0.0)
    except (TypeError, ValueError):
        return float(fallback or 0.0)


def _day_features(value: Any) -> tuple[float, float]:
    if isinstance(value, datetime):
        day = value.timetuple().tm_yday
    else:
        try:
            day = datetime.fromisoformat(str(value).replace("Z", "+00:00")).timetuple().tm_yday
        except (TypeError, ValueError):
            day = 1
    angle = 2 * math.pi * day / 366.0
    return math.sin(angle), math.cos(angle)
