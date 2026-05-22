from datetime import UTC, datetime

from app.ingestion.sources.banggianongsan import BangGiaNongSanScraper
from app.ingestion.sources.baohatinh import BaoHaTinhScraper
from app.ingestion.sources.baonghean import BaoNgheAnScraper
from app.ingestion.sources.fertilizer_vietnga import VietNgaFertilizerPriceScraper, classify_fertilizer_product
from app.ingestion.sources.socongthuong_daklak import SoCongThuongDakLakScraper


def test_banggianongsan_parser_extracts_varieties_provinces_and_markets():
    html = """
    <html><body>
    <h2>Bảng giá sầu riêng mới nhất - 28/04/2026</h2>
    <h3>Bảng giá chi tiết (cập nhật gần nhất)</h3>
    Sầu riêng Ri6 A (đ/kg) 80.000 – 86.000 80.000 – 86.000 Không đổi
    Sầu riêng Thái VIP A (đ/kg) 120.000 – 130.000 120.000 – 130.000 Không đổi
    Sầu riêng Musang King B (đ/kg) 105.000 – 120.000 105.000 – 120.000 Không đổi
    So sánh nhanh
    <h3>Giá theo từng tỉnh</h3>
    Cần Thơ: 65.000 – 95.000 VND/kg
    Tiền Giang: 70.000 – 100.000 VND/kg
    <h3>Giá tại các chợ đầu mối</h3>
    Thủ Đức 70.000 – 100.000 90.000 – 120.000 Nguồn hàng lớn
    </body></html>
    """
    result = BangGiaNongSanScraper().parse(html)

    assert len(result.observations) >= 6
    assert any(item.variety_name == "Ri6" and item.quality_grade == "Loại A" for item in result.observations)
    assert any(item.province == "Tiền Giang" for item in result.observations)
    assert any(item.province == "Thủ Đức" and item.variety_name == "Sầu Thái Monthong" for item in result.observations)


def test_baonghean_parser_extracts_region_variety_matrix():
    html = """
    <html><body>
    <h1>Giá sầu riêng hôm nay 17/4/2026: RI6 giữ mức 60.000 đồng</h1>
    Khu vực / Loại sầu riêng Giá ngày 17/4 (đồng/kg)
    Tây Nam Bộ RI6 đẹp lựa 55.000 - 60.000 RI6 xô 25.000 - 28.000
    Sầu Thái đẹp lựa 85.000 - 90.000 Sầu Thái xô 45.000 - 50.000
    Đông Nam Bộ RI6 đẹp lựa 55.000 - 60.000 RI6 xô 25.000 - 30.000
    Sầu Thái đẹp lựa 75.000 - 85.000 Sầu Thái xô 40.000 - 50.000
    Tây Nguyên RI6 đẹp lựa 52.000 - 54.000 RI6 xô 25.000 - 30.000
    Sầu Thái đẹp lựa 72.000 - 74.000 Sầu Thái xô 32.000 - 35.000
    </body></html>
    """
    result = BaoNgheAnScraper().parse(html)

    assert len(result.observations) == 12
    assert any(
        item.region_name == "Tây Nguyên"
        and item.variety_name == "Sầu Thái Dona"
        and item.quality_grade == "Hàng xô"
        and item.max_price_vnd == 35000
        for item in result.observations
    )


def test_socongthuong_daklak_parser_extracts_more_varieties():
    html = """
    <html><body>
    <h1>Bảng giá nông sản ngày 23/4/2026</h1>
    GIÁ SẦU RIÊNG TRONG NƯỚC
    Sầu riêng Ri6 A (đ/kg) 80.000 – 86.000 Không đổi
    Sầu riêng Thái VIP A (đ/kg) 120.000 – 130.000 Không đổi
    Sầu riêng Musang King A (đ/kg) 170.000 – 180.000 Không đổi
    Sầu riêng Chuồng Bò A (đ/kg) 70.000 – 75.000 Không đổi
    GIÁ BƠ TRONG NƯỚC
    </body></html>
    """
    result = SoCongThuongDakLakScraper().parse(html)

    assert len(result.observations) == 4
    assert any(item.variety_name == "Sầu Musang King" for item in result.observations)
    assert any(item.variety_name == "Sầu Chuồng Bò" for item in result.observations)


