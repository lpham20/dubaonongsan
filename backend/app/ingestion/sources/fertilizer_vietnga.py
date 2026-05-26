from __future__ import annotations

from datetime import UTC, datetime
import re
import unicodedata

from bs4 import BeautifulSoup
import requests

from app.ingestion.http import fetch_html, request_headers
from app.ingestion.input_price_records import InputPriceObservation, InputPriceScrapeResult
from app.ingestion.parsing import normalize_space


SOURCE = "vietnga.vn"
PAGE_URL = "https://vietnga.vn/gia-phan-bon-hom-nay/"
AJAX_URL = "https://vietnga.vn/wp-admin/admin-ajax.php?action=pricing_filter"
REGION_NAME = "Đồng bằng sông Cửu Long"
PROVINCE = "Miền Tây"
PACKAGE_SIZE_KG = 50.0
MAX_BACKFILL_DATES = 24
MAX_BRAND_LENGTH = 120

PRICE_RANGE_RE = re.compile(
    r"(?P<low>\d{1,3}(?:[.,]\d{3})+)\s*(?:-|–|—|đến|to)\s*(?P<high>\d{1,3}(?:[.,]\d{3})+)",
    re.IGNORECASE,
)


class VietNgaFertilizerPriceScraper:
    source = SOURCE
    source_url = PAGE_URL

    def scrape(self) -> InputPriceScrapeResult:
        page_html = fetch_html(PAGE_URL)
        observations: list[InputPriceObservation] = []
        for date_id, date_label in self._extract_date_options(page_html)[:MAX_BACKFILL_DATES]:
            observed_at = _parse_date_label(date_label)
            html = self._fetch_price_table(date_id)
            observations.extend(self.parse_table(html, observed_at, date_id=date_id))
        return InputPriceScrapeResult(self.source, self.source_url, observations)

    def parse_table(
        self,
        html: str,
        observed_at: datetime,
        *,
        date_id: str = "",
    ) -> list[InputPriceObservation]:
        soup = BeautifulSoup(html, "html.parser")
        observations: list[InputPriceObservation] = []
        for row in soup.select(".table-row:not(.heading-row)"):
            cells = row.find_all("div", class_="table-cell", recursive=False)
            if len(cells) < 4:
                continue
            product_label = normalize_space(cells[2].get_text(" "))
            if not product_label:
                continue
            price_text = self._price_text(cells[3])
            price = _parse_price_range_midpoint(price_text)
            if price is None:
                continue
            product = classify_fertilizer_product(product_label)
            observations.append(
                InputPriceObservation(
                    observed_at=observed_at,
                    product_slug=product["slug"],
                    product_name=product["name"],
                    product_type=product["product_type"],
                    nutrient_profile=product["nutrient_profile"],
                    province=PROVINCE,
                    region_name=REGION_NAME,
                    brand=product["brand"],
                    seller_name="Phân Bón Việt Nga",
                    source=self.source,
                    source_url=f"{PAGE_URL}#date-{date_id}" if date_id else PAGE_URL,
                    package_price_vnd=price,
                    package_size_kg=PACKAGE_SIZE_KG,
                    confidence_score=0.86,
                    data_kind="scraped",
                )
            )
        return observations

    @staticmethod
    def _extract_date_options(html: str) -> list[tuple[str, str]]:
        soup = BeautifulSoup(html, "html.parser")
        select = soup.find("select", attrs={"name": "date"})
        if select is None:
            return []
        output: list[tuple[str, str]] = []
        for option in select.find_all("option"):
            value = normalize_space(option.get("value") or "")
            label = normalize_space(option.get_text(" "))
            if value and re.fullmatch(r"\d+", value) and re.search(r"\d{1,2}/\d{1,2}/\d{4}", label):
                output.append((value, label))
        return output

    @staticmethod
    def _fetch_price_table(date_id: str) -> str:
        headers = request_headers({"Referer": PAGE_URL, "X-Requested-With": "XMLHttpRequest"})
        response = requests.post(AJAX_URL, data={"date": date_id, "area": "all"}, headers=headers, timeout=20)
        response.raise_for_status()
        payload = response.json()
        html = payload.get("html")
        if not isinstance(html, str):
            raise ValueError("VietNga pricing_filter response did not include html")
        return html

    @staticmethod
    def _price_text(cell) -> str:
        target = cell.select_one(".sub-cell") or cell
        for hidden_label in target.select(".show-tablet"):
            hidden_label.decompose()
        return normalize_space(target.get_text(" "))


