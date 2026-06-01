import re

from bs4 import BeautifulSoup

from app.ingestion.http import fetch_html
from app.ingestion.parsing import (
    PRICE_RANGE_RE,
    classify_variety_and_grade,
    normalize_space,
    parse_article_date,
    parse_price_range,
    strip_accents,
)
from app.ingestion.records import PriceObservation, ScrapeResult


SOURCE = "banggianongsan.com"
URL = "https://banggianongsan.com/"

PROVINCE_REGIONS = {
    "An Giang": "Tây Nam Bộ",
    "Bến Tre": "Tây Nam Bộ",
    "Bình Phước": "Đông Nam Bộ",
    "Cà Mau": "Tây Nam Bộ",
    "Cần Thơ": "Tây Nam Bộ",
    "Đắk Lắk": "Tây Nguyên",
    "Đắk Nông": "Tây Nguyên",
    "Đồng Nai": "Đông Nam Bộ",
    "Đồng Tháp": "Tây Nam Bộ",
    "Gia Lai": "Tây Nguyên",
    "Kon Tum": "Tây Nguyên",
    "Lâm Đồng": "Tây Nguyên",
    "Tây Ninh": "Đông Nam Bộ",
    "Tiền Giang": "Tây Nam Bộ",
    "Vĩnh Long": "Tây Nam Bộ",
}

PROVINCE_ALIASES = {
    "ba ria - vung tau": "Bà Rịa - Vũng Tàu",
    "binh phuoc": "Bình Phước",
    "can tho": "Cần Thơ",
    "dak lak": "Đắk Lắk",
    "dak nong": "Đắk Nông",
    "dong nai": "Đồng Nai",
    "dong thap": "Đồng Tháp",
    "gia lai": "Gia Lai",
    "lam dong": "Lâm Đồng",
    "tay ninh": "Tây Ninh",
    "tien giang": "Tiền Giang",
    "vinh long": "Vĩnh Long",
}

DOMESTIC_PRICE_FLOOR = {
    "sau_rieng": 20_000.0,
    "ca_phe": 45_000.0,
    "ho_tieu": 60_000.0,
}


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
        observations.extend(self._parse_homepage_tables(soup, observed_at))
        observations.extend(self._parse_variety_table(text, observed_at))
        observations.extend(self._parse_province_prices(text, observed_at))
        observations.extend(self._parse_market_prices(text, observed_at))
        return ScrapeResult(self.source, self.source_url, _dedupe_observations(observations))

    def _parse_homepage_tables(self, soup: BeautifulSoup, observed_at):
        rows: list[PriceObservation] = []
        for table in soup.select("table"):
            for tr in table.select("tr"):
                cells = [normalize_space(cell.get_text(" ")) for cell in tr.find_all(["td", "th"])]
                if len(cells) < 3:
                    continue
                parsed = self._parse_homepage_row(cells, observed_at)
                if parsed:
                    rows.append(parsed)
        return rows

    def _parse_homepage_row(self, cells: list[str], observed_at) -> PriceObservation | None:
        label = cells[0]
        price_cell = cells[2] if len(cells) >= 3 else cells[-1]
        crop_type = _crop_from_label(label)
        if not crop_type:
            return None
        if not _is_domestic_vnd_kg(label, price_cell):
            return None
        price = _parse_price_cell(price_cell)
        if not price:
            return None
        if price[1] < DOMESTIC_PRICE_FLOOR[crop_type]:
            return None

        province = _province_from_label(label)
        region_name = PROVINCE_REGIONS.get(province or "")
        if province and not region_name:
            return None
        if crop_type == "sau_rieng":
            fallback_region = _durian_region_from_label(label)
            region_name = region_name or fallback_region
            if not region_name:
                return None
        elif province is None:
            return None

        variety_name, quality_grade = _classify_homepage_product(label, crop_type)
        return PriceObservation(
            observed_at=observed_at,
            variety_name=variety_name,
            quality_grade=quality_grade,
            region_name=region_name,
            province=province,
            source=self.source,
            source_url=self.source_url,
            min_price_vnd=price[0],
            max_price_vnd=price[1],
            crop_type=crop_type,
        )

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


def _dedupe_observations(observations: list[PriceObservation]) -> list[PriceObservation]:
    deduped: dict[tuple, PriceObservation] = {}
    for observation in observations:
        key = (
            observation.observed_at,
            observation.crop_type,
            observation.variety_name,
            observation.quality_grade,
            observation.region_name,
            observation.province,
            observation.source,
        )
        deduped[key] = observation
    return list(deduped.values())


def _crop_from_label(label: str) -> str | None:
    folded = strip_accents(label).lower()
    if "sau rieng" in folded:
        return "sau_rieng"
    if "ca phe" in folded:
        return "ca_phe"
    if "ho tieu" in folded or folded.startswith("tieu "):
        return "ho_tieu"
    return None


def _is_domestic_vnd_kg(label: str, price_cell: str) -> bool:
    raw = f"{label} {price_cell}".lower()
    folded = strip_accents(raw)
    if "usd" in folded or "cent" in folded or "london" in folded or "new york" in folded:
        return False
    raw_units = ["đ/kg", "đồng/kg", "vnd/kg", "vnđ/kg"]
    folded_units = ["d/kg", "dong/kg", "vnd/kg", "vnd/kg"]
    return any(unit in raw for unit in raw_units) or any(unit in folded for unit in folded_units)


def _parse_price_cell(value: str) -> tuple[float, float] | None:
    normalized = value.replace("–", "-").replace("—", "-").replace("đến", "-")
    price_range = parse_price_range(normalized)
    if price_range:
        return price_range
    match = re.search(r"\d{1,3}(?:[.,]\d{3})+", normalized)
    if not match:
        return None
    digits = re.sub(r"\D", "", match.group(0))
    if not digits:
        return None
    price = float(int(digits))
    return price, price


def _province_from_label(label: str) -> str | None:
    folded = strip_accents(label).lower()
    for alias, province in PROVINCE_ALIASES.items():
        if alias in folded:
            return province
    return None


def _durian_region_from_label(label: str) -> str | None:
    folded = strip_accents(label).lower()
    if "dbscl" in folded or "dong bang song cuu long" in folded:
        return "Tây Nam Bộ"
    return None


def _classify_homepage_product(label: str, crop_type: str) -> tuple[str, str]:
    folded = strip_accents(label).lower()
    if crop_type == "ca_phe":
        return "Cà phê tổng hợp", "Tổng hợp"
    if crop_type == "ho_tieu":
        return ("Tiêu trắng" if "trang" in folded else "Tiêu đen"), "Tổng hợp"

    if "ri6" in folded or "ri 6" in folded:
        variety = "Ri6"
    elif "musang" in folded:
        variety = "Sầu Musang King"
    elif "black thorn" in folded:
        variety = "Sầu Black Thorn"
    elif "chuong bo" in folded:
        variety = "Sầu Chuồng Bò"
    elif "thai" in folded:
        variety = "Sầu Thái Dona"
    else:
        variety = "Sầu riêng tổng hợp"

    if "loai a" in folded:
        grade = "Loại A"
    elif "loai b" in folded:
        grade = "Loại B"
    elif "loai c" in folded:
        grade = "Loại C"
    else:
        grade = "Tổng hợp"
    return variety, grade
