from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime
import json
import logging
import math
from pathlib import Path
import threading
from typing import Any

import numpy as np

from app.core.config import get_settings
from app.ml_engine.world_fertilizer_features import build_inference_tensor, normalize_commodity_slug
from app.ml_engine.model_registry import _load_tflite_module


logger = logging.getLogger(__name__)
_CACHE: OrderedDict[str, "WorldFertilizerLSTMArtifact"] = OrderedDict()
_CACHE_LOCK = threading.Lock()


@dataclass
class WorldFertilizerLSTMArtifact:
    commodity_slug: str
    interpreter: Any
    input_details: list[dict[str, Any]]
    output_details: list[dict[str, Any]]
    scaler: dict[str, Any]
    meta: dict[str, Any]
    model_path: Path
    lock: threading.Lock

    @property
    def model_kind(self) -> str:
        return str(self.meta.get("model_kind") or "world-fertilizer-lstm-tflite")


@dataclass
class WorldFertilizerLSTMPrediction:
    prices: list[float]
    model_kind: str
    meta: dict[str, Any]


def predict_world_fertilizer_lstm(
    commodity_slug: str,
    points: list[tuple[datetime, float, str]],
    *,
    horizon_days: int,
) -> WorldFertilizerLSTMPrediction | None:
    artifact = load_world_fertilizer_lstm_artifact(commodity_slug)
    if artifact is None:
        return None

    lookback_window = int(artifact.scaler.get("lookback_window") or 60)
    if len(points) < lookback_window:
        return None
    window = points[-lookback_window:]
    prices = [float(price) for _, price, _ in window if price and price > 0]
    if len(prices) != lookback_window:
        return None

    features = build_inference_tensor(window, artifact.scaler)
    with artifact.lock:
        artifact.interpreter.set_tensor(artifact.input_details[0]["index"], features.astype(np.float32))
        artifact.interpreter.invoke()
        y_norm = artifact.interpreter.get_tensor(artifact.output_details[0]["index"])[0]

    target_mean = float(artifact.scaler.get("target_mean") or 0.0)
    target_std = max(float(artifact.scaler.get("target_std") or 1.0), 1e-6)
    cumulative_returns = np.asarray(y_norm, dtype=np.float32) * target_std + target_mean
    cumulative_returns = np.clip(cumulative_returns, -0.55, 0.55)
    base_price = prices[-1]
    predicted = [round(float(base_price * math.exp(float(value))), 2) for value in cumulative_returns[:horizon_days]]
    if len(predicted) < horizon_days and predicted:
        predicted.extend([predicted[-1]] * (horizon_days - len(predicted)))
    if not predicted or any(not math.isfinite(value) or value <= 0 for value in predicted):
        return None
    return WorldFertilizerLSTMPrediction(prices=predicted[:horizon_days], model_kind=artifact.model_kind, meta=artifact.meta)


def load_world_fertilizer_lstm_artifact(commodity_slug: str) -> WorldFertilizerLSTMArtifact | None:
    settings = get_settings()
    key = normalize_commodity_slug(commodity_slug)
    with _CACHE_LOCK:
        cached = _CACHE.get(key)
        if cached is not None:
            _CACHE.move_to_end(key)
            return cached

    artifacts_dir = Path(settings.ml_artifacts)
    model_path = artifacts_dir / f"world_lstm_{key}.tflite"
    scaler_path = artifacts_dir / f"world_lstm_{key}.scaler.json"
    meta_path = artifacts_dir / f"world_lstm_{key}.meta.json"
    if not model_path.exists() or not scaler_path.exists():
        return None

    try:
        tflite = _load_tflite_module()
        interpreter = tflite.Interpreter(model_path=str(model_path))
        interpreter.allocate_tensors()
        scaler = json.loads(scaler_path.read_text(encoding="utf-8"))
        _validate_scaler(scaler, commodity_slug=key)
        meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
        artifact = WorldFertilizerLSTMArtifact(
            commodity_slug=key,
            interpreter=interpreter,
            input_details=interpreter.get_input_details(),
            output_details=interpreter.get_output_details(),
            scaler=scaler,
            meta=meta,
            model_path=model_path,
            lock=threading.Lock(),
        )
    except Exception as exc:
        logger.exception("Failed to load world fertilizer LSTM artifact commodity=%s: %s", key, exc)
        return None

    with _CACHE_LOCK:
        _CACHE[key] = artifact
        _CACHE.move_to_end(key)
        while len(_CACHE) > 1:
            _CACHE.popitem(last=False)
    logger.info("Loaded world fertilizer LSTM artifact commodity=%s path=%s", key, model_path)
    return artifact


def invalidate_world_fertilizer_lstm_cache(commodity_slug: str | None = None) -> None:
    with _CACHE_LOCK:
        if commodity_slug is None:
            _CACHE.clear()
        else:
            _CACHE.pop(normalize_commodity_slug(commodity_slug), None)


def _validate_scaler(scaler: dict[str, Any], *, commodity_slug: str) -> None:
    required = {
        "commodity_slug",
        "lookback_window",
        "horizon_days",
        "feature_columns",
        "feature_mean",
        "feature_std",
        "target_mean",
        "target_std",
    }
    missing = required - set(scaler)
    if missing:
        raise ValueError(f"World fertilizer scaler missing keys: {sorted(missing)}")
    if str(scaler.get("commodity_slug")) != commodity_slug:
        raise ValueError(f"World fertilizer scaler commodity mismatch: {scaler.get('commodity_slug')} != {commodity_slug}")
    feature_count = len(scaler.get("feature_columns") or [])
    if len(scaler.get("feature_mean") or []) != feature_count or len(scaler.get("feature_std") or []) != feature_count:
        raise ValueError("World fertilizer scaler feature dimensions are inconsistent")
