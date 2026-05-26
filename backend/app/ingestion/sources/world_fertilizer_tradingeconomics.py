from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
import os
from typing import Any

import requests

from app.ingestion.http import request_headers
from app.ingestion.world_fertilizer_records import WorldFertilizerObservation, WorldFertilizerScrapeResult


SOURCE = "tradingeconomics_urea_daily"
SOURCE_URL = "https://tradingeconomics.com/commodity/urea"
API_URL = "https://api.tradingeconomics.com/markets/historical/urea:com"
QUOTE_TYPE = "Trading Economics Urea benchmark"
DEFAULT_BACKFILL_START = date(2019, 1, 1)
MAX_REQUEST_DAYS = 365


class TradingEconomicsUreaDailyScraper:
    source = SOURCE
    source_url = SOURCE_URL

    def scrape(self) -> WorldFertilizerScrapeResult:
        api_key = os.getenv("MARKETAI_TRADING_ECONOMICS_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError(
                "MARKETAI_TRADING_ECONOMICS_API_KEY is not configured; "
                "daily Urea history was not requested from Trading Economics."
            )

        start_date = _backfill_start_date()
        end_date = datetime.now(UTC).date()
        headers = request_headers({"Accept": "application/json", "Authorization": api_key})
        observations: list[WorldFertilizerObservation] = []
        for window_start, window_end in _request_windows(start_date, end_date):
            response = requests.get(
                API_URL,
                params={"d1": window_start.isoformat(), "d2": window_end.isoformat(), "f": "json"},
                headers=headers,
                timeout=60,
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, list):
                raise ValueError("Unexpected Trading Economics API response for Urea historical data.")
            observations.extend(parse_trading_economics_urea_history(payload))
        observations.sort(key=lambda observation: observation.observed_at)
        return WorldFertilizerScrapeResult(source=SOURCE, source_url=SOURCE_URL, observations=observations)


def parse_trading_economics_urea_history(payload: list[dict[str, Any]]) -> list[WorldFertilizerObservation]:
    observations: list[WorldFertilizerObservation] = []
    for item in payload:
        observed_at = _parse_observed_at(item.get("Date"))
        price = _parse_price(item.get("Close"))
        if observed_at is None or price is None:
            continue
        observations.append(
            WorldFertilizerObservation(
                observed_at=observed_at,
                commodity_slug="urea",
                quote_type=QUOTE_TYPE,
                source=SOURCE,
                source_url=SOURCE_URL,
                price_usd_per_tonne=round(price, 2),
                confidence_score=0.92,
                raw_json={
                    "symbol": item.get("Symbol", "UREA:COM"),
                    "open": item.get("Open"),
                    "high": item.get("High"),
                    "low": item.get("Low"),
                    "close": item.get("Close"),
                },
            )
        )
    return sorted(observations, key=lambda observation: observation.observed_at)


def _backfill_start_date() -> date:
    configured = os.getenv("MARKETAI_TRADING_ECONOMICS_UREA_BACKFILL_START", "").strip()
    if not configured:
        return DEFAULT_BACKFILL_START
    try:
        return date.fromisoformat(configured)
    except ValueError as exc:
        raise ValueError("MARKETAI_TRADING_ECONOMICS_UREA_BACKFILL_START must be YYYY-MM-DD.") from exc


def _request_windows(start_date: date, end_date: date) -> list[tuple[date, date]]:
    windows: list[tuple[date, date]] = []
    cursor = start_date
    while cursor <= end_date:
        window_end = min(cursor + timedelta(days=MAX_REQUEST_DAYS - 1), end_date)
        windows.append((cursor, window_end))
        cursor = window_end + timedelta(days=1)
    return windows


def _parse_observed_at(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    for format_string in ("%d/%m/%Y", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.strptime(text, format_string).replace(tzinfo=UTC)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:
        return None


def _parse_price(value: Any) -> float | None:
    try:
        price = float(value)
    except (TypeError, ValueError):
        return None
    return price if price > 0 else None
