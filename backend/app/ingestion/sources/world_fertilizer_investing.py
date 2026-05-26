from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
import re
from typing import Any

import requests

from app.ingestion.http import request_headers
from app.ingestion.world_fertilizer_records import WorldFertilizerObservation, WorldFertilizerScrapeResult


SOURCE = "investing_urea_current"
SOURCE_URL = "https://vn.investing.com/commodities/urea-granular-fob-middle-east-futures"
READER_URL = f"https://r.jina.ai/{SOURCE_URL}"
QUOTE_TYPE = "Investing Urea Granular FOB Middle East futures current"


class InvestingUreaCurrentScraper:
    source = SOURCE
    source_url = SOURCE_URL

    def scrape(self) -> WorldFertilizerScrapeResult:
        response = requests.get(
            READER_URL,
            headers=request_headers({"Accept": "text/plain, text/markdown, */*"}),
            timeout=45,
        )
        response.raise_for_status()
        observation = parse_investing_urea_current(response.text, fetched_at=datetime.now(UTC))
        return WorldFertilizerScrapeResult(source=SOURCE, source_url=SOURCE_URL, observations=[observation])


def parse_investing_urea_current(markdown: str, *, fetched_at: datetime) -> WorldFertilizerObservation:
    lines = [line.strip() for line in markdown.splitlines() if line.strip()]
    heading_index = _find_line(lines, "UMEc1")
    if heading_index is None:
        raise ValueError("Investing Urea page did not contain UMEc1.")

    search_window = lines[heading_index : heading_index + 40]
    price_index, price = _first_price(search_window)
    if price_index is None or price is None:
        raise ValueError("Investing Urea page did not contain a current price.")

    status_line = _first_status_line(search_window[price_index + 1 :])
    observed_at = _parse_observed_date(status_line, fetched_at=fetched_at)
    change_value, change_pct = _parse_change(search_window[price_index + 1] if price_index + 1 < len(search_window) else "")

    return WorldFertilizerObservation(
        observed_at=observed_at,
        commodity_slug="urea",
        quote_type=QUOTE_TYPE,
        source=SOURCE,
        source_url=SOURCE_URL,
        price_usd_per_tonne=round(price, 2),
        confidence_score=0.9,
        raw_json={
            "symbol": "UMEc1",
            "display_source": SOURCE_URL,
            "reader_url": READER_URL,
            "status_line": status_line,
            "change": change_value,
            "change_pct": change_pct,
        },
    )


def _find_line(lines: list[str], needle: str) -> int | None:
    needle_lower = needle.lower()
    for index, line in enumerate(lines):
        if needle_lower in line.lower():
            return index
    return None


def _first_price(lines: list[str]) -> tuple[int | None, float | None]:
    for index, line in enumerate(lines):
        value = _parse_decimal(line)
        if value is not None and 100 <= value <= 5000:
            return index, value
    return None, None


def _first_status_line(lines: list[str]) -> str | None:
    status_markers = ("dong cua", "đóng cửa", "delayed", "tri hoan", "trì hoãn", "market closed", "du lieu", "dữ liệu")
    for line in lines:
        normalized = _strip_accents(line.lower())
        if "·" in line and any(marker in normalized for marker in status_markers):
            return line
    for line in lines:
        if re.search(r"\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b", line):
            return line
    return None


def _parse_observed_date(status_line: str | None, *, fetched_at: datetime) -> datetime:
    if status_line:
        match = re.search(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b", status_line)
        if match:
            day = int(match.group(1))
            month = int(match.group(2))
            raw_year = match.group(3)
            year = _normalize_year(raw_year, fetched_at.date()) if raw_year else fetched_at.year
            parsed = date(year, month, day)
            if parsed > fetched_at.date() + _ONE_WEEK:
                parsed = date(year - 1, month, day)
            return datetime(parsed.year, parsed.month, parsed.day, tzinfo=UTC)
    return datetime(fetched_at.year, fetched_at.month, fetched_at.day, tzinfo=UTC)


_ONE_WEEK = timedelta(days=7)


def _normalize_year(raw_year: str | None, today: date) -> int:
    if not raw_year:
        return today.year
    year = int(raw_year)
    if year < 100:
        return 2000 + year
    return year


def _parse_change(line: str) -> tuple[float | None, float | None]:
    match = re.search(r"([-+]?\d+(?:[.,]\d+)?)\s*\(\s*([-+]?\d+(?:[.,]\d+)?)%\s*\)", line)
    if not match:
        return None, None
    return _parse_decimal(match.group(1)), _parse_decimal(match.group(2))


def _parse_decimal(value: Any) -> float | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not re.fullmatch(r"[-+]?\d{1,4}(?:[.,]\d{1,4})?", text):
        return None
    try:
        return float(text.replace(",", "."))
    except ValueError:
        return None


def _strip_accents(value: str) -> str:
    replacements = {
        "đ": "d",
        "á": "a",
        "à": "a",
        "ả": "a",
        "ã": "a",
        "ạ": "a",
        "ă": "a",
        "ắ": "a",
        "ằ": "a",
        "ẳ": "a",
        "ẵ": "a",
        "ặ": "a",
        "â": "a",
        "ấ": "a",
        "ầ": "a",
        "ẩ": "a",
        "ẫ": "a",
        "ậ": "a",
        "é": "e",
        "è": "e",
        "ẻ": "e",
        "ẽ": "e",
        "ẹ": "e",
        "ê": "e",
        "ế": "e",
        "ề": "e",
        "ể": "e",
        "ễ": "e",
        "ệ": "e",
        "í": "i",
        "ì": "i",
        "ỉ": "i",
        "ĩ": "i",
        "ị": "i",
        "ó": "o",
        "ò": "o",
        "ỏ": "o",
        "õ": "o",
        "ọ": "o",
        "ô": "o",
        "ố": "o",
        "ồ": "o",
        "ổ": "o",
        "ỗ": "o",
        "ộ": "o",
        "ơ": "o",
        "ớ": "o",
        "ờ": "o",
        "ở": "o",
        "ỡ": "o",
        "ợ": "o",
        "ú": "u",
        "ù": "u",
        "ủ": "u",
        "ũ": "u",
        "ụ": "u",
        "ư": "u",
        "ứ": "u",
        "ừ": "u",
        "ử": "u",
        "ữ": "u",
        "ự": "u",
        "ý": "y",
        "ỳ": "y",
        "ỷ": "y",
        "ỹ": "y",
        "ỵ": "y",
    }
    return "".join(replacements.get(ch, ch) for ch in value)
