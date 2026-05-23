import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.ingestion.http import fetch_html
from app.ingestion.parsing import normalize_space, parse_article_date, parse_price_range, strip_accents
from app.ingestion.records import PriceObservation, ScrapeResult


SOURCE = "Sở Công Thương Đắk Lắk"
URLS = [
    "https://socongthuong.daklak.gov.vn/vi/news/thong-tin-gia-ca-thi-truong/bang-gia-nong-san-ngay-23-4-2026-6247.html",
    "https://socongthuong.daklak.gov.vn/vi/news/thong-tin-gia-ca-thi-truong/bang-gia-nong-san-ngay-8-4-2026-6220.html",
    "https://socongthuong.daklak.gov.vn/vi/news/thong-tin-gia-ca-thi-truong/bang-gia-nong-san-ngay-01-4-2026-6209.html",
    "https://socongthuong.daklak.gov.vn/vi/news/thong-tin-gia-ca-thi-truong/bang-gia-nong-san-ngay-26-3-2026-6202.html",
]

HISTORICAL_URLS = [
    "https://socongthuong.daklak.gov.vn/vi/news/thong-tin-gia-ca-thi-truong/bang-gia-nong-san-ngay-12-02-2026-6151.html",
    "https://socongthuong.daklak.gov.vn/vi/news/thong-tin-gia-ca-thi-truong/bang-gia-nong-san-ngay-25-02-2026-6160.html",
    "https://socongthuong.daklak.gov.vn/vi/news/thong-tin-gia-ca-thi-truong/bang-gia-nong-san-ngay-23-3-2026-6195.html",
    "https://socongthuong.daklak.gov.vn/vi/news/thong-tin-gia-ca-thi-truong/bang-gia-nong-san-ngay-25-3-2026-6199.html",
    "https://socongthuong.daklak.gov.vn/vi/news/thong-tin-gia-ca-thi-truong/bang-gia-nong-san-ngay-31-3-2026-6207.html",
    "https://socongthuong.daklak.gov.vn/vi/news/thong-tin-gia-ca-thi-truong/bang-gia-nong-san-ngay-6-4-2026-6217.html",
    "https://socongthuong.daklak.gov.vn/vi/news/thong-tin-gia-ca-thi-truong/bang-gia-nong-san-ngay-7-4-2026-6219.html",
    "https://socongthuong.daklak.gov.vn/vi/news/thong-tin-gia-ca-thi-truong/bang-gia-nong-san-ngay-9-4-2026-6224.html",
    "https://socongthuong.daklak.gov.vn/vi/news/thong-tin-gia-ca-thi-truong/bang-gia-nong-san-ngay-16-4-2026-6237.html",
    "https://socongthuong.daklak.gov.vn/vi/news/thong-tin-gia-ca-thi-truong/bang-gia-nong-san-ngay-05-5-2026-6255.html",
    "https://socongthuong.daklak.gov.vn/vi/news/thong-tin-gia-ca-thi-truong/bang-gia-nong-san-ngay-12-5-2026-6261.html",
    "https://socongthuong.daklak.gov.vn/vi/news/thong-tin-gia-ca-thi-truong/bang-gia-nong-san-ngay-15-5-2026-6270.html",
]
ARCHIVE_INDEX_URL = "https://socongthuong.daklak.gov.vn/vi/news/thong-tin-gia-ca-thi-truong/"
ARCHIVE_INDEX_PAGES = 50
TABLE_PRICE_RE = re.compile(r"\d{1,3}(?:[.,]\d{3})(?:\s*(?:-|–|—|đến)\s*\d{1,3}(?:[.,]\d{3}))?", re.IGNORECASE)


