from bs4 import BeautifulSoup

from app.ingestion.http import fetch_html
from app.ingestion.parsing import (
    PRICE_RANGE_RE,
    classify_variety_and_grade,
    normalize_space,
    parse_article_date,
    parse_price_range,
)
from app.ingestion.records import PriceObservation, ScrapeResult


SOURCE = "baonghean.vn"
URL = "https://baonghean.vn/gia-sau-rieng-hom-nay-17-4-2026-ri6-giu-muc-60-000-dong-10333229.html"


class BaoNgheAnScraper:
    source = SOURCE
    source_url = URL

    def scrape(self) -> ScrapeResult:
        return self.parse(fetch_html(self.source_url))

    def parse(self, html: str) -> ScrapeResult:
        soup = BeautifulSoup(html, "html.parser")
        text = normalize_space(soup.get_text(" "))
        observed_at = parse_article_date(text)
        rows = self._parse_region_matrix(text, observed_at)
        return ScrapeResult(self.source, self.source_url, rows)

    def _parse_region_matrix(self, text: str, observed_at):
        rows = []
        region_aliases = {
            "Tây Nam Bộ": ("Tây Nam Bộ", None),
            "Đông Nam Bộ": ("Đông Nam Bộ", None),
            "Tây Nguyên": ("Tây Nguyên", None),
        }
        labels_by_position = [
            ("Ri6", "Loại A"),
            ("Ri6", "Hàng xô"),
            ("Sầu Thái Dona", "Loại A"),
            ("Sầu Thái Dona", "Hàng xô"),
        ]
        region_labels = list(region_aliases.keys())
        detail_start = text.find("Chi tiết giá sầu riêng")
        searchable_text = text[detail_start:] if detail_start != -1 else text

        for region_label, (region_name, province) in region_aliases.items():
            region_idx = searchable_text.find(region_label)
            if region_idx == -1:
                continue
            next_region_indexes = [
                idx
                for other in region_labels
                if other != region_label and (idx := searchable_text.find(other, region_idx + 1)) != -1
            ]
            end = min(next_region_indexes) if next_region_indexes else region_idx + 700
            segment = searchable_text[region_idx:end]
            ranges = [parse_price_range(match.group(0)) for match in PRICE_RANGE_RE.finditer(segment)]
            ranges = [price for price in ranges if price is not None]
            for (variety, grade), price in zip(labels_by_position, ranges[:4], strict=False):
                rows.append(
                    PriceObservation(
                        observed_at=observed_at,
                        variety_name=variety,
                        quality_grade=grade,
                        region_name=region_name,
                        province=province,
                        source=self.source,
                        source_url=self.source_url,
                        min_price_vnd=price[0],
                        max_price_vnd=price[1],
                    )
                )
        return rows
