from bs4 import BeautifulSoup

from app.ingestion.http import fetch_html
from app.ingestion.parsing import PRICE_RANGE_RE, normalize_space, parse_article_date, parse_price_range
from app.ingestion.records import PriceObservation, ScrapeResult


SOURCE = "Báo Hà Tĩnh (chuẩn vùng)"
URL = "https://baohatinh.vn/tv/gia-sau-rieng-hom-nay-17-3-2026-ri6-va-sau-rieng-thai-di-ngang-suc-mua-van-thap-34595.html"


class BaoHaTinhScraper:
    source = SOURCE
    source_url = URL

    def scrape(self) -> ScrapeResult:
        return self.parse(fetch_html(self.source_url), self.source_url)

    def parse(self, html: str, source_url: str | None = None) -> ScrapeResult:
        url = source_url or self.source_url
        soup = BeautifulSoup(html, "html.parser")
        text = normalize_space(soup.get_text(" "))
        observed_at = parse_article_date(text)
        observations: list[PriceObservation] = []

        regions = {
            "Tây Nam Bộ": ["Tiền Giang", "Cần Thơ", "Đồng Tháp", "Bến Tre", "Vĩnh Long"],
            "Đông Nam Bộ": ["Đồng Nai", "Bình Phước", "Tây Ninh"],
            "Tây Nguyên": ["Đắk Lắk", "Lâm Đồng", "Gia Lai", "Đắk Nông"],
        }
        labels_by_position = [
            ("Ri6", "Loại A"),
            ("Ri6", "Hàng xô"),
            ("Sầu Thái Dona", "Loại A"),
            ("Sầu Thái Dona", "Hàng xô"),
        ]
        region_labels = list(regions.keys())
        detail_start = text.find("Bảng giá sầu riêng hôm nay")
        searchable_text = text[detail_start:] if detail_start != -1 else text

        for region_name, provinces in regions.items():
            region_idx = searchable_text.find(region_name)
            if region_idx == -1:
                continue
            next_region_indexes = [
                idx
                for other in region_labels
                if other != region_name and (idx := searchable_text.find(other, region_idx + 1)) != -1
            ]
            end = min(next_region_indexes) if next_region_indexes else region_idx + 700
            segment = searchable_text[region_idx:end]
            ranges = [parse_price_range(match.group(0)) for match in PRICE_RANGE_RE.finditer(segment)]
            prices = [price for price in ranges if price is not None][:4]

            for province in provinces:
                for (variety, grade), price in zip(labels_by_position, prices, strict=False):
                    observations.append(
                        PriceObservation(
                            observed_at=observed_at,
                            variety_name=variety,
                            quality_grade=grade,
                            region_name=region_name,
                            province=province,
                            source=self.source,
                            source_url=url,
                            min_price_vnd=price[0],
                            max_price_vnd=price[1],
                        )
                    )
        return ScrapeResult(self.source, url, observations)