class SoCongThuongDakLakScraper:
    source = SOURCE
    source_url = URLS[0]

    def scrape(self) -> ScrapeResult:
        observations: list[PriceObservation] = []
        for url in URLS:
            observations.extend(self.parse(fetch_html(url), url).observations)
        return ScrapeResult(self.source, ", ".join(URLS), observations)

    def parse(self, html: str, source_url: str | None = None) -> ScrapeResult:
        url = source_url or self.source_url
        soup = BeautifulSoup(html, "html.parser")
        text = normalize_space(soup.get_text(" "))
        observed_at = parse_article_date(text)
        observations: list[PriceObservation] = []

        start = text.find("GIÁ SẦU RIÊNG")
        if start == -1:
            return ScrapeResult(self.source, url, observations)
        end_candidates = [idx for marker in ["GIÁ BƠ", "GIÁ CÀ PHÊ", "Bảng giá"] if (idx := text.find(marker, start + 1)) != -1]
        segment = text[start : min(end_candidates) if end_candidates else start + 2500]

        if "Giá sầu riêng tại khu vực miền Đông" in segment and "Giá sầu riêng tại Tây Nguyên" in segment:
            observations.extend(self._parse_regional_durian_table(segment, observed_at, url))
            return ScrapeResult(self.source, url, observations)

        known_labels = [
            "Sầu riêng Ri6 A",
            "Sầu riêng Ri6 B",
            "Sầu riêng Ri6 C",
            "Sầu riêng Ri6 (Loại A)",
            "Sầu riêng Ri6 (Loại B)",
            "Sầu riêng Ri6 (Loại C)",
            "Sầu riêng Ri6 loại A",
            "Sầu riêng Ri6 loại B",
            "Sầu riêng Ri6 loại C",
            "Sầu riêng Thái VIP A",
            "Sầu riêng Thái VIP B",
            "Sầu riêng Thái A",
            "Sầu riêng Thái B",
            "Sầu riêng Thái (Loại A)",
            "Sầu riêng Thái (Loại B)",
            "Sầu riêng Thái (Loại C)",
            "Sầu riêng Thái loại A",
            "Sầu riêng Thái loại B",
            "Sầu riêng Thái loại C",
            "Sầu riêng Thái (VIP A)",
            "Sầu riêng Thái (VIP B)",
            "Sầu riêng Thái (Mẫu đẹp A)",
            "Sầu riêng Thái (Mẫu đẹp B)",
            "Musang King (Loại A)",
            "Musang King (Loại B)",
            "Sầu riêng Musang King A",
            "Sầu riêng Musang King B",
            "Chuồng Bò (Loại A)",
            "Chuồng Bò (Loại B)",
            "Sầu riêng Chuồng Bò A",
            "Sầu riêng Chuồng Bò B",
            "Black Thorn (Loại A)",
            "Sầu riêng Black Thorn A",
            "Sáp Hữu (Loại A)",
            "Sáp Hữu (Loại B)",
            "Sáu Hữu (Loại A)",
            "Sáu Hữu (Loại B)",
        ]

        for label in known_labels:
            idx = segment.find(label)
            if idx == -1:
                continue
            window = segment[idx : idx + 130]
            price = parse_price_range(window)
            if not price:
                continue
            variety, grade = self._classify(label)
            observations.append(
                PriceObservation(
                    observed_at=observed_at,
                    variety_name=variety,
                    quality_grade=grade,
                    region_name="Thị trường Việt Nam",
                    province=None,
                    source=self.source,
                    source_url=url,
                    min_price_vnd=price[0],
                    max_price_vnd=price[1],
                )
            )
        return ScrapeResult(self.source, url, observations)

    def _parse_regional_durian_table(self, segment: str, observed_at, url: str) -> list[PriceObservation]:
        sections = [
            (
                "Giá sầu riêng tại khu vực miền Đông",
                "Giá sầu riêng tại Tây Nguyên",
                [(0, "Đồng Nai"), (1, "Bình Phước"), (2, "Tây Ninh")],
            ),
            (
                "Giá sầu riêng tại Tây Nguyên",
                "GIÁ BƠ",
                [(1, "Gia Lai"), (2, "Đắk Lắk")],
            ),
        ]
        row_labels = [
            "Sầu riêng Ri6 loại A",
            "Sầu riêng Ri6 loại B",
            "Sầu riêng Ri6 loại C",
            "Sầu riêng Thái loại A",
            "Sầu riêng Thái loại B",
            "Sầu riêng Thái loại C",
        ]
        observations: list[PriceObservation] = []
        for section_start, section_end, province_columns in sections:
            start = segment.find(section_start)
            if start == -1:
                continue
            end = segment.find(section_end, start + len(section_start))
            table = segment[start : end if end != -1 else len(segment)]
            for label in row_labels:
                row_start = table.find(label)
                if row_start == -1:
                    continue
                following = [table.find(next_label, row_start + len(label)) for next_label in row_labels]
                following = [index for index in following if index != -1]
                row_end = min(following) if following else len(table)
                ranges = [self._parse_table_price_cell(match.group(0)) for match in TABLE_PRICE_RE.finditer(table[row_start:row_end])]
                variety, grade = self._classify(label)
                for column, province in province_columns:
                    if column >= len(ranges) or ranges[column] is None:
                        continue
                    min_price, max_price = ranges[column]
                    observations.append(
                        PriceObservation(
                            observed_at=observed_at,
                            variety_name=variety,
                            quality_grade=grade,
                            region_name="Tây Nguyên" if province in {"Gia Lai", "Đắk Lắk"} else "Đông Nam Bộ",
                            province=province,
                            source=self.source,
                            source_url=url,
                            min_price_vnd=min_price,
                            max_price_vnd=max_price,
                        )
                    )
        return observations

    @staticmethod
    def _parse_table_price_cell(value: str) -> tuple[float, float]:
        price_range = parse_price_range(value)
        if price_range:
            return price_range
        amount = float(re.sub(r"\D", "", value))
        return amount, amount

    @staticmethod
    def _classify(label: str) -> tuple[str, str]:
        folded = strip_accents(label).lower()
        if "musang" in folded:
            variety = "Sầu Musang King"
        elif "chuong bo" in folded:
            variety = "Sầu Chuồng Bò"
        elif "black thorn" in folded:
            variety = "Sầu Black Thorn"
        elif "sap huu" in folded or "sau huu" in folded:
            variety = "Sầu Sáp Hữu"
        elif "thai" in folded:
            variety = "Sầu Thái Dona"
        else:
            variety = "Ri6"

        if "vip a" in folded:
            grade = "Loại VIP A"
        elif "vip b" in folded:
            grade = "Loại VIP B"
        elif "loai a" in folded or " a" in f" {folded}" or "mau dep a" in folded:
            grade = "Loại A"
        elif "loai b" in folded or " b" in f" {folded}" or "mau dep b" in folded:
            grade = "Loại B"
        elif "loai c" in folded or " c" in f" {folded}":
            grade = "Loại C"
        else:
            grade = "Tổng hợp"
        return variety, grade


