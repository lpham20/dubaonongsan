from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class PriceObservation:
    observed_at: datetime
    variety_name: str
    quality_grade: str
    region_name: str
    province: str | None
    source: str
    source_url: str
    min_price_vnd: float
    max_price_vnd: float
    crop_type: str = "sau_rieng"
    volume_traded_tons: float | None = None


@dataclass(frozen=True)
class ScrapeResult:
    source: str
    source_url: str
    observations: list[PriceObservation]
