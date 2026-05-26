from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
import random
from typing import Any

import numpy as np
import tensorflow as tf

from app.ml_engine.feature_pipeline import build_training_windows, raw_feature_matrix, raw_target_values
from app.ml_engine.normalization import FEATURE_COLUMNS, Scaler
from app.ml_engine.training.data import group_series, load_snapshot


logger = logging.getLogger("marketai.train_lstm")


def train(
    crop_type: str,
    snapshot_path: Path,
    artifacts_dir: Path,
    epochs: int,
    lookback_window: int,
    horizon_days: int,
    stride: int,
    batch_size: int,
    target_mode: str,
) -> dict[str, Any]:
    _set_determinism()
    rows = load_snapshot(snapshot_path, crop_type=crop_type)
    if not rows:
        raise RuntimeError(f"No rows found for crop={crop_type} in {snapshot_path}")

    grouped = group_series(rows)
    eligible = {
        key: value
        for key, value in grouped.items()
        if len(value) >= lookback_window + horizon_days
    }
    if not eligible:
        raise RuntimeError(f"No eligible series for crop={crop_type}; need >= {lookback_window + horizon_days} rows")

    fit_rows = [row for series in eligible.values() for row in series]
    target_values = raw_target_values(fit_rows)
    if target_mode == "delta":
        target_values = _target_deltas(eligible, lookback_window, horizon_days, stride)

    scaler = Scaler.fit(
        crop_type=crop_type,
        feature_matrix=raw_feature_matrix(fit_rows, FEATURE_COLUMNS),
        target_values=target_values,
        lookback_window=lookback_window,
        horizon_days=horizon_days,
        feature_columns=FEATURE_COLUMNS,
        target_mode=target_mode,
    )

    train_x_chunks: list[np.ndarray] = []
    train_y_chunks: list[np.ndarray] = []
    val_x_chunks: list[np.ndarray] = []
    val_y_chunks: list[np.ndarray] = []
    for series in eligible.values():
        x, y = build_training_windows(series, scaler, stride=stride)
        if len(x):
            if len(x) == 1:
                train_x_chunks.append(x)
                train_y_chunks.append(y)
                continue
            split_index = min(len(x) - 1, max(1, int(len(x) * 0.82)))
            train_x_chunks.append(x[:split_index])
            train_y_chunks.append(y[:split_index])
            val_x_chunks.append(x[split_index:])
            val_y_chunks.append(y[split_index:])
    if not train_x_chunks:
        raise RuntimeError(f"No training windows built for crop={crop_type}")

    x_train = np.concatenate(train_x_chunks, axis=0)
    y_train = np.concatenate(train_y_chunks, axis=0)
    if val_x_chunks:
        x_val = np.concatenate(val_x_chunks, axis=0)
        y_val = np.concatenate(val_y_chunks, axis=0)
    elif len(x_train) > 1:
        x_train, x_val = x_train[:-1], x_train[-1:]
        y_train, y_val = y_train[:-1], y_train[-1:]
    else:
        raise RuntimeError(f"Not enough windows for validation crop={crop_type}")

    order = np.arange(len(x_train))
    np.random.shuffle(order)
    x_train = x_train[order]
    y_train = y_train[order]

    model = _build_model(lookback_window, len(FEATURE_COLUMNS), horizon_days)
    callbacks = [
        tf.keras.callbacks.EarlyStopping(
            monitor="val_loss",
            patience=4,
            min_delta=1e-5,
            restore_best_weights=True,
        )
    ]
    history = model.fit(
        x_train,
        y_train,
        validation_data=(x_val, y_val),
        epochs=epochs,
        batch_size=batch_size,
        verbose=2,
        callbacks=callbacks,
    )

    metrics = _validation_metrics(model, x_val, y_val, scaler)
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    keras_path = artifacts_dir / f"lstm_{crop_type}.keras"
    scaler_path = artifacts_dir / f"lstm_{crop_type}.scaler.json"
    meta_path = artifacts_dir / f"lstm_{crop_type}.meta.json"

    model.save(keras_path)
    scaler_path.write_text(scaler.to_json(), encoding="utf-8")
    meta = {
        "crop_type": crop_type,
        "model_kind": "lstm-keras",
        "lookback_window": lookback_window,
        "horizon_days": horizon_days,
        "target_mode": target_mode,
        "feature_columns": list(FEATURE_COLUMNS),
        "series_total": len(grouped),
        "series_eligible": len(eligible),
        "training_windows": int(len(x_train)),
        "validation_windows": int(len(x_val)),
        "epochs_requested": epochs,
        "epochs_ran": len(history.history.get("loss", [])),
        **metrics,
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Saved %s, %s, %s", keras_path, scaler_path, meta_path)
    return meta


def _build_model(lookback_window: int, feature_count: int, horizon_days: int) -> tf.keras.Model:
    inputs = tf.keras.Input(shape=(lookback_window, feature_count), name="feature_window")
    x = tf.keras.layers.LSTM(
        24,
        activation="tanh",
        recurrent_activation="sigmoid",
        name="price_lstm",
    )(inputs)
    x = tf.keras.layers.Dense(48, activation="relu", name="forecast_dense")(x)
    outputs = tf.keras.layers.Dense(horizon_days, name="forecast_horizon")(x)
    model = tf.keras.Model(inputs=inputs, outputs=outputs, name="marketai_lstm_forecaster")
    model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=0.001), loss="mse", metrics=["mae"])
    return model


