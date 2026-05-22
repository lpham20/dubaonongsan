from app.ingestion.sources.fertilizer_public_sources import (
    CoffeeMarketFertilizerPriceScraper,
    SFarmOrganicFertilizerPriceScraper,
    TheFinancesFertilizerPriceScraper,
    VinacamFertilizerPriceScraper,
)
from app.ingestion.sources.fertilizer_vietnga import VietNgaFertilizerPriceScraper


INPUT_PRICE_SCRAPERS = {
    "vietnga_fertilizer": VietNgaFertilizerPriceScraper,
    "vinacam_fertilizer": VinacamFertilizerPriceScraper,
    "thefinances_fertilizer": TheFinancesFertilizerPriceScraper,
    "sfarm_organic_fertilizer": SFarmOrganicFertilizerPriceScraper,
    "coffee_market_fertilizer": CoffeeMarketFertilizerPriceScraper,
}


def build_input_price_scrapers(source: str | None = None):
    if source:
        if source not in INPUT_PRICE_SCRAPERS:
            raise ValueError(f"Unknown input price scraper source: {source}")
        return [INPUT_PRICE_SCRAPERS[source]()]
    return [factory() for factory in INPUT_PRICE_SCRAPERS.values()]
