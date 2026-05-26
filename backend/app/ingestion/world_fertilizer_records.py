from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class WorldFertilizerObservation:
    observed_at: datetime
    commodity_slug: str
    quote_type: str
    source: str
    source_url: str | None
    price_usd_per_tonne: float
    confidence_score: float
    raw_json: dict[str, Any] | None = None


@dataclass(slots=True)
class WorldFertilizerScrapeResult:
    source: str
    source_url: str
    observations: list[WorldFertilizerObservation]
