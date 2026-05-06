import os

os.environ["MARKETAI_DATABASE_URL"] = "sqlite:///:memory:"
os.environ["MARKETAI_START_SCHEDULER_IN_API"] = "false"

from fastapi.testclient import TestClient
import pytest

from app.main import app


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_historical_prices_returns_seeded_points(client):
    response = client.get("/api/v1/analytics/historical-prices?region_id=1&variety=1&limit=5")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 5
    assert payload[0]["max_price_vnd"] > 0


def test_regions_metadata_only_returns_production_locations(client):
    response = client.get("/api/v1/metadata/regions")
    assert response.status_code == 200
    payload = response.json()
    labels = {row["province"] or row["region_name"] for row in payload}
    assert "Thủ Đức" not in labels
    assert "Bình Điền" not in labels
    assert "Thị trường Việt Nam" not in labels
    assert "Đồng Tháp" in labels
    assert "Tiền Giang" not in labels
    assert "Đắk Lắk" in labels


def test_forecast_returns_30_days(client):
    response = client.get("/api/v1/analytics/forecast-30-days?region_id=1&variety=1")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 30
    assert payload[0]["forecast_price_vnd"] > 0


def test_sensor_webhook_persists_payload(client):
    response = client.post(
        "/api/v1/sensors/maturity-telemetry",
        headers={"x-api-key": "marketai-iot-dev-key"},
        json={
            "device_id": "T-Abyss-001",
            "region_id": 1,
            "maturity_index": 8.2,
            "status": "Sẵn sàng thu hoạch",
            "timestamp": "2026-04-28T09:10:00Z",
        },
    )
    assert response.status_code == 201
    assert response.json()["id"] > 0


