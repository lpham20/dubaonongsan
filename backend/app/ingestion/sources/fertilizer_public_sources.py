from __future__ import annotations

from datetime import UTC, datetime
import re
import unicodedata

from bs4 import BeautifulSoup

from app.ingestion.http import fetch_html
from app.ingestion.input_price_records import InputPriceObservation, InputPriceScrapeResult
from app.ingestion.parsing import normalize_space
from app.ingestion.sources.fertilizer_vietnga import classify_fertilizer_product


PACKAGE_SIZE_50KG = 50.0


class VinacamFertilizerPriceScraper:
    source = "vinacam.com.vn"
    source_url = "https://vinacam.com.vn/bang-gia-phan-bon"

    _markets = {
        "HCM": ("TP.HCM", "Đông Nam Bộ"),
        "HN": ("Hà Nội", "Miền Bắc"),
        "Quy Nhơn": ("Quy Nhơn", "Duyên hải Nam Trung Bộ"),
    }

    def scrape(self) -> InputPriceScrapeResult:
        return self.parse_html(fetch_html(self.source_url))

    def parse_html(self, html: str) -> InputPriceScrapeResult:
        soup = BeautifulSoup(html, "html.parser")
        observed_at = _extract_date(soup.get_text(" ", strip=True), default=datetime.now(UTC))
        observations: list[InputPriceObservation] = []
        table = soup.find("table")
        if table is None:
            return InputPriceScrapeResult(self.source, self.source_url, observations)

        for row in table.find_all("tr"):
            cells = [normalize_space(cell.get_text(" ")) for cell in row.find_all(["td", "th"])]
            if len(cells) < 5 or not cells[1] or "Tên Phân Bón" in cells[1]:
                continue
            product_label = _strip_fertilizer_prefix(cells[1])
            product = classify_fertilizer_product(product_label)
            for market_label, raw_price in zip(("HCM", "HN", "Quy Nhơn"), cells[2:5], strict=False):
                price_per_kg = _parse_price(raw_price)
                if price_per_kg is None:
                    continue
                if not _is_reasonable_kg_price(str(product["slug"]), price_per_kg):
                    continue
                province, region_name = self._markets[market_label]
                observations.append(
                    InputPriceObservation(
                        observed_at=observed_at,
                        product_slug=str(product["slug"]),
                        product_name=str(product["name"]),
                        product_type=str(product["product_type"]),
                        nutrient_profile=product["nutrient_profile"],
                        province=province,
                        region_name=region_name,
                        brand=product["brand"],
                        seller_name="Vinacam",
                        source=self.source,
                        source_url=self.source_url,
                        package_price_vnd=round(price_per_kg * PACKAGE_SIZE_50KG, 2),
                        package_size_kg=PACKAGE_SIZE_50KG,
                        confidence_score=0.9,
                        data_kind="scraped",
                    )
                )
        return InputPriceScrapeResult(self.source, self.source_url, observations)


class TheFinancesFertilizerPriceScraper:
    source = "thefinances.org"
    source_url = "https://thefinances.org/gia-phan-bon/"

    def scrape(self) -> InputPriceScrapeResult:
        return self.parse_html(fetch_html(self.source_url))

    def parse_html(self, html: str) -> InputPriceScrapeResult:
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(" ", strip=True)
        observed_at = _extract_date(text, default=datetime.now(UTC))
        observations: list[InputPriceObservation] = []
        table = soup.find("table")
        if table is None:
            return InputPriceScrapeResult(self.source, self.source_url, observations)

        for row in table.find_all("tr"):
            cells = [normalize_space(cell.get_text(" ")) for cell in row.find_all(["td", "th"])]
            if len(cells) < 5:
                continue
            province = _normalize_province(cells[0])
            if not province:
                continue
            price_per_kg = _parse_price(cells[2])
            if price_per_kg is None:
                continue
            product_label = _strip_fertilizer_prefix(cells[1])
            product = classify_fertilizer_product(product_label)
            slug = str(product["slug"])
            if not _is_reasonable_kg_price(slug, price_per_kg):
                continue
            observations.append(
                InputPriceObservation(
                    observed_at=observed_at,
                    product_slug=slug,
                    product_name=str(product["name"]),
                    product_type=str(product["product_type"]),
                    nutrient_profile=product["nutrient_profile"],
                    province=province,
                    region_name=_region_for_province(province),
                    brand=product["brand"],
                    seller_name=normalize_space(cells[4])[:120] or None,
                    source=self.source,
                    source_url=self.source_url,
                    package_price_vnd=round(price_per_kg * PACKAGE_SIZE_50KG, 2),
                    package_size_kg=PACKAGE_SIZE_50KG,
                    confidence_score=0.64,
                    data_kind="scraped",
                )
            )
        return InputPriceScrapeResult(self.source, self.source_url, observations)