def test_baohatinh_parser_expands_region_prices_to_provinces():
    html = """
    <html><body>
    Giá sầu riêng hôm nay 17/3/2026
    Bảng giá sầu riêng hôm nay 17/3/2026
    Tây Nam Bộ RI6 Loại 1 55.000 – 60.000 Hàng xô 25.000 – 28.000
    Sầu riêng Thái Hàng tuyển 85.000 – 90.000 Hàng xô 45.000 – 50.000
    Đông Nam Bộ RI6 Loại đẹp 55.000 – 60.000 Hàng xô 25.000 – 30.000
    Sầu riêng Thái Loại tuyển 75.000 – 85.000 Hàng xô 40.000 – 50.000
    Tây Nguyên RI6 Đạt chuẩn 52.000 – 54.000 Hàng xô 25.000 – 30.000
    Sầu riêng Thái Hàng tuyển 72.000 – 74.000 Hàng xô 32.000 – 35.000
    </body></html>
    """
    result = BaoHaTinhScraper().parse(html)

    assert len(result.observations) == 48
    assert any(
        item.province == "Đồng Nai"
        and item.variety_name == "Ri6"
        and item.quality_grade == "Loại A"
        and item.max_price_vnd == 60000
        for item in result.observations
    )
    assert any(item.province == "Gia Lai" and item.variety_name == "Sầu Thái Dona" for item in result.observations)


def test_vietnga_fertilizer_parser_extracts_current_price_rows():
    html = """
    <div class="table-row heading-row">
      <div class="table-cell">STT</div><div class="table-cell">Hình ảnh</div>
      <div class="table-cell">Tên sản phẩm</div><div class="table-cell">Miền Tây</div>
    </div>
    <div class="table-row">
      <div class="table-cell">1</div><div class="table-cell"></div>
      <div class="table-cell">Ure Cà Mau</div>
      <div class="table-cell"><div class="sub-cells"><div class="table-cell sub-cell"><span class="show-tablet">Miền Tây</span>935.000 - 985.000</div></div></div>
    </div>
    <div class="table-row">
      <div class="table-cell">2</div><div class="table-cell"></div>
      <div class="table-cell">DAP Đình Vũ (hạt xanh)</div>
      <div class="table-cell"><div class="sub-cells"><div class="table-cell sub-cell"><span class="show-tablet">Miền Tây</span>1.075.000 - 1.125.000</div></div></div>
    </div>
    <div class="table-row">
      <div class="table-cell">3</div><div class="table-cell"></div>
      <div class="table-cell">NPK Bình Điền 20-20-15</div>
      <div class="table-cell"><div class="sub-cells"><div class="table-cell sub-cell"><span class="show-tablet">Miền Tây</span>1.030.000 - 1.080.000</div></div></div>
    </div>
    """
    result = VietNgaFertilizerPriceScraper().parse_table(html, observed_at=datetime(2026, 5, 20, tzinfo=UTC))

    assert len(result) == 3
    assert result[0].product_slug == "ure"
    assert result[0].brand == "Cà Mau"
    assert result[0].package_price_vnd == 960000
    assert result[1].product_slug == "dap"
    assert result[1].brand == "Đình Vũ"
    assert result[2].product_slug == "npk-20-20-15"
    assert result[2].brand == "Bình Điền"


def test_vietnga_fertilizer_classifier_normalizes_common_products():
    assert classify_fertilizer_product("Kali Canada Hạt Miểng 60%")["slug"] == "kali-mop"
    assert classify_fertilizer_product("Lân LT (hạt)")["brand"] == "Lâm Thao"
    assert classify_fertilizer_product("NPK Việt Nhật 16-16-8-13S")["brand"] == "Việt Nhật"
