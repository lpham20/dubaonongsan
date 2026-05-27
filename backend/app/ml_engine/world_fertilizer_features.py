from __future__ import annotations

from datetime import datetime
import math
from typing import Any

import numpy as np


FEATURE_COLUMNS = ["log_price", "log_return", "seasonal_sin", "seasonal_cos"]


def normalize_commodity_slug(value: str) -> str:
    return value.strip().lower().replace("-", "_")


def raw_feature_matrix(points: list[tuple[datetime, float, str]]) -> np.ndarray:
    prices = np.asarray([float(price) for _, price, _ in points], dtype=np.float32)
    log_prices = np.log(np.maximum(prices, 1e-6))
    returns = np.zeros_like(log_prices)
    returns[1:] = np.diff(log_prices)
    seasonal_sin = []
    seasonal_cos = []
    for observed_at, _, _ in points:
        day_of_year = max(1, int(observed_at.timetuple().tm_yday))
        angle = 2 * math.pi * day_of_year / 365.25
        seasonal_sin.append(math.sin(angle))
        seasonal_cos.append(math.cos(angle))
    return np.column_stack(
        [
            log_prices,
            returns,
            np.asarray(seasonal_sin, dtype=np.float32),
            np.asarray(seasonal_cos, dtype=np.float32),
        ]
    ).astype(np.float32)


def feature_scaler(raw_features: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    feature_mean = raw_features.mean(axis=0)
    feature_std = raw_features.std(axis=0)
    feature_std = np.where(feature_std < 1e-6, 1.0, feature_std)
    return feature_mean, feature_std


def normalize_features(raw_features: np.ndarray, feature_mean: np.ndarray, feature_std: np.ndarray) -> np.ndarray:
    safe_std = np.where(feature_std < 1e-6, 1.0, feature_std)
    return ((raw_features - feature_mean) / safe_std).astype(np.float32)


def build_inference_tensor(points: list[tuple[datetime, float, str]], scaler: dict[str, Any]) -> np.ndarray:
    raw = raw_feature_matrix(points)
    mean = np.asarray(scaler["feature_mean"], dtype=np.float32)
    std = np.asarray(scaler["feature_std"], dtype=np.float32)
    normalized = normalize_features(raw, mean, std)
    return normalized[None, :, :]