class SFarmOrganicFertilizerPriceScraper:
    source = "sfarm.vn"
    source_url = "https://sfarm.vn/bang-gia-phan-bo-u-hoai-da-qua-xu-ly-moi-nhat-sll5/"

    def scrape(self) -> InputPriceScrapeResult:
        return self.parse_html(fetch_html(self.source_url))

    def parse_html(self, html: str) -> InputPriceScrapeResult:
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(" ", strip=True)
        date_match = re.search(r"Bảng giá được cập nhật vào\s*(\d{1,2}/\d{1,2}/\d{4})", text, flags=re.IGNORECASE)
        observed_at = _parse_date(date_match.group(1)) if date_match else datetime.now(UTC)
        observations: list[InputPriceObservation] = []
        for row in soup.select("table tr"):
            cells = [normalize_space(cell.get_text(" ")) for cell in row.find_all(["td", "th"])]
            if len(cells) < 3 or cells[0].lower().startswith("sản phẩm"):
                continue
            package_size = _parse_package_size_kg(cells[1])
            package_price = _parse_price(cells[2])
            if package_size is None or package_price is None:
                continue
            observations.append(
                InputPriceObservation(
                    observed_at=observed_at,
                    product_slug="phan-bo-u-hoai-sfarm",
                    product_name="Phân bò ủ hoai SFARM",
                    product_type="Phân hữu cơ",
                    nutrient_profile="Hữu cơ vi sinh",
                    province="TP.HCM",
                    region_name="Đông Nam Bộ",
                    brand="SFARM",
                    seller_name="SFARM",
                    source=self.source,
                    source_url=self.source_url,
                    package_price_vnd=package_price,
                    package_size_kg=package_size,
                    confidence_score=0.72,
                    data_kind="scraped",
                )
            )
        return InputPriceScrapeResult(self.source, self.source_url, observations)


class CoffeeMarketFertilizerPriceScraper:
    source = "giathitruongcaphe.com"
    _pages = {
        "Đắk Lắk": "https://giathitruongcaphe.com/content/fertilizer/province/dak-lak",
        "Gia Lai": "https://giathitruongcaphe.com/content/fertilizer/province/gia-lai",
        "Lâm Đồng": "https://giathitruongcaphe.com/content/fertilizer/province/lam-dong",
    }
    source_url = "https://giathitruongcaphe.com/content/fertilizer/province/dak-lak"

    def scrape(self) -> InputPriceScrapeResult:
        observations: list[InputPriceObservation] = []
        for province, url in self._pages.items():
            observations.extend(self.parse_html(fetch_html(url), province=province, source_url=url).observations)
        return InputPriceScrapeResult(self.source, self.source_url, observations)

    def parse_html(self, html: str, *, province: str, source_url: str | None = None) -> InputPriceScrapeResult:
        source_url = source_url or self._pages.get(province, self.source_url)
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text("\n", strip=True)
        date_match = re.search(r"Cập nhật lần cuối:\s*(\d{1,2}/\d{1,2}/\d{4})", text, flags=re.IGNORECASE)
        observed_at = _parse_date(date_match.group(1)) if date_match else _extract_date(text, default=datetime.now(UTC))
        lines = [normalize_space(line) for line in text.splitlines() if normalize_space(line)]
        observations: list[InputPriceObservation] = []
        for index, line in enumerate(lines):
            if not line.lower().startswith("phân "):
                continue
            if index + 5 >= len(lines):
                continue
            brand = lines[index + 1]
            low = _parse_price(lines[index + 2])
            separator = lines[index + 3]
            high = _parse_price(lines[index + 4])
            unit = lines[index + 5].lower()
            if separator != "-" or low is None or high is None or "bao" not in unit:
                continue
            product = classify_fertilizer_product(_strip_fertilizer_prefix(f"{line} {brand}"))
            price = round((low + high) / 2, 2)
            if not _is_reasonable_package_price(str(product["slug"]), price):
                continue
            observations.append(
                InputPriceObservation(
                    observed_at=observed_at,
                    product_slug=str(product["slug"]),
                    product_name=str(product["name"]),
                    product_type=str(product["product_type"]),
                    nutrient_profile=product["nutrient_profile"],
                    province=province,
                    region_name="Tây Nguyên",
                    brand=product["brand"] or brand,
                    seller_name="Coffee Market Monitor",
                    source=self.source,
                    source_url=source_url,
                    package_price_vnd=price,
                    package_size_kg=PACKAGE_SIZE_50KG,
                    confidence_score=0.58,
                    data_kind="scraped",
                )
            )
        return InputPriceScrapeResult(self.source, source_url, observations)


