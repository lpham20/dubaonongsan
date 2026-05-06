GRADE_LABELS = {
    "Grade A": "Loại A",
    "Grade B": "Loại B",
    "Grade C": "Loại C",
    "VIP A": "Loại VIP A",
    "VIP B": "Loại VIP B",
    "Bulk": "Hàng xô",
    "Market": "Giá chợ",
    "Mixed": "Tổng hợp",
}

REGION_LABELS = {
    "Mekong Delta": "Tây Nam Bộ",
    "Central Highlands": "Tây Nguyên",
    "Southeast": "Đông Nam Bộ",
    "Vietnam Market": "Thị trường Việt Nam",
    "Ho Chi Minh Wholesale": "Chợ đầu mối TP.HCM",
}

PROVINCE_LABELS = {
    "Tien Giang": "Tiền Giang",
    "Dak Lak": "Đắk Lắk",
    "Lam Dong": "Lâm Đồng",
}

VARIETY_LABELS = {
    "Thai Dona": "Sầu Thái Dona",
    "Monthong": "Sầu Thái Monthong",
    "Musang King": "Sầu Musang King",
    "Black Thorn": "Sầu Black Thorn",
    "Chuong Bo": "Sầu Chuồng Bò",
    "Mixed Durian": "Sầu riêng tổng hợp",
}

STATUS_LABELS = {
    "Ready to Harvest": "Sẵn sàng thu hoạch",
    "Monitoring": "Đang theo dõi",
    "running": "đang chạy",
    "success": "thành công",
    "failed": "thất bại",
}

SOURCE_LABELS = {
    "Cho Thu Duc": "Chợ Thủ Đức",
}


def vi_grade(value: str | None) -> str | None:
    return GRADE_LABELS.get(value or "", value)


def vi_region(value: str | None) -> str | None:
    return REGION_LABELS.get(value or "", value)


def vi_province(value: str | None) -> str | None:
    return PROVINCE_LABELS.get(value or "", value)


def vi_variety(value: str | None) -> str | None:
    return VARIETY_LABELS.get(value or "", value)


def vi_status(value: str | None) -> str | None:
    return STATUS_LABELS.get(value or "", value)


def vi_source(value: str | None) -> str | None:
    return SOURCE_LABELS.get(value or "", value)

