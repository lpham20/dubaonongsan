from app.services.data_loader import DataLoader


def test_calibrated_prices_are_not_labeled_as_observed():
    point = DataLoader._row_to_point({"exchange_source": "Hiệu chỉnh từ nguồn công khai"})

    assert point["is_synthetic"] is True
    assert point["data_kind"] == "Hiệu chỉnh"


def test_direct_scrape_prices_remain_observed():
    point = DataLoader._row_to_point({"exchange_source": "Sở Công Thương Đắk Lắk"})

    assert point["is_synthetic"] is False
    assert point["data_kind"] == "Quan sát"