def _extract_date(text: str, *, default: datetime) -> datetime:
    match = re.search(r"(\d{1,2}/\d{1,2}/\d{4})", text)
    return _parse_date(match.group(1)) if match else default


def _parse_date(value: str) -> datetime:
    day, month, year = (int(part) for part in value.split("/"))
    return datetime(year, month, day, tzinfo=UTC)


def _parse_price(value: str) -> float | None:
    value = normalize_space(value)
    if not value or value in {"-", "–", "—"}:
        return None
    digits = re.sub(r"\D", "", value)
    if not digits:
        return None
    return float(int(digits))


def _parse_package_size_kg(value: str) -> float | None:
    match = re.search(r"(\d+(?:[.,]\d+)?)\s*kg", value, flags=re.IGNORECASE)
    if not match:
        return None
    return float(match.group(1).replace(",", "."))


def _strip_fertilizer_prefix(value: str) -> str:
    value = normalize_space(value)
    value = re.sub(r"^(?:Phân\s+)+", "", value, flags=re.IGNORECASE)
    return normalize_space(value)


def _normalize_province(value: str) -> str | None:
    value = normalize_space(value)
    folded = _fold(value)
    if not value:
        return None
    if "tphcm" in folded or "tp hcm" in folded or "tp.hcm" in folded or "tan quy" in folded:
        return "TP.HCM"
    if "tay nam bo" in folded:
        return "Tây Nam Bộ"
    return value


def _region_for_province(value: str) -> str:
    folded = _fold(value)
    if folded in {"an giang", "ca mau", "tien giang", "tra vinh", "tay nam bo"}:
        return "Đồng bằng sông Cửu Long"
    if folded in {"tp.hcm", "tp hcm", "tphcm"}:
        return "Đông Nam Bộ"
    if folded in {"dak lak", "gia lai", "lam dong"}:
        return "Tây Nguyên"
    if folded in {"ha noi"}:
        return "Miền Bắc"
    return "Việt Nam"


def _is_reasonable_kg_price(slug: str, price_per_kg: float) -> bool:
    if slug.startswith("npk"):
        return 5_000 <= price_per_kg <= 30_000
    ranges = {
        "ure": (5_000, 25_000),
        "dap": (10_000, 38_000),
        "kali-mop": (6_000, 30_000),
        "kali-sop": (10_000, 45_000),
        "sa": (2_000, 15_000),
        "lan-nung-chay": (1_500, 12_000),
    }
    low, high = ranges.get(slug, (1_000, 80_000))
    return low <= price_per_kg <= high


def _is_reasonable_package_price(slug: str, package_price: float) -> bool:
    return _is_reasonable_kg_price(slug, package_price / PACKAGE_SIZE_50KG)


def _fold(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value)
    folded = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    return folded.replace("đ", "d").replace("Đ", "D").lower()
