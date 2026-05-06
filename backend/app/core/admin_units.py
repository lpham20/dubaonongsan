from __future__ import annotations

import re
import unicodedata


NON_PRODUCTION_REGIONS = {"Thị trường Việt Nam", "Chợ đầu mối TP.HCM"}

PROVINCE_TO_REGION = {
    "Điện Biên": "Tây Bắc",
    "Sơn La": "Tây Bắc",
    "Đắk Lắk": "Tây Nguyên",
    "Lâm Đồng": "Tây Nguyên",
    "Gia Lai": "Tây Nguyên",
    "Quảng Ngãi": "Tây Nguyên",
    "Đồng Nai": "Đông Nam Bộ",
    "Tây Ninh": "Đông Nam Bộ",
    "Thành phố Hồ Chí Minh": "Đông Nam Bộ",
    "Cần Thơ": "Đồng bằng sông Cửu Long",
    "Vĩnh Long": "Đồng bằng sông Cửu Long",
    "Đồng Tháp": "Đồng bằng sông Cửu Long",
    "Cà Mau": "Đồng bằng sông Cửu Long",
    "An Giang": "Đồng bằng sông Cửu Long",
}

CROP_PROVINCES = {
    "sau_rieng": {"Cần Thơ", "Vĩnh Long", "Đồng Tháp", "Đắk Lắk", "Lâm Đồng", "Đồng Nai", "Tây Ninh"},
    "ca_phe": {"Đắk Lắk", "Lâm Đồng", "Gia Lai", "Quảng Ngãi", "Sơn La", "Điện Biên", "Đồng Nai"},
    "ho_tieu": {"Đắk Lắk", "Lâm Đồng", "Gia Lai", "Đồng Nai", "Thành phố Hồ Chí Minh"},
    "lua": {"Cần Thơ", "Vĩnh Long", "Đồng Tháp", "Cà Mau", "An Giang", "Tây Ninh"},
}

PROVINCE_ALIASES = {
    "dak lak": "Đắk Lắk",
    "daklak": "Đắk Lắk",
    "dac lac": "Đắk Lắk",
    "phu yen": "Đắk Lắk",
    "dak nong": "Lâm Đồng",
    "daknong": "Lâm Đồng",
    "lam dong": "Lâm Đồng",
    "binh thuan": "Lâm Đồng",
    "gia lai": "Gia Lai",
    "binh dinh": "Gia Lai",
    "kon tum": "Quảng Ngãi",
    "quang ngai": "Quảng Ngãi",
    "dong nai": "Đồng Nai",
    "binh phuoc": "Đồng Nai",
    "ba ria vung tau": "Thành phố Hồ Chí Minh",
    "ba ria - vung tau": "Thành phố Hồ Chí Minh",
    "br vt": "Thành phố Hồ Chí Minh",
    "tp hcm": "Thành phố Hồ Chí Minh",
    "tphcm": "Thành phố Hồ Chí Minh",
    "ho chi minh": "Thành phố Hồ Chí Minh",
    "thanh pho ho chi minh": "Thành phố Hồ Chí Minh",
    "tay ninh": "Tây Ninh",
    "long an": "Tây Ninh",
    "can tho": "Cần Thơ",
    "soc trang": "Cần Thơ",
    "hau giang": "Cần Thơ",
    "vinh long": "Vĩnh Long",
    "ben tre": "Vĩnh Long",
    "tra vinh": "Vĩnh Long",
    "dong thap": "Đồng Tháp",
    "tien giang": "Đồng Tháp",
    "ca mau": "Cà Mau",
    "bac lieu": "Cà Mau",
    "an giang": "An Giang",
    "kien giang": "An Giang",
    "son la": "Sơn La",
    "dien bien": "Điện Biên",
}

REGION_ALIASES = {
    "mekong delta": "Đồng bằng sông Cửu Long",
    "tay nam bo": "Đồng bằng sông Cửu Long",
    "dong bang song cuu long": "Đồng bằng sông Cửu Long",
    "central highlands": "Tây Nguyên",
    "tay nguyen": "Tây Nguyên",
    "southeast": "Đông Nam Bộ",
    "dong nam bo": "Đông Nam Bộ",
    "vietnam market": "Thị trường Việt Nam",
    "thi truong viet nam": "Thị trường Việt Nam",
    "ho chi minh wholesale": "Chợ đầu mối TP.HCM",
    "cho dau moi tp hcm": "Chợ đầu mối TP.HCM",
}


def normalize_location(region_name: str | None, province: str | None) -> tuple[str, str | None]:
    region = normalize_region_name(region_name)
    normalized_province = normalize_province_name(province)

    if normalized_province is None and region not in NON_PRODUCTION_REGIONS:
        normalized_province = normalize_province_name(region_name)

    if normalized_province:
        region = PROVINCE_TO_REGION.get(normalized_province, region)

    return region, normalized_province


def normalize_region_name(value: str | None) -> str:
    cleaned = _clean_label(value)
    if not cleaned:
        return "Thị trường Việt Nam"
    return REGION_ALIASES.get(_fold(cleaned), cleaned)


def normalize_province_name(value: str | None) -> str | None:
    cleaned = _clean_label(value)
    if not cleaned:
        return None
    folded = _fold(cleaned)
    if folded in REGION_ALIASES:
        return None
    if folded in {"thu duc", "binh dien", "ben thanh", "cho thu duc", "cho binh dien"}:
        return None
    return PROVINCE_ALIASES.get(folded, cleaned)


def is_production_region(region_name: str | None, province: str | None) -> bool:
    region, normalized_province = normalize_location(region_name, province)
    return normalized_province is not None and region not in NON_PRODUCTION_REGIONS


def is_crop_province(crop: str, province: str | None) -> bool:
    normalized = normalize_province_name(province)
    allowed = CROP_PROVINCES.get(crop)
    return bool(normalized and (allowed is None or normalized in allowed))


def _clean_label(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def _fold(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value.lower())
    without_marks = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    folded = (
        without_marks.replace("đ", "d")
        .replace("tp.", "thanh pho ")
        .replace("tp ", "thanh pho ")
        .replace("-", " ")
        .replace(".", " ")
        .strip()
    )
    return re.sub(r"\s+", " ", folded)
