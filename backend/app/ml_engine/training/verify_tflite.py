from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import tensorflow as tf

from app.ml_engine.feature_pipeline import build_inference_tensor
from app.ml_engine.normalization import Scaler
from app.ml_engine.training.data import group_series, load_snapshot


def test_match(crop_type: str, snapshot_path: Path, artifacts_dir: Path, tolerance: float) -> dict:
    keras_path = artifacts_dir / f"lstm_{crop_type}.keras"
    tflite_path = artifacts_dir / f"lstm_{crop_type}.tflite"
    scaler_path = artifacts_dir / f"lstm_{crop_type}.scaler.json"
    scaler = Scaler.from_json(scaler_path.read_text(encoding="utf-8"))
    sample = _sample_window(crop_type, snapshot_path, scaler.lookback_window)

    x = build_inference_tensor(
        sample,
        scaler,
        region_id=int(sample[-1]["region_id"]),
        variety_id=int(sample[-1]["variety_id"]),
    ).astype(np.float32)
    keras_model = tf.keras.models.load_model(keras_path, compile=False)
    keras_pred = keras_model.predict(x, verbose=0)[0]

    interpreter = tf.lite.Interpreter(model_path=str(tflite_path))
    interpreter.allocate_tensors()
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    interpreter.set_tensor(input_details[0]["index"], x)
    interpreter.invoke()
    tflite_pred = interpreter.get_tensor(output_details[0]["index"])[0]

    last_price = float(sample[-1]["max_price_vnd"])
    keras_price = scaler.denormalize_forecast(keras_pred, last_price=last_price)
    tflite_price = scaler.denormalize_forecast(tflite_pred, last_price=last_price)
    max_diff = float(np.max(np.abs(keras_price - tflite_price)))
    rel_diff = max_diff / max(1.0, float(np.mean(np.abs(keras_price))))
    result = {
        "crop_type": crop_type,
        "max_diff_vnd_per_kg": round(max_diff, 4),
        "rel_diff_pct": round(rel_diff * 100, 4),
        "tolerance_pct": round(tolerance * 100, 4),
        "passed": rel_diff < tolerance,
    }
    if not result["passed"]:
        raise AssertionError(json.dumps(result, ensure_ascii=False))
    return result


def _sample_window(crop_type: str, snapshot_path: Path, lookback_window: int) -> list[dict]:
    rows = load_snapshot(snapshot_path, crop_type=crop_type)
    grouped = group_series(rows)
    for series in grouped.values():
        if len(series) >= lookback_window:
            return series[-lookback_window:]
    raise RuntimeError(f"No sample window for crop={crop_type}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--crop", required=True)
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--artifacts-dir", default=Path("ml_artifacts"), type=Path)
    parser.add_argument("--tolerance", default=0.05, type=float)
    args = parser.parse_args()
    print(json.dumps(test_match(args.crop, args.snapshot, args.artifacts_dir, args.tolerance), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
