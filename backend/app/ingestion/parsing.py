from datetime import UTC, datetime
import re
import unicodedata


PRICE_RANGE_RE = re.compile(
    r"(?P<min>\d{1,3}(?:[.,]\d{3})+|\d{2,3})\s*(?:-|–|—|đến)\s*"
    r"(?P<max>\d{1,3}(?:[.,]\d{3})+|\d{2,3})",
    re.IGNORECASE,
)

DATE_RE = re.compile(r"(?P<day>\d{1,2})[/-](?P<month>\d{1,2})(?:[/-](?P<year>\d{4}))?")


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value)
    folded = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    return folded.replace("đ", "d").replace("Đ", "D")


def parse_price_range(value: str) -> tuple[float, float] | None:
    match = PRICE_RANGE_RE.search(value)
    if not match:
        return None
    low = _parse_price(match.group("min"))
    high = _parse_price(match.group("max"))
    return (min(low, high), max(low, high))


def parse_article_date(text: str, default: datetime | None = None) -> datetime:
    match = DATE_RE.search(text)
    if not match:
        return default or datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    year = int(match.group("year") or datetime.now(UTC).year)
    return datetime(
        year,
        int(match.group("month")),
        int(match.group("day")),
        tzinfo=UTC,
    )


def classify_variety_and_grade(label: str) -> tuple[str, str]:
    folded = strip_accents(label).lower()
    if "ri6" in folded or "ri 6" in folded:
        variety = "Ri6"
    elif "musang" in folded:
        variety = "Sầu Musang King"
    elif "monthong" in folded:
        variety = "Sầu Thái Monthong"
    elif "dona" in folded or "thai" in folded:
        variety = "Sầu Thái Dona"
    elif "chuong bo" in folded:
        variety = "Sầu Chuồng Bò"
    else:
        variety = "Sầu riêng tổng hợp"

    if "vip" in folded and " a" in f" {folded}":
        grade = "Loại VIP A"
    elif "vip" in folded and " b" in f" {folded}":
        grade = "Loại VIP B"
    elif "loai a" in folded or " a" in f" {folded}" or "dep" in folded or "tuyen" in folded:
        grade = "Loại A"
    elif "loai b" in folded or " b" in f" {folded}":
        grade = "Loại B"
    elif " c" in f" {folded}":
        grade = "Loại C"
    elif "xo" in folded:
        grade = "Hàng xô"
    else:
        grade = "Tổng hợp"
    return variety, grade


def _parse_price(value: str) -> float:
    digits = re.sub(r"\D", "", value)
    if not digits:
        raise ValueError(f"Cannot parse price from {value!r}")
    number = int(digits)
    if number < 1000:
        number *= 1000
    return float(number)
