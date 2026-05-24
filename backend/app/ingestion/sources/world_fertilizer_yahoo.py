from __future__ import annotations

from datetime import UTC, datetime
import os
from typing import Any
from urllib.parse import quote

import requests

from app.ingestion.http import DEFAULT_HEADERS
from app.ingestion.world_fertilizer_records import WorldFertilizerObservation, WorldFertilizerScrapeResult


SOURCE = "yahoo_urea_futures_daily"
DEFAULT_SYMBOL = "UME=F"
DEFAULT_RANGE = "5y"
INTERVAL = "1d"
SOURCE_URL = f"https://finance.yahoo.com/quote/{quote(DEFAULT_SYMBOL, safe='')}/history"
CHART_URL_TEMPLATE = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
QUOTE_TYPE = "CME Urea Granular FOB Middle East futures continuous"


class YahooUreaFuturesDailyScraper:
    source = SOURCE
    source_url = SOURCE_URL

    def scrape(self) -> WorldFertilizerScrapeResult:
        symbol = os.getenv("MARKETAI_YAHOO_UREA_SYMBOL", DEFAULT_SYMBOL).strip() or DEFAULT_SYMBOL
        range_value = os.getenv("MARKETAI_YAHOO_UREA_RANGE", DEFAULT_RANGE).strip() or DEFAULT_RANGE
        url = CHART_URL_TEMPLATE.format(symbol=quote(symbol, safe=""))
        response = requests.get(
            url,
            params={
                "range": range_value,
                "interval": INTERVAL,
                "includePrePost": "false",
                "events": "history",
            },
            headers={**DEFAULT_HEADERS, "Accept": "application/json"},
            timeout=45,
        )
        response.raise_for_status()
        observations = parse_yahoo_urea_chart(response.json(), symbol=symbol)
        source_url = f"https://finance.yahoo.com/quote/{quote(symbol, safe='')}/history"
        return WorldFertilizerScrapeResult(source=SOURCE, source_url=source_url, observations=observations)


def parse_yahoo_urea_chart(payload: dict[str, Any], *, symbol: str = DEFAULT_SYMBOL) -> list[WorldFertilizerObservation]:
    result = ((payload.get("chart") or {}).get("result") or [None])[0]
    if not isinstance(result, dict):
        error = (payload.get("chart") or {}).get("error") if isinstance(payload.get("chart"), dict) else None
        raise ValueError(f"Yahoo Finance chart did not return Urea history: {error or 'empty result'}")

    timestamps = result.get("timestamp") or []
    quote = ((result.get("indicators") or {}).get("quote") or [{}])[0]
    opens = quote.get("open") or []
    highs = quote.get("high") or []
    lows = quote.get("low") or []
    closes = quote.get("close") or []
    volumes = quote.get("volume") or []
    meta = result.get("meta") or {}
    source_url = f"https://finance.yahoo.com/quote/{quote_symbol(symbol)}/history"

    observations: list[WorldFertilizerObservation] = []
    for index, timestamp in enumerate(timestamps):
        observed_at = _parse_timestamp(timestamp)
        close = _parse_price(closes[index] if index < len(closes) else None)
        if observed_at is None or close is None:
            continue
        observations.append(
            WorldFertilizerObservation(
                observed_at=observed_at,
                commodity_slug="urea",
                quote_type=QUOTE_TYPE,
                source=SOURCE,
                source_url=source_url,
                price_usd_per_tonne=round(close, 2),
                confidence_score=0.82,
                raw_json={
                    "symbol": symbol,
                    "exchange": meta.get("exchangeName") or meta.get("exchange"),
                    "instrument_type": meta.get("instrumentType"),
                    "open": _safe_index(opens, index),
                    "high": _safe_index(highs, index),
                    "low": _safe_index(lows, index),
                    "close": close,
                    "volume": _safe_index(volumes, index),
                    "usage_note": "Daily Yahoo Finance history is stored for model training/backfill; official monthly anchor remains separate.",
                },
            )
        )
    return sorted(observations, key=lambda observation: observation.observed_at)


def quote_symbol(symbol: str) -> str:
    return quote(symbol, safe="")


def _parse_timestamp(value: Any) -> datetime | None:
    try:
        timestamp = int(value)
    except (TypeError, ValueError):
        return None
    return datetime.fromtimestamp(timestamp, tz=UTC).replace(hour=0, minute=0, second=0, microsecond=0)


def _parse_price(value: Any) -> float | None:
    try:
        price = float(value)
    except (TypeError, ValueError):
        return None
    return price if price > 0 else None


def _safe_index(values: list[Any], index: int) -> Any:
    return values[index] if index < len(values) else None