def classify_fertilizer_product(label: str) -> dict[str, str | None]:
    folded = _fold(label)
    formula = _extract_npk_formula(label)
    brand = _extract_brand(label, folded, formula)

    if "npk" in folded:
        formula_slug = (formula or "npk").replace("+", "-").replace(" ", "-").lower()
        return {
            "slug": formula_slug if formula_slug.startswith("npk") else f"npk-{formula_slug}",
            "name": formula or "NPK",
            "product_type": "Phân hỗn hợp",
            "nutrient_profile": formula.replace("NPK ", "") if formula else None,
            "brand": brand,
        }
    if "dap" in folded:
        return {
            "slug": "dap",
            "name": "DAP",
            "product_type": "Phân đơn",
            "nutrient_profile": "18-46-0",
            "brand": brand,
        }
    if "k2so4" in folded or "sulphate" in folded or "sulfate" in folded or "sop" in folded:
        return {
            "slug": "kali-sop",
            "name": "Kali SOP",
            "product_type": "Phân đơn",
            "nutrient_profile": "50% K2O + 18% S",
            "brand": brand,
        }
    if "kali" in folded or "kaly" in folded or "kcl" in folded:
        return {
            "slug": "kali-mop",
            "name": "Kali MOP",
            "product_type": "Phân đơn",
            "nutrient_profile": "K2O",
            "brand": brand,
        }
    if "ure" in folded or "uree" in folded or "urea" in folded or re.search(r"\bdam\b", folded):
        return {
            "slug": "ure",
            "name": "Urê",
            "product_type": "Phân đơn",
            "nutrient_profile": "46% N",
            "brand": brand,
        }
    if "lan" in folded:
        return {
            "slug": "lan-nung-chay",
            "name": "Lân nung chảy",
            "product_type": "Phân lân",
            "nutrient_profile": "P2O5",
            "brand": brand,
        }
    if "phan bo" in folded or "huu co" in folded or "vi sinh" in folded:
        return {
            "slug": _slugify(label),
            "name": label,
            "product_type": "Phân hữu cơ",
            "nutrient_profile": "Hữu cơ",
            "brand": brand,
        }
    if re.search(r"\bsa\b", folded):
        return {
            "slug": "sa",
            "name": "SA",
            "product_type": "Phân đơn",
            "nutrient_profile": "21% N + 24% S",
            "brand": brand,
        }
    return {
        "slug": _slugify(label),
        "name": label,
        "product_type": "Phân bón",
        "nutrient_profile": None,
        "brand": brand,
    }


def _extract_npk_formula(label: str) -> str | None:
    match = re.search(r"NPK\s+(\d{1,2}[-–]\d{1,2}[-–]\d{1,2})(?:\+\s*TE)?", label, re.IGNORECASE)
    if not match:
        match = re.search(r"(\d{1,2}[-–]\d{1,2}[-–]\d{1,2})(?:[-–]\d{1,2}S)?", label, re.IGNORECASE)
    if not match:
        return None
    formula = match.group(1).replace("–", "-")
    return f"NPK {formula}"


def _extract_brand(label: str, folded: str, formula: str | None) -> str | None:
    clean = re.sub(r"\([^)]*\)", "", label)
    clean = re.sub(r"\b\d{1,2}%\b", "", clean)
    clean = normalize_space(clean)

    if "npk" in folded:
        brand = re.sub(r"(?i)\bNPK\b", "", clean)
        if formula:
            brand = brand.replace(formula.replace("NPK ", ""), "")
            brand = brand.replace(formula, "")
        brand = re.sub(r"[-–+]?\s*\bTE\b", "", brand, flags=re.IGNORECASE)
        return _normalize_brand_alias(normalize_space(brand))
    for prefix in ("Urea", "Urê", "Ure", "Đạm", "DAP", "Kali", "Kaly", "Lân", "SA"):
        if clean.lower().startswith(prefix.lower()):
            brand = normalize_space(clean[len(prefix):])
            return _normalize_brand_alias(brand)
    return _normalize_brand_alias(clean)


def _normalize_brand_alias(value: str | None) -> str | None:
    if not value:
        return None
    value = normalize_space(value)
    folded = _fold(value)
    aliases = {
        "nga": "Nga",
        "nhap khau": "Nhập khẩu",
        "phu my": "Phú Mỹ",
        "ca mau": "Cà Mau",
        "dinh vu": "Đình Vũ",
        "lao cai": "Lào Cai",
        "hong ha": "Hồng Hà",
        "tuong phong": "Tường Phong",
        "viet nhat": "Việt Nhật",
        "binh dien": "Bình Điền",
        "con co": "Con Cò",
        "lam thao": "Lâm Thao",
        "lt": "Lâm Thao",
        "van dien": "Văn Điển",
        "israel": "Israel",
        "canada": "Canada",
        "uzbekistan": "Uzbekistan",
        "bot do": "Bột đỏ",
        "bot trang": "Bột trắng",
    }
    for key, label in aliases.items():
        if key in folded:
            return label
    return value[:MAX_BRAND_LENGTH].rstrip()


def _parse_price_range_midpoint(value: str) -> float | None:
    match = PRICE_RANGE_RE.search(value)
    if not match:
        return None
    low = _parse_price(match.group("low"))
    high = _parse_price(match.group("high"))
    return round((low + high) / 2, 2)


def _parse_price(value: str) -> float:
    digits = re.sub(r"\D", "", value)
    if not digits:
        raise ValueError(f"Cannot parse price from {value!r}")
    number = int(digits)
    if number < 1000:
        number *= 1000
    return float(number)


def _parse_date_label(label: str) -> datetime:
    match = re.search(r"(?P<day>\d{1,2})/(?P<month>\d{1,2})/(?P<year>\d{4})", label)
    if not match:
        raise ValueError(f"Cannot parse VietNga price date from {label!r}")
    return datetime(int(match.group("year")), int(match.group("month")), int(match.group("day")), tzinfo=UTC)


def _fold(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value)
    folded = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    return folded.replace("đ", "d").replace("Đ", "D").lower()


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", _fold(value)).strip("-")
    return slug[:80] or "phan-bon"