def _validation_metrics(model: tf.keras.Model, x_val: np.ndarray, y_val: np.ndarray, scaler: Scaler) -> dict[str, float]:
    pred_norm = model.predict(x_val, verbose=0)
    max_price_index = scaler.feature_columns.index("max_price_vnd")
    last_price = x_val[:, -1, max_price_index] * scaler.feature_std[max_price_index] + scaler.feature_mean[max_price_index]
    pred = _decode_targets(scaler, pred_norm, last_price)
    actual = _decode_targets(scaler, y_val, last_price)
    baseline = np.repeat(last_price[:, None], actual.shape[1], axis=1)
    model_rmse = float(np.sqrt(np.mean((pred - actual) ** 2)))
    model_mae = float(np.mean(np.abs(pred - actual)))
    baseline_rmse = float(np.sqrt(np.mean((baseline - actual) ** 2)))
    baseline_mae = float(np.mean(np.abs(baseline - actual)))
    improvement = ((baseline_rmse - model_rmse) / baseline_rmse * 100.0) if baseline_rmse else 0.0
    return {
        "validation_rmse_vnd_per_kg": round(model_rmse, 2),
        "validation_mae_vnd_per_kg": round(model_mae, 2),
        "validation_baseline_rmse_vnd_per_kg": round(baseline_rmse, 2),
        "validation_baseline_mae_vnd_per_kg": round(baseline_mae, 2),
        "validation_rmse_improvement_pct": round(improvement, 2),
    }


def _target_deltas(
    eligible: dict[tuple[int, int], list[dict[str, Any]]],
    lookback_window: int,
    horizon_days: int,
    stride: int,
) -> np.ndarray:
    values: list[float] = []
    step = max(1, stride)
    for series in eligible.values():
        max_start = len(series) - lookback_window - horizon_days + 1
        for start in range(0, max_start, step):
            last_price = float(series[start + lookback_window - 1].get("max_price_vnd") or 0.0)
            future = series[start + lookback_window : start + lookback_window + horizon_days]
            values.extend(float(row.get("max_price_vnd") or 0.0) - last_price for row in future)
    if not values:
        return np.asarray([0.0], dtype=np.float32)
    return np.asarray(values, dtype=np.float32)


def _decode_targets(scaler: Scaler, values: np.ndarray, last_price: np.ndarray) -> np.ndarray:
    decoded = scaler.denormalize_price(values)
    if scaler.target_mode == "delta":
        return decoded + last_price[:, None]
    return decoded


def _set_determinism() -> None:
    random.seed(42)
    np.random.seed(42)
    tf.keras.utils.set_random_seed(42)
    tf.random.set_seed(42)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--crop", required=True)
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--artifacts-dir", default=Path("ml_artifacts"), type=Path)
    parser.add_argument("--epochs", default=30, type=int)
    parser.add_argument("--lookback-window", default=60, type=int)
    parser.add_argument("--horizon-days", default=30, type=int)
    parser.add_argument("--stride", default=7, type=int)
    parser.add_argument("--batch-size", default=64, type=int)
    parser.add_argument("--target-mode", choices=["price", "delta"], default="delta")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    meta = train(
        crop_type=args.crop,
        snapshot_path=args.snapshot,
        artifacts_dir=args.artifacts_dir,
        epochs=args.epochs,
        lookback_window=args.lookback_window,
        horizon_days=args.horizon_days,
        stride=args.stride,
        batch_size=args.batch_size,
        target_mode=args.target_mode,
    )
    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
