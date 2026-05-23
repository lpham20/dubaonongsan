from app.ingestion.sources.banggianongsan import BangGiaNongSanScraper
from app.ingestion.sources.baohatinh import BaoHaTinhScraper
from app.ingestion.sources.baonghean import BaoNgheAnScraper
from app.ingestion.sources.coffee_market import CoffeeMarketScraper
from app.ingestion.sources.socongthuong_daklak import SoCongThuongDakLakHistoryScraper, SoCongThuongDakLakScraper
from app.ingestion.sources.vietnamvn import VietnamVnScraper


SCRAPERS = {
    "banggianongsan": BangGiaNongSanScraper,
    "baohatinh": BaoHaTinhScraper,
    "baonghean": BaoNgheAnScraper,
    "coffee_market": CoffeeMarketScraper,
    "socongthuong_daklak": SoCongThuongDakLakScraper,
    "socongthuong_daklak_history": SoCongThuongDakLakHistoryScraper,
    "vietnamvn": VietnamVnScraper,
}

DISABLED_SCRAPERS = {
    # These sources currently return stale historical prices while the scraper
    # technically succeeds. Keep them out of scheduled runs until their parser
    # or upstream feed is verified.
    "baohatinh",
    "vietnamvn",
}

MANUAL_ONLY_SCRAPERS = {"socongthuong_daklak_history"}


def build_scrapers(source: str | None = None):
    if source:
        if source not in SCRAPERS:
            raise ValueError(f"Unknown scraper source: {source}")
        if source in DISABLED_SCRAPERS:
            raise ValueError(f"Scraper source is disabled: {source}")
        return [SCRAPERS[source]()]
    return [
        factory()
        for name, factory in SCRAPERS.items()
        if name not in DISABLED_SCRAPERS and name not in MANUAL_ONLY_SCRAPERS
    ]
