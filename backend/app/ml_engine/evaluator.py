from math import sqrt
from statistics import mean
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ml_engine.lstm_forecaster import ForecastConfig, LSTMForecaster
from app.models import DailyMarketPrice
from app.services.data_loader import DataLoader


VND_PER_USD = 24500


class ForecastEvaluator:
    def __init__(
        self,
        db: Session,
        config: ForecastConfig | None = None,
        crop_type: str = "sau_rieng",
        region_id: int | None = None,
        variety_id: int | None = None,
    ) -> None:
        self.db = db
        self.config = config or ForecastConfig()
        self.crop_type = crop_type
        self.region_id = region_id
        self.variety_id = variety_id

    def backtest(self) -> dict:
        squared_errors: list[float] = []
        absolute_errors: list[float] = []
        evaluated_series = 0

        for region_id, variety_id in self._series_keys():
            points = DataLoader(self.db).historical_prices(
                region_id=region_id,
                variety_id=variety_id,
                crop_type=self.crop_type,
                quality_grade="Loại A",
                limit=1000,
            )
            if len(points) < self.config.lookback_window + 7:
                continue
            evaluated_series += 1
            max_start = len(points) - self.config.lookback_window - 1
            step = max(1, self.config.horizon_days // 2)

            for start in range(0, max_start, step):
                window = points[start : start + self.config.lookback_window]
                actual = points[
                    start
                    + self.config.lookback_window : start
                    + self.config.lookback_window
                    + self.config.horizon_days
                ]
                if not actual:
                    continue
                forecast = LSTMForecaster(
                    self.config,
                    crop_type=self.crop_type,
                    region_id=region_id,
                    variety_id=variety_id,
                ).predict_30_days(window)[: len(actual)]
                for predicted, actual_point in zip(forecast, actual, strict=False):
                    actual_price = float(actual_point["max_price_vnd"])
                    error = predicted - actual_price
                    squared_errors.append(error * error)
                    absolute_errors.append(abs(error))

        if not squared_errors:
            return {
                "rmse_vnd_per_kg": None,
                "mae_vnd_per_kg": None,
                "rmse_usd_per_kg": 0.0,
                "mae_usd_per_kg": 0.0,
                "backtest_samples": 0,
                "evaluated_series": evaluated_series,
                "note": "Chưa đủ dữ liệu lịch sử để backtest với cửa sổ 60 ngày.",
            }

        rmse_vnd = sqrt(mean(squared_errors))
        mae_vnd = mean(absolute_errors)
        return {
            "rmse_vnd_per_kg": round(rmse_vnd, 2),
            "mae_vnd_per_kg": round(mae_vnd, 2),
            "rmse_usd_per_kg": round(rmse_vnd / VND_PER_USD, 4),
            "mae_usd_per_kg": round(mae_vnd / VND_PER_USD, 4),
            "lookback_days": self.config.lookback_window,
            "forecast_horizon_days": self.config.horizon_days,
            "backtest_samples": len(squared_errors),
            "evaluated_series": evaluated_series,
            "note": "Sai số được tính bằng backtest trượt trên dữ liệu lịch sử hiện có.",
        }

    def _series_keys(self) -> list[tuple[int, int]]:
        if self.region_id and self.variety_id:
            return [(self.region_id, self.variety_id)]
        rows = self.db.execute(
            select(
                DailyMarketPrice.region_id,
                DailyMarketPrice.variety_id,
            )
            .where(DailyMarketPrice.quality_grade == "Loại A")
            .where(DailyMarketPrice.crop_type == self.crop_type)
            .distinct()
        ).all()
        keys = [(int(row[0]), int(row[1])) for row in rows]
        if self.region_id:
            keys = [key for key in keys if key[0] == self.region_id]
        if self.variety_id:
            keys = [key for key in keys if key[1] == self.variety_id]
        return keys
