from __future__ import annotations

from app.ingestion.sources.world_fertilizer_tradingeconomics import TradingEconomicsUreaDailyScraper
from app.ingestion.sources.world_fertilizer_vietnambiz import VietnamBizWorldFertilizerScraper
from app.ingestion.sources.world_fertilizer_worldbank import WorldBankPinkSheetScraper
from app.ingestion.sources.world_fertilizer_yahoo import YahooUreaFuturesDailyScraper


WORLD_FERTILIZER_SCRAPERS = {
    "worldbank_pinksheet": WorldBankPinkSheetScraper,
    "vietnambiz_world_fertilizer": VietnamBizWorldFertilizerScraper,
    "tradingeconomics_urea_daily": TradingEconomicsUreaDailyScraper,
    "yahoo_urea_futures_daily": YahooUreaFuturesDailyScraper,
}

DEFAULT_WORLD_FERTILIZER_SOURCES = ("worldbank_pinksheet", "vietnambiz_world_fertilizer")


def build_world_fertilizer_scrapers(source: str | None = None):
    if source:
        scraper_cls = WORLD_FERTILIZER_SCRAPERS.get(source)
        if scraper_cls is None:
            raise ValueError(f"Unknown world fertilizer scraper source: {source}")
        return [scraper_cls()]
    return [WORLD_FERTILIZER_SCRAPERS[source_key]() for source_key in DEFAULT_WORLD_FERTILIZER_SOURCES]
