from __future__ import annotations

from app.ingestion.sources.world_fertilizer_vietnambiz import VietnamBizWorldFertilizerScraper
from app.ingestion.sources.world_fertilizer_worldbank import WorldBankPinkSheetScraper


WORLD_FERTILIZER_SCRAPERS = {
    "worldbank_pinksheet": WorldBankPinkSheetScraper,
    "vietnambiz_world_fertilizer": VietnamBizWorldFertilizerScraper,
}


def build_world_fertilizer_scrapers(source: str | None = None):
    if source:
        scraper_cls = WORLD_FERTILIZER_SCRAPERS.get(source)
        if scraper_cls is None:
            raise ValueError(f"Unknown world fertilizer scraper source: {source}")
        return [scraper_cls()]
    return [scraper_cls() for scraper_cls in WORLD_FERTILIZER_SCRAPERS.values()]
