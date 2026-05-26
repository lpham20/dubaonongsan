from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
import logging
from pathlib import Path
import random
from typing import Any

import numpy as np
import tensorflow as tf

from app.ingestion.sources.world_fertilizer_commoditypriceapi import CommodityPriceApiUreaPublicScraper


logger = logging.getLogger("marketai.train_world_fertilizer_lstm")
FEATURE_COLUMNS = ["log_price", "log_return", "seasonal_sin", "seasonal_cos"]


def train(
    *,
    commodity_slug: str,
    artifacts_dir: Path,
    epochs: int,
    lookback_window: int,
    horizon_days: int,
    batch_size: int,
) -> dict[str, Any]:
    _set_determinism()
    observations = CommodityPriceApiUreaPublicScraper().scrape().observations
    observations = [row for row in observations if row.commodity_slug == commodity_slug and row.price_usd_per_tonne > 0]
    observations.sort(key=lambda row: row.observed_at)
    if len(observations) < lookback_window + horizon_days + 10:
        raise RuntimeError(f"Not enough {commodity_slug} observations for LSTM training: {len(observations)}")

    points = [(row.observed_at, float(row.price_usd_per_tonne), row.quote_type) for row in observations]
    raw_features = _raw_features(points)
    feature_mean = raw_features.mean(axis=0)
    feature_std = raw_features.std(axis=0)
    feature_std = np.where(feature_std < 1e-6, 1.0, feature_std)

    windows: list[np.ndarray] = []
    targets: list[np.ndarray] = []
    base_prices: list[float] = []
    max_start = len(points) - lookback_window - horizon_days + 1
    for start in range(max_start):
        end = start + lookback_window
        future_end = end + horizon_days
        window = (raw_features[start:end] - feature_mean) / feature_std
        base_price = float(points[end - 1][1])
        future_prices = np.asarray([price for _, price, _ in points[end:future_end]], dtype=np.float32)
        target = np.log(np.maximum(future_prices, 1e-6) / max(base_price, 1e-6))
        windows.append(window.astype(np.float32))
        targets.append(target.astype(np.float32))
        base_prices.append(base_price)
    x_all = np.stack(windows)
    y_raw = np.stack(targets)
    target_mean = float(np.mean(y_raw))
    target_std = max(float(np.std(y_raw)), 1e-6)
    y_all = ((y_raw - target_mean) / target_std).astype(np.float32)
    base_all = np.asarray(base_prices, dtype=np.float32)

    split = max(1, int(len(x_all) * 0.82))
    x_train, x_val = x_all[:split], x_all[split:]
    y_train, y_val = y_all[:split], y_all[split:]
    base_val = base_all[split:]
    actual_val_returns = y_raw[split:]
    if not len(x_val):
        x_train, x_val = x_all[:-1], x_all[-1:]
        y_train, y_val = y_all[:-1], y_all[-1:]
        base_val = base_all[-1:]
        actual_val_returns = y_raw[-1:]

    model = _build_model(lookback_window, len(FEATURE_COLUMNS), horizon_days)
    callbacks = [
        tf.keras.callbacks.EarlyStopping(
            monitor="val_loss",
            patience=8,
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
    metrics = _validation_metrics(model, x_val, actual_val_returns, base_val, target_mean, target_std)

    artifacts_dir.mkdir(parents=True, exist_ok=True)
    key = commodity_slug.strip().lower().replace("-", "_")
    keras_path = artifacts_dir / f"world_lstm_{key}.keras"
    tflite_path = artifacts_dir / f"world_lstm_{key}.tflite"
    scaler_path = artifacts_dir / f"world_lstm_{key}.scaler.json"
    meta_path = artifacts_dir / f"world_lstm_{key}.meta.json"

    model.save(keras_path)
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    tflite_path.write_bytes(converter.convert())

    scaler = {
        "commodity_slug": commodity_slug,
        "lookback_window": lookback_window,
        "horizon_days": horizon_days,
        "feature_columns": FEATURE_COLUMNS,
        "feature_mean": feature_mean.astype(float).tolist(),
        "feature_std": feature_std.astype(float).tolist(),
        "target": "future_cumulative_log_return",
        "target_mean": target_mean,
        "target_std": target_std,
    }
    scaler_path.write_text(json.dumps(scaler, ensure_ascii=False, indent=2), encoding="utf-8")
    meta = {
        "commodity_slug": commodity_slug,
        "model_kind": "world-fertilizer-lstm-tflite-v1",
        "source": "commoditypriceapi_urea_public_1y",
        "source_symbol": "UREA",
        "observations": len(points),
        "first_observed_at": points[0][0].isoformat(),
        "last_observed_at": points[-1][0].isoformat(),
        "lookback_window": lookback_window,
        "horizon_days": horizon_days,
        "training_windows": int(len(x_train)),
        "validation_windows": int(len(x_val)),
        "epochs_requested": epochs,
        "epochs_ran": len(history.history.get("loss", [])),
        "trained_at": datetime.now(UTC).isoformat(),
        **metrics,
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Saved world fertilizer LSTM artifacts to %s", artifacts_dir)
    return meta


def _build_model(lookback_window: int, feature_count: int, horizon_days: int) -> tf.keras.Model:
    inputs = tf.keras.Input(shape=(lookback_window, feature_count), name="world_feature_window")
    x = tf.keras.layers.LSTM(
        24,
        activation="tanh",
        recurrent_activation="sigmoid",
        unroll=True,
        name="world_price_lstm",
    )(inputs)
    x = tf.keras.layers.Dense(48, activation="relu", name="world_forecast_dense")(x)
    outputs = tf.keras.layers.Dense(
        horizon_days,
        kernel_initializer=tf.keras.initializers.RandomNormal(stddev=0.01, seed=42),
        bias_initializer="zeros",
        name="world_forecast_horizon",
    )(x)
    model = tf.keras.Model(inputs=inputs, outputs=outputs, name="marketai_world_fertilizer_lstm")
    model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=0.001), loss=tf.keras.losses.Huber(), metrics=["mae"])
    return model


def _validation_metrics(
    model: tf.keras.Model,
    x_val: np.ndarray,
    actual_returns: np.ndarray,
    base_prices: np.ndarray,
    target_mean: float,
    target_std: float,
) -> dict[str, float]:
    pred_norm = model.predict(x_val, verbose=0)
    pred_returns = pred_norm * target_std + target_mean
    pred_prices = base_prices[:, None] * np.exp(pred_returns)
    actual_prices = base_prices[:, None] * np.exp(actual_returns)
    naive_prices = np.repeat(base_prices[:, None], actual_prices.shape[1], axis=1)
    model_rmse = float(np.sqrt(np.mean((pred_prices - actual_prices) ** 2)))
    model_mae = float(np.mean(np.abs(pred_prices - actual_prices)))
    naive_rmse = float(np.sqrt(np.mean((naive_prices - actual_prices) ** 2)))
    naive_mae = float(np.mean(np.abs(naive_prices - actual_prices)))
    improvement = ((naive_rmse - model_rmse) / naive_rmse * 100) if naive_rmse else 0.0
    return {
        "validation_rmse_usd_per_tonne": round(model_rmse, 4),
        "validation_mae_usd_per_tonne": round(model_mae, 4),
        "validation_naive_rmse_usd_per_tonne": round(naive_rmse, 4),
        "validation_naive_mae_usd_per_tonne": round(naive_mae, 4),
        "validation_rmse_improvement_pct": round(improvement, 2),
    }


def _raw_features(points: list[tuple[datetime, float, str]]) -> np.ndarray:
    prices = np.asarray([float(price) for _, price, _ in points], dtype=np.float32)
    log_prices = np.log(np.maximum(prices, 1e-6))
    returns = np.zeros_like(log_prices)
    returns[1:] = np.diff(log_prices)
    seasonal_sin = []
    seasonal_cos = []
    for observed_at, _, _ in points:
        day_of_year = max(1, int(observed_at.timetuple().tm_yday))
        angle = 2 * np.pi * day_of_year / 365.25
        seasonal_sin.append(np.sin(angle))
        seasonal_cos.append(np.cos(angle))
    return np.column_stack(
        [
            log_prices,
            returns,
            np.asarray(seasonal_sin, dtype=np.float32),
            np.asarray(seasonal_cos, dtype=np.float32),
        ]
    ).astype(np.float32)


def _set_determinism() -> None:
    random.seed(42)
    np.random.seed(42)
    tf.keras.utils.set_random_seed(42)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--commodity", default="urea")
    parser.add_argument("--artifacts-dir", default=Path("ml_artifacts"), type=Path)
    parser.add_argument("--epochs", default=50, type=int)
    parser.add_argument("--lookback-window", default=60, type=int)
    parser.add_argument("--horizon-days", default=30, type=int)
    parser.add_argument("--batch-size", default=32, type=int)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    meta = train(
        commodity_slug=args.commodity,
        artifacts_dir=args.artifacts_dir,
        epochs=args.epochs,
        lookback_window=args.lookback_window,
        horizon_days=args.horizon_days,
        batch_size=args.batch_size,
    )
    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
