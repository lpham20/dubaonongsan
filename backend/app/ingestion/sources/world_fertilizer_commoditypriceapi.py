from __future__ import annotations

from datetime import UTC, datetime
import json
import re
from typing import Any

import requests

from app.ingestion.http import request_headers
from app.ingestion.world_fertilizer_records import WorldFertilizerObservation, WorldFertilizerScrapeResult


SOURCE = "commoditypriceapi_urea_public_1y"
SOURCE_URL = "https://commoditypriceapi.com/tools/urea/prices"
QUOTE_TYPE = "CommodityPriceAPI Urea benchmark public 1Y"
SYMBOL = "UREA"
PUBLIC_HISTORY_DAYS = 365
NEXT_ROUTER_STATE_TREE = (
    "%5B%22%22%2C%7B%22children%22%3A%5B%5B%22symbol%22%2C%22urea%22%2C%22d%22%2Cnull%5D%2C"
    "%7B%22children%22%3A%5B%22prices%22%2C%7B%22children%22%3A%5B%22__PAGE__%22%2C%7B%7D%2C"
    "null%2Cnull%2C0%5D%7D%2Cnull%2Cnull%2C0%5D%7D%2Cnull%2Cnull%2C0%5D%7D%2Cnull%2Cnull%2C16%5D"
)


class CommodityPriceApiUreaPublicScraper:
    source = SOURCE
    source_url = SOURCE_URL

    def scrape(self) -> WorldFertilizerScrapeResult:
        page_response = requests.get(
            SOURCE_URL,
            headers=request_headers({"Accept": "text/html"}),
            timeout=45,
        )
        page_response.raise_for_status()
        page_html = page_response.text
        action_id = parse_next_action_id(page_html)

        response = requests.post(
            SOURCE_URL,
            data=json.dumps([PUBLIC_HISTORY_DAYS, SYMBOL]),
            headers=request_headers({
                "Accept": "text/x-component",
                "Content-Type": "text/plain;charset=UTF-8",
                "Next-Action": action_id,
                "Next-Router-State-Tree": NEXT_ROUTER_STATE_TREE,
                "Referer": SOURCE_URL,
            }),
            timeout=60,
        )
        response.raise_for_status()
        payload = parse_next_action_payload(response.text)
        observations = parse_commoditypriceapi_urea_history(payload)

        latest_quote = parse_public_latest_quote(page_html)
        if latest_quote is not None:
            observations = _upsert_latest_quote(observations, latest_quote)

        return WorldFertilizerScrapeResult(source=SOURCE, source_url=SOURCE_URL, observations=observations)


def parse_next_action_id(html: str) -> str:
    slot_match = re.search(r'timeSeriesData\\?":\\?"\$h(?P<slot>\d+)\\?"', html)
    candidates = re.findall(r'(?P<slot>\d+):\{\\"id\\":\\"(?P<id>[a-f0-9]{32,})\\",\\"bound\\":null\}', html)
    candidates.extend(re.findall(r'(?P<slot>\d+):\{"id":"(?P<id>[a-f0-9]{32,})","bound":null\}', html))
    if not candidates:
        raise ValueError("CommodityPriceAPI page did not expose a Next action id for Urea time-series data.")
    if slot_match:
        wanted = slot_match.group("slot")
        for slot, action_id in candidates:
            if slot == wanted:
                return action_id
    return candidates[0][1]


def parse_next_action_payload(text: str) -> dict[str, Any]:
    for line in text.splitlines():
        if line.startswith("1:{"):
            payload = json.loads(line[2:])
            if not isinstance(payload, dict):
                break
            return payload
        if line.startswith('1:"$undefined"') or line.startswith("1:E"):
            break
    raise ValueError("CommodityPriceAPI public time-series action did not return a usable payload.")


def parse_commoditypriceapi_urea_history(payload: dict[str, Any]) -> list[WorldFertilizerObservation]:
    rates = payload.get("rates")
    if not isinstance(rates, dict):
        raise ValueError("CommodityPriceAPI Urea payload did not include rates.")

    observations: list[WorldFertilizerObservation] = []
    for date_text, symbols in rates.items():
        if not isinstance(symbols, dict):
            continue
        item = symbols.get(SYMBOL)
        if not isinstance(item, dict):
            continue
        observed_at = _parse_date(date_text)
        close = _parse_price(item.get("close"))
        if observed_at is None or close is None:
            continue
        observations.append(
            WorldFertilizerObservation(
                observed_at=observed_at,
                commodity_slug="urea",
                quote_type=QUOTE_TYPE,
                source=SOURCE,
                source_url=SOURCE_URL,
                price_usd_per_tonne=round(close, 2),
                confidence_score=0.94,
                raw_json={
                    "symbol": SYMBOL,
                    "open": item.get("open"),
                    "high": item.get("high"),
                    "low": item.get("low"),
                    "close": close,
                    "start_date": payload.get("startDate"),
                    "end_date": payload.get("endDate"),
                    "usage_note": "Public 1Y Urea benchmark from CommodityPriceAPI tools page; used as canonical daily world Urea signal.",
                },
            )
        )
    return sorted(observations, key=lambda observation: observation.observed_at)


def parse_public_latest_quote(html: str) -> WorldFertilizerObservation | None:
    match = re.search(
        r'\\"prices\\":\{\\"success\\":true,\\"timestamp\\":(?P<timestamp>\d+),\\"rates\\":\{\\"UREA\\":(?P<price>[0-9.]+)\}',
        html,
    )
    if match is None:
        return None
    observed_at = datetime.fromtimestamp(int(match.group("timestamp")), tz=UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    price = _parse_price(match.group("price"))
    if price is None:
        return None
    return WorldFertilizerObservation(
        observed_at=observed_at,
        commodity_slug="urea",
        quote_type=QUOTE_TYPE,
        source=SOURCE,
        source_url=SOURCE_URL,
        price_usd_per_tonne=round(price, 2),
        confidence_score=0.95,
        raw_json={
            "symbol": SYMBOL,
            "close": price,
            "timestamp": int(match.group("timestamp")),
            "usage_note": "Latest public Urea quote embedded in CommodityPriceAPI tools page.",
        },
    )


def _upsert_latest_quote(
    observations: list[WorldFertilizerObservation],
    latest_quote: WorldFertilizerObservation,
) -> list[WorldFertilizerObservation]:
    by_day = {item.observed_at.date(): item for item in observations}
    by_day[latest_quote.observed_at.date()] = latest_quote
    return sorted(by_day.values(), key=lambda observation: observation.observed_at)


def _parse_date(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.strptime(value.strip(), "%Y-%m-%d")
    except ValueError:
        return None
    return parsed.replace(tzinfo=UTC)


def _parse_price(value: Any) -> float | None:
    try:
        price = float(value)
    except (TypeError, ValueError):
        return None
    return price if price > 0 else None
