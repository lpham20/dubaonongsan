from dataclasses import dataclass
import logging
import math
from statistics import mean

import numpy as np

from app.ml_engine.feature_pipeline import build_inference_tensor
from app.ml_engine.model_registry import load_lstm_artifact


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ForecastConfig:
    lookback_window: int = 60
    horizon_days: int = 30
    rmse_usd_per_kg: float = 0.45
    mae_usd_per_kg: float = 0.32


class LSTMForecaster:
    """Forecast facade.

    Production deployments can load a TensorFlow/Keras `model.keras` artifact here.
    The MVP keeps a deterministic statistical fallback so the API remains runnable
    without GPU-heavy dependencies during local development.
    """

    def __init__(
        self,
        config: ForecastConfig | None = None,
        crop_type: str = "sau_rieng",
        region_id: int | None = None,
        variety_id: int | None = None,
    ) -> None:
        self.config = config or ForecastConfig()
        self.crop_type = crop_type
        self.region_id = region_id
        self.variety_id = variety_id
        self.last_model_kind = "baseline-statistical"

    def predict_30_days(self, feature_window: list[dict]) -> list[float]:
        artifact = load_lstm_artifact(self.crop_type)
        if artifact is not None and len(feature_window) >= self.config.lookback_window:
            try:
                forecasts = self._predict_tflite(feature_window, artifact)
                self.last_model_kind = artifact.model_kind
                return forecasts
            except Exception as exc:
                logger.exception("TFLite forecast failed crop=%s, falling back: %s", self.crop_type, exc)

        self.last_model_kind = "baseline-statistical"
        return self._predict_baseline(feature_window)

    def _predict_tflite(self, feature_window: list[dict], artifact) -> list[float]:
        x = build_inference_tensor(
            feature_window,
            scaler=artifact.scaler,
            region_id=self.region_id,
            variety_id=self.variety_id,
        ).astype(np.float32)

        with artifact.lock:
            artifact.interpreter.set_tensor(artifact.input_details[0]["index"], x)
            artifact.interpreter.invoke()
            y_norm = artifact.interpreter.get_tensor(artifact.output_details[0]["index"])[0]

        last_price = float(feature_window[-1].get("max_price_vnd") or 0)
        y = artifact.scaler.denormalize_forecast(np.asarray(y_norm, dtype=np.float32), last_price=last_price)
        if len(y) < self.config.horizon_days:
            y = np.pad(y, (0, self.config.horizon_days - len(y)), mode="edge")
        y = y[: self.config.horizon_days]

        price_floor = max(1000.0, last_price * 0.5) if last_price > 0 else 1000.0
        price_ceiling = last_price * 1.8 if last_price > 0 else float("inf")
        clipped = np.clip(y, price_floor, price_ceiling)
        return [round(float(value), 2) for value in clipped]

    def _predict_baseline(self, feature_window: list[dict]) -> list[float]:
        prices = [float(row["max_price_vnd"]) for row in feature_window if row.get("max_price_vnd")]
        if not prices:
            return []
        if len(prices) < 8:
            return [round(prices[-1], 2)] * self.config.horizon_days

        short_avg = mean(prices[-7:])
        long_avg = mean(prices[-30:]) if len(prices) >= 30 else mean(prices)
        trend = (short_avg - long_avg) / max(1, min(30, len(prices)))
        volatility = self._std(prices[-30:]) if len(prices) >= 30 else self._std(prices)
        last_price = prices[-1]

        forecasts: list[float] = []
        price_floor = max(1000.0, last_price * 0.55) if last_price < 25000 else 25000.0
        for day in range(1, self.config.horizon_days + 1):
            seasonal = math.sin(day / 4.8) * volatility * 0.09
            weather_bias = self._weather_bias(feature_window[-min(len(feature_window), 14) :])
            forecast = last_price + trend * day + seasonal + weather_bias * day
            forecasts.append(round(max(price_floor, forecast), 2))
        return forecasts

    @staticmethod
    def _std(values: list[float]) -> float:
        avg = mean(values)
        return math.sqrt(mean([(value - avg) ** 2 for value in values]))

    @staticmethod
    def _weather_bias(window: list[dict]) -> float:
        if not window:
            return 0.0
        rain = mean([float(row.get("precipitation_mm") or 0) for row in window])
        temp = mean([float(row.get("temp_max_celsius") or 30) for row in window])
        maturity = mean([float(row.get("maturity_index") or 6) for row in window])
        return (temp - 31.5) * 18 - max(0, rain - 20) * 12 + max(0, maturity - 7) * 22
