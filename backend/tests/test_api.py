from copy import deepcopy
from datetime import UTC, datetime, timedelta
import os

os.environ["MARKETAI_DATABASE_URL"] = "sqlite:///:memory:"
os.environ["MARKETAI_START_SCHEDULER_IN_API"] = "false"

from fastapi.testclient import TestClient
import pytest

from app.db import SessionLocal
from app.main import app
from app.models import AppUser, RevokedToken
from app.services.auth import create_access_token, hash_password


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


def create_user_token(email: str, password: str = "StrongPass123", *, is_admin: bool = False) -> tuple[str, int]:
    with SessionLocal() as db:
        user = AppUser(
            email=email,
            display_name=email.split("@", 1)[0],
            password_hash=hash_password(password),
            created_at=datetime.now(UTC),
            is_admin=is_admin,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return create_access_token(user), user.user_id


FERTILIZER_RECOMMENDATION_PAYLOAD = {
    "crop": "robusta_coffee",
    "growth_stage": "mature_kinh_doanh",
    "yield_target_t_ha": 3.5,
    "tree_density_per_ha": 1100,
    "soil": {
        "texture": "basaltic_red",
        "ph_kcl": 4.3,
        "organic_carbon_pct": 2.8,
        "total_n_pct": 0.18,
        "available_p_method": "bray_ii",
        "available_p_mg_per_100g": 4.5,
        "exchangeable_k_method": "nh4oac",
        "exchangeable_k2o_mg_per_100g": 12,
        "cec_cmolc_per_kg": 8,
        "sample_depth_cm": 30,
        "sample_date": "2026-05-21",
    },
    "location": {"province": "Dak Lak"},
    "climate": {"annual_rainfall_mm": 1900, "irrigation_available": True},
    "field": {"slope_pct": 5, "years_under_current_crop": 10},
    "preferences": {"language": "vi", "include_product_mix": True},
}


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
    assert payload[0]["model_kind"] == "baseline-statistical"


def test_input_price_endpoints_return_fertilizer_data(client):
    products = client.get("/api/v1/input-prices/products?category=fertilizer")
    assert products.status_code == 200
    product_payload = products.json()
    assert any(item["slug"] == "ure" for item in product_payload)

    latest = client.get("/api/v1/input-prices/latest?category=fertilizer&product_slug=ure&province=Đắk Lắk")
    assert latest.status_code == 200
    latest_payload = latest.json()
    assert latest_payload
    assert latest_payload[0]["product_slug"] == "ure"
    assert latest_payload[0]["package_price_vnd"] > 0
    assert latest_payload[0]["normalized_price_vnd"] > 0

    history = client.get("/api/v1/input-prices/history?product_slug=ure&province=Đắk Lắk&months=12")
    assert history.status_code == 200
    assert len(history.json()) >= 12

    forecast = client.get("/api/v1/input-prices/forecast?product_slug=ure&province=Đắk Lắk&days=30")
    assert forecast.status_code == 200
    forecast_payload = forecast.json()
    assert len(forecast_payload) == 30
    assert forecast_payload[0]["model_kind"] == "input-price-baseline-v1"


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


def test_fertilizer_recommendation_requires_login(client, test_password):
    response = client.post("/api/v1/fertilizer/recommend", json=FERTILIZER_RECOMMENDATION_PAYLOAD)
    assert response.status_code == 401

    response = client.post(
        "/api/v1/auth/register",
        json={"email": "fertilizer@example.com", "password": test_password, "display_name": "Fertilizer User"},
    )
    assert response.status_code == 201
    token = response.json()["access_token"]

    response = client.post(
        "/api/v1/fertilizer/recommend",
        headers={"Authorization": f"Bearer {token}"},
        json=FERTILIZER_RECOMMENDATION_PAYLOAD,
    )
    assert response.status_code == 200
    payload = response.json()
    assert "recommendation" in payload
    assert len(payload["session_id"]) == 36
    assert len(payload["session_code"]) == 8

    feedback = client.post(
        f"/api/v1/sessions/{payload['session_code']}/feedback",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "actual_yield_t_ha": 3.8,
            "harvest_date": "2026-12-10",
            "fertilizer_followed_pct": 85,
            "rating": 4,
            "note": "Vườn làm theo phần lớn khuyến nghị.",
        },
    )
    assert feedback.status_code == 201
    assert feedback.json()["session_code"] == payload["session_code"]


def test_yield_feedback_requires_auth_and_owner(client):
    owner_token, _ = create_user_token("feedback-owner@example.com")
    other_token, _ = create_user_token("feedback-other@example.com")

    recommendation = client.post(
        "/api/v1/fertilizer/recommend",
        headers={"Authorization": f"Bearer {owner_token}"},
        json=FERTILIZER_RECOMMENDATION_PAYLOAD,
    )
    assert recommendation.status_code == 200
    session_code = recommendation.json()["session_code"]

    payload = {
        "actual_yield_t_ha": 3.6,
        "harvest_date": "2026-12-15",
        "fertilizer_followed_pct": 90,
        "rating": 5,
        "contact_phone": "0912345678",
    }

    anonymous = client.post(f"/api/v1/sessions/{session_code}/feedback", json=payload)
    assert anonymous.status_code == 401

    other_user = client.post(
        f"/api/v1/sessions/{session_code}/feedback",
        headers={"Authorization": f"Bearer {other_token}"},
        json=payload,
    )
    assert other_user.status_code == 403

    wildcard = client.post(
        f"/api/v1/sessions/{session_code[:7]}_/feedback",
        headers={"Authorization": f"Bearer {owner_token}"},
        json=payload,
    )
    assert wildcard.status_code == 404

    owner = client.post(
        f"/api/v1/sessions/{session_code}/feedback",
        headers={"Authorization": f"Bearer {owner_token}"},
        json=payload,
    )
    assert owner.status_code == 201


