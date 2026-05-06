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


SOURCE = "banggianongsan.com"
URL = "https://banggianongsan.com/bang-gia-sau-rieng/"


class BangGiaNongSanScraper:
    source = SOURCE
    source_url = URL

    def scrape(self) -> ScrapeResult:
        return self.parse(fetch_html(self.source_url))

    def parse(self, html: str) -> ScrapeResult:
        soup = BeautifulSoup(html, "html.parser")
        text = normalize_space(soup.get_text(" "))
        observed_at = parse_article_date(text)
        observations: list[PriceObservation] = []
        observations.extend(self._parse_variety_table(text, observed_at))
        observations.extend(self._parse_province_prices(text, observed_at))
        observations.extend(self._parse_market_prices(text, observed_at))
        return ScrapeResult(self.source, self.source_url, observations)

    def _parse_variety_table(self, text: str, observed_at):
        rows = []
        start = text.find("Bảng giá chi tiết")
        end = text.find("So sánh nhanh", start)
        segment = text[start:end] if start != -1 and end != -1 else text
        markers = [
            "Sầu riêng Ri6 A",
            "Sầu riêng Ri6 B",
            "Sầu riêng Thái VIP A",
            "Sầu riêng Thái VIP B",
            "Sầu riêng Thái A",
            "Sầu riêng Thái B",
            "Sầu riêng Musang King A",
            "Sầu riêng Chuồng Bò A",
            "Sầu riêng Ri6 C",
            "Sầu riêng Musang King B",
        ]
        for marker in markers:
            idx = segment.find(marker)
            if idx == -1:
                continue
            window = segment[idx : idx + 180]
            price = parse_price_range(window)
            if not price:
                continue
            variety, grade = classify_variety_and_grade(marker)
            rows.append(
                PriceObservation(
                    observed_at=observed_at,
                    variety_name=variety,
                    quality_grade=grade,
                    region_name="Thị trường Việt Nam",
                    province=None,
                    source=self.source,
                    source_url=self.source_url,
                    min_price_vnd=price[0],
                    max_price_vnd=price[1],
                )
            )
        return rows

    def _parse_province_prices(self, text: str, observed_at):
        rows = []
        provinces = ["Cần Thơ", "Tiền Giang", "Đồng Tháp", "Bến Tre", "Vĩnh Long"]
        for province in provinces:
            idx = text.find(f"{province}:")
            if idx == -1:
                continue
            window = text[idx : idx + 90]
            price = parse_price_range(window)
            if not price:
                continue
            rows.append(
                PriceObservation(
                    observed_at=observed_at,
                    variety_name="Sầu riêng tổng hợp",
                    quality_grade="Tổng hợp",
                    region_name="Tây Nam Bộ",
                    province=province,
                    source=self.source,
                    source_url=self.source_url,
                    min_price_vnd=price[0],
                    max_price_vnd=price[1],
                )
            )
        return rows

    def _parse_market_prices(self, text: str, observed_at):
        rows = []
        markets = ["Thủ Đức", "Bình Điền", "Bến Thành"]
        for market in markets:
            idx = text.find(market)
            if idx == -1:
                continue
            window = text[idx : idx + 160]
            ranges = [parse_price_range(match.group(0)) for match in PRICE_RANGE_RE.finditer(window)]
            ranges = [price for price in ranges if price is not None][:2]
            for variety_name, price in zip(["Ri6", "Sầu Thái Monthong"], ranges, strict=False):
                rows.append(
                    PriceObservation(
                        observed_at=observed_at,
                        variety_name=variety_name,
                        quality_grade="Giá chợ",
                        region_name="Chợ đầu mối TP.HCM",
                        province=market,
                        source=self.source,
                        source_url=self.source_url,
                        min_price_vnd=price[0],
                        max_price_vnd=price[1],
                    )
                )
        return rows
