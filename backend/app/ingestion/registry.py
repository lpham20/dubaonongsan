from app.ingestion.sources.banggianongsan import BangGiaNongSanScraper
from app.ingestion.sources.baohatinh import BaoHaTinhScraper
from app.ingestion.sources.baonghean import BaoNgheAnScraper
from app.ingestion.sources.coffee_market import CoffeeMarketScraper
from app.ingestion.sources.socongthuong_daklak import SoCongThuongDakLakScraper
from app.ingestion.sources.vietnamvn import VietnamVnScraper


SCRAPERS = {
    "banggianongsan": BangGiaNongSanScraper,
    "baohatinh": BaoHaTinhScraper,
    "baonghean": BaoNgheAnScraper,
    "coffee_market": CoffeeMarketScraper,
    "socongthuong_daklak": SoCongThuongDakLakScraper,
    "vietnamvn": VietnamVnScraper,
}


def build_scrapers(source: str | None = None):
    if source:
        if source not in SCRAPERS:
            raise ValueError(f"Unknown scraper source: {source}")
        return [SCRAPERS[source]()]
    return [factory() for factory in SCRAPERS.values()]
