from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import tensorflow as tf

from app.ml_engine.feature_pipeline import build_inference_tensor
from app.ml_engine.normalization import Scaler
from app.ml_engine.training.data import group_series, load_snapshot


def backtest(crop_type: str, snapshot_path: Path, artifacts_dir: Path, min_improvement_pct: float = 10.0) -> dict:
    scaler = Scaler.from_json((artifacts_dir / f"lstm_{crop_type}.scaler.json").read_text(encoding="utf-8"))
    interpreter = tf.lite.Interpreter(model_path=str(artifacts_dir / f"lstm_{crop_type}.tflite"))
    interpreter.allocate_tensors()
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()

    series_scores: list[dict] = []
    for (region_id, variety_id), series in group_series(load_snapshot(snapshot_path, crop_type=crop_type)).items():
        if len(series) < scaler.lookback_window + scaler.horizon_days:
            continue
        model_errors: list[float] = []
        baseline_errors: list[float] = []
        max_start = len(series) - scaler.lookback_window - scaler.horizon_days + 1
        start_from = max(0, max_start - 180)
        for start in range(start_from, max_start, scaler.horizon_days):
            window = series[start : start + scaler.lookback_window]
            actual_rows = series[start + scaler.lookback_window : start + scaler.lookback_window + scaler.horizon_days]
            last_price = float(window[-1].get("max_price_vnd") or 0.0)
            if last_price <= 0:
                raise ValueError(
                    f"Invalid last_price={last_price} for crop={crop_type} "
                    f"region_id={region_id} variety_id={variety_id} start={start}"
                )
            actual_values = [float(row.get("max_price_vnd") or 0.0) for row in actual_rows]
            if any(value <= 0 for value in actual_values):
                raise ValueError(
                    f"Invalid actual price in backtest for crop={crop_type} "
                    f"region_id={region_id} variety_id={variety_id} start={start}"
                )
            actual = np.asarray(actual_values, dtype=np.float32)
            pred = _predict(interpreter, input_details, output_details, scaler, window, region_id, variety_id)
            baseline = np.repeat(last_price, len(actual))
            model_errors.extend((pred[: len(actual)] - actual).tolist())
            baseline_errors.extend((baseline - actual).tolist())
        if not model_errors:
            continue
        model_rmse = float(np.sqrt(np.mean(np.square(model_errors))))
        baseline_rmse = float(np.sqrt(np.mean(np.square(baseline_errors))))
        improvement = ((baseline_rmse - model_rmse) / baseline_rmse * 100.0) if baseline_rmse else 0.0
        series_scores.append(
            {
                "region_id": region_id,
                "variety_id": variety_id,
                "model_rmse_vnd_per_kg": round(model_rmse, 2),
                "baseline_rmse_vnd_per_kg": round(baseline_rmse, 2),
                "improvement_pct": round(improvement, 2),
                "passed": improvement >= min_improvement_pct,
            }
        )

    evaluated = len(series_scores)
    passed = sum(1 for item in series_scores if item["passed"])
    pass_rate = (passed / evaluated * 100.0) if evaluated else 0.0
    result = {
        "crop_type": crop_type,
        "evaluated_series": evaluated,
        "passed_series": passed,
        "pass_rate_pct": round(pass_rate, 2),
        "min_improvement_pct": min_improvement_pct,
        "passed_70pct_gate": pass_rate >= 70.0,
        "series": series_scores,
    }
    (artifacts_dir / f"lstm_{crop_type}.backtest.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if not result["passed_70pct_gate"]:
        raise AssertionError(json.dumps({k: v for k, v in result.items() if k != "series"}, ensure_ascii=False))
    return result


def _predict(interpreter, input_details, output_details, scaler: Scaler, window, region_id, variety_id) -> np.ndarray:
    x = build_inference_tensor(window, scaler, region_id=region_id, variety_id=variety_id).astype(np.float32)
    interpreter.set_tensor(input_details[0]["index"], x)
    interpreter.invoke()
    y_norm = interpreter.get_tensor(output_details[0]["index"])[0]
    return scaler.denormalize_forecast(np.asarray(y_norm, dtype=np.float32), last_price=float(window[-1]["max_price_vnd"]))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--crop", required=True)
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--artifacts-dir", default=Path("ml_artifacts"), type=Path)
    parser.add_argument("--min-improvement-pct", default=10.0, type=float)
    args = parser.parse_args()
    print(
        json.dumps(
            backtest(args.crop, args.snapshot, args.artifacts_dir, args.min_improvement_pct),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