def test_login_lockout_after_5_failed_attempts(client):
    create_user_token("lockout@example.com", "CorrectPass123")
    for _ in range(5):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "lockout@example.com", "password": "wrong-password"},
        )
        assert response.status_code == 401

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "lockout@example.com", "password": "CorrectPass123"},
    )
    assert response.status_code == 429


def test_logout_revokes_token_and_cleanup_job(client):
    token, user_id = create_user_token("logout@example.com")
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 200

    logout = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert logout.status_code == 204
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401

    admin_token, _ = create_user_token("cleanup-admin@example.com", is_admin=True)
    with SessionLocal() as db:
        db.add(
            RevokedToken(
                jti="expired-test-token",
                user_id=user_id,
                revoked_at=datetime.now(UTC) - timedelta(days=2),
                expires_at=datetime.now(UTC) - timedelta(days=1),
            )
        )
        db.commit()

    cleanup = client.post(
        "/api/v1/platform/jobs/revoked-token-cleanup",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert cleanup.status_code == 200
    assert cleanup.json()["deleted"] >= 1


def test_fertilizer_tier1_agronomy_rules():
    from app.services.fertilizer_engine import recommend

    coffee = recommend(deepcopy(FERTILIZER_RECOMMENDATION_PAYLOAD))
    coffee_splits = coffee["recommendation"]["splits"]
    assert sum(item["n_pct"] for item in coffee_splits) == 100
    assert sum(item["p2o5_pct"] for item in coffee_splits) == 100
    assert sum(item["k2o_pct"] for item in coffee_splits) == 100
    post_harvest = coffee_splits[0]
    assert post_harvest["calendar_window"] == "Tháng 1-2"
    assert (post_harvest["n_pct"], post_harvest["p2o5_pct"], post_harvest["k2o_pct"]) == (15, 50, 15)
    assert coffee["confidence"]["calibration_tier"] == "high"
    assert coffee["confidence"]["badge_vi"] == "Đã hiệu chuẩn"

    durian = deepcopy(FERTILIZER_RECOMMENDATION_PAYLOAD)
    durian.update({"crop": "durian", "variety": "Ri6", "yield_target_t_ha": 25, "tree_density_per_ha": 150})
    durian["soil"]["texture"] = "basaltic_red"
    durian["soil"]["available_p_mg_per_kg"] = 18
    durian_result = recommend(durian)
    durian_total = durian_result["recommendation"]["annual_total"]
    assert durian_total["n_kg_ha"] <= 300
    assert durian_total["p2o5_kg_ha"] <= 200
    assert durian_total["k2o_kg_ha"] <= 250
    assert durian_result["confidence"]["calibration_tier"] == "low"
    assert durian_result["confidence"]["badge_vi"] == "Tham chiếu quốc tế"
    assert all("WASI 2025" not in item["title"] for item in durian_result["rationale"]["sources_cited"])

    pepper = deepcopy(FERTILIZER_RECOMMENDATION_PAYLOAD)
    pepper.update({"crop": "black_pepper", "yield_target_t_ha": 3, "tree_density_per_ha": 1600})
    pepper["soil"]["texture"] = "basaltic_red"
    pepper["soil"]["available_p_mg_per_100g"] = None
    pepper["soil"]["available_p_mg_per_kg"] = 110
    pepper_result = recommend(pepper)
    assert pepper_result["recommendation"]["annual_total"]["p2o5_kg_ha"] == 0
    assert any(warning["code"] == "PEPPER_P_EXCESS" for warning in pepper_result["warnings"])
    assert pepper_result["confidence"]["calibration_tier"] == "medium"

    fruit_fill = deepcopy(durian)
    fruit_fill["growth_stage"] = "fruit_fill"
    fruit_fill["preferences"] = {"language": "vi", "include_product_mix": True, "preferred_k_source": "kcl"}
    fruit_fill_result = recommend(fruit_fill)
    fruit_fill_products = fruit_fill_result["recommendation"]["product_mix_options"][0]["products"]
    assert any(product["sku"] == "phu_my_k2so4_50" for product in fruit_fill_products)
    assert any(warning["code"] == "DURIAN_NO_KCL_FRUIT_FILL" for warning in fruit_fill_result["warnings"])

    fruit_set = deepcopy(durian)
    fruit_set["growth_stage"] = "fruit_set"
    fruit_set["preferences"] = {"language": "vi", "include_product_mix": True, "preferred_k_source": "kcl"}
    fruit_set_result = recommend(fruit_set)
    fruit_set_products = fruit_set_result["recommendation"]["product_mix_options"][0]["products"]
    assert any(product["sku"] == "phu_my_kcl_60" for product in fruit_set_products)
    assert not any(warning["code"] == "DURIAN_NO_KCL_FRUIT_FILL" for warning in fruit_set_result["warnings"])


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
        "/api/v1/platform/jobs/yield-feedback-reminder",
        "/api/v1/platform/jobs/revoked-token-cleanup",
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
    response = client.get("/api/v1/content/image-proxy?url=https://attacker.com/test.jpg")
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


def test_sitemap_includes_static_seo_routes(client):
    response = client.get("/api/v1/sitemap.xml")
    assert response.status_code == 200
    body = response.text
    assert "https://dubaonongsan.com/khuyen-nghi-bon-phan" in body
    assert "https://dubaonongsan.com/khuyen-nghi-bon-phan/logic" in body
    assert "https://dubaonongsan.com/bao-cao-nang-suat" in body


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
