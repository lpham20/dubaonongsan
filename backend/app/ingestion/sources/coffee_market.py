from datetime import UTC, datetime
import re

from bs4 import BeautifulSoup

from app.ingestion.http import fetch_html
from app.ingestion.parsing import normalize_space, parse_article_date, strip_accents
from app.ingestion.records import PriceObservation, ScrapeResult


SOURCE = "Tổng hợp giá cà phê công khai"
URLS = [
    "https://baonghean.vn/gia-ca-phe-hom-nay-20-4-2026-tang-dong-loat-300-dong-10333605.html",
    "https://www.vietnam.vn/gia-ca-phe-hom-nay-12-3-2026-dong-loat-lao-doc",
    "https://socongthuong.daklak.gov.vn/vi/news/thong-tin-gia-ca-thi-truong/bang-gia-nong-san-ngay-24-3-2026-6196.html",
]

PROVINCE_REGION = {
    "Đắk Lắk": "Tây Nguyên",
    "Đắk Nông": "Tây Nguyên",
    "Lâm Đồng": "Tây Nguyên",
    "Gia Lai": "Tây Nguyên",
    "Kon Tum": "Tây Nguyên",
    "Bình Phước": "Đông Nam Bộ",
    "Đồng Nai": "Đông Nam Bộ",
    "Bà Rịa - Vũng Tàu": "Đông Nam Bộ",
    "Sơn La": "Tây Bắc",
    "Điện Biên": "Tây Bắc",
}

class CoffeeMarketScraper:
    source = SOURCE
    source_url = ", ".join(URLS)

    def scrape(self) -> ScrapeResult:
        texts = []
        for url in URLS:
            try:
                texts.append(self._fetch_text(url))
            except Exception:
                continue
        return self.parse(" ".join(texts), self.source_url)

    def parse(self, html: str, source_url: str | None = None) -> ScrapeResult:
        url = source_url or self.source_url
        soup = BeautifulSoup(html, "html.parser")
        text = normalize_space(soup.get_text(" "))
        folded = strip_accents(text).lower()
        observed_at = parse_article_date(text, default=datetime(2026, 3, 24, tzinfo=UTC))
        province_prices = self._extract_province_prices(folded)

        observations: list[PriceObservation] = []
        for province, base_price in province_prices.items():
            region = PROVINCE_REGION.get(province)
            if not region:
                continue
            observations.append(
                PriceObservation(
                    observed_at=observed_at,
                    variety_name="Cà phê tổng hợp",
                    quality_grade="Tổng hợp",
                    region_name=region,
                    province=province,
                    source=self.source,
                    source_url=url,
                    min_price_vnd=base_price,
                    max_price_vnd=base_price,
                    crop_type="ca_phe",
                )
            )
        return ScrapeResult(self.source, url, observations)

    @staticmethod
    def _fetch_text(url: str) -> str:
        return BeautifulSoup(fetch_html(url), "html.parser").get_text(" ")

    @staticmethod
    def _extract_province_prices(folded_text: str) -> dict[str, float]:
        prices: dict[str, float] = {}
        aliases = {
            "Đắk Lắk": ["dak lak", "daklak"],
            "Đắk Nông": ["dak nong", "daknong"],
            "Lâm Đồng": ["lam dong"],
            "Gia Lai": ["gia lai"],
            "Kon Tum": ["kon tum"],
            "Bình Phước": ["binh phuoc"],
            "Đồng Nai": ["dong nai"],
            "Bà Rịa - Vũng Tàu": ["ba ria", "vung tau"],
            "Sơn La": ["son la"],
            "Điện Biên": ["dien bien"],
        }
        for province, province_aliases in aliases.items():
            for alias in province_aliases:
                match = re.search(rf"{alias}.{{0,80}}?(\d{{2,3}}[.,]\d{{3}}|\d{{5,6}})", folded_text)
                if not match:
                    continue
                raw = re.sub(r"\D", "", match.group(1))
                value = float(raw)
                if value < 1000:
                    value *= 1000
                if 50000 <= value <= 250000:
                    prices[province] = value
                    break
        return prices
