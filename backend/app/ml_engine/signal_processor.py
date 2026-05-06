from datetime import datetime
from statistics import mean


def detect_optimal_sell_points(price_time_series: list[dict]) -> list[dict]:
    """Phát hiện điểm cảnh báo bán bằng độ nổi bật đỉnh giá và Bollinger Band."""

    if len(price_time_series) < 22:
        return []

    prices = [float(point["max_price_vnd"]) for point in price_time_series]
    timestamps = [point["timestamp"] for point in price_time_series]
    std_all = _std(prices)
    prominence_threshold = 0.2 * std_all
    signals: list[dict] = []
    last_signal_idx = -99

    for idx in range(10, len(prices) - 2):
        local_peak = prices[idx] > prices[idx - 1] and prices[idx] >= prices[idx + 1]
        if not local_peak:
            continue
        prominence = prices[idx] - max(min(prices[idx - 5 : idx]), min(prices[idx + 1 : idx + 6]))
        if prominence < prominence_threshold or idx - last_signal_idx < 14:
            continue

        trailing = prices[max(0, idx - 20) : idx]
        if len(trailing) < 10:
            continue
        bollinger_upper = mean(trailing) + 2 * _std(trailing)
        ma_now = mean(prices[idx - 9 : idx + 1])
        ma_next = mean(prices[idx - 8 : idx + 2])
        trend_derivative = ma_next - ma_now

        if prices[idx] >= bollinger_upper and trend_derivative <= 0:
            signals.append(
                {
                    "timestamp": _as_datetime(timestamps[idx]),
                    "price_vnd": round(prices[idx], 2),
                    "signal": "CẢNH BÁO BÁN",
                    "reason": "Đỉnh giá cục bộ vượt dải Bollinger trên trong khi trung bình động 10 ngày bắt đầu suy yếu.",
                    "prominence": round(prominence, 2),
                }
            )
            last_signal_idx = idx

    return signals


def _std(values: list[float]) -> float:
    if not values:
        return 0.0
    avg = mean(values)
    return (sum((value - avg) ** 2 for value in values) / len(values)) ** 0.5


def _as_datetime(value) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))