def test_auth_and_watchlist_flow(client, test_password):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "farmer@example.com", "password": test_password, "display_name": "Farmer"},
    )
    assert response.status_code == 201
    token = response.json()["access_token"]

    response = client.post(
        "/api/v1/watchlist",
        headers={"Authorization": f"Bearer {token}"},
        json={"crop_type": "sau_rieng", "region_id": 1, "variety_id": 1, "label": "Tiền Giang - Ri6"},
    )
    assert response.status_code == 201

    response = client.get("/api/v1/watchlist", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()[0]["label"] == "Tiền Giang - Ri6"


def test_public_api_requires_key(client):
    response = client.get("/api/v1/public/prices?region_id=1&variety_id=1&limit=2")
    assert response.status_code == 401

    response = client.get(
        "/api/v1/public/prices?region_id=1&variety_id=1&limit=2",
        headers={"x-api-key": "marketai-public-demo-key"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_admin_endpoints_reject_anonymous_and_non_admin_users(client, test_password):
    anonymous = client.post("/api/v1/ingestion/scrape-prices")
    assert anonymous.status_code == 401
    anonymous_runs = client.get("/api/v1/ingestion/scrape-runs")
    assert anonymous_runs.status_code == 401

    response = client.post(
        "/api/v1/auth/register",
        json={"email": "viewer@example.com", "password": test_password, "display_name": "Viewer"},
    )
    assert response.status_code == 201
    token = response.json()["access_token"]

    protected_routes = [
        "/api/v1/content/news/scrape",
        "/api/v1/platform/jobs/scrape",
        "/api/v1/platform/jobs/data-quality",
        "/api/v1/platform/jobs/news",
        "/api/v1/platform/jobs/retrain",
        "/api/v1/ingestion/backfill-model-ready",
    ]
    for route in protected_routes:
        response = client.post(route, headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 403

    response = client.get("/api/v1/ingestion/scrape-runs", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


def test_sensor_webhook_requires_iot_key(client):
    response = client.post(
        "/api/v1/sensors/maturity-telemetry",
        json={
            "device_id": "T-Abyss-002",
            "region_id": 1,
            "maturity_index": 7.4,
            "timestamp": "2026-04-28T09:10:00Z",
        },
    )
    assert response.status_code == 401


def test_image_proxy_blocks_private_or_untrusted_hosts(client):
    response = client.get("/api/v1/content/image-proxy?url=http://127.0.0.1/test.jpg")
    assert response.status_code == 403


def test_excel_and_pdf_exports(client):
    xlsx = client.get("/api/v1/analytics/export.xlsx?region_id=1&variety=1")
    pdf = client.get("/api/v1/analytics/export.pdf?region_id=1&variety=1")

    assert xlsx.status_code == 200
    assert xlsx.content.startswith(b"PK")
    assert pdf.status_code == 200
    assert pdf.content.startswith(b"%PDF")


def test_content_portal_returns_news_and_guides(client):
    news = client.get("/api/v1/content/news")
    guides = client.get("/api/v1/content/guides?crop=sau_rieng")

    assert news.status_code == 200
    assert news.json()[0]["source_url"].startswith("https://")
    assert guides.status_code == 200
    assert any("sầu riêng" in item["title"].lower() for item in guides.json())


def test_news_filter_rejects_offtopic_finance_and_electricity():
    from datetime import UTC, datetime

    from app.models import NewsArticle
    from app.services.content_portal import _is_keepable_news_article

    now = datetime.now(UTC)
    off_topic_rows = [
        NewsArticle(
            source_name="Báo Nông nghiệp và Môi trường",
            source_url="https://nongnghiepmoitruong.vn/quy-i-2026-mb-bao-lai-hon-9600-ty-dong-d809001.html",
            title="Quý I/2026: MB báo lãi hơn 9.600 tỷ đồng",
            summary="Ngân hàng ghi nhận lợi nhuận tăng trong quý I.",
            excerpt="Ngân hàng ghi nhận lợi nhuận tăng trong quý I.",
            category="Ảnh hưởng giá",
            image_url=None,
            published_at=now,
            scraped_at=now,
        ),
        NewsArticle(
            source_name="Báo Nông nghiệp và Môi trường",
            source_url="https://nongnghiepmoitruong.vn/evn-dam-bao-cung-ung-dien-dip-nghi-le-30-4--1-5-d809053.html",
            title="EVN đảm bảo cung ứng điện dịp nghỉ lễ 30/4 - 1/5",
            summary="Ngành điện lên kế hoạch cung ứng điện cho kỳ nghỉ lễ.",
            excerpt="Ngành điện lên kế hoạch cung ứng điện cho kỳ nghỉ lễ.",
            category="Ảnh hưởng giá",
            image_url=None,
            published_at=now,
            scraped_at=now,
        ),
    ]

    assert all(not _is_keepable_news_article(row) for row in off_topic_rows)


def test_news_filter_keeps_agricultural_market_news():
    from datetime import UTC, datetime

    from app.models import NewsArticle
    from app.services.content_portal import _is_keepable_news_article

    now = datetime.now(UTC)
    rows = [
        NewsArticle(
            source_name="Báo Nông nghiệp và Môi trường",
            source_url="https://nongnghiepmoitruong.vn/xuat-khau-ca-phe-viet-nam-tang-manh-d809101.html",
            title="Xuất khẩu cà phê Việt Nam tăng mạnh trong tháng 4",
            summary="Giá cà phê và nhu cầu nhập khẩu từ châu Âu tiếp tục nâng sức mua.",
            excerpt="Giá cà phê và nhu cầu nhập khẩu từ châu Âu tiếp tục nâng sức mua.",
            category="Xuất khẩu",
            image_url=None,
            published_at=now,
            scraped_at=now,
        ),
        NewsArticle(
            source_name="Báo Công Thương",
            source_url="https://congthuong.vn/gia-phan-bon-va-vat-tu-nong-nghiep-can-duoc-theo-doi-809102.html",
            title="Giá phân bón và vật tư nông nghiệp cần được theo dõi sát",
            summary="Chi phí đầu vào thay đổi có thể ảnh hưởng đến kế hoạch mùa vụ.",
            excerpt="Chi phí đầu vào thay đổi có thể ảnh hưởng đến kế hoạch mùa vụ.",
            category="Phân bón - vật tư",
            image_url=None,
            published_at=now,
            scraped_at=now,
        ),
    ]

    assert all(_is_keepable_news_article(row) for row in rows)
