from __future__ import annotations

from collections import defaultdict
import csv
from datetime import datetime
from pathlib import Path
from typing import Any


NUMERIC_COLUMNS = (
    "region_id",
    "variety_id",
    "min_price_vnd",
    "max_price_vnd",
    "volume_traded_tons",
    "temp_max_celsius",
    "precipitation_mm",
    "maturity_index",
)


def load_snapshot(path: str | Path, crop_type: str | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for raw in reader:
            crop = str(raw.get("crop_type") or "").strip()
            if crop_type and crop != crop_type:
                continue
            row: dict[str, Any] = dict(raw)
            row["crop_type"] = crop
            row["timestamp"] = _parse_datetime(raw.get("timestamp") or raw.get("record_timestamp"))
            for column in NUMERIC_COLUMNS:
                row[column] = _float_or_none(raw.get(column))
            if row.get("max_price_vnd") and row.get("region_id") and row.get("variety_id") and row.get("timestamp"):
                rows.append(row)
    rows.sort(key=lambda item: (item["crop_type"], int(item["region_id"]), int(item["variety_id"]), item["timestamp"]))
    return rows


def group_series(rows: list[dict[str, Any]]) -> dict[tuple[int, int], list[dict[str, Any]]]:
    grouped: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(int(row["region_id"]), int(row["variety_id"]))].append(row)
    for key in list(grouped):
        grouped[key] = _fill_forward(grouped[key])
    return grouped


def _fill_forward(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    numeric = ("min_price_vnd", "max_price_vnd", "volume_traded_tons", "temp_max_celsius", "precipitation_mm", "maturity_index")
    result = [dict(row) for row in rows]
    last_seen: dict[str, Any] = {}
    for row in result:
        for key in numeric:
            if row.get(key) is None:
                row[key] = last_seen.get(key)
            else:
                last_seen[key] = row[key]
    fallback: dict[str, Any] = {}
    for key in numeric:
        fallback[key] = next((row.get(key) for row in result if row.get(key) is not None), 0.0)
    for row in result:
        for key in numeric:
            if row.get(key) is None:
                row[key] = fallback[key]
    return result


def _float_or_none(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if not value:
        return None
    text = str(value).replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        try:
            return datetime.strptime(str(value)[:19], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None
