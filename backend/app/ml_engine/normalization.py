from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

import numpy as np


FEATURE_COLUMNS = (
    "max_price_vnd",
    "min_price_vnd",
    "volume_traded_tons",
    "temp_max_celsius",
    "precipitation_mm",
    "maturity_index",
    "region_id",
    "variety_id",
    "day_sin",
    "day_cos",
)


@dataclass(frozen=True)
class Scaler:
    crop_type: str
    feature_columns: tuple[str, ...]
    feature_mean: list[float]
    feature_std: list[float]
    target_mean: float
    target_std: float
    lookback_window: int
    horizon_days: int
    target_mode: str = "price"
    version: int = 1

    @classmethod
    def fit(
        cls,
        crop_type: str,
        feature_matrix: np.ndarray,
        target_values: np.ndarray,
        lookback_window: int,
        horizon_days: int,
        feature_columns: tuple[str, ...] = FEATURE_COLUMNS,
        target_mode: str = "price",
    ) -> "Scaler":
        feature_mean = np.nanmean(feature_matrix, axis=0)
        feature_std = np.nanstd(feature_matrix, axis=0)
        feature_std = np.where(feature_std < 1e-6, 1.0, feature_std)
        target_mean = float(np.nanmean(target_values))
        target_std = float(np.nanstd(target_values))
        if target_std < 1e-6:
            target_std = 1.0
        return cls(
            crop_type=crop_type,
            feature_columns=feature_columns,
            feature_mean=[float(value) for value in feature_mean],
            feature_std=[float(value) for value in feature_std],
            target_mean=target_mean,
            target_std=target_std,
            lookback_window=lookback_window,
            horizon_days=horizon_days,
            target_mode=target_mode,
        )

    @classmethod
    def from_json(cls, payload: str | dict[str, Any]) -> "Scaler":
        data = json.loads(payload) if isinstance(payload, str) else payload
        return cls(
            crop_type=str(data["crop_type"]),
            feature_columns=tuple(data.get("feature_columns") or FEATURE_COLUMNS),
            feature_mean=[float(value) for value in data["feature_mean"]],
            feature_std=[float(value) for value in data["feature_std"]],
            target_mean=float(data["target_mean"]),
            target_std=float(data["target_std"]),
            lookback_window=int(data["lookback_window"]),
            horizon_days=int(data["horizon_days"]),
            target_mode=str(data.get("target_mode", "price")),
            version=int(data.get("version", 1)),
        )

    def to_json(self) -> str:
        return json.dumps(
            {
                "version": self.version,
                "crop_type": self.crop_type,
                "feature_columns": list(self.feature_columns),
                "feature_mean": self.feature_mean,
                "feature_std": self.feature_std,
                "target_mean": self.target_mean,
                "target_std": self.target_std,
                "lookback_window": self.lookback_window,
                "horizon_days": self.horizon_days,
                "target_mode": self.target_mode,
            },
            ensure_ascii=False,
            indent=2,
        )

    def transform_features(self, values: np.ndarray) -> np.ndarray:
        mean = np.asarray(self.feature_mean, dtype=np.float32)
        std = np.asarray(self.feature_std, dtype=np.float32)
        return (values.astype(np.float32) - mean) / std

    def transform_price(self, values: np.ndarray) -> np.ndarray:
        return (values.astype(np.float32) - self.target_mean) / self.target_std

    def denormalize_price(self, values: np.ndarray) -> np.ndarray:
        return values.astype(np.float32) * self.target_std + self.target_mean

    def denormalize_forecast(self, values: np.ndarray, last_price: float) -> np.ndarray:
        decoded = self.denormalize_price(values)
        if self.target_mode == "delta":
            return decoded + float(last_price)
        return decoded
