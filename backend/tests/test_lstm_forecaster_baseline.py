from app.ml_engine.lstm_forecaster import ForecastConfig, LSTMForecaster


def _flat_rice_window(price: float = 8500.0) -> list[dict]:
    return [
        {
            "max_price_vnd": price,
            "precipitation_mm": 0,
            "temp_max_celsius": 38,
            "maturity_index": 10,
        }
        for _ in range(30)
    ]


def test_rice_weather_bias_is_capped_to_small_relative_shift() -> None:
    forecaster = LSTMForecaster(config=ForecastConfig(horizon_days=30), crop_type="lua")

    forecast = forecaster._predict_baseline(_flat_rice_window())

    assert forecast[-1] <= 8670.0


def test_weather_component_scales_toward_horizon_limit() -> None:
    forecaster = LSTMForecaster(config=ForecastConfig(horizon_days=30), crop_type="lua")

    day_15_shift = forecaster._weather_component(100.0, day=15, last_price=8500.0)
    day_30_shift = forecaster._weather_component(100.0, day=30, last_price=8500.0)

    assert day_15_shift == 85.0
    assert day_30_shift == 170.0
