from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class InputPriceObservation:
    observed_at: datetime
    product_slug: str
    product_name: str
    product_type: str
    nutrient_profile: str | None
    province: str
    region_name: str | None
    brand: str | None
    seller_name: str | None
    source: str
    source_url: str
    package_price_vnd: float
    package_size_kg: float
    confidence_score: float = 0.86
    data_kind: str = "scraped"


@dataclass(frozen=True)
class InputPriceScrapeResult:
    source: str
    source_url: str
    observations: list[InputPriceObservation]