class SoCongThuongDakLakHistoryScraper(SoCongThuongDakLakScraper):
    """One-off observed-price backfill; intentionally excluded from hourly jobs."""

    source = f"{SOURCE} (backfill lịch sử)"
    source_url = ARCHIVE_INDEX_URL
    archive_index_pages = ARCHIVE_INDEX_PAGES

    def scrape(self) -> ScrapeResult:
        observations: list[PriceObservation] = []
        for url in self.discover_article_urls():
            observations.extend(self.parse(fetch_html(url), url).observations)
        return ScrapeResult(self.source, self.source_url, observations)

    def discover_article_urls(self) -> list[str]:
        """Read a bounded official archive window for a manual history backfill."""
        urls = set(HISTORICAL_URLS)
        scheduled_urls = set(URLS)
        for page in range(1, self.archive_index_pages + 1):
            listing_url = ARCHIVE_INDEX_URL if page == 1 else f"{ARCHIVE_INDEX_URL}page-{page}/"
            soup = BeautifulSoup(fetch_html(listing_url), "html.parser")
            for link in soup.select("a[href]"):
                article_url = urljoin(listing_url, link.get("href", ""))
                if not article_url.startswith(ARCHIVE_INDEX_URL):
                    continue
                if "bang-gia-nong-san-ngay" not in article_url or not article_url.endswith(".html"):
                    continue
                if "/savefile/" in article_url or article_url in scheduled_urls:
                    continue
                urls.add(article_url)
        return sorted(urls)
